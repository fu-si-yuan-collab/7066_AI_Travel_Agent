"""FastAPI application entry point.
FastAPI 应用入口：注册路由、配置中间件、管理生命周期。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import init_db
from app.api.routes import chat, trips, users, preferences


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库表，关闭时清理资源。"""
    await init_db()  # 自动建表（开发便利，生产环境应使用 alembic 迁移）
    yield


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# 跨域中间件 —— 允许所有来源（包括 Vercel 部署的前端）
# 生产环境可改为具体域名，如 ["https://your-app.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # credentials=True 与 allow_origins=["*"] 不兼容，改为 False
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由模块
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(trips.router, prefix="/api/v1/trips", tags=["Trips"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(preferences.router, prefix="/api/v1/preferences", tags=["Preferences"])


@app.get("/health")
async def health_check():
    """健康检查接口，用于 Docker / K8s 存活探测。"""
    return {"status": "ok"}
