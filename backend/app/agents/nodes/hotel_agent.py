"""Hotel comparison node – searches multiple platforms and compares prices.
酒店比价节点 —— 从多个平台搜索酒店，合并结果进行价格对比。
这是我们产品的核心差异化功能：解决不同平台报价混乱的问题。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.services.hotel_service import search_hotels_multi_platform


async def hotel_node(state: AgentState) -> dict:
    """跨平台搜索酒店并比价。"""
    plan = state.travel_plan

    # 目的地缺失则跳过
    if not plan.destination:
        return {
            "messages": [AIMessage(content="Skipping hotel search – no destination specified.")],
            "hotel_results": [],
        }

    prefs = state.user_preferences
    try:
        results = await search_hotels_multi_platform(
            destination=plan.destination,
            checkin=plan.start_date,
            checkout=plan.end_date,
            guests=plan.num_travelers,
            star_rating=prefs.get("preferred_hotel_stars"),    # 用户偏好的星级
            max_price=prefs.get("daily_budget_high"),          # 每晚预算上限
        )
        summary = f"Found {len(results)} hotel options across platforms."
    except Exception as e:
        results = []
        summary = f"Hotel search error: {e}"

    return {
        "messages": [AIMessage(content=summary)],
        "hotel_results": results,
    }
