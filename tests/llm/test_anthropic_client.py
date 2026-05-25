from __future__ import annotations

import json
from unittest.mock import patch
import unittest

from backend.src.config import LLMConfig
from backend.src.llm import AnthropicLLMClient, LangChainRunnableLLMClient, build_configured_llm_client


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class AnthropicLLMClientTests(unittest.TestCase):
    def test_build_configured_llm_client_returns_anthropic_client(self) -> None:
        config = LLMConfig(
            provider="anthropic",
            api_key="anthropic-test-key",
            base_url="https://api.anthropic.com",
            model="claude-sonnet-4-20250514",
            temperature=0.2,
            timeout_seconds=30.0,
            max_tokens=512,
        )

        client = build_configured_llm_client(config)

        self.assertIsInstance(
            client,
            (LangChainRunnableLLMClient, AnthropicLLMClient),
        )
        if isinstance(client, LangChainRunnableLLMClient):
            self.assertEqual("ChatAnthropic", client.runnable.__class__.__name__)

    def test_invoke_json_posts_messages_request_and_parses_response(self) -> None:
        client = AnthropicLLMClient(
            api_key="anthropic-test-key",
            model="claude-sonnet-4-20250514",
            base_url="https://anthropic.example.test",
            temperature=0.1,
            timeout_seconds=7.5,
            max_tokens=256,
        )

        response_payload = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "summary": "Claude structured answer",
                            "confidence": "high",
                        }
                    ),
                }
            ],
            "model": "claude-sonnet-4-20250514",
            "role": "assistant",
            "type": "message",
        }

        captured_request = {}

        def fake_urlopen(http_request, timeout):
            captured_request["url"] = http_request.full_url
            captured_request["timeout"] = timeout
            captured_request["headers"] = dict(http_request.header_items())
            captured_request["body"] = json.loads(http_request.data.decode("utf-8"))
            return FakeHTTPResponse(response_payload)

        with patch("backend.src.llm.anthropic_client.request.urlopen", side_effect=fake_urlopen):
            result = client.invoke_json(
                "System prompt",
                payload={"subject": "BTC"},
                schema={"summary": "string", "confidence": "string"},
            )

        self.assertEqual(
            "https://anthropic.example.test/v1/messages",
            captured_request["url"],
        )
        self.assertEqual(7.5, captured_request["timeout"])
        self.assertEqual("anthropic-test-key", captured_request["headers"]["X-api-key"])
        self.assertEqual("2023-06-01", captured_request["headers"]["Anthropic-version"])
        self.assertEqual("claude-sonnet-4-20250514", captured_request["body"]["model"])
        self.assertEqual(0.1, captured_request["body"]["temperature"])
        self.assertEqual(256, captured_request["body"]["max_tokens"])
        self.assertEqual("System prompt", captured_request["body"]["system"][:13])
        self.assertEqual("user", captured_request["body"]["messages"][0]["role"])
        self.assertEqual("Claude structured answer", result["summary"])
        self.assertEqual("high", result["confidence"])


if __name__ == "__main__":
    unittest.main()
