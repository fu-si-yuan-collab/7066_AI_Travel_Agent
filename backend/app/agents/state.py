"""LangGraph shared state definition.
LangGraph 共享状态定义：状态在图的每个节点之间流转。
每个节点读取需要的字段、写回结果。LangGraph 通过 checkpointer 在每步之后自动持久化状态，
所以对话可以随时恢复。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


@dataclass
class TravelPlan:
    """结构化旅行计划：由 coordinator 节点从用户自然语言输入中提取。"""
    destination: str = ""                          # 目的地
    origin: str = ""                               # 出发地
    start_date: str = ""                           # 出发日期
    end_date: str = ""                             # 返回日期
    num_travelers: int = 1                         # 旅行人数
    budget: float | None = None                    # 总预算
    currency: str = "CNY"                          # 货币单位
    travel_style: str = "balanced"                 # 旅行风格：budget / balanced / luxury
    interests: list[str] = field(default_factory=list)  # 兴趣标签，如 ["beach", "museum"]
    special_requirements: str = ""                 # 特殊需求（无障碍、带小孩等）


@dataclass
class AgentState:
    """中心状态对象：在图的所有节点之间共享。

    ``messages`` 使用 ``add_messages`` reducer，每个节点只需追加新消息，
    而不是替换整个列表。
    """

    # ── 对话历史（自动累积） ──
    messages: Annotated[list[AnyMessage], add_messages] = field(default_factory=list)

    # ── 结构化旅行计划（从用户输入解析） ──
    travel_plan: TravelPlan = field(default_factory=TravelPlan)

    # ── 用户信息（从数据库加载） ──
    user_id: str = ""
    user_preferences: dict[str, Any] = field(default_factory=dict)  # 用户偏好

    # ── 工作流控制 ──
    current_step: str = "initial"      # 当前阶段：initial → collecting_info → searching → planning → complete
    needs_user_input: bool = False      # 是否需要用户补充信息（HITL 中断）
    pending_question: str = ""          # 待回答的问题

    # ── 各专业节点的搜索结果 ──
    flight_results: list[dict] = field(default_factory=list)       # 航班搜索结果
    hotel_results: list[dict] = field(default_factory=list)        # 酒店比价结果
    weather_data: dict[str, Any] = field(default_factory=dict)     # 天气预报数据
    navigation_data: dict[str, Any] = field(default_factory=dict)  # 导航路线数据
    activity_results: list[dict] = field(default_factory=list)     # 景点/活动搜索结果

    # ── 生成的行程 ──
    itinerary: dict[str, Any] = field(default_factory=dict)        # 完整行程规划
    budget_breakdown: dict[str, Any] = field(default_factory=dict) # 预算分解

    # ── ReAct 工具调用记录（用于前端展示 agent actions） ──
    tool_steps: list[dict] = field(default_factory=list)           # 每个工具调用的摘要
    calendar_events: list[dict] = field(default_factory=list)      # 待导入日历的事件列表

    # ── 错误追踪 ──
    errors: list[str] = field(default_factory=list)
