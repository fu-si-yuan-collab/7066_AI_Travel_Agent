"""Trip data access layer.
行程数据访问层：封装所有行程相关的数据库操作。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import Trip
from app.models.schemas import TripCreate


async def get_trips_by_user(db: AsyncSession, user_id: str) -> list[Trip]:
    """获取某用户的所有行程（按创建时间倒序）。"""
    result = await db.execute(
        select(Trip).where(Trip.user_id == user_id).order_by(Trip.created_at.desc())
    )
    return list(result.scalars().all())


async def get_trip_by_id(db: AsyncSession, trip_id: str) -> Trip | None:
    """根据行程 ID 查询单个行程。"""
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    return result.scalar_one_or_none()


async def create_trip(db: AsyncSession, user_id: str, data: TripCreate) -> Trip:
    """创建新行程并写入数据库。"""
    trip = Trip(user_id=user_id, **data.model_dump())
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


async def update_trip_status(db: AsyncSession, trip_id: str, status: str) -> None:
    """更新行程状态。"""
    trip = await get_trip_by_id(db, trip_id)
    if trip:
        trip.status = status
        await db.commit()


async def delete_trip(db: AsyncSession, trip_id: str) -> None:
    """删除行程。"""
    trip = await get_trip_by_id(db, trip_id)
    if trip:
        await db.delete(trip)
        await db.commit()
