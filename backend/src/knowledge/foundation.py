"""Foundation knowledge taxonomy and schema helpers.

Foundation knowledge is the project owner's durable trading framework: rules,
playbooks, risk principles, and agent boundaries. The helpers here standardize
metadata without defining the user's actual trading beliefs.
"""

from __future__ import annotations

from typing import Any, Literal

FoundationCategory = Literal[
    "market_structure",
    "risk_framework",
    "setup_playbook",
    "position_sizing",
    "macro_framework",
    "indicator_explanation",
    "agent_rules",
    "execution_rules",
    "reflection_principles",
    "research_notes",
]
FoundationPrincipleType = Literal[
    "principle",
    "rule",
    "playbook",
    "checklist",
    "definition",
    "boundary",
]
FoundationPriority = Literal["critical", "high", "medium", "low"]
FoundationStatus = Literal["draft", "active", "deprecated"]
FoundationRuleDirection = Literal[
    "allow",
    "block",
    "reduce",
    "increase",
    "observe",
    "neutral",
]

FOUNDATION_CATEGORIES: tuple[str, ...] = (
    "market_structure",
    "risk_framework",
    "setup_playbook",
    "position_sizing",
    "macro_framework",
    "indicator_explanation",
    "agent_rules",
    "execution_rules",
    "reflection_principles",
    "research_notes",
)
FOUNDATION_PRINCIPLE_TYPES: tuple[str, ...] = (
    "principle",
    "rule",
    "playbook",
    "checklist",
    "definition",
    "boundary",
)
FOUNDATION_PRIORITIES: tuple[str, ...] = ("critical", "high", "medium", "low")
FOUNDATION_STATUSES: tuple[str, ...] = ("draft", "active", "deprecated")
FOUNDATION_RULE_DIRECTIONS: tuple[str, ...] = (
    "allow",
    "block",
    "reduce",
    "increase",
    "observe",
    "neutral",
)
OPPOSING_RULE_DIRECTIONS: frozenset[frozenset[str]] = frozenset(
    (
        frozenset(("allow", "block")),
        frozenset(("increase", "reduce")),
    )
)
FOUNDATION_CATEGORY_ALIASES: dict[str, str] = {
    "research": "research_notes",
    "research_note": "research_notes",
    "rules": "agent_rules",
    "risk": "risk_framework",
    "setup": "setup_playbook",
    "strategy": "setup_playbook",
    "strategy_record": "setup_playbook",
}


def normalize_foundation_metadata(metadata: dict[str, Any]) -> None:
    """Normalize foundation-specific metadata fields in place."""
    metadata.setdefault("foundation_schema_version", "1")
    metadata.setdefault("principle_type", "principle")
    metadata.setdefault("priority", "medium")
    metadata.setdefault("status", "active")
    metadata.setdefault("rule_direction", "neutral")
    metadata.setdefault("owner_defined", False)

    category = _normalize_token(str(metadata.get("foundation_category") or metadata.get("category") or "research_notes"))
    category = FOUNDATION_CATEGORY_ALIASES.get(category, category)
    metadata["foundation_category"] = category
    metadata["category"] = category

    for field in ("principle_type", "priority", "status", "rule_direction"):
        metadata[field] = _normalize_token(str(metadata.get(field, "")))

    for field in ("applies_to", "valid_when", "invalid_when", "conflicts_with"):
        metadata[field] = normalize_string_list(metadata.get(field))

    if "rule_id" in metadata:
        metadata["rule_id"] = _normalize_token(str(metadata["rule_id"]))


def normalize_string_list(value: Any) -> list[str]:
    """Normalize schema fields that can be provided as a string or list."""
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = [value]
    normalized_values: list[str] = []
    for item in raw_values:
        normalized = " ".join(str(item).strip().lower().split())
        if normalized and normalized not in normalized_values:
            normalized_values.append(normalized)
    return normalized_values


def validate_foundation_metadata(metadata: dict[str, Any]) -> list[str]:
    """Return validation issue codes for foundation metadata."""
    issues: list[str] = []
    if metadata.get("foundation_category") not in FOUNDATION_CATEGORIES:
        issues.append("invalid_foundation_category")
    if metadata.get("principle_type") not in FOUNDATION_PRINCIPLE_TYPES:
        issues.append("invalid_principle_type")
    if metadata.get("priority") not in FOUNDATION_PRIORITIES:
        issues.append("invalid_priority")
    if metadata.get("status") not in FOUNDATION_STATUSES:
        issues.append("invalid_status")
    if metadata.get("rule_direction") not in FOUNDATION_RULE_DIRECTIONS:
        issues.append("invalid_rule_direction")
    return issues


def foundation_rule_key(metadata: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    """Return a coarse key used for possible static rule conflict checks."""
    return (
        str(metadata.get("foundation_category", "")),
        str(metadata.get("topic", "")),
        tuple(metadata.get("applies_to", []) or ()),
    )


def directions_conflict(left: str, right: str) -> bool:
    """Return whether two coarse rule directions oppose one another."""
    return frozenset((left, right)) in OPPOSING_RULE_DIRECTIONS


def _normalize_token(value: str) -> str:
    return "_".join(value.strip().lower().replace("-", "_").split())
