"""Trip CRUD endpoints.
行程管理接口：创建、查询、修改状态、删除行程。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.repositories.trip_repo import (
    create_trip,
    get_trip_by_id,
    get_trips_by_user,
    update_trip_status,
    delete_trip,
)
from app.models.schemas import TripCreate, TripOut

router = APIRouter()


@router.get("", response_model=list[TripOut])
async def list_trips(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有行程列表。"""
    return await get_trips_by_user(db, user_id)


@router.post("", response_model=TripOut, status_code=201)
async def create(
    body: TripCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建新行程计划。"""
    return await create_trip(db, user_id, body)


@router.get("/{trip_id}", response_model=TripOut)
async def get_trip(
    trip_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取行程详情（仅限本人访问）。"""
    trip = await get_trip_by_id(db, trip_id)
    if not trip or trip.user_id != user_id:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.patch("/{trip_id}/status")
async def change_status(
    trip_id: str,
    status: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新行程状态（draft → confirmed → completed → cancelled）。"""
    trip = await get_trip_by_id(db, trip_id)
    if not trip or trip.user_id != user_id:
        raise HTTPException(status_code=404, detail="Trip not found")
    await update_trip_status(db, trip_id, status)
    return {"ok": True}


@router.delete("/{trip_id}", status_code=204)
async def remove_trip(
    trip_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """删除行程。"""
    trip = await get_trip_by_id(db, trip_id)
    if not trip or trip.user_id != user_id:
        raise HTTPException(status_code=404, detail="Trip not found")
    await delete_trip(db, trip_id)
