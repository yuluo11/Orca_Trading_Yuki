from __future__ import annotations

import json
from urllib import error
from unittest.mock import patch
import unittest

from backend.src.llm.client import LangChainRunnableLLMClient
from backend.src.llm.openai_client import OpenAICompatibleLLMClient


class FlakyRunnable:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, input, config=None):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary runnable failure")
        return {"summary": "Recovered"}


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class RetryBehaviorTests(unittest.TestCase):
    def test_langchain_runnable_client_retries_once_and_recovers(self) -> None:
        runnable = FlakyRunnable()
        client = LangChainRunnableLLMClient(
            runnable,
            provider_name="test_provider",
            model_name="test-model",
            max_retries=1,
        )

        result = client.invoke_json("Prompt", payload={"subject": "NVDA"})

        self.assertEqual({"summary": "Recovered"}, result)
        self.assertEqual(2, runnable.calls)

    def test_openai_client_retries_once_after_urlerror(self) -> None:
        client = OpenAICompatibleLLMClient(
            api_key="test-key",
            model="gpt-test-mini",
            base_url="https://example-llm.test/v1",
            timeout_seconds=5.0,
            max_retries=1,
        )

        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"summary": "Recovered", "confidence": "medium"})
                    }
                }
            ]
        }
        calls = {"count": 0}

        def flaky_urlopen(http_request, timeout):
            calls["count"] += 1
            if calls["count"] == 1:
                raise error.URLError("temporary network failure")
            return FakeHTTPResponse(response_payload)

        with patch("backend.src.llm.openai_client.request.urlopen", side_effect=flaky_urlopen):
            result = client.invoke_json(
                "System prompt",
                payload={"subject": "NVDA"},
                schema={"summary": "string", "confidence": "string"},
            )

        self.assertEqual("Recovered", result["summary"])
        self.assertEqual(2, calls["count"])


if __name__ == "__main__":
    unittest.main()
