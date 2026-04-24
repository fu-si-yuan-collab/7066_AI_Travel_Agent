"""Itinerary composition node – builds day-by-day plan using all collected data.
行程编排节点 —— 强制使用 JSON mode 输出，确保格式完全固定。
"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from app.agents.state import AgentState
from app.agents.prompts.templates import ITINERARY_AGENT_SYSTEM
from app.core.llm import get_llm


async def itinerary_node(state: AgentState) -> dict:
    """综合所有搜索结果，生成完整行程规划（强制 JSON 输出）。"""

    # 使用 JSON mode 强制输出纯 JSON，不允许任何自然语言文本
    llm = get_llm(temperature=0.3).bind(
        response_format={"type": "json_object"}
    )

    # 汇总所有搜索结果作为上下文
    context = {
        "travel_plan": {
            "destination": state.travel_plan.destination,
            "origin": state.travel_plan.origin,
            "start_date": state.travel_plan.start_date,
            "end_date": state.travel_plan.end_date,
            "budget_per_person_cny": state.travel_plan.budget,
            "total_budget_cny": (state.travel_plan.budget or 0) * (state.travel_plan.num_travelers or 1),
            "travelers": state.travel_plan.num_travelers,
            "travel_style": state.travel_plan.travel_style,
            "interests": state.travel_plan.interests,
            "special_requirements": state.travel_plan.special_requirements,
        },
        "flights": state.flight_results[:3],
        "hotels": state.hotel_results[:5],
        "weather": state.weather_data,
        "restaurants": [a for a in state.activity_results if a.get("category") == "restaurant"][:6],
        "attractions": [a for a in state.activity_results if a.get("category") != "restaurant"][:6],
        "navigation": state.navigation_data,
        "user_preferences": state.user_preferences,
    }

    messages = [
        SystemMessage(content=ITINERARY_AGENT_SYSTEM),
        HumanMessage(content=f"Generate the trip plan for this request:\n{json.dumps(context, ensure_ascii=False, default=str)}"),
    ]

    response = await llm.ainvoke(messages)

    # JSON mode 保证输出是纯 JSON，直接解析
    try:
        itinerary = json.loads(response.content)
    except json.JSONDecodeError:
        # 极少数情况下仍然失败，尝试提取 JSON block
        import re
        match = re.search(r"\{[\s\S]*\}", response.content)
        try:
            itinerary = json.loads(match.group(0)) if match else {}
        except Exception:
            itinerary = {}

    return {
        "messages": [AIMessage(content=response.content)],
        "itinerary": itinerary,
        "current_step": "budgeting",
    }
