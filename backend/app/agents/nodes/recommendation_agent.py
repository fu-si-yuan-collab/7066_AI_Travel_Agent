"""Recommendation node.
在 itinerary 之前输出 baseline Top-K 候选，供最终规划参考。
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.db.database import async_session
from app.recommendations.baseline import rank_candidates_with_baseline


async def recommendation_node(state: AgentState) -> dict:
    """生成个性化推荐候选。"""
    if not state.user_id:
        return {
            "messages": [AIMessage(content="Skipping recommendations – no user context.")],
            "recommended_candidates": [],
        }

    try:
        async with async_session() as db:
            topk = await rank_candidates_with_baseline(db, state, top_k=12)
        summary = f"Generated {len(topk)} personalized candidates (content + collaborative baseline)."
    except Exception as e:
        topk = []
        summary = f"Recommendation baseline error: {e}"

    return {
        "messages": [AIMessage(content=summary)],
        "recommended_candidates": topk,
    }
