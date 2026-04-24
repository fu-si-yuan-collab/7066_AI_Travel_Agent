"""Budget analysis node – breaks down costs and suggests tiers.
预算分析节点 —— 根据行程计算总费用，拆分各项开支，
提供 Budget / Balanced / Premium 三档方案。
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from app.agents.state import AgentState
from app.agents.prompts.templates import BUDGET_AGENT_SYSTEM
from app.core.llm import get_llm


async def budget_node(state: AgentState) -> dict:
    """分析预算并生成费用明细。"""

    # 初始化 LLM（低温度，保证数字计算准确）
    llm = get_llm(temperature=0.2)

    # 汇总行程和价格数据
    context = {
        "itinerary": state.itinerary,
        "flights": state.flight_results[:3],
        "hotels": state.hotel_results[:5],
        "budget": state.travel_plan.budget,
        "currency": state.travel_plan.currency,
        "travel_style": state.travel_plan.travel_style,
    }

    messages = [
        SystemMessage(content=BUDGET_AGENT_SYSTEM),
        HumanMessage(content=f"Analyse the budget for this trip:\n```json\n{json.dumps(context, ensure_ascii=False, default=str)}\n```"),
    ]

    response = await llm.ainvoke(messages)

    # 尝试从回复中解析预算明细 JSON
    match = re.search(r"```json\s*(.*?)\s*```", response.content, re.DOTALL)
    breakdown = {}
    if match:
        try:
            breakdown = json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return {
        "messages": [AIMessage(content=response.content)],
        "budget_breakdown": breakdown,
        "current_step": "complete",    # 流程结束
    }
