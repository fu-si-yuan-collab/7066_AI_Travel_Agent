"""User registration and authentication endpoints.
用户注册和登录接口：提供 JWT Token 认证。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.repositories.user_repo import create_user, get_user_by_email
from app.models.schemas import TokenResponse, UserLogin, UserOut, UserRegister

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """用户注册：检查邮箱唯一性 → 创建用户 → 返回用户信息。"""
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await create_user(db, body.email, hash_password(body.password), body.nickname)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录：验证密码 → 签发 JWT Token。"""
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # 将 user.id 写入 token 的 sub 字段
    token = create_access_token(data={"sub": user.id})
    return TokenResponse(access_token=token)
