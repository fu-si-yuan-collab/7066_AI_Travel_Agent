"""JWT authentication utilities.
JWT 认证工具：密码哈希、Token 签发与验证。
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import get_settings

settings = get_settings()

# 密码哈希上下文（使用 bcrypt 算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Bearer Token 提取器（从请求头的 Authorization: Bearer xxx 中提取 token）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


def hash_password(password: str) -> str:
    """将明文密码哈希为 bcrypt 格式。"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否与哈希值匹配。"""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """签发 JWT Token。
    data 中通常包含 {"sub": user_id}，过期时间默认 24 小时。
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI 依赖注入：从 JWT Token 中提取当前用户 ID。
    如果 token 无效或过期，抛出 401 异常。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception
