"""Interaction event repository.
行为日志仓储：记录事件，并提供 baseline 协同过滤所需统计。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import InteractionEvent


POSITIVE_EVENTS = {"click", "save", "add_to_trip", "final_adopt", "like"}
NEGATIVE_EVENTS = {"dislike", "not_relevant"}

EVENT_ALIASES = {
    "mark_adopted": "final_adopt",
    "adopt": "final_adopt",
    "favorite": "save",
    "bookmark": "save",
    "open": "click",
}

VALID_EVENT_TYPES = {
    "exposure",
    "click",
    "save",
    "add_to_trip",
    "final_adopt",
    "delete",
    "feedback",
    "chat_submit",
    "chat_response",
}

_BASE_EVENT_WEIGHT = {
    "exposure": 0.08,
    "click": 0.35,
    "save": 0.7,
    "add_to_trip": 1.0,
    "final_adopt": 1.5,
    "feedback:like": 1.3,
    "feedback:dislike": -1.1,
    "feedback:not_relevant": -1.25,
    "delete": -0.9,
}
_DECAY_PER_DAY = 0.985


def _time_decay(created_at) -> float:
    if not created_at:
        return 1.0
    elapsed_days = max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds() / 86400)
    return _DECAY_PER_DAY ** elapsed_days


def _event_weight(event_type: str, feedback_label: str) -> float:
    key = f"feedback:{feedback_label}" if event_type == "feedback" and feedback_label else event_type
    return _BASE_EVENT_WEIGHT.get(key, 0.0)


def _normalize_score(raw: float) -> float:
    if raw == 0:
        return 0.0
    return math.tanh(raw / 2.5) * 2.5


def _canonical_event_type(event_type: str) -> str:
    raw = (event_type or "").strip().lower()
    canonical = EVENT_ALIASES.get(raw, raw)
    return canonical if canonical in VALID_EVENT_TYPES else "exposure"


def _canonical_feedback_label(feedback_label: str) -> str:
    value = (feedback_label or "").strip().lower()
    if value in {"like", "dislike", "not_relevant"}:
        return value
    return ""


def _enrich_metadata(metadata_json: dict | None, *, event_type: str, session_id: str) -> dict:
    now = datetime.now(timezone.utc)
    metadata: dict = dict(metadata_json or {})
    metadata.setdefault("schema_version", "interaction/v2")
    metadata.setdefault("server_timestamp", now.isoformat())
    metadata.setdefault("hour_of_day", now.hour)
    metadata.setdefault("day_of_week", now.weekday())
    metadata.setdefault("event_type_canonical", event_type)
    metadata.setdefault("has_session", bool(session_id))
    return metadata


async def log_interaction_event(
    db: AsyncSession,
    user_id: str,
    *,
    event_type: str,
    item_type: str,
    item_id: str,
    session_id: str = "",
    feedback_label: str = "",
    item_title: str = "",
    destination: str = "",
    travel_style: str = "",
    budget: float = 0.0,
    currency: str = "CNY",
    metadata_json: dict | None = None,
) -> InteractionEvent:
    canonical_event_type = _canonical_event_type(event_type)
    canonical_feedback_label = _canonical_feedback_label(feedback_label)
    event = InteractionEvent(
        user_id=user_id,
        session_id=session_id,
        event_type=canonical_event_type,
        feedback_label=canonical_feedback_label,
        item_type=item_type,
        item_id=item_id,
        item_title=item_title,
        destination=destination,
        travel_style=travel_style,
        budget=budget,
        currency=currency,
        metadata_json=_enrich_metadata(
            metadata_json,
            event_type=canonical_event_type,
            session_id=session_id,
        ),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_user_item_affinity(
    db: AsyncSession,
    user_id: str,
    item_type: str,
) -> dict[str, float]:
    """计算用户对某类 item 的简单偏好分。"""
    result = await db.execute(
        select(InteractionEvent.item_id, InteractionEvent.event_type, InteractionEvent.feedback_label, InteractionEvent.created_at)
        .where(InteractionEvent.user_id == user_id, InteractionEvent.item_type == item_type)
    )
    scores: dict[str, float] = defaultdict(float)
    for item_id, event_type, feedback_label, created_at in result.all():
        weight = _event_weight(event_type, feedback_label)
        if weight == 0:
            continue
        scores[item_id] += weight * _time_decay(created_at)
    return {item_id: round(_normalize_score(score), 4) for item_id, score in scores.items()}


async def get_neighbor_item_scores(
    db: AsyncSession,
    user_id: str,
    item_type: str,
    seed_item_ids: list[str],
) -> dict[str, float]:
    """简化协同过滤：找与当前用户有共同正反馈的邻居，再聚合其偏好。"""
    if not seed_item_ids:
        return {}

    seed_result = await db.execute(
        select(InteractionEvent.user_id, InteractionEvent.item_id, InteractionEvent.event_type, InteractionEvent.feedback_label, InteractionEvent.created_at)
        .where(InteractionEvent.item_type == item_type, InteractionEvent.item_id.in_(seed_item_ids))
    )
    neighbors: set[str] = set()
    for other_user_id, _item_id, event_type, feedback_label, _created_at in seed_result.all():
        if other_user_id == user_id:
            continue
        if _event_weight(event_type, feedback_label) > 0:
            neighbors.add(other_user_id)

    if not neighbors:
        return {}

    neighbor_events = await db.execute(
        select(InteractionEvent.user_id, InteractionEvent.item_id, InteractionEvent.event_type, InteractionEvent.feedback_label, InteractionEvent.created_at)
        .where(InteractionEvent.user_id.in_(neighbors), InteractionEvent.item_type == item_type)
    )

    counts: dict[str, float] = defaultdict(float)
    for _other_user_id, item_id, event_type, feedback_label, created_at in neighbor_events.all():
        if item_id in seed_item_ids:
            continue
        weight = _event_weight(event_type, feedback_label)
        if weight <= 0:
            continue
        counts[item_id] += weight * _time_decay(created_at)

    denom = max(1, len(neighbors))
    return {k: round(_normalize_score(v / denom), 4) for k, v in counts.items()}


async def get_destination_popularity_scores(
    db: AsyncSession,
    destination: str,
    item_type: str,
) -> dict[str, float]:
    """按目的地统计 item 热度（用于 baseline 的 popularity 信号）。"""
    if not destination:
        return {}
    result = await db.execute(
        select(InteractionEvent.item_id, InteractionEvent.event_type, InteractionEvent.feedback_label, InteractionEvent.created_at)
        .where(
            InteractionEvent.destination == destination,
            InteractionEvent.item_type == item_type,
        )
    )
    counts: dict[str, float] = defaultdict(float)
    for item_id, event_type, feedback_label, created_at in result.all():
        counts[item_id] += _event_weight(event_type, feedback_label) * _time_decay(created_at)
    if not counts:
        return {}
    max_v = max(max(counts.values()), 1.0)
    return {k: round(max(0.0, v / max_v), 4) for k, v in counts.items()}


async def get_user_recent_event_profile(
    db: AsyncSession,
    *,
    user_id: str,
    lookback_days: int = 90,
) -> dict:
    """Aggregate recent interaction behavior for feature priors."""
    result = await db.execute(
        select(
            InteractionEvent.item_type,
            InteractionEvent.event_type,
            InteractionEvent.feedback_label,
            InteractionEvent.created_at,
        ).where(InteractionEvent.user_id == user_id)
    )

    now = datetime.now(timezone.utc)
    type_weight_sum: dict[str, float] = defaultdict(float)
    event_count = 0
    positive_count = 0

    for item_type, event_type, feedback_label, created_at in result.all():
        if created_at:
            age_days = max(0.0, (now - created_at).total_seconds() / 86400)
            if age_days > lookback_days:
                continue
        weight = _event_weight(event_type, feedback_label)
        decay = _time_decay(created_at)
        type_weight_sum[str(item_type or "unknown")] += weight * decay
        event_count += 1
        if weight > 0:
            positive_count += 1

    if event_count == 0:
        return {"engagement_rate": 0.0, "type_affinity": {}}

    min_v = min(type_weight_sum.values()) if type_weight_sum else 0.0
    max_v = max(type_weight_sum.values()) if type_weight_sum else 1.0
    span = max(1e-9, max_v - min_v)
    type_affinity = {
        item_type: round((score - min_v) / span, 4)
        for item_type, score in type_weight_sum.items()
    }

    return {
        "engagement_rate": round(positive_count / max(1, event_count), 4),
        "type_affinity": type_affinity,
    }
