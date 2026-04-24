"""Flight search node – queries flight APIs and returns comparison results.
机票搜索节点 —— 调用航班 API，返回多平台比价结果。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.services.flight_service import search_flights


async def flight_node(state: AgentState) -> dict:
    """根据旅行计划搜索航班。"""
    plan = state.travel_plan

    # 如果出发地或目的地缺失，跳过搜索
    if not plan.origin or not plan.destination:
        return {
            "messages": [AIMessage(content="Skipping flight search – origin or destination not specified.")],
            "flight_results": [],
        }

    try:
        results = await search_flights(
            origin=plan.origin,
            destination=plan.destination,
            departure_date=plan.start_date,
            return_date=plan.end_date,
            passengers=plan.num_travelers,
            cabin_class=state.user_preferences.get("preferred_transport", "economy"),
        )
        summary = f"Found {len(results)} flight options."
    except Exception as e:
        results = []
        summary = f"Flight search error: {e}"

    return {
        "messages": [AIMessage(content=summary)],
        "flight_results": results,
    }
