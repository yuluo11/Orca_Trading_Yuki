"""Typed decision-layer payload contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, TypedDict

from .knowledge import KnowledgeEvidenceItem, RankedKnowledgeDocument
from .memory import DecisionMemoryValidationSummary
from .observation import GuidancePriorsSummary


class DecisionReferenceCase(TypedDict, total=False):
    """Compact reference case surfaced by the decision layer."""

    title: str
    fit: str
    match_reasons: list[str]
    metadata: dict[str, Any]


class MemoryPersistenceAssessment(TypedDict, total=False):
    """Assessment describing whether a candidate memory should be persisted."""

    eligible: bool
    blocking_issues: list[str]
    warnings: list[str]
    outcome_label: str


class DecisionOutput(TypedDict, total=False):
    """Structured advisory output produced by the decision layer."""

    subject: str
    symbol: str | None
    trade_date: str | None
    decision_summary: str
    recommendation: str
    advisory_scope: str
    portfolio_context_used: bool
    portfolio_context_summary: str
    position_impact: str
    timing_decision: str
    action_conditions: list[str]
    no_action_reasons: list[str]
    aggregated_risks: list[str]
    rationale: str
    confidence: str
    reference_cases: list[DecisionReferenceCase]
    case_fit_assessment: str
    applied_setup_labels: list[str]
    prompt: str
    decision_context: "DecisionContext"
    applied_postmortem_guidance: list[str]
    raw_model_output: dict[str, Any]


class DecisionContext(TypedDict, total=False):
    """Structured decision-memory context supplied to the advisory agent."""

    agent: str
    subject: str
    symbol: str | None
    trade_date: str | None
    query: str
    scenario_profile: dict[str, Any]
    datasets: list[str]
    document_count: int
    validation_summary: DecisionMemoryValidationSummary
    documents: list[RankedKnowledgeDocument]
    evidence: list[KnowledgeEvidenceItem]
    postmortem_lessons: list[dict[str, str]]
    guidance_priors: GuidancePriorsSummary
    setup_outcome_priors: dict[str, Any]
    setup_recommendation_outcome_priors: dict[str, Any]


ALLOWED_DECISION_RECOMMENDATIONS = (
    "consider_buy",
    "consider_reduce",
    "hold",
    "keep_watch",
    "no_trade",
)
ALLOWED_DECISION_CONFIDENCE = ("low", "medium", "high")

DECISION_OUTPUT_SCHEMA: dict[str, Any] = {
    "decision_summary": "string",
    "recommendation": "|".join(ALLOWED_DECISION_RECOMMENDATIONS),
    "portfolio_context_used": "boolean",
    "portfolio_context_summary": "string",
    "position_impact": "string",
    "timing_decision": "string",
    "action_conditions": ["string"],
    "no_action_reasons": ["string"],
    "aggregated_risks": ["string"],
    "rationale": "string",
    "confidence": "|".join(ALLOWED_DECISION_CONFIDENCE),
    "reference_cases": [
        {
            "title": "string",
            "memory_type": "decision_case|decision_postmortem|external_reference_decision",
            "fit": "high|medium|low",
            "why_relevant": "string",
        }
    ],
    "case_fit_assessment": "string",
    "applied_postmortem_guidance": ["string"],
    "applied_setup_labels": ["string"],
}

DECISION_OUTPUT_FIELDS = tuple(DECISION_OUTPUT_SCHEMA.keys())


def decision_output_schema() -> dict[str, Any]:
    """Return a copy of the shared decision-output schema."""
    return deepcopy(DECISION_OUTPUT_SCHEMA)


def decision_output_instruction_keys() -> str:
    """Render the canonical key list used in decision prompt instructions."""
    return ", ".join(DECISION_OUTPUT_FIELDS)


def extract_decision_output_contract(result: Mapping[str, Any] | None) -> DecisionOutput:
    """Return only the fields that belong to the shared decision output contract."""
    if not isinstance(result, Mapping):
        return {}
    return {
        field_name: result[field_name]
        for field_name in DECISION_OUTPUT_FIELDS
        if field_name in result
    }
