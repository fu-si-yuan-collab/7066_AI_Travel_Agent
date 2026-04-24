"""Flight search service – aggregates results from multiple providers.
机票搜索服务 —— 聚合多个数据源的航班结果，统一格式后按价格排序。

支持的数据源：
- Amadeus API（主要）
- SerpAPI → Google Flights（备用/补充）
"""

from __future__ import annotations

import hashlib
import json

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.cache import cache_get, cache_set

settings = get_settings()

# Amadeus OAuth Token 缓存（避免每次请求都重新获取）
_amadeus_token: str | None = None


async def _get_amadeus_token() -> str:
    """获取 Amadeus OAuth2 访问令牌（客户端凭证模式）。"""
    global _amadeus_token
    if _amadeus_token:
        return _amadeus_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.amadeus.com/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.AMADEUS_CLIENT_ID,
                "client_secret": settings.AMADEUS_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        _amadeus_token = resp.json()["access_token"]
        return _amadeus_token


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _search_amadeus(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    passengers: int = 1,
    cabin_class: str = "ECONOMY",
) -> list[dict]:
    """通过 Amadeus Flight Offers API 搜索航班。"""
    token = await _get_amadeus_token()
    params = {
        "originLocationCode": origin,           # 出发机场 IATA 代码
        "destinationLocationCode": destination, # 到达机场 IATA 代码
        "departureDate": departure_date,        # 出发日期 YYYY-MM-DD
        "adults": passengers,
        "travelClass": cabin_class.upper(),     # ECONOMY / BUSINESS / FIRST
        "max": 10,                              # 最多返回 10 个结果
    }
    if return_date:
        params["returnDate"] = return_date

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.amadeus.com/v2/shopping/flight-offers",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    # 解析 Amadeus 响应，提取关键字段
    results = []
    for offer in data.get("data", []):
        segments = offer.get("itineraries", [{}])[0].get("segments", [])
        first_seg = segments[0] if segments else {}
        last_seg = segments[-1] if segments else {}
        price_info = offer.get("price", {})
        results.append({
            "source": "amadeus",
            "airline": first_seg.get("carrierCode", ""),
            "flight_number": first_seg.get("number", ""),
            "departure_airport": first_seg.get("departure", {}).get("iataCode", ""),
            "arrival_airport": last_seg.get("arrival", {}).get("iataCode", ""),
            "departure_time": first_seg.get("departure", {}).get("at", ""),
            "arrival_time": last_seg.get("arrival", {}).get("at", ""),
            "stops": len(segments) - 1,         # 中转次数
            "price": float(price_info.get("total", 0)),
            "currency": price_info.get("currency", "USD"),
        })
    return results


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def _search_serpapi_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    passengers: int = 1,
    **kwargs,
) -> list[dict]:
    """通过 SerpAPI Google Flights 引擎搜索航班。"""
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "adults": passengers,
        "api_key": settings.SERPAPI_API_KEY,
    }
    if return_date:
        params["return_date"] = return_date

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    # 解析 Google Flights 结果
    results = []
    for flight in data.get("best_flights", []) + data.get("other_flights", []):
        legs = flight.get("flights", [])
        first = legs[0] if legs else {}
        last = legs[-1] if legs else {}
        results.append({
            "source": "google_flights",
            "airline": first.get("airline", ""),
            "flight_number": first.get("flight_number", ""),
            "departure_airport": first.get("departure_airport", {}).get("id", ""),
            "arrival_airport": last.get("arrival_airport", {}).get("id", ""),
            "departure_time": first.get("departure_airport", {}).get("time", ""),
            "arrival_time": last.get("arrival_airport", {}).get("time", ""),
            "duration_minutes": flight.get("total_duration", 0),
            "stops": len(legs) - 1,
            "price": float(flight.get("price", 0)),
            "currency": "USD",
        })
    return results


async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    passengers: int = 1,
    cabin_class: str = "economy",
) -> list[dict]:
    """聚合所有可用数据源的航班结果，带 Redis 缓存。

    优先尝试 Amadeus，再用 SerpAPI 补充。
    结果按价格升序排列。缓存 30 分钟。
    """
    # 生成缓存 key（基于搜索参数的 MD5 哈希）
    cache_key = "flights:" + hashlib.md5(
        json.dumps({"o": origin, "d": destination, "dep": departure_date, "ret": return_date, "p": passengers}).encode()
    ).hexdigest()

    cached = await cache_get(cache_key)
    if cached:
        return cached

    all_results: list[dict] = []

    # 优先尝试 Amadeus
    if settings.AMADEUS_CLIENT_ID:
        try:
            all_results.extend(await _search_amadeus(origin, destination, departure_date, return_date, passengers, cabin_class))
        except Exception:
            pass

    # SerpAPI 作为备用/补充
    if settings.SERPAPI_API_KEY:
        try:
            all_results.extend(await _search_serpapi_flights(origin, destination, departure_date, return_date, passengers))
        except Exception:
            pass

    # 按价格升序排列
    all_results.sort(key=lambda x: x.get("price", float("inf")))

    # 缓存 30 分钟
    if all_results:
        await cache_set(cache_key, all_results, ttl=1800)

    return all_results
