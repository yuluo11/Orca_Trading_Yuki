"""Optional LangChain-backed provider builders."""

from __future__ import annotations

from ..config import LLMConfig
from .client import LLMClient, LangChainRunnableLLMClient


def build_langchain_backed_llm_client(config: LLMConfig) -> LLMClient | None:
    """Build a LangChain-backed client when the provider SDK is installed."""
    if config.provider == "mock" or not config.is_configured:
        return None

    provider = config.provider.lower()
    if provider == "openai_compatible":
        return _build_langchain_openai_client(config)
    if provider in {"anthropic", "claude"}:
        return _build_langchain_anthropic_client(config)
    if provider == "gemini":
        return _build_langchain_gemini_client(config)
    return None


def _build_langchain_openai_client(config: LLMConfig) -> LLMClient | None:
    """Build a ChatOpenAI-backed client when langchain-openai is available."""
    try:
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError:
        return None

    kwargs = {
        "model": config.model or "",
        "temperature": config.temperature,
        "timeout": config.timeout_seconds,
        "max_retries": config.max_retries,
    }
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.base_url:
        kwargs["base_url"] = config.base_url
    if config.max_tokens is not None:
        kwargs["max_tokens"] = config.max_tokens

    return LangChainRunnableLLMClient(
        ChatOpenAI(**kwargs),
        provider_name="openai_compatible",
        model_name=config.model,
        max_retries=config.max_retries,
    )


def _build_langchain_anthropic_client(config: LLMConfig) -> LLMClient | None:
    """Build a ChatAnthropic-backed client when langchain-anthropic is available."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ModuleNotFoundError:
        return None

    kwargs = {
        "model": config.model or "",
        "temperature": config.temperature,
        "timeout": config.timeout_seconds,
        "max_retries": config.max_retries,
    }
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.base_url:
        kwargs["base_url"] = config.base_url
    if config.max_tokens is not None:
        kwargs["max_tokens"] = config.max_tokens

    return LangChainRunnableLLMClient(
        ChatAnthropic(**kwargs),
        provider_name="anthropic",
        model_name=config.model,
        max_retries=config.max_retries,
    )


def _build_langchain_gemini_client(config: LLMConfig) -> LLMClient | None:
    """Build a ChatGoogleGenerativeAI-backed client when the SDK is available."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ModuleNotFoundError:
        return None

    kwargs = {
        "model": config.model or "",
        "temperature": config.temperature,
        "timeout": config.timeout_seconds,
        "max_retries": config.max_retries,
    }
    if config.api_key:
        kwargs["google_api_key"] = config.api_key
    if config.max_tokens is not None:
        kwargs["max_output_tokens"] = config.max_tokens

    return LangChainRunnableLLMClient(
        ChatGoogleGenerativeAI(**kwargs),
        provider_name="gemini",
        model_name=config.model,
        max_retries=config.max_retries,
    )
