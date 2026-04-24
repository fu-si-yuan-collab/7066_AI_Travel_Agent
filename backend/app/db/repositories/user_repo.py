"""User data access layer.
用户数据访问层：封装所有用户相关的数据库操作。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """根据邮箱查找用户（用于登录和注册查重）。"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """根据用户 ID 查找用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, hashed_password: str, nickname: str = "") -> User:
    """创建新用户并写入数据库。"""
    user = User(email=email, hashed_password=hashed_password, nickname=nickname)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
