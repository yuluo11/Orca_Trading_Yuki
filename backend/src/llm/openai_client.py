"""OpenAI-compatible LLM client for live backend model invocation."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from urllib import error, request

from .client import extract_text_content, invoke_with_retries, parse_json_response


class OpenAICompatibleLLMClient:
    """Invoke chat-completions style OpenAI-compatible HTTP endpoints."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
        max_tokens: int | None = None,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.max_retries = max(0, max_retries)

    def invoke(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Any:
        """Invoke the configured chat-completions endpoint and return raw text content."""
        request_payload = {
            "model": self.model,
            "messages": self._build_messages(prompt, payload=payload),
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            request_payload["max_tokens"] = self.max_tokens

        response_payload = invoke_with_retries(
            lambda: self._post_json(
                "/chat/completions",
                body=request_payload,
            ),
            provider_name="openai_compatible",
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
        """Invoke the endpoint and normalize the result into a JSON object."""
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

    def _build_messages(
        self,
        prompt: str,
        *,
        payload: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        """Build chat-completions messages from prompt text and optional payload JSON."""
        messages: list[dict[str, str]] = [{"role": "system", "content": prompt}]
        if payload is not None:
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, indent=2),
                }
            )
        return messages

    def _post_json(self, path: str, *, body: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON POST request to the configured OpenAI-compatible endpoint."""
        raw_body = json.dumps(body).encode("utf-8")
        http_request = request.Request(
            url=f"{self.base_url}{path}",
            data=raw_body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
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
        """Extract the first message content from a chat-completions response."""
        choices = response_payload.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return response_payload
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return response_payload
        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            return response_payload
        return message.get("content", response_payload)
