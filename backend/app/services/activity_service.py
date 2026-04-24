"""Activity / POI search service.
景点与活动搜索服务 —— 通过 SerpAPI 搜索目的地的景点、活动和兴趣点 (POI)。
支持根据用户兴趣标签（如 beach, museum）过滤结果。
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.cache import cache_get, cache_set

settings = get_settings()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def search_activities(
    destination: str,
    interests: list[str] | None = None,
    limit: int = 15,
) -> list[dict]:
    """搜索目的地的景点和活动。

    Args:
        destination: 目的地名称
        interests: 用户兴趣标签列表（如 ["beach", "museum"]）
        limit: 最大返回数量

    Returns:
        景点列表，每个包含名称、评分、地址、经纬度等信息
    """
    cache_key = f"activities:{destination}:{','.join(interests or [])}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # 构建搜索查询（加入用户兴趣标签）
    query = f"things to do in {destination}"
    if interests:
        query += " " + " ".join(interests[:3])  # 最多加 3 个兴趣词

    params = {
        "engine": "google",
        "q": query,
        "api_key": settings.SERPAPI_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://serpapi.com/search", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

    results = []

    # 解析本地搜索结果（Google Maps 上的地点）
    for place in data.get("local_results", {}).get("places", []):
        results.append({
            "name": place.get("title", ""),
            "description": place.get("description", ""),
            "rating": place.get("rating"),
            "reviews": place.get("reviews"),
            "address": place.get("address", ""),
            "type": place.get("type", "attraction"),
            "latitude": place.get("gps_coordinates", {}).get("latitude"),
            "longitude": place.get("gps_coordinates", {}).get("longitude"),
            "thumbnail": place.get("thumbnail", ""),
        })

    # 解析热门景点（Google 的 Top Sights 卡片）
    for sight in data.get("top_sights", {}).get("sights", []):
        results.append({
            "name": sight.get("title", ""),
            "description": sight.get("description", ""),
            "rating": sight.get("rating"),
            "reviews": sight.get("reviews"),
            "address": "",
            "type": "sight",
            "latitude": None,
            "longitude": None,
            "thumbnail": sight.get("thumbnail", ""),
        })

    results = results[:limit]
    if results:
        await cache_set(cache_key, results, ttl=86400)  # 景点信息变化慢，缓存 24 小时

    return results
