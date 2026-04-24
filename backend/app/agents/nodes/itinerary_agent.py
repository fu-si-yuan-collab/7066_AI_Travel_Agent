"""Itinerary composition node – builds day-by-day plan using all collected data.
行程编排节点 —— 将所有收集到的数据（机票、酒店、天气、景点、路线）
汇总为一个完整的逐日行程规划。
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from app.agents.state import AgentState
from app.agents.prompts.templates import ITINERARY_AGENT_SYSTEM
from app.core.llm import get_llm


async def itinerary_node(state: AgentState) -> dict:
    """综合所有搜索结果，生成完整行程规划。"""

    # 初始化 LLM（温度稍高，鼓励更丰富的行程建议）
    llm = get_llm(temperature=0.4)

    # 汇总所有搜索结果作为 LLM 的上下文
    context = {
        "travel_plan": {
            "destination": state.travel_plan.destination,
            "origin": state.travel_plan.origin,
            "start_date": state.travel_plan.start_date,
            "end_date": state.travel_plan.end_date,
            "budget": state.travel_plan.budget,
            "travel_style": state.travel_plan.travel_style,
            "interests": state.travel_plan.interests,
        },
        "flights": state.flight_results[:3],       # 只取前3个航班，节省 token
        "hotels": state.hotel_results[:5],          # 前5个酒店
        "weather": state.weather_data,
        "activities": state.activity_results[:10],  # 前10个景点
        "navigation": state.navigation_data,
        "user_preferences": state.user_preferences,
    }

    messages = [
        SystemMessage(content=ITINERARY_AGENT_SYSTEM),
        HumanMessage(content=f"Please create a detailed itinerary based on:\n```json\n{json.dumps(context, ensure_ascii=False, default=str)}\n```"),
    ]

    response = await llm.ainvoke(messages)

    # 尝试从 LLM 回复中解析结构化行程 JSON
    match = re.search(r"```json\s*(.*?)\s*```", response.content, re.DOTALL)
    itinerary = {}
    if match:
        try:
            itinerary = json.loads(match.group(1))
        except json.JSONDecodeError:
            pass  # JSON 解析失败时保持空字典，不阻塞流程

    return {
        "messages": [AIMessage(content=response.content)],
        "itinerary": itinerary,
        "current_step": "budgeting",   # 下一步进入预算分析
    }
