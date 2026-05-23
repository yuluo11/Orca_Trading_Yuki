"""Typed analyst-layer payload contracts."""

from __future__ import annotations

from typing import Any, TypedDict

from .knowledge import KnowledgeDocument, KnowledgeEvidenceItem


class AnalystResult(TypedDict, total=False):
    """Single analyst output returned from one analyst agent."""

    analyst: str
    subject: str
    symbol: str | None
    trade_date: str | None
    summary: str
    signals: list[str]
    risks: list[str]
    confidence: str
    prompt: str
    query: str
    documents: list[KnowledgeDocument]
    evidence: list[KnowledgeEvidenceItem]
    tool_trace: list[dict[str, Any]]
    raw_model_output: dict[str, Any]


class AnalystOrchestrationResult(TypedDict, total=False):
    """Aggregated analyst output produced by the orchestrator."""

    subject: str
    symbol: str | None
    trade_date: str | None
    extra_context: str | None
    analyst_sequence: list[str]
    overall_summary: str
    overall_confidence: str
    key_signals: list[str]
    portfolio_risks: list[str]
    cross_analyst_observations: list[str]
    analyst_results: list[AnalystResult]
    message_count: int
    messages: list[Any]
