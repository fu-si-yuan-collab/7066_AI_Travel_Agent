"""Preference learning service.
把用户交互与显式设置转化为 learned_tags，供推荐排序实时使用。
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import InteractionEvent
from app.models.preference import UserPreference


_EVENT_DELTA = {
    "exposure": 0.02,
    "click": 0.20,
    "save": 0.45,
    "add_to_trip": 0.60,
    "final_adopt": 0.95,
    "delete": -0.65,
    "chat_submit": 0.03,
    "chat_response": 0.01,
    "feedback:like": 0.90,
    "feedback:dislike": -0.90,
    "feedback:not_relevant": -1.00,
}

_DECAY_PER_DAY = 0.985
_NOISE_FLOOR = 0.06
_MAX_TAGS = 64


def _tokenize(text: str, max_tokens: int = 5) -> list[str]:
    text = (text or "").lower()
    ascii_tokens = re.findall(r"[a-z0-9_]{2,}", text)
    zh_tokens = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    tokens = ascii_tokens + zh_tokens
    return tokens[:max_tokens]


def _clip(v: float, lo: float = -3.0, hi: float = 6.0) -> float:
    return max(lo, min(hi, v))


def _apply_time_decay(learned: dict[str, float], last_updated_at) -> dict[str, float]:
    if not learned or not last_updated_at:
        return learned

    now = datetime.now(timezone.utc)
    elapsed_days = max(0.0, (now - last_updated_at).total_seconds() / 86400)
    if elapsed_days <= 0:
        return learned

    factor = _DECAY_PER_DAY ** elapsed_days
    return {k: round(v * factor, 4) for k, v in learned.items()}


def _normalize_learned_tags(learned: dict[str, float]) -> dict[str, float]:
    if not learned:
        return {}

    # 去噪：去掉接近 0 的弱信号。
    cleaned = {k: float(v) for k, v in learned.items() if abs(float(v)) >= _NOISE_FLOOR}
    if not cleaned:
        return {}

    # 只保留最显著的标签，避免长期累积噪声。
    top_items = sorted(cleaned.items(), key=lambda item: abs(item[1]), reverse=True)[:_MAX_TAGS]
    cleaned = dict(top_items)

    # 归一化：控制 learned_tags 的数值范围，避免单个标签无限放大。
    max_abs = max(abs(v) for v in cleaned.values()) or 1.0
    scale = max(1.0, max_abs / 3.0)
    return {k: round(_clip(v / scale, -3.0, 3.0), 4) for k, v in cleaned.items()}


async def _get_repeat_count(
    db: AsyncSession,
    *,
    user_id: str,
    event_type: str,
    item_id: str,
) -> int:
    if not item_id:
        return 0

    result = await db.execute(
        select(InteractionEvent.id)
        .where(
            InteractionEvent.user_id == user_id,
            InteractionEvent.event_type == event_type,
            InteractionEvent.item_id == item_id,
        )
    )
    return len(result.all())


def _damped_delta(delta: float, repeat_count: int) -> float:
    # 重复点击不再线性累积，随着次数增加边际收益迅速下降。
    if repeat_count <= 1:
        return delta
    return delta / math.sqrt(repeat_count)


async def _get_or_create_preferences(db: AsyncSession, user_id: str) -> UserPreference:
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = UserPreference(user_id=user_id)
        db.add(pref)
        await db.flush()
    return pref


async def learn_from_interaction(
    db: AsyncSession,
    *,
    user_id: str,
    event_type: str,
    feedback_label: str = "",
    item_type: str = "",
    item_id: str = "",
    item_title: str = "",
    destination: str = "",
    metadata_json: dict | None = None,
) -> None:
    """根据行为事件更新 learned_tags。"""
    pref = await _get_or_create_preferences(db, user_id)
    learned = _apply_time_decay(dict(pref.learned_tags or {}), pref.updated_at)

    key = f"feedback:{feedback_label}" if event_type == "feedback" and feedback_label else event_type
    delta = _EVENT_DELTA.get(key, 0.02)
    repeat_count = await _get_repeat_count(db, user_id=user_id, event_type=event_type, item_id=item_id)
    delta = _damped_delta(delta, repeat_count)

    tags: set[str] = set()
    if destination:
        tags.add(f"dest:{destination.strip().lower()}")
    if item_type:
        tags.add(f"type:{item_type.strip().lower()}")
    for t in _tokenize(item_title):
        tags.add(f"kw:{t}")

    if metadata_json:
        for k in ("platform", "type", "cuisine", "travel_style"):
            v = metadata_json.get(k)
            if isinstance(v, str) and v.strip():
                tags.add(f"{k}:{v.strip().lower()}")

    if not tags:
        tags.add("generic:interaction")

    for tag in tags:
        old = float(learned.get(tag, 0.0))
        learned[tag] = round(_clip(old + delta), 4)

    pref.learned_tags = _normalize_learned_tags(learned)
    await db.commit()


async def learn_from_explicit_preferences(
    db: AsyncSession,
    *,
    user_id: str,
    pref_update: dict,
) -> None:
    """把用户在 Preferences 页显式保存的设置同步到 learned_tags。"""
    if not pref_update:
        return

    pref = await _get_or_create_preferences(db, user_id)
    learned = _apply_time_decay(dict(pref.learned_tags or {}), pref.updated_at)

    style = pref_update.get("preferred_travel_style")
    if isinstance(style, str) and style:
        learned[f"style:{style.lower()}"] = round(_clip(float(learned.get(f"style:{style.lower()}", 0.0)) + 1.5), 4)

    transport = pref_update.get("preferred_transport")
    if isinstance(transport, str) and transport:
        learned[f"transport:{transport.lower()}"] = round(_clip(float(learned.get(f"transport:{transport.lower()}", 0.0)) + 1.0), 4)

    stars = pref_update.get("preferred_hotel_stars")
    if stars is not None:
        try:
            s = int(round(float(stars)))
            learned[f"stars:{s}"] = round(_clip(float(learned.get(f"stars:{s}", 0.0)) + 1.3), 4)
        except Exception:
            pass

    cuisine = pref_update.get("preferred_cuisine")
    if isinstance(cuisine, str) and cuisine.strip():
        for c in [x.strip().lower() for x in cuisine.split(",") if x.strip()]:
            tag = f"cuisine:{c}"
            learned[tag] = round(_clip(float(learned.get(tag, 0.0)) + 1.2), 4)

    high = pref_update.get("daily_budget_high")
    if high is not None:
        try:
            h = float(high)
            bucket = "budget:low" if h <= 400 else "budget:mid" if h <= 1200 else "budget:high"
            learned[bucket] = round(_clip(float(learned.get(bucket, 0.0)) + 1.0), 4)
        except Exception:
            pass

    pref.learned_tags = _normalize_learned_tags(learned)
    await db.commit()
