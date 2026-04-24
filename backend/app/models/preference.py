"""User preference model – stores learned travel preferences.
用户偏好模型 —— 存储 AI 学习到的旅行偏好。
其中 learned_tags 字段由推荐系统（ML 团队）动态更新，
记录用户对各类旅行标签的偏好权重（如 beach: 0.8, museum: 0.3）。
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserPreference(Base):
    """持久化的用户偏好，AI 在推荐时会引用这些数据。"""
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, index=True)

    # 旅行风格偏好
    preferred_travel_style: Mapped[str] = mapped_column(String(50), default="balanced")  # budget / balanced / luxury
    preferred_transport: Mapped[str] = mapped_column(String(50), default="any")          # flight / train / driving / any
    preferred_hotel_stars: Mapped[float] = mapped_column(Float, default=3.0)             # 偏好酒店星级
    preferred_cuisine: Mapped[str] = mapped_column(Text, default="")                     # 偏好菜系（逗号分隔）

    # 预算默认值
    daily_budget_low: Mapped[float] = mapped_column(Float, default=300.0)     # 每日预算下限
    daily_budget_high: Mapped[float] = mapped_column(Float, default=1000.0)   # 每日预算上限
    currency: Mapped[str] = mapped_column(String(10), default="CNY")          # 默认货币

    # ML 团队学习到的偏好（JSON 格式，由推荐引擎更新）
    learned_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)    # 例如 {"beach": 0.8, "museum": 0.3}
    interaction_history_summary: Mapped[str] = mapped_column(Text, default="") # 交互历史摘要

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="preferences")
