"""Restaurant search service using Google Places API.
餐厅搜索服务 —— 使用 Google Places API 获取真实餐厅数据。
同一个 GOOGLE_MAPS_API_KEY 即可调用，无需额外申请。
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.cache import cache_get, cache_set

settings = get_settings()

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def search_restaurants(
    destination: str,
    cuisine_keywords: list[str] | None = None,
    limit: int = 8,
) -> list[dict]:
    """Search real restaurants via Google Places API.

    Args:
        destination: City or area name (e.g. "Shinjuku Tokyo")
        cuisine_keywords: e.g. ["ramen", "sushi", "izakaya"]
        limit: Max results to return

    Returns:
        List of restaurant dicts with name, rating, address, price_level, etc.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        return []

    keywords = " ".join(cuisine_keywords[:2]) if cuisine_keywords else "restaurant"
    query = f"{keywords} restaurant in {destination}"

    cache_key = f"restaurants:{query}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Step 1: Text search to find restaurants
    async with httpx.AsyncClient(timeout=15) as c:
        resp = await c.get(
            f"{PLACES_BASE}/textsearch/json",
            params={
                "query": query,
                "type": "restaurant",
                "key": settings.GOOGLE_MAPS_API_KEY,
                "language": "en",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    places = data.get("results", [])[:limit]

    for place in places:
        # Step 2: Get place details for opening hours and reviews
        place_id = place.get("place_id", "")
        details = {}
        if place_id:
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    det_resp = await c.get(
                        f"{PLACES_BASE}/details/json",
                        params={
                            "place_id": place_id,
                            "fields": "name,rating,formatted_address,price_level,opening_hours,reviews,website,formatted_phone_number,user_ratings_total",
                            "key": settings.GOOGLE_MAPS_API_KEY,
                            "language": "en",
                        },
                    )
                    det_resp.raise_for_status()
                    details = det_resp.json().get("result", {})
            except Exception:
                pass

        # Price level: 0=Free, 1=Inexpensive, 2=Moderate, 3=Expensive, 4=Very Expensive
        price_level = details.get("price_level") or place.get("price_level", 2)
        price_map = {0: "Free", 1: "¥", 2: "¥¥", 3: "¥¥¥", 4: "¥¥¥¥"}
        # Rough CNY estimate per person
        price_cny_map = {0: 0, 1: 50, 2: 120, 3: 250, 4: 500}

        # Extract top review snippet
        reviews = details.get("reviews", [])
        top_review = reviews[0].get("text", "")[:100] if reviews else ""

        # Opening hours today
        opening_hours = details.get("opening_hours", {})
        open_now = opening_hours.get("open_now")
        weekday_text = opening_hours.get("weekday_text", [])

        results.append({
            "name": details.get("name") or place.get("name", ""),
            "address": details.get("formatted_address") or place.get("formatted_address", ""),
            "rating": details.get("rating") or place.get("rating", 0),
            "user_ratings_total": details.get("user_ratings_total") or place.get("user_ratings_total", 0),
            "price_level": price_level,
            "price_symbol": price_map.get(price_level, "¥¥"),
            "avg_price_cny": price_cny_map.get(price_level, 120),
            "open_now": open_now,
            "opening_hours": weekday_text[:3] if weekday_text else [],  # first 3 days
            "top_review": top_review,
            "website": details.get("website", ""),
            "phone": details.get("formatted_phone_number", ""),
            "place_id": place_id,
            "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "",
            "photo_reference": (place.get("photos") or [{}])[0].get("photo_reference", ""),
            "types": place.get("types", []),
            "latitude": place.get("geometry", {}).get("location", {}).get("lat"),
            "longitude": place.get("geometry", {}).get("location", {}).get("lng"),
        })

    if results:
        await cache_set(cache_key, results, ttl=86400)  # cache 24h

    return results


def get_photo_url(photo_reference: str, max_width: int = 400) -> str:
    """Build a Google Places photo URL from a photo reference."""
    if not photo_reference or not settings.GOOGLE_MAPS_API_KEY:
        return ""
    return (
        f"{PLACES_BASE}/photo"
        f"?maxwidth={max_width}"
        f"&photo_reference={photo_reference}"
        f"&key={settings.GOOGLE_MAPS_API_KEY}"
    )
