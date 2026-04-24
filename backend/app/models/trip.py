"""Trip / Itinerary ORM models.
行程模型：存储完整的旅行计划，包括逐日安排和具体活动。
三层结构：Trip（整体行程） → TripDay（每一天） → TripActivity（每个活动）
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, Date, DateTime, Float, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Trip(Base):
    """一次完整的旅行计划。"""
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)  # 所属用户
    title: Mapped[str] = mapped_column(String(200), default="")              # 行程标题
    destination: Mapped[str] = mapped_column(String(200), nullable=False)    # 目的地
    origin: Mapped[str] = mapped_column(String(200), default="")             # 出发地
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)     # 出发日期
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)       # 返回日期
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)       # 总预算
    currency: Mapped[str] = mapped_column(String(10), default="CNY")         # 货币
    status: Mapped[str] = mapped_column(String(20), default="draft")         # 状态：draft / confirmed / completed / cancelled
    travel_style: Mapped[str] = mapped_column(String(50), default="balanced")  # 风格：budget / balanced / luxury
    notes: Mapped[str] = mapped_column(Text, default="")                     # 备注
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 扩展元数据
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="trips")
    days = relationship("TripDay", back_populates="trip", lazy="selectin", order_by="TripDay.day_number")


class TripDay(Base):
    """行程中的一天。"""
    __tablename__ = "trip_days"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id"), index=True)  # 所属行程
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)   # 第几天（从 1 开始）
    date: Mapped[date | None] = mapped_column(Date, nullable=True)     # 具体日期
    summary: Mapped[str] = mapped_column(Text, default="")             # 当天概要

    trip = relationship("Trip", back_populates="days")
    activities = relationship("TripActivity", back_populates="day", lazy="selectin", order_by="TripActivity.order")


class TripActivity(Base):
    """一天中的一个具体活动。"""
    __tablename__ = "trip_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    day_id: Mapped[str] = mapped_column(String(36), ForeignKey("trip_days.id"), index=True)  # 所属天
    order: Mapped[int] = mapped_column(Integer, default=0)               # 排序
    type: Mapped[str] = mapped_column(String(50), default="sightseeing") # 类型：sightseeing / dining / transport / hotel / activity
    name: Mapped[str] = mapped_column(String(200), nullable=False)       # 活动名称
    description: Mapped[str] = mapped_column(Text, default="")           # 描述
    location: Mapped[str] = mapped_column(String(300), default="")       # 地点
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)  # 纬度
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True) # 经度
    start_time: Mapped[str] = mapped_column(String(10), default="")      # 开始时间 HH:MM
    end_time: Mapped[str] = mapped_column(String(10), default="")        # 结束时间
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)    # 预估费用
    booking_url: Mapped[str] = mapped_column(String(500), default="")    # 预订链接
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    day = relationship("TripDay", back_populates="activities")
