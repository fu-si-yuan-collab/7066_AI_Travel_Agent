"""Planning agent node – two-phase ReAct + JSON synthesis.
规划节点 —— 两阶段：
  Phase 1: ReAct 循环，LLM 动态调用真实 API 工具收集数据
  Phase 2: JSON mode 综合，用相同的固定 schema 生成行程（保证输出稳定性）
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage

from app.agents.state import AgentState
from app.agents.tools import search_weather, find_flights, find_hotels, find_restaurants, find_activities
from app.agents.prompts.templates import REACT_GATHERING_SYSTEM, ITINERARY_AGENT_SYSTEM
from app.core.llm import get_llm


_TOOLS = [search_weather, find_flights, find_hotels, find_restaurants, find_activities]
_TOOLS_DICT = {t.name: t for t in _TOOLS}


def _summarize_tool_result(tool_name: str, result_str: str) -> str:
    """从工具返回的 JSON 字符串中提取人类可读摘要。"""
    try:
        data = json.loads(result_str)
    except Exception:
        return tool_name.replace("_", " ")

    if isinstance(data, dict) and data.get("error"):
        return f"{tool_name}: error - {str(data['error'])[:60]}"

    if tool_name == "search_weather":
        if isinstance(data, list) and data:
            lows = [d.get("temp_min", 0) for d in data if isinstance(d, dict)]
            highs = [d.get("temp_max", 0) for d in data if isinstance(d, dict)]
            cond = data[0].get("description", "") if isinstance(data[0], dict) else ""
            low = min(lows) if lows else 0
            high = max(highs) if highs else 0
            return f"Weather: {low:.0f}–{high:.0f}°C, {cond}"
        return "Weather data retrieved"

    elif tool_name == "find_flights":
        if isinstance(data, list) and data:
            prices = [f.get("price", f.get("total_price", 0)) for f in data if isinstance(f, dict)]
            prices = [p for p in prices if isinstance(p, (int, float)) and p > 0]
            if prices:
                return f"Found {len(data)} flights, cheapest ¥{min(prices):,.0f}"
            return f"Found {len(data)} flight options"
        return "No flights found"

    elif tool_name == "find_hotels":
        if isinstance(data, list) and data:
            prices = [
                h.get("price_per_night", h.get("price", h.get("rate_per_night", 0)))
                for h in data if isinstance(h, dict)
            ]
            prices = [p for p in prices if isinstance(p, (int, float)) and p > 0]
            if prices:
                return f"Found {len(data)} hotels, from ¥{min(prices):,.0f}/night"
            return f"Found {len(data)} hotels"
        return "No hotels found"

    elif tool_name == "find_restaurants":
        if isinstance(data, list):
            return f"Found {len(data)} restaurants"
        return "Restaurant data retrieved"

    elif tool_name == "find_activities":
        if isinstance(data, list):
            return f"Found {len(data)} attractions & activities"
        return "Activity data retrieved"

    return tool_name.replace("_", " ")


def _extract_calendar_events(itinerary: dict) -> list[dict]:
    """从行程 JSON 中提取日历事件列表（每个活动 + 酒店入住）。"""
    events = []
    for day in itinerary.get("daily_itinerary", []):
        date = day.get("date", "")
        if not date:
            continue
        for activity in day.get("activities", []):
            m = re.match(r"(\d{2}):(\d{2})", str(activity))
            time = f"{m.group(1)}:{m.group(2)}" if m else "09:00"
            # Remove time prefix and emoji, keep text before " — "
            title = re.sub(r"^\d{2}:\d{2}\s*[·•]\s*", "", str(activity))
            title = re.sub(r"\s*—.*$", "", title).strip()[:75]
            events.append({
                "date": date,
                "time": time,
                "title": title or str(activity)[:75],
                "description": str(activity)[:200],
            })
        hotel = day.get("hotel_for_tonight", {})
        if isinstance(hotel, dict) and hotel.get("name"):
            events.append({
                "date": date,
                "time": "15:00",
                "title": f"Check-in: {hotel['name']}",
                "description": hotel.get("highlights", ""),
            })
    return events


async def planning_node(state: AgentState) -> dict:
    """两阶段规划：ReAct 工具调用 + JSON mode 综合输出。"""

    # ── 构建上下文 ──────────────────────────────────────────────────────────
    plan = state.travel_plan
    context = json.dumps({
        "travel_plan": {
            "destination": plan.destination,
            "origin": plan.origin,
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "budget_per_person_cny": plan.budget,
            "total_budget_cny": (plan.budget or 0) * (plan.num_travelers or 1),
            "travelers": plan.num_travelers,
            "travel_style": plan.travel_style,
            "interests": plan.interests,
            "special_requirements": plan.special_requirements,
        },
        "user_preferences": state.user_preferences,
    }, ensure_ascii=False, default=str)

    # ── PHASE 1: ReAct 工具调用循环 ─────────────────────────────────────────
    llm_with_tools = get_llm(temperature=0.3).bind_tools(_TOOLS)
    messages = [
        SystemMessage(content=REACT_GATHERING_SYSTEM),
        HumanMessage(content=f"Gather travel data for this trip:\n{context}"),
    ]
    tool_steps: list[dict] = []

    for _ in range(8):  # 最多 8 轮，防止无限循环
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break  # LLM 不再调用工具，进入综合阶段

        for tc in response.tool_calls:
            tool_fn = _TOOLS_DICT.get(tc["name"])
            if not tool_fn:
                continue
            try:
                raw_result = await tool_fn.ainvoke(tc["args"])
                # ainvoke returns the tool's return value (str in our case)
                result_str = raw_result if isinstance(raw_result, str) else json.dumps(raw_result, ensure_ascii=False, default=str)
                status = "success"
                try:
                    result_data = json.loads(result_str)
                except Exception:
                    result_data = {}
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                result_data = {}
                status = "error"

            tool_steps.append({
                "tool": tc["name"],
                "status": status,
                "args": tc["args"],
                "summary": _summarize_tool_result(tc["name"], result_str),
                "result": result_data,
            })
            messages.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))

    # ── PHASE 2: JSON mode 综合，使用与之前相同的固定 schema ────────────────
    gathered = {s["tool"]: s["result"] for s in tool_steps if s["status"] == "success"}
    synthesis_input = {
        **json.loads(context),
        "tool_results": gathered,
    }

    llm_json = get_llm(temperature=0.3).bind(response_format={"type": "json_object"})
    final_response = await llm_json.ainvoke([
        SystemMessage(content=ITINERARY_AGENT_SYSTEM),
        HumanMessage(content=(
            f"Generate the complete trip plan using the real data from tool results:\n"
            f"{json.dumps(synthesis_input, ensure_ascii=False, default=str)}"
        )),
    ])

    try:
        itinerary = json.loads(final_response.content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", final_response.content)
        try:
            itinerary = json.loads(match.group(0)) if match else {}
        except Exception:
            itinerary = {}

    calendar_events = _extract_calendar_events(itinerary)

    return {
        "messages": [AIMessage(content=final_response.content)],
        "itinerary": itinerary,
        "tool_steps": tool_steps,
        "calendar_events": calendar_events,
        "current_step": "complete",
    }
