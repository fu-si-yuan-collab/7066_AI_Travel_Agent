"""Real API tools for the ReAct planning agent.
每个工具封装一个真实 API 调用，供 LLM 通过 bind_tools() 动态调用。
"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.services.weather_service import get_weather_forecast
from app.services.flight_service import search_flights as _search_flights
from app.services.hotel_service import search_hotels_multi_platform
from app.services.restaurant_service import search_restaurants as _search_restaurants
from app.services.activity_service import search_activities


@tool
async def search_weather(destination: str, start_date: str, end_date: str) -> str:
    """Get weather forecast for the travel destination during trip dates.
    Always call this first to plan activities and packing appropriately.

    Args:
        destination: City or country name (e.g. "Tokyo", "Bangkok")
        start_date: Trip start date in YYYY-MM-DD format
        end_date: Trip end date in YYYY-MM-DD format
    """
    try:
        result = await get_weather_forecast(destination, start_date, end_date)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def find_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    travelers: int = 1,
) -> str:
    """Search for available flights between cities.
    Call this when user prefers flying or transport preference is unspecified.
    SKIP this tool if user explicitly prefers train, car, bus, or self-driving.

    Args:
        origin: Departure city name or IATA code (e.g. "Shanghai", "PVG")
        destination: Arrival city name or IATA code (e.g. "Tokyo", "NRT")
        departure_date: Outbound date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format
        travelers: Number of passengers (default 1)
    """
    try:
        results = await _search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=travelers,
        )
        return json.dumps(results[:5], ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def find_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    stars: int = 3,
    max_price_per_night: int = 1000,
) -> str:
    """Search for hotels in the destination matching budget and preferences.
    Set max_price_per_night = budget_per_person / trip_duration_days / 2.

    Args:
        destination: City or area name (e.g. "Shinjuku Tokyo")
        check_in: Check-in date in YYYY-MM-DD format
        check_out: Check-out date in YYYY-MM-DD format
        stars: Preferred star rating 1-5 (default 3)
        max_price_per_night: Maximum price per night in CNY (default 1000)
    """
    try:
        results = await search_hotels_multi_platform(
            destination=destination,
            checkin=check_in,
            checkout=check_out,
            guests=1,
            star_rating=float(stars),
            max_price=float(max_price_per_night),
        )
        return json.dumps(results[:6], ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def find_restaurants(destination: str, cuisines: list[str]) -> str:
    """Find real restaurant recommendations in the destination via Google Places.
    Always call this to provide dining options for the trip.

    Args:
        destination: City or area name (e.g. "Tokyo Shinjuku")
        cuisines: List of cuisine types matching user interests
                  (e.g. ["ramen", "sushi"] or ["local food", "street food"])
    """
    try:
        results = await _search_restaurants(
            destination=destination,
            cuisine_keywords=cuisines,
            limit=8,
        )
        return json.dumps(results[:8], ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def find_activities(destination: str, interests: list[str]) -> str:
    """Search for tourist attractions and activities matching user interests.
    Always call this to populate the daily itinerary with real attractions.

    Args:
        destination: City name (e.g. "Tokyo", "Paris")
        interests: User interest tags (e.g. ["culture", "nature", "shopping", "food"])
    """
    try:
        results = await search_activities(
            destination=destination,
            interests=interests,
            limit=10,
        )
        return json.dumps(results[:10], ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
