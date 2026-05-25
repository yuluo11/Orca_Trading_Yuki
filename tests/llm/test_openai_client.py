from __future__ import annotations

import io
import json
from unittest.mock import patch
import unittest

from backend.src.config import LLMConfig
from backend.src.llm import OpenAICompatibleLLMClient, build_configured_llm_client


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class OpenAICompatibleLLMClientTests(unittest.TestCase):
    def test_build_configured_llm_client_returns_none_when_incomplete(self) -> None:
        config = LLMConfig(
            provider="openai_compatible",
            api_key=None,
            base_url="https://api.openai.com/v1",
            model=None,
            temperature=0.2,
            timeout_seconds=60.0,
            max_tokens=None,
        )

        self.assertIsNone(build_configured_llm_client(config))

    def test_invoke_json_posts_chat_completion_request_and_parses_response(self) -> None:
        client = OpenAICompatibleLLMClient(
            api_key="test-key",
            model="gpt-test-mini",
            base_url="https://example-llm.test/v1",
            temperature=0.3,
            timeout_seconds=5.0,
            max_tokens=128,
        )

        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "Structured answer",
                                "confidence": "medium",
                            }
                        )
                    }
                }
            ]
        }

        captured_request = {}

        def fake_urlopen(http_request, timeout):
            captured_request["url"] = http_request.full_url
            captured_request["timeout"] = timeout
            captured_request["headers"] = dict(http_request.header_items())
            captured_request["body"] = json.loads(http_request.data.decode("utf-8"))
            return FakeHTTPResponse(response_payload)

        with patch("backend.src.llm.openai_client.request.urlopen", side_effect=fake_urlopen):
            result = client.invoke_json(
                "System prompt",
                payload={"subject": "NVDA"},
                schema={"summary": "string", "confidence": "string"},
            )

        self.assertEqual(
            "https://example-llm.test/v1/chat/completions",
            captured_request["url"],
        )
        self.assertEqual(5.0, captured_request["timeout"])
        self.assertEqual("Bearer test-key", captured_request["headers"]["Authorization"])
        self.assertEqual("gpt-test-mini", captured_request["body"]["model"])
        self.assertEqual(0.3, captured_request["body"]["temperature"])
        self.assertEqual(128, captured_request["body"]["max_tokens"])
        self.assertEqual("system", captured_request["body"]["messages"][0]["role"])
        self.assertEqual("user", captured_request["body"]["messages"][1]["role"])
        self.assertEqual("Structured answer", result["summary"])
        self.assertEqual("medium", result["confidence"])


if __name__ == "__main__":
    unittest.main()
