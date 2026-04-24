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
from app.db.repositories.preference_repo import get_user_preferences
from app.models.schemas import ChatRequest, ChatResponse

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

    # 提取最后一条 AI 消息作为回复
    ai_messages = [m for m in result.get("messages", []) if hasattr(m, "content") and m.type == "ai"]
    reply = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process that."

    # 如果生成了完整行程，一并返回
    trip_plan = None
    if result.get("itinerary"):
        trip_plan = result["itinerary"]
    elif result.get("budget_breakdown"):
        trip_plan = {
            "itinerary": result.get("itinerary", {}),
            "budget": result.get("budget_breakdown", {}),
        }

    return ChatResponse(
        reply=reply,
        thread_id=thread_id,
        trip_plan=trip_plan,
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
