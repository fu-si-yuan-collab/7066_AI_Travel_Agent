"""Restaurant search node – fetches real restaurant data via Google Places API.
餐厅搜索节点 —— 用 Google Places API 获取真实餐厅数据，
替代 LLM 凭空生成的餐厅推荐，提供真实评分、地址、营业时间。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.services.restaurant_service import search_restaurants


async def restaurant_node(state: AgentState) -> dict:
    """Search real restaurants for the destination based on user interests."""
    plan = state.travel_plan

    if not plan.destination:
        return {
            "messages": [AIMessage(content="Skipping restaurant search – no destination.")],
            "activity_results": state.activity_results,
        }

    # Extract cuisine interests from user preferences
    cuisine_keywords = []
    prefs = state.user_preferences
    if prefs.get("preferred_cuisine"):
        cuisine_keywords = [c.strip() for c in prefs["preferred_cuisine"].split(",") if c.strip()]

    # Also extract from interests
    food_keywords = [i for i in (plan.interests or []) if any(
        w in i.lower() for w in ["food", "ramen", "sushi", "restaurant", "dining", "cuisine", "izakaya", "美食", "餐"]
    )]
    cuisine_keywords.extend(food_keywords[:2])

    if not cuisine_keywords:
        cuisine_keywords = ["local food"]

    try:
        restaurants = await search_restaurants(
            destination=plan.destination,
            cuisine_keywords=cuisine_keywords,
            limit=6,
        )
        summary = f"Found {len(restaurants)} real restaurants via Google Places."
    except Exception as e:
        restaurants = []
        summary = f"Restaurant search error: {e}"

    # Merge into activity_results so itinerary_agent can use them
    existing = state.activity_results or []
    restaurant_activities = [
        {**r, "category": "restaurant"}
        for r in restaurants
    ]

    return {
        "messages": [AIMessage(content=summary)],
        "activity_results": existing + restaurant_activities,
    }
