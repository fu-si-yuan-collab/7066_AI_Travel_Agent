"""Baseline recommendation engine.
包含两部分：
1) 内容过滤（destination/budget/style/cuisine/hotel stars/season/travelers）
2) 简化协同过滤（基于用户-项目交互矩阵的邻居聚合）
"""

from __future__ import annotations

from datetime import datetime
import math
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.db.repositories.interaction_repo import (
    get_destination_popularity_scores,
    get_neighbor_item_scores,
    get_user_recent_event_profile,
    get_user_item_affinity,
)
from app.recommendations.feature_engineering import (
    budget_fit_feature,
    build_ranking_features,
    season_match_feature,
)
from app.recommendations.online_ranker import score_with_online_model


def _month_to_season(month: int) -> str:
    if month in {12, 1, 2}:
        return "winter"
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    return "autumn"


def _safe_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _item_id(prefix: str, name: str, destination: str, source: str = "") -> str:
    return f"{prefix}:{name.strip().lower()}:{destination.strip().lower()}:{source.strip().lower()}"


def _tokenize(text: str, max_tokens: int = 6) -> list[str]:
    text = (text or "").lower()
    ascii_tokens = re.findall(r"[a-z0-9_]{2,}", text)
    zh_tokens = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    return (ascii_tokens + zh_tokens)[:max_tokens]


def _build_user_profile(state: AgentState) -> dict[str, float]:
    prefs = state.user_preferences or {}
    learned = prefs.get("learned_tags") if isinstance(prefs.get("learned_tags"), dict) else {}
    profile: dict[str, float] = {str(k): float(v) for k, v in (learned or {}).items()}

    travel_style = str(prefs.get("preferred_travel_style") or state.travel_plan.travel_style or "balanced").lower()
    profile[f"style:{travel_style}"] = profile.get(f"style:{travel_style}", 0.0) + 1.2

    preferred_transport = str(prefs.get("preferred_transport") or "").lower()
    if preferred_transport:
        profile[f"transport:{preferred_transport}"] = profile.get(f"transport:{preferred_transport}", 0.0) + 0.7

    try:
        stars = int(round(_safe_float(prefs.get("preferred_hotel_stars"), 3.0)))
        profile[f"stars:{stars}"] = profile.get(f"stars:{stars}", 0.0) + 1.0
    except Exception:
        pass

    cuisines = [c.strip().lower() for c in str(prefs.get("preferred_cuisine") or "").split(",") if c.strip()]
    for cuisine in cuisines:
        profile[f"cuisine:{cuisine}"] = profile.get(f"cuisine:{cuisine}", 0.0) + 1.0
        profile[f"kw:{cuisine}"] = profile.get(f"kw:{cuisine}", 0.0) + 0.8

    if state.travel_plan.destination:
        profile[f"dest:{state.travel_plan.destination.lower()}"] = profile.get(f"dest:{state.travel_plan.destination.lower()}", 0.0) + 0.8

    return profile


def _profile_similarity(candidate: dict, user_profile: dict[str, float]) -> float:
    tags = candidate.get("tags") or []
    if not tags or not user_profile:
        return 0.0

    tag_weights = [float(user_profile.get(tag, 0.0)) for tag in tags if tag in user_profile]
    if not tag_weights:
        return 0.0

    numerator = sum(tag_weights)
    denom = math.sqrt(sum(w * w for w in user_profile.values()) or 1.0) * math.sqrt(len(tags))
    if denom == 0:
        return 0.0
    return max(-1.0, min(1.0, numerator / denom))


def _normalize_rows(rows: list[dict], keys: list[str]) -> None:
    for key in keys:
        values = [float(row["raw_scores"].get(key, 0.0)) for row in rows]
        min_v = min(values) if values else 0.0
        max_v = max(values) if values else 0.0
        span = max_v - min_v
        for row in rows:
            raw_v = float(row["raw_scores"].get(key, 0.0))
            row["norm_scores"][key] = 0.0 if span <= 1e-9 else round((raw_v - min_v) / span, 4)


