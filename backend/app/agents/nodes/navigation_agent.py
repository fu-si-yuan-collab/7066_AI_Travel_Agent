"""Navigation / routing node – plans routes between activities.
导航路线规划节点 —— 在景点之间规划最优路线。
支持高德地图（国内）和 Google Maps（国际）。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.services.maps_service import plan_route


async def navigation_node(state: AgentState) -> dict:
    """在行程各点之间规划导航路线。"""

    # 没有活动/景点数据时跳过
    if not state.activity_results:
        return {
            "messages": [AIMessage(content="No activities to route between yet.")],
            "navigation_data": {},
        }

    try:
        # 从活动列表中提取有经纬度的点作为途经点
        waypoints = [
            {"name": a.get("name", ""), "lat": a.get("latitude"), "lng": a.get("longitude")}
            for a in state.activity_results
            if a.get("latitude") and a.get("longitude")
        ]
        data = await plan_route(waypoints=waypoints, mode="driving")
        summary = f"Route planned with {len(waypoints)} waypoints."
    except Exception as e:
        data = {}
        summary = f"Navigation error: {e}"

    return {
        "messages": [AIMessage(content=summary)],
        "navigation_data": data,
    }
