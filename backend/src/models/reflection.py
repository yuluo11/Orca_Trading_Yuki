"""Typed reflection-layer payload contracts."""

from __future__ import annotations

from typing import Any, TypedDict

from .decision import MemoryPersistenceAssessment
from .knowledge import KnowledgeEvidenceItem, RankedKnowledgeDocument
from .memory import DecisionMemoryRecord


class ReflectionReferenceCase(TypedDict, total=False):
    """Compact reference case surfaced by the reflection layer."""

    title: str
    memory_type: str
    fit: str
    why_relevant: str


class ReflectionProfile(TypedDict, total=False):
    """Compact profile summarizing how the current decision should be reviewed."""

    symbol: str | None
    recommendation: str
    decision_confidence: str
    outcome_label: str
    market_regime: str
    analyst_alignment: str
    signal_tags: list[str]
    risk_tags: list[str]
    timing_tags: list[str]
    portfolio_state_tags: list[str]
    decision_quality_hint: str
    exit_reason: str


class ReflectionAnalystSummary(TypedDict, total=False):
    """Reduced analyst aggregation included in reflection prompts and context."""

    overall_summary: str
    overall_confidence: str
    key_signals: list[str]
    portfolio_risks: list[str]
    cross_analyst_observations: list[str]


class RealizedOutcomeSummary(TypedDict, total=False):
    """Normalized realized outcome summary used during post-trade review."""

    outcome_label: str
    status: str
    summary: str
    result: str
    notes: str


class ExecutionSummary(TypedDict, total=False):
    """Normalized execution snapshot for a finished trade or review window."""

    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    holding_period_days: float
    position_size_pct: float
    summary: str


class OutcomeMetrics(TypedDict, total=False):
    """Normalized outcome metrics derived from a completed trade."""

    outcome_label: str
    performance_assessment: str
    summary: str
    result: str
    notes: str
    realized_pnl_pct: float
    pnl_pct: float
    benchmark_relative_return_pct: float
    benchmark_relative_return: float
    max_drawdown_pct: float
    holding_return_pct: float
    position_size_pct: float
    holding_period_days: float


class ExitContext(TypedDict, total=False):
    """Normalized exit metadata used during postmortem review."""

    exit_date: str
    exit_reason: str
    exit_trigger: str
    status: str
    summary: str
    notes: str


class PostTradeValidationResult(TypedDict, total=False):
    """Validation result over structured post-trade review fields."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    execution_summary: ExecutionSummary
    outcome_metrics: OutcomeMetrics
    exit_context: ExitContext


class PostTradeCompletenessResult(TypedDict, total=False):
    """Completeness assessment for whether post-trade inputs are reusable."""

    status: str
    outcome_label: str
    completeness_score: float
    present_inputs: list[str]
    missing_inputs: list[str]


class CandidateMemorySeed(TypedDict, total=False):
    """Small seed structure used to anchor candidate postmortem generation."""

    title: str
    subject: str
    symbol: str | None
    recommendation: str
    confidence: str
    outcome_label: str
    exit_reason: str


class ReflectionContext(TypedDict, total=False):
    """Structured reflection context passed from services into the reflection agent."""

    agent: str
    subject: str
    symbol: str | None
    trade_date: str | None
    query: str
    reflection_profile: ReflectionProfile
    datasets: list[str]
    document_count: int
    validation_summary: dict[str, Any]
    documents: list[RankedKnowledgeDocument]
    historical_cases: list[RankedKnowledgeDocument]
    evidence: list[KnowledgeEvidenceItem]
    original_decision: dict[str, Any]
    analyst_summary: ReflectionAnalystSummary
    realized_outcome: RealizedOutcomeSummary
    execution_summary: ExecutionSummary
    outcome_metrics: OutcomeMetrics
    exit_context: ExitContext
    post_trade_validation: PostTradeValidationResult
    post_trade_completeness: PostTradeCompletenessResult
    post_trade_notes: str
    feedback_notes: str
    candidate_memory_seed: CandidateMemorySeed


class ReflectionPersistenceResult(TypedDict, total=False):
    """Persistence outcome returned after storing a reflection memory candidate."""

    persisted: bool
    status: str
    title: str
    record_name: str
    path: str
    reason: str
    memory_persistence: MemoryPersistenceAssessment
    validation: dict[str, Any]


class ReflectionOutput(TypedDict, total=False):
    """Structured post-decision reflection output."""

    subject: str
    symbol: str | None
    trade_date: str | None
    reflection_summary: str
    what_worked: list[str]
    what_failed_or_underweighted: list[str]
    lessons: list[str]
    future_adjustments: list[str]
    confidence_change: str
    reference_cases: list[ReflectionReferenceCase]
    candidate_memory: DecisionMemoryRecord
    prompt: str
    reflection_context: ReflectionContext
    memory_persistence: MemoryPersistenceAssessment
    raw_model_output: dict[str, Any]