def _build_candidates(state: AgentState) -> list[dict]:
    destination = state.travel_plan.destination or ""
    candidates: list[dict] = []

    # 酒店候选
    for h in state.hotel_results[:25]:
        price = _safe_float(h.get("price_per_night") or h.get("price"), 0.0)
        stars = _safe_float(h.get("star_rating"), 0.0)
        title = str(h.get("name") or "")
        source = str(h.get("source") or "")
        candidates.append({
            "item_type": "hotel",
            "item_id": _item_id("hotel", title, destination, source),
            "title": title,
            "destination": destination,
            "price": price,
            "stars": stars,
            "rating": _safe_float(h.get("user_rating"), 0.0),
            "tags": [
                "type:hotel",
                f"dest:{destination.lower()}",
                f"platform:{source.lower()}",
                f"stars:{int(round(stars or 0))}",
                *[f"kw:{t}" for t in _tokenize(title)],
            ],
            "raw": h,
        })

    # 活动/餐厅候选
    for a in state.activity_results[:40]:
        title = str(a.get("name") or "")
        category = str(a.get("category") or a.get("type") or "activity")
        desc = str(a.get("description") or "")
        candidates.append({
            "item_type": "restaurant" if category == "restaurant" else "activity",
            "item_id": _item_id(category, title, destination),
            "title": title,
            "destination": destination,
            "price": _safe_float(a.get("avg_price_cny") or a.get("price_level"), 0.0),
            "stars": 0.0,
            "rating": _safe_float(a.get("rating"), 0.0),
            "tags": [
                f"type:{'restaurant' if category == 'restaurant' else 'activity'}",
                f"dest:{destination.lower()}",
                *[f"kw:{t}" for t in _tokenize(title)],
                *[f"kw:{t}" for t in _tokenize(desc, max_tokens=3)],
            ],
            "raw": a,
        })

    return [c for c in candidates if c["title"]]


def _content_score(candidate: dict, state: AgentState) -> float:
    prefs = state.user_preferences or {}
    plan = state.travel_plan
    score = 0.0

    # 目的地匹配
    if candidate.get("destination") and candidate["destination"] == plan.destination:
        score += 2.0

    # 预算匹配
    price = _safe_float(candidate.get("price"), 0.0)
    low = _safe_float(prefs.get("daily_budget_low"), 300.0)
    high = _safe_float(prefs.get("daily_budget_high"), 1000.0)
    if price > 0:
        if low <= price <= high:
            score += 2.0
        elif price > high * 1.8:
            score -= 1.3

    # 旅行风格
    style = str((prefs.get("preferred_travel_style") or plan.travel_style or "balanced")).lower()
    if style == "budget" and price and price <= high:
        score += 1.0
    if style == "luxury" and (candidate.get("stars", 0) >= 4.5 or price >= high):
        score += 1.2

    # 酒店星级偏好
    if candidate.get("item_type") == "hotel":
        pref_stars = _safe_float(prefs.get("preferred_hotel_stars"), 3.0)
        stars = _safe_float(candidate.get("stars"), 3.0)
        score += max(0.0, 1.5 - abs(stars - pref_stars))

    # 菜系偏好
    if candidate.get("item_type") == "restaurant":
        cuisines = str(prefs.get("preferred_cuisine") or "").lower().split(",")
        title = str(candidate.get("title") or "").lower()
        tags_joined = " ".join(candidate.get("tags") or [])
        if any(c.strip() and (c.strip() in title or c.strip() in tags_joined) for c in cuisines):
            score += 1.8

    # 季节 & 人数（轻量规则）
    if plan.start_date:
        try:
            month = datetime.fromisoformat(plan.start_date).month
            season = _month_to_season(month)
            text = (str(candidate.get("title", "")) + " " + " ".join(candidate.get("tags") or [])).lower()
            if season == "summer" and any(k in text for k in ["beach", "island", "outdoor"]):
                score += 0.6
            if season == "winter" and any(k in text for k in ["museum", "indoor", "onsen"]):
                score += 0.6
        except Exception:
            pass

    if (plan.num_travelers or 1) >= 3:
        text = (str(candidate.get("title", "")) + " " + " ".join(candidate.get("tags") or [])).lower()
        if any(k in text for k in ["family", "group", "suite"]):
            score += 0.5

    return score


def _learned_tags_score(candidate: dict, state: AgentState) -> float:
    learned = (state.user_preferences or {}).get("learned_tags") or {}
    if not isinstance(learned, dict) or not learned:
        return 0.0

    tag_set = set(candidate.get("tags") or [])
    score = 0.0
    for tag, weight in learned.items():
        try:
            w = float(weight)
        except Exception:
            continue
        if tag in tag_set:
            score += max(-2.0, min(3.0, w)) * 0.35
    return score


