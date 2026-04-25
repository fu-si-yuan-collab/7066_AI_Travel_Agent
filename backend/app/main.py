"""FastAPI application entry point.
FastAPI 应用入口：注册路由、配置中间件、管理生命周期。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import init_db
from app.api.routes import chat, trips, users, preferences, interactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库表，连接失败时打印警告但不阻止启动。"""
    try:
        await init_db()
    except Exception as e:
        # 数据库暂时不可用时不阻止服务启动（Railway 插件可能需要几秒才就绪）
        import logging
        logging.warning(f"DB init warning (will retry on first request): {e}")
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
app.include_router(interactions.router, prefix="/api/v1/interactions", tags=["Interactions"])


@app.get("/health")
async def health_check():
    """健康检查接口，用于 Docker / K8s 存活探测。"""
    return {"status": "ok"}
