from __future__ import annotations

import unittest

from backend.src.llm import LangChainRunnableLLMClient, MockLLMClient, OpenAICompatibleLLMClient


class StreamingRunnable:
    def __init__(self) -> None:
        self.invoked = False
        self.streamed = False

    def invoke(self, input, config=None):
        self.invoked = True
        return "fallback invoke"

    def stream(self, input, config=None):
        self.streamed = True
        yield {"content": [{"type": "text", "text": "Hello"}]}
        yield {"content": [{"type": "text", "text": " world"}]}


class StreamingBehaviorTests(unittest.TestCase):
    def test_langchain_runnable_client_streams_multiple_chunks_when_supported(self) -> None:
        runnable = StreamingRunnable()
        client = LangChainRunnableLLMClient(
            runnable,
            provider_name="test_provider",
            model_name="test-model",
        )

        chunks = list(client.stream("Prompt", payload={"subject": "NVDA"}))

        self.assertEqual(["Hello", " world"], chunks)
        self.assertTrue(runnable.streamed)
        self.assertFalse(runnable.invoked)

    def test_openai_client_stream_falls_back_to_single_invoke_chunk(self) -> None:
        client = OpenAICompatibleLLMClient(
            api_key="test-key",
            model="gpt-test-mini",
        )

        client.invoke = lambda prompt, payload=None: "single chunk response"  # type: ignore[method-assign]
        chunks = list(client.stream("Prompt", payload={"subject": "NVDA"}))

        self.assertEqual(["single chunk response"], chunks)

    def test_mock_client_stream_yields_configured_chunk(self) -> None:
        client = MockLLMClient(response="mock stream output")

        chunks = list(client.stream("Prompt", payload={"subject": "NVDA"}))

        self.assertEqual(["mock stream output"], chunks)
        self.assertEqual("stream", client.calls[0]["method"])


if __name__ == "__main__":
    unittest.main()