async def rank_candidates_with_baseline(
    db: AsyncSession,
    state: AgentState,
    top_k: int = 12,
) -> list[dict]:
    """输出 Top-K 推荐候选，供 itinerary 节点使用。"""
    candidates = _build_candidates(state)
    if not candidates:
        return []

    by_type: dict[str, list[dict]] = {}
    for c in candidates:
        by_type.setdefault(c["item_type"], []).append(c)

    ranked: list[dict] = []
    destination = state.travel_plan.destination or ""
    user_profile = _build_user_profile(state)
    behavior_profile = await get_user_recent_event_profile(db, user_id=state.user_id)
    type_affinity = behavior_profile.get("type_affinity", {}) if isinstance(behavior_profile, dict) else {}
    learned_tags = (state.user_preferences or {}).get("learned_tags") if isinstance((state.user_preferences or {}).get("learned_tags"), dict) else {}
    prefs = state.user_preferences or {}
    budget_low = _safe_float(prefs.get("daily_budget_low"), 300.0)
    budget_high = _safe_float(prefs.get("daily_budget_high"), 1000.0)

    for item_type, items in by_type.items():
        affinity = await get_user_item_affinity(db, state.user_id, item_type)
        seed_ids = [item_id for item_id, s in affinity.items() if s > 0.8]
        neighbor_scores = await get_neighbor_item_scores(db, state.user_id, item_type, seed_ids)
        popularity_scores = await get_destination_popularity_scores(db, destination, item_type)
        per_type_rows: list[dict] = []

        for c in items:
            content = _content_score(c, state)
            learned_score = _learned_tags_score(c, state)
            profile_similarity = _profile_similarity(c, user_profile)
            self_affinity = affinity.get(c["item_id"], 0.0)
            collaborative = neighbor_scores.get(c["item_id"], 0.0)
            popularity = popularity_scores.get(c["item_id"], 0.0)

            c["raw_scores"] = {
                "content": round(content, 4),
                "learned_tags": round(learned_score, 4),
                "profile_similarity": round(profile_similarity, 4),
                "self_affinity": round(self_affinity, 4),
                "collaborative": round(collaborative, 4),
                "popularity": round(popularity, 4),
            }
            c["norm_scores"] = {}
            per_type_rows.append(c)

        _normalize_rows(per_type_rows, [
            "content",
            "learned_tags",
            "profile_similarity",
            "self_affinity",
            "collaborative",
            "popularity",
        ])

        for c in per_type_rows:
            ns = c["norm_scores"]
            base_score = (
                0.26 * ns.get("content", 0.0)
                + 0.18 * ns.get("learned_tags", 0.0)
                + 0.22 * ns.get("profile_similarity", 0.0)
                + 0.12 * ns.get("self_affinity", 0.0)
                + 0.15 * ns.get("collaborative", 0.0)
                + 0.07 * ns.get("popularity", 0.0)
            )

            text_blob = f"{c.get('title', '')} {' '.join(c.get('tags') or [])}"
            features = build_ranking_features(
                content=ns.get("content", 0.0),
                learned_tags=ns.get("learned_tags", 0.0),
                profile_similarity=ns.get("profile_similarity", 0.0),
                self_affinity=ns.get("self_affinity", 0.0),
                collaborative=ns.get("collaborative", 0.0),
                popularity=ns.get("popularity", 0.0),
                budget_fit=budget_fit_feature(_safe_float(c.get("price"), 0.0), budget_low, budget_high),
                season_match=season_match_feature(state.travel_plan.start_date, text_blob),
                rating=_safe_float(c.get("rating"), 0.0),
            )
            model_score = score_with_online_model(features, learned_tags)
            item_type_prior = float(type_affinity.get(c.get("item_type", ""), 0.5))

            final_score = 0.7 * base_score + 0.25 * model_score + 0.05 * item_type_prior
            c["scores"] = {
                **{k: round(float(v), 3) for k, v in c["raw_scores"].items()},
                "base": round(base_score, 3),
                "model": round(model_score, 3),
                "final": round(final_score, 3),
            }
            c["ranking_features"] = features
            c["reason"] = (
                f"content={c['scores']['content']}, "
                f"lt={c['scores']['learned_tags']}, "
                f"profile={c['scores']['profile_similarity']}, "
                f"cf={c['scores']['collaborative']}, "
                f"pop={c['scores']['popularity']}, "
                f"ml={c['scores']['model']}"
            )
            ranked.append(c)

    ranked.sort(key=lambda x: x["scores"]["final"], reverse=True)

    # 轻量多样性重排：避免 Top-K 被单一类型占满。
    reranked: list[dict] = []
    seen_type_count: dict[str, int] = {}
    for item in ranked:
        item_type = str(item.get("item_type") or "unknown")
        penalty = 0.08 * seen_type_count.get(item_type, 0)
        item["scores"]["final"] = round(float(item["scores"]["final"]) - penalty, 3)
        seen_type_count[item_type] = seen_type_count.get(item_type, 0) + 1
        reranked.append(item)

    reranked.sort(key=lambda x: x["scores"]["final"], reverse=True)
    return reranked[:top_k]
