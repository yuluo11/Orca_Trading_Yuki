"""Stable setup-taxonomy helpers for decision observations and reuse."""

from __future__ import annotations

from typing import Any


def normalize_string_list(value: Any) -> list[str]:
    """Normalize optional metadata values into a non-empty lowercase string list."""
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip().lower()]
    return []


def infer_setup_labels(scenario_profile: dict[str, Any] | None) -> list[str]:
    """Infer stable setup labels from a scenario profile."""
    if not isinstance(scenario_profile, dict):
        return []

    market_regime = str(scenario_profile.get("market_regime", "")).strip().lower()
    signal_tags = set(normalize_string_list(scenario_profile.get("signal_tags")))
    risk_tags = set(normalize_string_list(scenario_profile.get("risk_tags")))
    timing_tags = set(normalize_string_list(scenario_profile.get("timing_tags")))
    portfolio_state_tags = set(normalize_string_list(scenario_profile.get("portfolio_state_tags")))

    labels: list[str] = []

    if market_regime == "event_driven" and (
        "momentum" in signal_tags or "news_catalyst" in signal_tags
    ):
        labels.append("event_momentum")
    if "momentum" in signal_tags and (
        "price_extension" in signal_tags or "near_local_high" in timing_tags
    ):
        labels.append("extended_momentum")
    if "event_fade" in risk_tags:
        labels.append("catalyst_fade_risk")
    if market_regime == "risk_off" or "drawdown_risk" in risk_tags:
        labels.append("defensive_drawdown")
    if "no_position" in portfolio_state_tags and "ample_cash" in portfolio_state_tags:
        labels.append("fresh_entry")
    if "existing_position" in portfolio_state_tags:
        labels.append("position_management")
    if "crowded_trade" in risk_tags and "momentum" in signal_tags:
        labels.append("crowded_momentum")

    if not labels and market_regime:
        labels.append(f"{market_regime}_setup")
    return _dedupe_preserve_order(labels)


def infer_primary_setup_label(scenario_profile: dict[str, Any] | None) -> str:
    """Return the primary setup label for a scenario profile."""
    labels = infer_setup_labels(scenario_profile)
    return labels[0] if labels else ""


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """De-duplicate while keeping the first-seen ordering."""
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = str(value).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped
