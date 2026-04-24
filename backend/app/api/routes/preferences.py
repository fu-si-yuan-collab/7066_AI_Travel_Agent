"""User preference management endpoints.
用户偏好管理接口：获取和更新旅行偏好设置。
偏好数据会被 Agent 在生成推荐时使用，实现"一人一策"的个性化体验。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.repositories.preference_repo import get_user_preferences, upsert_preferences
from app.models.schemas import PreferenceOut, PreferenceUpdate

router = APIRouter()


@router.get("", response_model=PreferenceOut | None)
async def get_prefs(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的旅行偏好设置。"""
    return await get_user_preferences(db, user_id)


@router.put("", response_model=PreferenceOut)
async def update_prefs(
    body: PreferenceUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建或更新用户偏好（不存在则创建，已存在则更新非空字段）。"""
    return await upsert_preferences(db, user_id, body)
