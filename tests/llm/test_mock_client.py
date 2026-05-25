from __future__ import annotations

import unittest

from backend.src.config import LLMConfig
from backend.src.llm import (
    LangChainRunnableLLMClient,
    MockLLMClient,
    OpenAICompatibleLLMClient,
    build_configured_llm_client,
)


class MockLLMClientTests(unittest.TestCase):
    def test_invoke_json_returns_configured_json_and_records_call(self) -> None:
        client = MockLLMClient(json_response={"summary": "Mocked", "confidence": "low"})

        result = client.invoke_json(
            "Prompt",
            payload={"subject": "NVDA"},
            schema={"summary": "string"},
        )

        self.assertEqual("Mocked", result["summary"])
        self.assertEqual("low", result["confidence"])
        self.assertEqual("invoke_json", client.calls[0]["method"])
        self.assertEqual({"subject": "NVDA"}, client.calls[0]["payload"])

    def test_build_configured_llm_client_returns_mock_client_for_mock_provider(self) -> None:
        config = LLMConfig(
            provider="mock",
            api_key=None,
            base_url=None,
            model=None,
            temperature=0.2,
            timeout_seconds=60.0,
            max_tokens=None,
            mock_response="fallback text",
            mock_json_response='{"summary": "Structured mock"}',
        )

        client = build_configured_llm_client(config)

        self.assertIsInstance(client, MockLLMClient)
        self.assertEqual({"summary": "Structured mock"}, client.invoke_json("Prompt"))

    def test_build_configured_llm_client_returns_openai_client_for_live_provider(self) -> None:
        config = LLMConfig(
            provider="openai_compatible",
            api_key="test-key",
            base_url="https://example-llm.test/v1",
            model="gpt-test-mini",
            temperature=0.2,
            timeout_seconds=60.0,
            max_tokens=128,
            mock_response=None,
            mock_json_response=None,
        )

        client = build_configured_llm_client(config)

        self.assertIsInstance(
            client,
            (LangChainRunnableLLMClient, OpenAICompatibleLLMClient),
        )
        if isinstance(client, LangChainRunnableLLMClient):
            self.assertEqual("ChatOpenAI", client.runnable.__class__.__name__)


if __name__ == "__main__":
    unittest.main()
