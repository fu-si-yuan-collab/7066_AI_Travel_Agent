"""Async database engine and session factory.
异步数据库引擎和会话工厂：使用 SQLAlchemy 2.0 的异步模式。
通过 asyncpg 驱动连接 PostgreSQL。
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# 创建异步引擎（使用 async_database_url 自动处理 Railway 的 postgresql:// 前缀）
engine = create_async_engine(settings.async_database_url, echo=settings.DEBUG)

# 创建异步会话工厂（expire_on_commit=False 避免提交后访问属性时触发惰性加载）
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


async def init_db():
    """自动建表（开发便利）。生产环境应使用 alembic 迁移。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI 依赖注入：每次请求获取一个数据库会话，请求结束后自动关闭。"""
    async with async_session() as session:
        yield session
