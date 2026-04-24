"""Maps / Navigation service – supports both Gaode (AMap) and Google Maps.
地图导航服务 —— 支持高德地图和 Google Maps 双引擎。
国内路线优先使用高德（Gaode/AMap），国际路线使用 Google Maps。

注意：高德 API 坐标格式是 lng,lat（经度在前），Google 是 lat,lng（纬度在前）。
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.cache import cache_get, cache_set

settings = get_settings()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def _amap_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str = "driving",
) -> dict:
    """通过高德地图 API 规划路线。"""
    # 高德支持的出行方式对应不同端点
    mode_endpoints = {
        "driving": "https://restapi.amap.com/v3/direction/driving",     # 驾车
        "transit": "https://restapi.amap.com/v3/direction/transit/integrated",  # 公交
        "walking": "https://restapi.amap.com/v3/direction/walking",     # 步行
    }
    url = mode_endpoints.get(mode, mode_endpoints["driving"])

    params = {
        "key": settings.AMAP_API_KEY,
        "origin": f"{origin[1]},{origin[0]}",        # 高德用 lng,lat 格式
        "destination": f"{destination[1]},{destination[0]}",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

    route_info = data.get("route", {})
    paths = route_info.get("paths", route_info.get("transits", []))
    if not paths:
        return {"error": "No route found"}

    best = paths[0]  # 取最优路线
    return {
        "provider": "amap",
        "mode": mode,
        "distance_meters": int(best.get("distance", 0)),   # 距离（米）
        "duration_seconds": int(best.get("duration", 0)),   # 耗时（秒）
        "steps": len(best.get("steps", [])),                # 导航步骤数
    }


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def _google_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str = "driving",
) -> dict:
    """通过 Google Maps Directions API 规划路线。"""
    params = {
        "origin": f"{origin[0]},{origin[1]}",        # Google 用 lat,lng 格式
        "destination": f"{destination[0]},{destination[1]}",
        "mode": mode,
        "key": settings.GOOGLE_MAPS_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    routes = data.get("routes", [])
    if not routes:
        return {"error": "No route found"}

    leg = routes[0]["legs"][0]
    return {
        "provider": "google_maps",
        "mode": mode,
        "distance_meters": leg["distance"]["value"],
        "duration_seconds": leg["duration"]["value"],
        "distance_text": leg["distance"]["text"],     # 可读距离（如 "5.2 km"）
        "duration_text": leg["duration"]["text"],      # 可读耗时（如 "12 mins"）
        "start_address": leg.get("start_address", ""),
        "end_address": leg.get("end_address", ""),
    }


async def plan_route(
    waypoints: list[dict],
    mode: str = "driving",
) -> dict:
    """规划多途经点路线。

    每个途经点格式：{"name": str, "lat": float, "lng": float}
    返回相邻途经点之间的路线段以及总距离和总耗时。
    """
    if len(waypoints) < 2:
        return {"segments": [], "total_duration_seconds": 0, "total_distance_meters": 0}

    cache_key = f"route:{hash(str(waypoints))}:{mode}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    segments = []
    total_duration = 0
    total_distance = 0

    # 逐段规划：从 waypoint[i] 到 waypoint[i+1]
    for i in range(len(waypoints) - 1):
        orig = (waypoints[i]["lat"], waypoints[i]["lng"])
        dest = (waypoints[i + 1]["lat"], waypoints[i + 1]["lng"])

        segment = None
        # 优先使用高德（国内路线）
        if settings.AMAP_API_KEY:
            try:
                segment = await _amap_route(orig, dest, mode)
            except Exception:
                pass

        # 高德失败或不可用时，尝试 Google Maps
        if segment is None and settings.GOOGLE_MAPS_API_KEY:
            try:
                segment = await _google_route(orig, dest, mode)
            except Exception:
                pass

        if segment and "error" not in segment:
            segment["from"] = waypoints[i]["name"]
            segment["to"] = waypoints[i + 1]["name"]
            total_duration += segment.get("duration_seconds", 0)
            total_distance += segment.get("distance_meters", 0)
            segments.append(segment)

    result = {
        "segments": segments,
        "total_duration_seconds": total_duration,
        "total_distance_meters": total_distance,
    }

    await cache_set(cache_key, result, ttl=3600)  # 缓存 1 小时
    return result
