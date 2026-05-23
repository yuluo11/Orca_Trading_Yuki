"""Typed knowledge-memory payload contracts shared by decision and reflection."""

from __future__ import annotations

from typing import TypedDict


class DecisionMemoryMetadata(TypedDict, total=False):
    """Normalized metadata attached to reusable decision-memory records."""

    source: str
    source_type: str
    title: str
    created_at: str
    updated_at: str
    category: str
    memory_type: str
    tags: list[str]
    symbol: str
    subject: str
    topic: str
    recommendation: str
    confidence: str
    market_regime: str
    analyst_alignment: str
    signal_tags: list[str]
    risk_tags: list[str]
    timing_tags: list[str]
    portfolio_state_tags: list[str]
    outcome_label: str
    quality_score: float
    dataset: str


class DecisionMemoryRecord(TypedDict, total=False):
    """Canonical processed record stored for decision-memory retrieval."""

    text: str
    metadata: DecisionMemoryMetadata


class DecisionMemoryValidationExample(TypedDict, total=False):
    """Compact example attached to validation summaries for diagnostics."""

    title: str
    errors: list[str]
    warnings: list[str]


class DecisionMemoryValidationSummary(TypedDict, total=False):
    """Aggregated validation stats for candidate decision-memory documents."""

    total_candidates: int
    valid_candidates: int
    invalid_candidates: int
    warning_candidates: int
    valid_warning_candidates: int
    invalid_warning_candidates: int
    invalid_examples: list[DecisionMemoryValidationExample]
    warning_examples: list[DecisionMemoryValidationExample]
