"""Anthropic Claude client for live backend model invocation."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from urllib import error, request

from .client import extract_text_content, invoke_with_retries, parse_json_response


DEFAULT_ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 1024


class AnthropicLLMClient:
    """Invoke Anthropic's Messages API for Claude models."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com",
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
        max_tokens: int | None = None,
        anthropic_version: str = DEFAULT_ANTHROPIC_VERSION,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.anthropic_version = anthropic_version
        self.max_retries = max(0, max_retries)

    def invoke(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Any:
        """Invoke Anthropic's Messages API and return raw text content."""
        response_payload = invoke_with_retries(
            lambda: self._post_json(
                "/v1/messages",
                body={
                    "model": self.model,
                    "system": prompt,
                    "messages": self._build_messages(payload=payload),
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            ),
            provider_name="anthropic",
            model_name=self.model,
            operation_name="invoke",
            max_retries=self.max_retries,
            payload_keys=sorted((payload or {}).keys()),
        )
        return self._extract_content(response_payload)

    def invoke_json(
        self,
        prompt: str,
        *,
        payload: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke Anthropic and normalize the model output into a JSON object."""
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
        """Yield one normalized chunk from the current non-streaming HTTP implementation."""
        response = self.invoke(prompt, payload=payload)
        text = extract_text_content(response)
        if text:
            yield text

    def _build_messages(self, *, payload: dict[str, Any] | None) -> list[dict[str, Any]]:
        """Build Anthropic Messages API payloads from optional JSON input."""
        if payload is None:
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please complete the task using the system instructions.",
                        }
                    ],
                }
            ]
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=False, indent=2),
                    }
                ],
            }
        ]

    def _post_json(self, path: str, *, body: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON POST request to the configured Anthropic endpoint."""
        raw_body = json.dumps(body).encode("utf-8")
        http_request = request.Request(
            url=f"{self.base_url}{path}",
            data=raw_body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.anthropic_version,
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM request failed with HTTP {exc.code}: {error_body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError("LLM response was not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise RuntimeError("LLM response must be a JSON object")
        return parsed

    def _extract_content(self, response_payload: dict[str, Any]) -> Any:
        """Extract joined text blocks from an Anthropic Messages API response."""
        content_blocks = response_payload.get("content", [])
        if not isinstance(content_blocks, list) or not content_blocks:
            return response_payload

        text_parts: list[str] = []
        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            text = block.get("text")
            if isinstance(text, str) and text:
                text_parts.append(text)

        if text_parts:
            return "\n".join(text_parts)
        return response_payload
