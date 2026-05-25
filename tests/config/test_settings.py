from __future__ import annotations

import os
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest

from backend.src.config import build_app_config


class AppConfigTests(unittest.TestCase):
    def test_build_app_config_derives_prompt_and_agent_settings_paths(self) -> None:
        src_dir = Path("/tmp/orca/backend/src")

        config = build_app_config(src_dir)

        resolved_src_dir = src_dir.resolve()

        self.assertEqual(resolved_src_dir, config.src_dir)
        self.assertEqual(resolved_src_dir / "prompts", config.prompts.root_dir)
        self.assertEqual(
            resolved_src_dir / "prompts" / "analysts",
            config.prompts.analysts_dir,
        )
        self.assertEqual(
            resolved_src_dir / "prompts" / "decision",
            config.prompts.decision_dir,
        )
        self.assertEqual(
            resolved_src_dir / "prompts" / "reflection",
            config.prompts.reflection_dir,
        )
        self.assertEqual(
            resolved_src_dir / "config" / "agent_settings",
            config.agent_settings.root_dir,
        )
        self.assertEqual(
            resolved_src_dir
            / "config"
            / "agent_settings"
            / "perception"
            / "active_perception",
            config.agent_settings.active_perception_dir,
        )
        self.assertFalse(hasattr(config.agent_settings, "skills_dir"))
        self.assertFalse(hasattr(config.agent_settings, "finskills_dir"))
        self.assertFalse(hasattr(config.agent_settings, "global_skills_dir"))
        self.assertEqual("openai_compatible", config.llm.provider)
        self.assertEqual("https://api.openai.com/v1", config.llm.base_url)
        self.assertEqual(0.2, config.llm.temperature)
        self.assertEqual(60.0, config.llm.timeout_seconds)
        self.assertEqual(2, config.llm.max_retries)
        self.assertIsNone(config.llm.api_key)
        self.assertIsNone(config.llm.model)
        self.assertIsNone(config.llm.mock_response)
        self.assertIsNone(config.llm.mock_json_response)
        self.assertFalse(config.llm.is_configured)
        self.assertEqual(
            (
                "market_analyst",
                "news_analyst",
                "sentiment_analyst",
                "social_analyst",
                "graph_analyst",
            ),
            config.workflow.default_analyst_sequence,
        )

    def test_build_app_config_reads_llm_environment_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ORCA_LLM_PROVIDER": "openai_compatible",
                "ORCA_LLM_API_KEY": "test-key",
                "ORCA_LLM_BASE_URL": "https://example-llm.test/v1",
                "ORCA_LLM_MODEL": "gpt-test-mini",
                "ORCA_LLM_TEMPERATURE": "0.45",
                "ORCA_LLM_TIMEOUT_SECONDS": "12.5",
                "ORCA_LLM_MAX_TOKENS": "256",
                "ORCA_LLM_MAX_RETRIES": "4",
                "ORCA_LLM_MOCK_RESPONSE": "unused",
                "ORCA_LLM_MOCK_JSON_RESPONSE": "{\"summary\": \"unused\"}",
            },
            clear=False,
        ):
            config = build_app_config(Path("/tmp/orca/backend/src"))

        self.assertEqual("openai_compatible", config.llm.provider)
        self.assertEqual("test-key", config.llm.api_key)
        self.assertEqual("https://example-llm.test/v1", config.llm.base_url)
        self.assertEqual("gpt-test-mini", config.llm.model)
        self.assertEqual(0.45, config.llm.temperature)
        self.assertEqual(12.5, config.llm.timeout_seconds)
        self.assertEqual(256, config.llm.max_tokens)
        self.assertEqual(4, config.llm.max_retries)
        self.assertEqual("unused", config.llm.mock_response)
        self.assertEqual("{\"summary\": \"unused\"}", config.llm.mock_json_response)
        self.assertTrue(config.llm.is_configured)

    def test_build_app_config_uses_anthropic_default_base_url_for_claude_provider(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ORCA_LLM_PROVIDER": "anthropic",
                "ORCA_LLM_API_KEY": "anthropic-test-key",
                "ORCA_LLM_BASE_URL": "",
                "ORCA_LLM_MODEL": "claude-sonnet-4-20250514",
            },
            clear=False,
        ):
            config = build_app_config(Path("/tmp/orca/backend/src"))

        self.assertEqual("anthropic", config.llm.provider)
        self.assertEqual("https://api.anthropic.com", config.llm.base_url)
        self.assertTrue(config.llm.is_configured)

    def test_build_app_config_reads_backend_dotenv_without_overriding_process_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            src_dir = repo_root / "backend" / "src"
            src_dir.mkdir(parents=True)
            backend_env = repo_root / "backend" / ".env"
            backend_env.write_text(
                "\n".join(
                    [
                        "ORCA_LLM_PROVIDER=anthropic",
                        "ORCA_LLM_API_KEY=file-key",
                        "ORCA_LLM_MODEL=claude-sonnet-4-20250514",
                        "ORCA_LLM_BASE_URL=https://api.anthropic.com",
                        "ORCA_LLM_TEMPERATURE=0.15",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "ORCA_LLM_API_KEY": "env-key",
                    "ORCA_LLM_TIMEOUT_SECONDS": "22.0",
                },
                clear=False,
            ):
                config = build_app_config(src_dir)

        self.assertEqual("anthropic", config.llm.provider)
        self.assertEqual("env-key", config.llm.api_key)
        self.assertEqual("claude-sonnet-4-20250514", config.llm.model)
        self.assertEqual("https://api.anthropic.com", config.llm.base_url)
        self.assertEqual(0.15, config.llm.temperature)
        self.assertEqual(22.0, config.llm.timeout_seconds)


if __name__ == "__main__":
    unittest.main()
