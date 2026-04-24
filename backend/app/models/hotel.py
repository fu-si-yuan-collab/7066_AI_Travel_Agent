"""Hotel comparison record model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class HotelRecord(Base):
    """Cached hotel search results for price comparison."""
    __tablename__ = "hotel_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("trips.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # ctrip / booking / agoda / google_hotels
    hotel_name: Mapped[str] = mapped_column(String(300), nullable=False)
    address: Mapped[str] = mapped_column(String(500), default="")
    star_rating: Mapped[float] = mapped_column(Float, default=0.0)
    user_rating: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    price_per_night: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    room_type: Mapped[str] = mapped_column(String(200), default="")
    amenities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    booking_url: Mapped[str] = mapped_column(String(500), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
