"""User ORM model.
用户模型：存储注册信息和认证数据。
与 UserPreference（偏好）和 Trip（行程）有一对多/一对一关系。
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)   # 登录邮箱（唯一）
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)                   # bcrypt 哈希后的密码
    nickname: Mapped[str] = mapped_column(String(100), default="")                              # 昵称
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)                              # 账号是否激活
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 关联关系
    trips = relationship("Trip", back_populates="user", lazy="selectin")             # 用户的所有行程
    preferences = relationship("UserPreference", back_populates="user", uselist=False, lazy="selectin")  # 用户偏好（一对一）
