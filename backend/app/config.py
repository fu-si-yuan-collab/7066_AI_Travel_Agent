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
    AZURE_OPENAI_ENDPOINT: str = ""          # Azure 资源终端点，如 https://xxx.openai.azure.com/
    AZURE_OPENAI_API_KEY: str = ""           # Azure OpenAI 密钥
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4.1-mini"  # 部署名称（对应模型）
    AZURE_OPENAI_API_VERSION: str = "2025-03-01-preview"  # API 版本

    # --- Azure AI Foundry（备用通道） ---
    FOUNDRY_PROJECT_ENDPOINT: str = ""
    FOUNDRY_PROJECT_API_KEY: str = ""
    FOUNDRY_PROJECT_DEPLOYMENT: str = "gpt-4.1-mini"

    # --- 数据库 ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/travel_agent"
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- 旅行 API ---
    SERPAPI_API_KEY: str = ""                # SerpAPI：用于 Google Flights / Hotels / POI 搜索
    AMADEUS_CLIENT_ID: str = ""             # Amadeus：备用机票/酒店数据源
    AMADEUS_CLIENT_SECRET: str = ""

    # --- 天气 API ---
    OPENWEATHER_API_KEY: str = ""           # OpenWeatherMap：天气预报

    # --- 地图 API ---
    AMAP_API_KEY: str = ""                  # 高德地图：国内导航
    GOOGLE_MAPS_API_KEY: str = ""           # Google Maps：国际导航

    # --- JWT 认证 ---
    JWT_SECRET_KEY: str = "change-me-in-production"  # 生产环境请更换
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440          # Token 有效期：24小时

    # extra="ignore" 允许 .env 中存在 Settings 未定义的变量（如 LANGCHAIN_* 等）
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例（带缓存，只加载一次）。"""
    return Settings()
