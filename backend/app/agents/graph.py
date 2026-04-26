"""LangGraph workflow definition.
LangGraph 工作流定义 —— AI 旅行管家的核心编排逻辑。

新架构（ReAct Agent）：
    ┌─────────────┐
    │ coordinator  │ ◄── 用户消息（信息收集阶段）
    └──────┬──────┘
           │
      信息足够吗？ ──否──► INTERRUPT（中断，返回追问给用户）
           │ 是
           ▼
    ┌──────────────────┐
    │  planning_agent  │  ← Phase 1: ReAct 工具调用（天气/航班/酒店/餐厅/景点）
    │                  │  ← Phase 2: JSON mode 综合生成完整行程
    └──────────────────┘
           │
          END
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import AgentState
from app.agents.nodes import (
    coordinator_node,
    flight_node,
    hotel_node,
    weather_node,
    navigation_node,
    restaurant_node,
    recommendation_node,
    itinerary_node,
    budget_node,
)
from app.agents.nodes.coordinator import coordinator_node
from app.agents.nodes.planning_agent import planning_node


def _should_continue(state: AgentState) -> str:
    """条件路由：coordinator 执行后，判断是否需要向用户追问。"""
    if state.needs_user_input:
        return "wait_for_user"    # 信息不足，中断图执行，等用户回复
    return "plan"                 # 信息充足，进入 ReAct 规划阶段


def build_graph(checkpointer=None):
    """构建并编译旅行管家的 Agent 图。

    Args:
        checkpointer: LangGraph 检查点器，用于状态持久化。
                      默认使用 MemorySaver（内存，适合开发）。
                      生产环境应使用 PostgresSaver。
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(AgentState)

    # ── 添加节点 ──────────────────────────────────────────────
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("flight_search", flight_node)
    graph.add_node("hotel_search", hotel_node)
    graph.add_node("weather_check", weather_node)
    graph.add_node("navigation", navigation_node)
    graph.add_node("restaurant_search", restaurant_node)   # 真实餐厅数据
    graph.add_node("recommend_candidates", recommendation_node)  # baseline 个性化候选
    graph.add_node("plan_itinerary", itinerary_node)
    graph.add_node("analyze_budget", budget_node)

    # ── 设置入口点 ──────────────────────────────────────────
    graph.set_entry_point("coordinator")

    # ── coordinator 条件分支 ──────────────────────────────────
    graph.add_conditional_edges(
        "coordinator",
        _should_continue,
        {
            "wait_for_user": END,       # 暂停图，把追问返回给用户
            "plan": "planning_agent",   # 信息充足 → ReAct 规划
        },
    )

    # ── 搜索阶段：依次执行（每个都是快速 API 调用） ──────────
    graph.add_edge("flight_search", "hotel_search")
    graph.add_edge("hotel_search", "weather_check")
    graph.add_edge("weather_check", "navigation")
    graph.add_edge("navigation", "restaurant_search")    # 搜索真实餐厅
    graph.add_edge("restaurant_search", "recommend_candidates")
    graph.add_edge("recommend_candidates", "plan_itinerary")
    graph.add_edge("plan_itinerary", "analyze_budget")
    graph.add_edge("analyze_budget", END)

    return graph.compile(checkpointer=checkpointer)


# 默认编译好的图实例（开发模式，使用内存存储）
travel_agent_graph = build_graph()
