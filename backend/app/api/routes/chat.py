"""Chat endpoint – the main conversational interface to the AI Travel Agent.
聊天接口 —— AI 旅行管家的核心对话入口。
支持普通请求-响应模式和 SSE 流式推送两种方式。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage

from app.agents.graph import travel_agent_graph
from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.repositories.interaction_repo import log_interaction_event
from app.db.repositories.preference_repo import get_user_preferences
from app.models.schemas import ChatRequest, ChatResponse
from app.services.preference_learning import learn_from_interaction

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user_id: str = Depends(get_current_user_id),   # 从 JWT token 中提取用户 ID
    db=Depends(get_db),                              # 注入数据库会话
):
    """向 AI 旅行管家发送消息并获取回复。

    通过 thread_id 维护多轮对话状态。
    传入相同的 thread_id 即可继续之前的对话。
    """
    thread_id = req.thread_id or str(uuid.uuid4())  # 没有 thread_id 则创建新会话

    # 从数据库加载用户偏好，用于个性化推荐
    prefs = await get_user_preferences(db, user_id)
    prefs_dict = {
        "preferred_travel_style": prefs.preferred_travel_style if prefs else "balanced",
        "preferred_transport": prefs.preferred_transport if prefs else "any",
        "preferred_hotel_stars": prefs.preferred_hotel_stars if prefs else 3.0,
        "preferred_cuisine": prefs.preferred_cuisine if prefs else "",
        "daily_budget_low": prefs.daily_budget_low if prefs else 300,
        "daily_budget_high": prefs.daily_budget_high if prefs else 1000,
        "currency": prefs.currency if prefs else "CNY",
        "learned_tags": prefs.learned_tags if prefs else {},
    }

    # 调用 LangGraph Agent 图
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "messages": [HumanMessage(content=req.message)],
        "user_id": user_id,
        "user_preferences": prefs_dict,
    }

    result = await travel_agent_graph.ainvoke(input_state, config=config)

    # 记录聊天提交事件（数据闭环）
    try:
        await log_interaction_event(
            db,
            user_id,
            event_type="chat_submit",
            item_type="chat",
            item_id=thread_id,
            session_id=thread_id,
            item_title=req.message[:120],
            destination=str(result.get("travel_plan", {}).destination if result.get("travel_plan") else ""),
            travel_style=prefs_dict.get("preferred_travel_style", ""),
            budget=float(prefs_dict.get("daily_budget_high", 0) or 0),
            currency=prefs_dict.get("currency", "CNY"),
            metadata_json={"message_length": len(req.message)},
        )
        await learn_from_interaction(
            db,
            user_id=user_id,
            event_type="chat_submit",
            item_type="chat",
            item_id=thread_id,
            item_title=req.message[:120],
            destination=str(result.get("travel_plan", {}).destination if result.get("travel_plan") else ""),
            metadata_json={"travel_style": prefs_dict.get("preferred_travel_style", "")},
        )
    except Exception:
        pass

    # 提取最后一条 AI 消息作为回复
    ai_messages = [m for m in result.get("messages", []) if hasattr(m, "content") and m.type == "ai"]
    last_content = ai_messages[-1].content if ai_messages else ""

    # 如果 itinerary 节点生成了结构化 JSON，直接把 JSON 字符串作为 reply
    # 前端的 parseTripJSON() 会自动检测并渲染成卡片
    import json, re
    itinerary = result.get("itinerary", {})
    recommended_candidates = result.get("recommended_candidates", [])
    if itinerary:
        # 把 baseline Top-K 一并放入 trip_plan，前端可展示“个性化候选来源”
        merged_trip_plan = {
            **itinerary,
            "recommended_candidates": recommended_candidates[:8],
        }
        reply = json.dumps(merged_trip_plan, ensure_ascii=False)
        trip_plan = merged_trip_plan
    else:
        # 没有完整行程（信息不足，还在追问阶段）—— 返回自然语言回复
        # 尝试从最后一条消息里提取 JSON block（itinerary_agent 可能把 JSON 嵌在文字里）
        match = re.search(r"```json\s*([\s\S]*?)\s*```", last_content)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if parsed.get("destination") or parsed.get("daily_itinerary"):
                    reply = match.group(1).strip()
                    trip_plan = parsed
                else:
                    reply = last_content
                    trip_plan = None
            except json.JSONDecodeError:
                reply = last_content
                trip_plan = None
        else:
            reply = last_content or "I'm sorry, I couldn't process that."
            trip_plan = None

    try:
        await log_interaction_event(
            db,
            user_id,
            event_type="chat_response",
            item_type="chat",
            item_id=thread_id,
            session_id=thread_id,
            item_title=(reply or "")[:120],
            destination=str((trip_plan or {}).get("destination", "") if isinstance(trip_plan, dict) else ""),
            travel_style=prefs_dict.get("preferred_travel_style", ""),
            budget=float(prefs_dict.get("daily_budget_high", 0) or 0),
            currency=prefs_dict.get("currency", "CNY"),
            metadata_json={"has_trip_plan": bool(trip_plan)},
        )
        await learn_from_interaction(
            db,
            user_id=user_id,
            event_type="chat_response",
            item_type="chat",
            item_id=thread_id,
            item_title=(reply or "")[:120],
            destination=str((trip_plan or {}).get("destination", "") if isinstance(trip_plan, dict) else ""),
            metadata_json={"travel_style": prefs_dict.get("preferred_travel_style", "")},
        )
    except Exception:
        pass

    return ChatResponse(
        reply=reply,
        thread_id=thread_id,
        trip_plan=trip_plan,
        tool_steps=result.get("tool_steps") or None,
        calendar_events=result.get("calendar_events") or None,
    )


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """流式版本 —— 通过 Server-Sent Events (SSE) 实时推送 Agent 输出。
    前端可以用 EventSource 或 fetch + ReadableStream 来消费。
    """
    from fastapi.responses import StreamingResponse

    thread_id = req.thread_id or str(uuid.uuid4())

    prefs = await get_user_preferences(db, user_id)
    prefs_dict = {
        "preferred_travel_style": prefs.preferred_travel_style if prefs else "balanced",
        "preferred_transport": prefs.preferred_transport if prefs else "any",
        "preferred_hotel_stars": prefs.preferred_hotel_stars if prefs else 3.0,
        "daily_budget_low": prefs.daily_budget_low if prefs else 300,
        "daily_budget_high": prefs.daily_budget_high if prefs else 1000,
        "currency": prefs.currency if prefs else "CNY",
    }

    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "messages": [HumanMessage(content=req.message)],
        "user_id": user_id,
        "user_preferences": prefs_dict,
    }

    async def event_generator():
        """异步生成器：遍历 LangGraph 事件流，逐 token 推送。"""
        async for event in travel_agent_graph.astream_events(input_state, config=config, version="v2"):
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                # LLM 正在生成 token
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield f"data: {chunk.content}\n\n"
            elif kind == "on_chain_end":
                # 某个节点执行完毕
                node = event.get("name", "")
                if node:
                    yield f"event: node_complete\ndata: {node}\n\n"
        yield "event: done\ndata: [DONE]\n\n"  # 流结束标记

    return StreamingResponse(event_generator(), media_type="text/event-stream")
