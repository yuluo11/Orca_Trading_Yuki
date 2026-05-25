"""LLM client abstractions and adapters for analyst agents."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from typing import Any, Callable, Protocol, TypeVar


logger = logging.getLogger(__name__)
RetryableOperation = TypeVar("RetryableOperation")


class LLMClient(Protocol):
    """Stable client interface consumed by analyst agents."""

    def invoke(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Any:
        """Invoke the model for free-form output."""

    def invoke_json(
        self,
        prompt: str,
        *,
        payload: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke the model and normalize the output into a JSON object."""

    def stream(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Iterator[str]:
        """Stream text chunks from the model when available."""


class LLMRunnable(Protocol):
    """Minimal invocation interface for LangChain-compatible runnables."""

    def invoke(self, input: Any, config: dict[str, Any] | None = None) -> Any:
        """Invoke the runnable with a prompt string or message list."""

    def stream(self, input: Any, config: dict[str, Any] | None = None) -> Iterator[Any]:
        """Stream chunk-like outputs from the runnable when supported."""


class LangChainRunnableLLMClient:
    """Adapt a LangChain-style runnable/chat model into the shared client interface."""

    def __init__(
        self,
        runnable: LLMRunnable,
        *,
        provider_name: str = "langchain_runnable",
        model_name: str | None = None,
        max_retries: int = 2,
    ) -> None:
        self.runnable = runnable
        self.provider_name = provider_name
        self.model_name = model_name
        self.max_retries = max(0, max_retries)

    def invoke(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Any:
        """Invoke the wrapped runnable with normalized prompt input."""
        llm_input = self._build_input(prompt, payload=payload)
        payload_keys = sorted((payload or {}).keys())
        return invoke_with_logging(
            lambda: self.runnable.invoke(llm_input),
            provider_name=self.provider_name,
            model_name=self.model_name,
            operation_name="invoke",
            payload_keys=payload_keys,
        )

    def invoke_json(
        self,
        prompt: str,
        *,
        payload: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke the runnable and parse the response as JSON when possible."""
        structured_prompt = prompt
        if schema:
            structured_prompt = (
                f"{prompt}\n\n"
                "Output schema:\n"
                f"{json.dumps(schema, ensure_ascii=False, indent=2)}"
            )
        response = self.invoke(structured_prompt, payload=payload)
        return parse_json_response(response)

    def stream(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Iterator[str]:
        """Stream text chunks from the runnable when supported, else fall back to one chunk."""
        llm_input = self._build_input(prompt, payload=payload)
        payload_keys = sorted((payload or {}).keys())

        stream_method = getattr(self.runnable, "stream", None)
        if callable(stream_method):
            yield from stream_with_logging(
                lambda: stream_method(llm_input),
                provider_name=self.provider_name,
                model_name=self.model_name,
                operation_name="stream",
                payload_keys=payload_keys,
            )
            return

        response = self.invoke(prompt, payload=payload)
        text = extract_text_content(response)
        if text:
            yield text

    def _build_input(self, prompt: str, *, payload: dict[str, Any] | None) -> Any:
        """Build a string or message-list input suitable for a runnable."""
        if payload is None:
            return prompt

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
        except ModuleNotFoundError:
            return (
                f"{prompt}\n\n"
                "Context JSON:\n"
                f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
            )

        return [
            SystemMessage(content=prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2)),
        ]

def ensure_llm_client(
    *,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> LLMClient | None:
    """Return a stable llm_client, adapting raw runnables when necessary."""
    if llm_client is not None:
        return llm_client
    if llm is not None:
        return LangChainRunnableLLMClient(llm)
    return None


def invoke_with_retries(
    operation: Callable[[], RetryableOperation],
    *,
    provider_name: str,
    operation_name: str,
    model_name: str | None = None,
    max_retries: int = 2,
    payload_keys: list[str] | None = None,
) -> RetryableOperation:
    """Run an LLM operation with lightweight retry and structured logging."""
    attempts = max(0, max_retries) + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        started_at = time.perf_counter()
        try:
            logger.info(
                "LLM %s start provider=%s model=%s attempt=%s payload_keys=%s",
                operation_name,
                provider_name,
                model_name or "unknown",
                attempt,
                payload_keys or [],
            )
            result = operation()
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "LLM %s success provider=%s model=%s attempt=%s duration_ms=%s",
                operation_name,
                provider_name,
                model_name or "unknown",
                attempt,
                duration_ms,
            )
            return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            if attempt >= attempts:
                logger.exception(
                    "LLM %s failed provider=%s model=%s attempt=%s duration_ms=%s",
                    operation_name,
                    provider_name,
                    model_name or "unknown",
                    attempt,
                    duration_ms,
                )
                break
            logger.warning(
                "LLM %s retry provider=%s model=%s attempt=%s duration_ms=%s error=%s",
                operation_name,
                provider_name,
                model_name or "unknown",
                attempt,
                duration_ms,
                exc,
            )

    assert last_error is not None
    raise last_error


def invoke_with_logging(
    operation: Callable[[], RetryableOperation],
    *,
    provider_name: str,
    operation_name: str,
    model_name: str | None = None,
    payload_keys: list[str] | None = None,
) -> RetryableOperation:
    """Run one LLM operation with structured logging and no outer retry loop."""
    started_at = time.perf_counter()
    logger.info(
        "LLM %s start provider=%s model=%s attempt=%s payload_keys=%s",
        operation_name,
        provider_name,
        model_name or "unknown",
        1,
        payload_keys or [],
    )
    try:
        result = operation()
    except Exception:  # noqa: BLE001
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "LLM %s failed provider=%s model=%s attempt=%s duration_ms=%s",
            operation_name,
            provider_name,
            model_name or "unknown",
            1,
            duration_ms,
        )
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "LLM %s success provider=%s model=%s attempt=%s duration_ms=%s",
        operation_name,
        provider_name,
        model_name or "unknown",
        1,
        duration_ms,
    )
    return result


def stream_with_logging(
    chunk_stream_factory: Callable[[], Iterator[Any]],
    *,
    provider_name: str,
    operation_name: str,
    model_name: str | None = None,
    payload_keys: list[str] | None = None,
) -> Iterator[str]:
    """Yield normalized streamed text chunks while logging lifecycle details."""
    started_at = time.perf_counter()
    chunk_count = 0
    logger.info(
        "LLM %s start provider=%s model=%s payload_keys=%s",
        operation_name,
        provider_name,
        model_name or "unknown",
        payload_keys or [],
    )
    try:
        for chunk in chunk_stream_factory():
            text = extract_text_content(chunk)
            if not text:
                continue
            chunk_count += 1
            yield text
    except Exception:  # noqa: BLE001
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "LLM %s failed provider=%s model=%s duration_ms=%s emitted_chunks=%s",
            operation_name,
            provider_name,
            model_name or "unknown",
            duration_ms,
            chunk_count,
        )
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "LLM %s success provider=%s model=%s duration_ms=%s emitted_chunks=%s",
        operation_name,
        provider_name,
        model_name or "unknown",
        duration_ms,
        chunk_count,
    )


def parse_json_response(response: Any) -> dict[str, Any]:
    """Normalize raw model output into a JSON object when possible."""
    if isinstance(response, dict):
        return response

    content = extract_text_content(response)
    if not isinstance(content, str):
        return {"summary": str(content)}

    stripped = content.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        fenced = extract_fenced_json(stripped)
        if fenced is None:
            return {"summary": stripped}
        try:
            parsed = json.loads(fenced)
        except json.JSONDecodeError:
            return {"summary": stripped}

    if isinstance(parsed, dict):
        return parsed
    return {"summary": stripped}


def extract_text_content(response: Any) -> str:
    """Extract normalized text content from string, message, or chunk-like outputs."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if response.get("type") == "text":
            return str(response.get("text", ""))
        if "content" in response:
            return extract_text_content(response.get("content"))
        return json.dumps(response, ensure_ascii=False)

    content = getattr(response, "content", response)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            parts.append(extract_text_content(item))
        return "\n".join(part for part in parts if part)

    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text

    if isinstance(content, str):
        return content
    return str(content)


def extract_fenced_json(text: str) -> str | None:
    """Extract a JSON object from a fenced block when present."""
    marker = "```"
    if marker not in text:
        return None
    for part in text.split(marker):
        candidate = part.strip()
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate
    return None
