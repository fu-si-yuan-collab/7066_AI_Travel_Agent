"""Weather service – OpenWeatherMap integration.
天气服务 —— 通过 OpenWeatherMap API 获取目的地天气预报。
先地理编码（城市名 → 经纬度），再调 5 天预报 API，最后聚合为逐日摘要。
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.cache import cache_get, cache_set

settings = get_settings()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def get_weather_forecast(
    location: str,
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """获取指定地点的天气预报。

    流程：
    1. 地理编码：城市名 → 经纬度
    2. 调用 5 天 / 3 小时预报 API
    3. 聚合为逐日摘要（最低温、最高温、降水概率等）
    """
    cache_key = f"weather:{location}:{start_date}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # 第一步：地理编码（城市名 → 经纬度）
    async with httpx.AsyncClient() as client:
        geo_resp = await client.get(
            "https://api.openweathermap.org/geo/1.0/direct",
            params={"q": location, "limit": 1, "appid": settings.OPENWEATHER_API_KEY},
            timeout=10,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

    if not geo_data:
        return {"error": f"Location '{location}' not found"}

    lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
    # 优先取中文名称
    location_name = geo_data[0].get("local_names", {}).get("zh", geo_data[0].get("name", location))

    # 第二步：调用 5 天 / 3 小时预报 API
    async with httpx.AsyncClient() as client:
        forecast_resp = await client.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "lat": lat,
                "lon": lon,
                "appid": settings.OPENWEATHER_API_KEY,
                "units": "metric",       # 摄氏度
                "lang": "zh_cn",         # 中文天气描述
            },
            timeout=10,
        )
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()

    # 第三步：将 3 小时粒度的数据聚合为逐日摘要
    daily: dict[str, dict] = {}
    for entry in forecast_data.get("list", []):
        date_str = entry["dt_txt"][:10]    # 提取日期部分 YYYY-MM-DD
        main = entry["main"]
        weather = entry["weather"][0] if entry.get("weather") else {}

        if date_str not in daily:
            daily[date_str] = {
                "date": date_str,
                "temp_min": main["temp_min"],       # 最低温度
                "temp_max": main["temp_max"],       # 最高温度
                "humidity": main["humidity"],        # 湿度
                "description": weather.get("description", ""),  # 天气描述
                "icon": weather.get("icon", ""),     # 天气图标代码
                "pop": entry.get("pop", 0),          # 降水概率（0~1）
            }
        else:
            # 同一天内取最低温的最小值、最高温的最大值
            d = daily[date_str]
            d["temp_min"] = min(d["temp_min"], main["temp_min"])
            d["temp_max"] = max(d["temp_max"], main["temp_max"])

    result = {
        "location": location_name,
        "latitude": lat,
        "longitude": lon,
        "daily_forecast": list(daily.values()),
    }

    await cache_set(cache_key, result, ttl=3600)  # 缓存 1 小时
    return result
