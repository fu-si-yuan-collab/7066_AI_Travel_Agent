"""Application configuration loaded from environment variables.
应用配置：从 .env 文件加载所有环境变量，使用 pydantic-settings 做校验。
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- 应用基本信息 ---
    APP_NAME: str = "AI Travel Agent"
    DEBUG: bool = False

    # --- Azure OpenAI（主力 LLM，替代原生 OpenAI） ---
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4.1-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-05-01-preview"

    # --- Azure AI Foundry（备用通道） ---
    FOUNDRY_PROJECT_ENDPOINT: str = ""
    FOUNDRY_PROJECT_API_KEY: str = ""
    FOUNDRY_PROJECT_DEPLOYMENT: str = "gpt-4.1-mini"

    # --- 数据库 ---
    # Railway 注入的是 postgresql:// 前缀，需要转成 asyncpg 格式
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/travel_agent"
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- 旅行 API ---
    SERPAPI_API_KEY: str = ""
    AMADEUS_CLIENT_ID: str = ""
    AMADEUS_CLIENT_SECRET: str = ""

    # --- 天气 API ---
    OPENWEATHER_API_KEY: str = ""

    # --- 地图 API ---
    AMAP_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    # --- JWT 认证 ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def async_database_url(self) -> str:
        """Railway 注入的 DATABASE_URL 是 postgresql:// 格式，
        SQLAlchemy asyncpg 需要 postgresql+asyncpg:// 格式，这里自动转换。"""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例（带缓存，只加载一次）。"""
    return Settings()
