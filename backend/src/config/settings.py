"""Typed configuration objects for backend runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_ANALYST_SEQUENCE = (
    "market_analyst",
    "news_analyst",
    "sentiment_analyst",
    "social_analyst",
    "graph_analyst",
)


@dataclass(frozen=True)
class PromptPaths:
    """Prompt directory layout used by analyst, decision, and reflection layers."""

    root_dir: Path
    analysts_dir: Path
    decision_dir: Path
    reflection_dir: Path


@dataclass(frozen=True)
class AgentSettingsPaths:
    """Filesystem layout for agent-setting assets under the config tree."""

    root_dir: Path
    perception_dir: Path
    active_perception_dir: Path
    technical_analyst_dir: Path


@dataclass(frozen=True)
class WorkflowConfig:
    """Runtime workflow defaults shared by backend entrypoints."""

    default_analyst_sequence: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    """Top-level backend configuration object."""

    src_dir: Path
    prompts: PromptPaths
    agent_settings: AgentSettingsPaths
    workflow: WorkflowConfig


def build_app_config(src_dir: Path | None = None) -> AppConfig:
    """Build a typed backend configuration object from the source root."""
    resolved_src_dir = (src_dir or Path(__file__).resolve().parents[1]).resolve()
    prompts_root_dir = resolved_src_dir / "prompts"
    agent_settings_root_dir = resolved_src_dir / "config" / "agent_settings"

    return AppConfig(
        src_dir=resolved_src_dir,
        prompts=PromptPaths(
            root_dir=prompts_root_dir,
            analysts_dir=prompts_root_dir / "analysts",
            decision_dir=prompts_root_dir / "decision",
            reflection_dir=prompts_root_dir / "reflection",
        ),
        agent_settings=AgentSettingsPaths(
            root_dir=agent_settings_root_dir,
            perception_dir=agent_settings_root_dir / "perception",
            active_perception_dir=agent_settings_root_dir / "perception" / "active_perception",
            technical_analyst_dir=agent_settings_root_dir
            / "perception"
            / "technical analyst",
        ),
        workflow=WorkflowConfig(
            default_analyst_sequence=DEFAULT_ANALYST_SEQUENCE,
        ),
    )
