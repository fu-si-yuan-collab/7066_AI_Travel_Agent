"""Weather advisory node – fetches weather data for the destination.
天气预报节点 —— 获取目的地的天气数据，辅助行程规划和穿衣建议。
"""

from __future__ import annotations

from langchain.schema import AIMessage

from app.agents.state import AgentState
from app.services.weather_service import get_weather_forecast


async def weather_node(state: AgentState) -> dict:
    """获取目的地旅行日期内的天气预报。"""
    plan = state.travel_plan

    if not plan.destination:
        return {
            "messages": [AIMessage(content="Skipping weather check – no destination.")],
            "weather_data": {},
        }

    try:
        data = await get_weather_forecast(
            location=plan.destination,
            start_date=plan.start_date,
            end_date=plan.end_date,
        )
        summary = f"Weather data retrieved for {plan.destination}."
    except Exception as e:
        data = {}
        summary = f"Weather fetch error: {e}"

    return {
        "messages": [AIMessage(content=summary)],
        "weather_data": data,
    }
