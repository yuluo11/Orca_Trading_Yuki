from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import patch
import unittest

from backend.src.config import LLMConfig
from backend.src.llm import LangChainRunnableLLMClient, build_langchain_backed_llm_client


class FakeChatOpenAI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def invoke(self, input, config=None):
        return {"summary": "ok"}


class FakeChatAnthropic:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def invoke(self, input, config=None):
        return {"summary": "ok"}


class LangChainFactoryTests(unittest.TestCase):
    def test_build_langchain_backed_llm_client_uses_chat_openai_when_sdk_exists(self) -> None:
        fake_module = ModuleType("langchain_openai")
        fake_module.ChatOpenAI = FakeChatOpenAI
        config = LLMConfig(
            provider="openai_compatible",
            api_key="test-key",
            base_url="https://example-llm.test/v1",
            model="gpt-test-mini",
            temperature=0.35,
            timeout_seconds=12.0,
            max_tokens=256,
        )

        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            client = build_langchain_backed_llm_client(config)

        self.assertIsInstance(client, LangChainRunnableLLMClient)
        self.assertIsInstance(client.runnable, FakeChatOpenAI)
        self.assertEqual("gpt-test-mini", client.runnable.kwargs["model"])
        self.assertEqual("https://example-llm.test/v1", client.runnable.kwargs["base_url"])
        self.assertEqual("test-key", client.runnable.kwargs["api_key"])
        self.assertEqual(0.35, client.runnable.kwargs["temperature"])
        self.assertEqual(12.0, client.runnable.kwargs["timeout"])
        self.assertEqual(256, client.runnable.kwargs["max_tokens"])

    def test_build_langchain_backed_llm_client_uses_chat_anthropic_when_sdk_exists(self) -> None:
        fake_module = ModuleType("langchain_anthropic")
        fake_module.ChatAnthropic = FakeChatAnthropic
        config = LLMConfig(
            provider="anthropic",
            api_key="anthropic-test-key",
            base_url="https://api.anthropic.com",
            model="claude-sonnet-4-20250514",
            temperature=0.1,
            timeout_seconds=9.0,
            max_tokens=512,
        )

        with patch.dict(sys.modules, {"langchain_anthropic": fake_module}):
            client = build_langchain_backed_llm_client(config)

        self.assertIsInstance(client, LangChainRunnableLLMClient)
        self.assertIsInstance(client.runnable, FakeChatAnthropic)
        self.assertEqual("claude-sonnet-4-20250514", client.runnable.kwargs["model"])
        self.assertEqual("https://api.anthropic.com", client.runnable.kwargs["base_url"])
        self.assertEqual("anthropic-test-key", client.runnable.kwargs["api_key"])
        self.assertEqual(0.1, client.runnable.kwargs["temperature"])
        self.assertEqual(9.0, client.runnable.kwargs["timeout"])
        self.assertEqual(512, client.runnable.kwargs["max_tokens"])


if __name__ == "__main__":
    unittest.main()
