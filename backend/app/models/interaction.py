"""User interaction event model for recommendation learning.
行为事件模型：记录曝光、点击、收藏、采纳、反馈等事件，
用于个性化推荐训练与在线优化。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class InteractionEvent(Base):
    """单条用户行为事件。"""

    __tablename__ = "interaction_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    # 会话与事件基础信息
    session_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)      # exposure/click/save/add_to_trip/delete/final_adopt/feedback
    feedback_label: Mapped[str] = mapped_column(String(32), default="")  # like/dislike/not_relevant

    # 目标对象信息
    item_type: Mapped[str] = mapped_column(String(64), index=True)        # hotel/restaurant/activity/trip_plan/chat
    item_id: Mapped[str] = mapped_column(String(255), index=True)
    item_title: Mapped[str] = mapped_column(String(255), default="")

    # 上下文特征（用于 baseline 推荐）
    destination: Mapped[str] = mapped_column(String(128), default="", index=True)
    travel_style: Mapped[str] = mapped_column(String(64), default="")
    budget: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user = relationship("User")
