"""Deterministic mock LLM client for tests and local prompt iteration."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from .client import parse_json_response


class MockLLMClient:
    """Return fixed responses without making external model calls."""

    def __init__(
        self,
        *,
        response: Any = None,
        json_response: dict[str, Any] | None = None,
    ) -> None:
        self.response = response if response is not None else ""
        self.json_response = dict(json_response) if json_response is not None else None
        self.calls: list[dict[str, Any]] = []

    def invoke(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Any:
        """Return the configured raw mock response and record the call."""
        self.calls.append(
            {
                "method": "invoke",
                "prompt": prompt,
                "payload": payload,
            }
        )
        if self.json_response is not None:
            return json.dumps(self.json_response, ensure_ascii=False)
        return self.response

    def invoke_json(
        self,
        prompt: str,
        *,
        payload: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the configured JSON response and record the structured call."""
        self.calls.append(
            {
                "method": "invoke_json",
                "prompt": prompt,
                "payload": payload,
                "schema": schema,
            }
        )
        if self.json_response is not None:
            return dict(self.json_response)
        return parse_json_response(self.response)

    def stream(self, prompt: str, *, payload: dict[str, Any] | None = None) -> Iterator[str]:
        """Yield the configured mock response as one streamed chunk."""
        self.calls.append(
            {
                "method": "stream",
                "prompt": prompt,
                "payload": payload,
            }
        )
        if self.json_response is not None:
            yield json.dumps(self.json_response, ensure_ascii=False)
            return
        if self.response is not None:
            yield str(self.response)
