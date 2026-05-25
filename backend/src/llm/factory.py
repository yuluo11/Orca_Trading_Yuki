"""Factory helpers for building configured LLM clients."""

from __future__ import annotations

import json

from ..config import LLMConfig
from .anthropic_client import AnthropicLLMClient
from .client import LLMClient
from .langchain_factory import build_langchain_backed_llm_client
from .mock_client import MockLLMClient
from .openai_client import OpenAICompatibleLLMClient


def build_configured_llm_client(config: LLMConfig) -> LLMClient | None:
    """Build the default runtime client from app configuration when possible."""
    if config.provider == "mock":
        return MockLLMClient(
            response=config.mock_response or "",
            json_response=_parse_mock_json_response(config.mock_json_response),
        )

    if not config.is_configured:
        return None

    langchain_client = build_langchain_backed_llm_client(config)
    if langchain_client is not None:
        return langchain_client

    if config.provider == "openai_compatible":
        return OpenAICompatibleLLMClient(
            api_key=config.api_key or "",
            model=config.model or "",
            base_url=config.base_url or "https://api.openai.com/v1",
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            max_retries=config.max_retries,
        )

    if config.provider in {"anthropic", "claude"}:
        return AnthropicLLMClient(
            api_key=config.api_key or "",
            model=config.model or "",
            base_url=config.base_url or "https://api.anthropic.com",
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            max_retries=config.max_retries,
        )

    raise ValueError(f"Unsupported LLM provider: {config.provider}")


def _parse_mock_json_response(value: str | None) -> dict[str, object] | None:
    """Parse a JSON-like mock response string when present."""
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("ORCA_LLM_MOCK_JSON_RESPONSE must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("ORCA_LLM_MOCK_JSON_RESPONSE must decode to a JSON object")
    return parsed
