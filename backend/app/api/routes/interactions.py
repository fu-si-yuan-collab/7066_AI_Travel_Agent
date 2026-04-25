"""Interaction tracking endpoints.
行为日志与反馈接口：用于推荐学习数据闭环。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.repositories.interaction_repo import log_interaction_event
from app.models.schemas import InteractionEventIn, InteractionFeedbackIn
from app.services.preference_learning import learn_from_interaction

router = APIRouter()


@router.post("/events")
async def track_event(
    body: InteractionEventIn,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
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
        metadata_json=body.metadata_json,
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
            metadata_json=body.metadata_json,
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
