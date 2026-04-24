"""Coordinator node – the entry point of the agent graph.
协调者节点 —— Agent 图的入口。

职责：
1. 将用户的自然语言输入解析为结构化的 TravelPlan。
2. 判断信息是否充足，决定下一步走向。
3. 信息不足时触发 HITL（Human-in-the-Loop）中断，向用户追问。
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from app.agents.state import AgentState, TravelPlan
from app.agents.prompts.templates import COORDINATOR_SYSTEM
from app.core.llm import get_llm


def _extract_json(text: str) -> dict | None:
    """尝试从 LLM 输出中提取 ```json ... ``` 代码块并解析。"""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


async def coordinator_node(state: AgentState) -> dict:
    """分析用户输入，提取/更新旅行计划，决定下一步流程。"""

    # 初始化 LLM（通过工厂函数，自动指向 Azure AI Foundry）
    llm = get_llm(temperature=0.3)

    # 构建 system prompt，注入用户偏好
    system_prompt = COORDINATOR_SYSTEM.format(
        user_preferences=json.dumps(state.user_preferences, ensure_ascii=False, default=str),
    )

    # 拼接系统提示 + 对话历史，调用 LLM
    messages = [SystemMessage(content=system_prompt)] + state.messages
    response = await llm.ainvoke(messages)
    content = response.content

    # 尝试从 LLM 回复中提取结构化旅行计划
    plan_data = _extract_json(content)
    travel_plan = state.travel_plan

    if plan_data:
        # 用 LLM 提取的字段更新计划（保留已有字段作为回退）
        travel_plan = TravelPlan(
            destination=plan_data.get("destination", travel_plan.destination),
            origin=plan_data.get("origin", travel_plan.origin),
            start_date=plan_data.get("start_date", travel_plan.start_date),
            end_date=plan_data.get("end_date", travel_plan.end_date),
            num_travelers=plan_data.get("num_travelers", travel_plan.num_travelers),
            budget=plan_data.get("budget", travel_plan.budget),
            currency=plan_data.get("currency", travel_plan.currency),
            travel_style=plan_data.get("travel_style", travel_plan.travel_style),
            interests=plan_data.get("interests", travel_plan.interests),
            special_requirements=plan_data.get("special_requirements", travel_plan.special_requirements),
        )

    # 判断关键信息是否齐全：至少需要目的地 + 出发/返回日期
    has_enough_info = bool(travel_plan.destination and travel_plan.start_date and travel_plan.end_date)

    if has_enough_info:
        next_step = "searching"          # 信息充足 → 进入搜索阶段
        needs_input = False
        pending_q = ""
    else:
        next_step = "collecting_info"    # 信息不足 → 中断，向用户追问
        needs_input = True
        pending_q = content              # LLM 的追问内容

    return {
        "messages": [AIMessage(content=content)],
        "travel_plan": travel_plan,
        "current_step": next_step,
        "needs_user_input": needs_input,
        "pending_question": pending_q,
    }
