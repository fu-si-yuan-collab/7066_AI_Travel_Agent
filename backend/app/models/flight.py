"""Flight search record model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class FlightRecord(Base):
    """Cached flight search results."""
    __tablename__ = "flight_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("trips.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # amadeus / google_flights / ctrip
    airline: Mapped[str] = mapped_column(String(100), default="")
    flight_number: Mapped[str] = mapped_column(String(20), default="")
    departure_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    departure_time: Mapped[str] = mapped_column(String(30), nullable=False)
    arrival_time: Mapped[str] = mapped_column(String(30), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    stops: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    cabin_class: Mapped[str] = mapped_column(String(20), default="economy")
    booking_url: Mapped[str] = mapped_column(String(500), default="")
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
