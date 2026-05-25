from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import patch
import unittest

from backend.src.config import LLMConfig
from backend.src.llm import LangChainRunnableLLMClient, build_langchain_backed_llm_client


class FakeChatGoogleGenerativeAI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def invoke(self, input, config=None):
        return {"summary": "ok"}


class GeminiFactoryTests(unittest.TestCase):
    def test_build_langchain_backed_llm_client_uses_chat_google_genai_when_sdk_exists(self) -> None:
        fake_module = ModuleType("langchain_google_genai")
        fake_module.ChatGoogleGenerativeAI = FakeChatGoogleGenerativeAI
        config = LLMConfig(
            provider="gemini",
            api_key="google-test-key",
            base_url=None,
            model="gemini-2.5-flash",
            temperature=0.25,
            timeout_seconds=11.0,
            max_tokens=768,
            max_retries=4,
        )

        with patch.dict(sys.modules, {"langchain_google_genai": fake_module}):
            client = build_langchain_backed_llm_client(config)

        self.assertIsInstance(client, LangChainRunnableLLMClient)
        self.assertIsInstance(client.runnable, FakeChatGoogleGenerativeAI)
        self.assertEqual("gemini-2.5-flash", client.runnable.kwargs["model"])
        self.assertEqual("google-test-key", client.runnable.kwargs["google_api_key"])
        self.assertEqual(0.25, client.runnable.kwargs["temperature"])
        self.assertEqual(11.0, client.runnable.kwargs["timeout"])
        self.assertEqual(768, client.runnable.kwargs["max_output_tokens"])
        self.assertEqual(4, client.runnable.kwargs["max_retries"])


if __name__ == "__main__":
    unittest.main()
