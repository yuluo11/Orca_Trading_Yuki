"""Typed decision-layer payload contracts."""

from __future__ import annotations

from typing import Any, TypedDict

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
