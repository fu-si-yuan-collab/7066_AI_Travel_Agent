"""Coordinator node – the entry point of the agent graph.
协调者节点 —— 只负责收集信息和追问，绝不生成行程。
当信息确认后输出固定格式的 confirmed JSON，触发后续搜索流程。
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from app.agents.state import AgentState, TravelPlan
from app.agents.prompts.templates import COORDINATOR_SYSTEM
from app.core.llm import get_llm


async def coordinator_node(state: AgentState) -> dict:
    """收集旅行信息，确认后触发搜索流程。"""

    llm = get_llm(temperature=0.2)

    system_prompt = COORDINATOR_SYSTEM.format(
        user_preferences=json.dumps(state.user_preferences, ensure_ascii=False, default=str),
    )

    messages = [SystemMessage(content=system_prompt)] + state.messages
    response = await llm.ainvoke(messages)
    content = response.content

    # 尝试提取 confirmed JSON（coordinator 确认信息后输出的固定格式）
    plan_data = None
    match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if parsed.get("confirmed"):
                plan_data = parsed
        except json.JSONDecodeError:
            pass

    travel_plan = state.travel_plan

    if plan_data:
        # 从 confirmed JSON 更新 TravelPlan
        budget_per_person = plan_data.get("budget_per_person_cny") or plan_data.get("total_budget_cny", 0)
        travel_plan = TravelPlan(
            destination=plan_data.get("destination", travel_plan.destination),
            origin=plan_data.get("origin", travel_plan.origin),
            start_date=plan_data.get("departure", travel_plan.start_date),
            end_date=plan_data.get("return", travel_plan.end_date),
            num_travelers=plan_data.get("travelers", travel_plan.num_travelers),
            budget=budget_per_person,
            currency=plan_data.get("currency", "CNY"),
            travel_style=plan_data.get("travel_style", travel_plan.travel_style),
            interests=plan_data.get("interests", travel_plan.interests),
            special_requirements=plan_data.get("special_requirements", travel_plan.special_requirements),
        )

    # 信息充足条件：有目的地 + 日期
    has_enough_info = bool(travel_plan.destination and travel_plan.start_date and travel_plan.end_date)

    if has_enough_info:
        # 不把 confirmed JSON 暴露给用户，替换为友好提示
        display_content = content
        if plan_data:
            display_content = f"✅ Got it! Planning your trip to **{travel_plan.destination}** ({travel_plan.start_date} → {travel_plan.end_date}). Searching flights, hotels, weather..."
        return {
            "messages": [AIMessage(content=display_content)],
            "travel_plan": travel_plan,
            "current_step": "searching",
            "needs_user_input": False,
            "pending_question": "",
        }
    else:
        return {
            "messages": [AIMessage(content=content)],
            "travel_plan": travel_plan,
            "current_step": "collecting_info",
            "needs_user_input": True,
            "pending_question": content,
        }
