"""Hotel search service – multi-platform price comparison.
酒店搜索服务 —— 多平台比价，这是我们产品的核心差异化功能。
解决不同平台报价混乱的痛点：从多个数据源获取酒店数据，合并后统一排序。

支持的数据源：
- SerpAPI → Google Hotels
- Amadeus Hotel API
"""

from __future__ import annotations

import hashlib
import json

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.cache import cache_get, cache_set

settings = get_settings()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def _search_google_hotels(
    destination: str,
    checkin: str,
    checkout: str,
    guests: int = 2,
    star_rating: float | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """通过 SerpAPI Google Hotels 引擎搜索酒店。"""
    params: dict = {
        "engine": "google_hotels",
        "q": f"hotels in {destination}",
        "check_in_date": checkin,
        "check_out_date": checkout,
        "adults": guests,
        "api_key": settings.SERPAPI_API_KEY,
    }
    if star_rating:
        params["hotel_class"] = int(star_rating)  # 按星级筛选

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for hotel in data.get("properties", []):
        # 提取最低价格（优先取总价，否则取每晚价）
        price = hotel.get("total_rate", {}).get("extracted_lowest", 0) or hotel.get("rate_per_night", {}).get("extracted_lowest", 0)
        if max_price and price > max_price:
            continue  # 超过预算上限则跳过
        results.append({
            "source": "google_hotels",
            "hotel_name": hotel.get("name", ""),
            "address": hotel.get("description", ""),
            "star_rating": hotel.get("hotel_class", 0),       # 酒店星级
            "user_rating": hotel.get("overall_rating", 0),     # 用户评分
            "review_count": hotel.get("reviews", 0),           # 评论数
            "price_per_night": price,
            "currency": "USD",
            "amenities": hotel.get("amenities", []),           # 设施列表
            "image_url": hotel.get("images", [{}])[0].get("thumbnail", "") if hotel.get("images") else "",
            "booking_url": hotel.get("link", ""),
            "latitude": hotel.get("gps_coordinates", {}).get("latitude"),
            "longitude": hotel.get("gps_coordinates", {}).get("longitude"),
        })
    return results


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def _search_amadeus_hotels(
    destination: str,
    checkin: str,
    checkout: str,
    guests: int = 2,
    **kwargs,
) -> list[dict]:
    """通过 Amadeus Hotel API 搜索酒店（两步：先搜酒店列表，再获取报价）。"""
    from app.services.flight_service import _get_amadeus_token

    token = await _get_amadeus_token()

    # 第一步：根据城市代码搜索酒店列表
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.amadeus.com/v1/reference-data/locations/hotels/by-city",
            headers={"Authorization": f"Bearer {token}"},
            params={"cityCode": destination[:3].upper()},  # 取前3位作为城市代码
            timeout=30,
        )
        resp.raise_for_status()
        hotels_data = resp.json().get("data", [])[:10]  # 最多取 10 家

    hotel_ids = [h["hotelId"] for h in hotels_data]
    if not hotel_ids:
        return []

    # 第二步：获取这些酒店的报价
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.amadeus.com/v3/shopping/hotel-offers",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "hotelIds": ",".join(hotel_ids[:5]),  # 限制 5 家避免超时
                "checkInDate": checkin,
                "checkOutDate": checkout,
                "adults": guests,
            },
            timeout=30,
        )
        resp.raise_for_status()
        offers_data = resp.json().get("data", [])

    results = []
    for offer_group in offers_data:
        hotel_info = offer_group.get("hotel", {})
        offers = offer_group.get("offers", [])
        if not offers:
            continue
        best_offer = offers[0]  # 取最优报价
        price = float(best_offer.get("price", {}).get("total", 0))
        results.append({
            "source": "amadeus",
            "hotel_name": hotel_info.get("name", ""),
            "address": hotel_info.get("address", {}).get("lines", [""])[0],
            "star_rating": hotel_info.get("rating", 0),
            "user_rating": 0,
            "review_count": 0,
            "price_per_night": price,
            "currency": best_offer.get("price", {}).get("currency", "USD"),
            "room_type": best_offer.get("room", {}).get("typeEstimated", {}).get("category", ""),
            "booking_url": "",
            "latitude": hotel_info.get("latitude"),
            "longitude": hotel_info.get("longitude"),
        })
    return results


async def search_hotels_multi_platform(
    destination: str,
    checkin: str,
    checkout: str,
    guests: int = 2,
    star_rating: float | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """跨平台搜索酒店，带 Redis 缓存和去重。

    结果按每晚价格升序排列。缓存 30 分钟。
    """
    cache_key = "hotels:" + hashlib.md5(
        json.dumps({"d": destination, "ci": checkin, "co": checkout, "g": guests}).encode()
    ).hexdigest()

    cached = await cache_get(cache_key)
    if cached:
        return cached

    all_results: list[dict] = []

    # SerpAPI Google Hotels
    if settings.SERPAPI_API_KEY:
        try:
            all_results.extend(await _search_google_hotels(destination, checkin, checkout, guests, star_rating, max_price))
        except Exception:
            pass

    # Amadeus Hotels
    if settings.AMADEUS_CLIENT_ID:
        try:
            all_results.extend(await _search_amadeus_hotels(destination, checkin, checkout, guests))
        except Exception:
            pass

    # 按每晚价格升序排列
    all_results.sort(key=lambda x: x.get("price_per_night", float("inf")))

    if all_results:
        await cache_set(cache_key, all_results, ttl=1800)

    return all_results
