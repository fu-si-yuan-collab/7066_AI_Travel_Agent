"""User preference data access layer.
用户偏好数据访问层：获取和更新用户的旅行偏好。
偏好会被 AI Agent 在推荐时引用，实现个性化推荐。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preference import UserPreference
from app.models.schemas import PreferenceUpdate


async def get_user_preferences(db: AsyncSession, user_id: str) -> UserPreference | None:
    """获取用户的偏好设置（如不存在则返回 None）。"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_preferences(
    db: AsyncSession, user_id: str, data: PreferenceUpdate
) -> UserPreference:
    """创建或更新用户偏好（Upsert 模式）：
    - 如果不存在：创建新记录
    - 如果已存在：只更新传入的非 None 字段
    """
    pref = await get_user_preferences(db, user_id)

    if pref is None:
        pref = UserPreference(user_id=user_id)
        db.add(pref)

    # 只更新非 None 的字段
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(pref, key, value)

    await db.commit()
    await db.refresh(pref)
    return pref
