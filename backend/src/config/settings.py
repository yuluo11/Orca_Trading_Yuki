"""Typed configuration objects for backend runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping


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
class LLMConfig:
    """Runtime configuration for the default LLM client."""

    provider: str
    api_key: str | None
    base_url: str | None
    model: str | None
    temperature: float
    timeout_seconds: float
    max_tokens: int | None
    mock_response: str | None = None
    mock_json_response: str | None = None

    @property
    def is_configured(self) -> bool:
        """Return whether enough information is present to build a live client."""
        if self.provider == "mock":
            return True
        return bool(self.api_key and self.model)


@dataclass(frozen=True)
class AppConfig:
    """Top-level backend configuration object."""

    src_dir: Path
    prompts: PromptPaths
    agent_settings: AgentSettingsPaths
    workflow: WorkflowConfig
    llm: LLMConfig


def build_app_config(src_dir: Path | None = None) -> AppConfig:
    """Build a typed backend configuration object from the source root."""
    resolved_src_dir = (src_dir or Path(__file__).resolve().parents[1]).resolve()
    prompts_root_dir = resolved_src_dir / "prompts"
    agent_settings_root_dir = resolved_src_dir / "config" / "agent_settings"
    env = _build_runtime_env(resolved_src_dir)
    llm_provider = (
        _read_env("ORCA_LLM_PROVIDER", env=env, default="openai_compatible")
        or "openai_compatible"
    )

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
        llm=LLMConfig(
            provider=llm_provider,
            api_key=_read_env("ORCA_LLM_API_KEY", env=env),
            base_url=_read_env(
                "ORCA_LLM_BASE_URL",
                env=env,
                default=_default_llm_base_url(llm_provider),
            ),
            model=_read_env("ORCA_LLM_MODEL", env=env),
            temperature=_read_env_float("ORCA_LLM_TEMPERATURE", env=env, default=0.2),
            timeout_seconds=_read_env_float(
                "ORCA_LLM_TIMEOUT_SECONDS",
                env=env,
                default=60.0,
            ),
            max_tokens=_read_env_int("ORCA_LLM_MAX_TOKENS", env=env),
            mock_response=_read_env("ORCA_LLM_MOCK_RESPONSE", env=env),
            mock_json_response=_read_env("ORCA_LLM_MOCK_JSON_RESPONSE", env=env),
        ),
    )


def _build_runtime_env(src_dir: Path) -> dict[str, str]:
    """Build a read-only environment view from .env files and process env."""
    backend_dir = src_dir.parent
    repo_root = backend_dir.parent

    merged: dict[str, str] = {}
    for env_path in (repo_root / ".env", backend_dir / ".env"):
        merged.update(_read_env_file(env_path))
    merged.update(os.environ)
    return merged


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a simple .env file without requiring third-party dependencies."""
    if not path.exists():
        return {}

    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue

        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        parsed[key] = value
    return parsed


def _read_env(
    name: str,
    *,
    env: Mapping[str, str] | None = None,
    default: str | None = None,
) -> str | None:
    """Read an environment variable and normalize blank values to the default."""
    value = (env or os.environ).get(name, "").strip()
    return value or default


def _read_env_float(
    name: str,
    *,
    env: Mapping[str, str] | None = None,
    default: float,
) -> float:
    """Read a float-like environment variable with a stable fallback."""
    raw_value = (env or os.environ).get(name, "").strip()
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _read_env_int(
    name: str,
    *,
    env: Mapping[str, str] | None = None,
) -> int | None:
    """Read an int-like environment variable with a blank-safe fallback."""
    raw_value = (env or os.environ).get(name, "").strip()
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _default_llm_base_url(provider: str) -> str | None:
    """Return the provider-appropriate default base URL."""
    if provider == "openai_compatible":
        return "https://api.openai.com/v1"
    if provider in {"anthropic", "claude"}:
        return "https://api.anthropic.com"
    if provider == "gemini":
        return None
    return None
