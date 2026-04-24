"""LLM factory – creates a configured LangChain chat model.
LLM 工厂 —— 统一创建 LLM 实例，所有 Agent 节点都通过这里获取 LLM。

Azure AI Foundry 资源级 endpoint 兼容 OpenAI API 格式：
  POST {endpoint}/models/chat/completions?api-version=2024-05-01-preview
  Authorization: Bearer {key}

使用 ChatOpenAI + custom base_url 来对接，无需 AzureChatOpenAI。
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import get_settings

settings = get_settings()


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    """返回配置好的 LLM 实例（指向 Azure AI Foundry 资源级 endpoint）。

    Foundry 资源级 endpoint 兼容 OpenAI Chat Completions API，
    只需把 base_url 指向 {endpoint}/models，用 Bearer token 认证即可。
    """
    endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
    api_version = settings.AZURE_OPENAI_API_VERSION

    return ChatOpenAI(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        # Foundry 的 OpenAI 兼容路径：/models，加上 api-version 查询参数
        base_url=f"{endpoint}/models",
        default_query={"api-version": api_version},
        default_headers={"Authorization": f"Bearer {settings.AZURE_OPENAI_API_KEY}"},
        temperature=temperature,
    )
