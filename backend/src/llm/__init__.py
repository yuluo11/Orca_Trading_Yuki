"""Shared LLM integration layer."""

from .anthropic_client import AnthropicLLMClient
from .client import (
    LLMClient,
    LLMRunnable,
    LangChainRunnableLLMClient,
    ensure_llm_client,
    extract_text_content,
)
from .factory import build_configured_llm_client
from .langchain_factory import build_langchain_backed_llm_client
from .mock_client import MockLLMClient
from .openai_client import OpenAICompatibleLLMClient

__all__ = [
    "AnthropicLLMClient",
    "LLMClient",
    "LLMRunnable",
    "LangChainRunnableLLMClient",
    "MockLLMClient",
    "OpenAICompatibleLLMClient",
    "build_configured_llm_client",
    "build_langchain_backed_llm_client",
    "ensure_llm_client",
    "extract_text_content",
]
