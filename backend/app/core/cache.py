"""Redis cache wrapper for API response caching.
Redis 缓存封装：用于缓存外部 API 响应（航班、酒店、天气等），
避免重复请求，提升响应速度。默认 TTL 1 小时。
"""

import json
from typing import Any

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

_pool: redis.Redis | None = None  # 全局连接池（惰性初始化）


async def get_redis() -> redis.Redis:
    """获取 Redis 连接（单例模式，复用连接池）。"""
    global _pool
    if _pool is None:
        _pool = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _pool


async def cache_get(key: str) -> Any | None:
    """从缓存中获取值，未命中则返回 None。"""
    r = await get_redis()
    val = await r.get(key)
    if val is not None:
        return json.loads(val)
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """写入缓存，带 TTL（默认 3600 秒 = 1 小时）。"""
    r = await get_redis()
    await r.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
