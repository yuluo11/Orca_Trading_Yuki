from __future__ import annotations

from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
