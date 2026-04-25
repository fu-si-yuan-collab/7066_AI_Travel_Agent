"""Interaction tracking endpoints.
行为日志与反馈接口：用于推荐学习数据闭环。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.repositories.interaction_repo import get_user_recent_event_profile, log_interaction_event
from app.db.repositories.preference_repo import get_user_preferences
from app.models.schemas import InteractionEventIn, InteractionFeedbackIn
from app.services.preference_learning import learn_from_interaction

router = APIRouter()


@router.post("/events")
async def track_event(
    body: InteractionEventIn,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    metadata = dict(body.metadata_json or {})
    if body.rank_position is not None:
        metadata["rank_position"] = body.rank_position
    if body.dwell_ms is not None:
        metadata["dwell_ms"] = body.dwell_ms
    if body.source_channel:
        metadata["source_channel"] = body.source_channel

    await log_interaction_event(
        db,
        user_id,
        event_type=body.event_type,
        item_type=body.item_type,
        item_id=body.item_id,
        session_id=body.session_id or "",
        item_title=body.item_title or "",
        destination=body.destination or "",
        travel_style=body.travel_style or "",
        budget=body.budget or 0.0,
        currency=body.currency or "CNY",
        metadata_json=metadata,
    )
    try:
        await learn_from_interaction(
            db,
            user_id=user_id,
            event_type=body.event_type,
            item_type=body.item_type,
            item_id=body.item_id,
            item_title=body.item_title or "",
            destination=body.destination or "",
            metadata_json=metadata,
        )
    except Exception:
        pass
    return {"ok": True}


@router.post("/feedback")
async def track_feedback(
    body: InteractionFeedbackIn,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await log_interaction_event(
        db,
        user_id,
        event_type="feedback",
        item_type=body.item_type,
        item_id=body.item_id,
        session_id=body.session_id or "",
        feedback_label=body.feedback,
        item_title=body.item_title or "",
        destination=body.destination or "",
        metadata_json=body.metadata_json,
    )
    try:
        await learn_from_interaction(
            db,
            user_id=user_id,
            event_type="feedback",
            feedback_label=body.feedback,
            item_type=body.item_type,
            item_id=body.item_id,
            item_title=body.item_title or "",
            destination=body.destination or "",
            metadata_json=body.metadata_json,
        )
    except Exception:
        pass
    return {"ok": True}


@router.get("/profile")
async def recommendation_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """返回推荐学习概览，便于联调与效果验证。"""
    behavior = await get_user_recent_event_profile(db, user_id=user_id)
    prefs = await get_user_preferences(db, user_id)
    learned = prefs.learned_tags if prefs and isinstance(prefs.learned_tags, dict) else {}
    top_tags = sorted(
        [(k, float(v)) for k, v in learned.items() if not str(k).startswith("model:w:")],
        key=lambda kv: abs(kv[1]),
        reverse=True,
    )[:20]
    model_weights = {k: v for k, v in learned.items() if str(k).startswith("model:w:")}

    return {
        "ok": True,
        "behavior": behavior,
        "top_learned_tags": [{"tag": k, "weight": round(v, 4)} for k, v in top_tags],
        "model_weights": model_weights,
    }
