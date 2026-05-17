"""Structured task and runtime state for the decision layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from ....knowledge.repository import DatasetName


@dataclass(slots=True)
class DecisionTask:
    """Structured input consumed by the decision advisory agent."""

    subject: str
    symbol: str | None = None
    trade_date: str | None = None
    extra_context: str | None = None
    overall_summary: str = ""
    overall_confidence: str = "low"
    key_signals: list[str] = field(default_factory=list)
    portfolio_risks: list[str] = field(default_factory=list)
    cross_analyst_observations: list[str] = field(default_factory=list)
    analyst_results: list[dict[str, Any]] = field(default_factory=list)
    analyst_sequence: list[str] = field(default_factory=list)
    datasets: tuple[DatasetName, ...] | None = None
    metadata_filter: dict[str, Any] | None = None
    max_documents: int | None = None
    messages: list[Any] = field(default_factory=list)

    @classmethod
    def from_analyst_payload(
        cls,
        analyst_payload: dict[str, Any],
        *,
        datasets: tuple[DatasetName, ...] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        max_documents: int | None = None,
        messages: list[Any] | None = None,
    ) -> "DecisionTask":
        """Build a decision task directly from analyst orchestrator output."""
        return cls(
            subject=str(analyst_payload.get("subject", "")).strip(),
            symbol=analyst_payload.get("symbol"),
            trade_date=analyst_payload.get("trade_date"),
            extra_context=analyst_payload.get("extra_context"),
            overall_summary=str(analyst_payload.get("overall_summary", "")).strip(),
            overall_confidence=str(analyst_payload.get("overall_confidence", "low")).strip(),
            key_signals=[
                str(item).strip()
                for item in analyst_payload.get("key_signals", [])
                if str(item).strip()
            ],
            portfolio_risks=[
                str(item).strip()
                for item in analyst_payload.get("portfolio_risks", [])
                if str(item).strip()
            ],
            cross_analyst_observations=[
                str(item).strip()
                for item in analyst_payload.get("cross_analyst_observations", [])
                if str(item).strip()
            ],
            analyst_results=list(analyst_payload.get("analyst_results", [])),
            analyst_sequence=[
                str(item).strip()
                for item in analyst_payload.get("analyst_sequence", [])
                if str(item).strip()
            ],
            datasets=datasets,
            metadata_filter=metadata_filter,
            max_documents=max_documents,
            messages=list(messages or analyst_payload.get("messages", [])),
        )


class DecisionRuntimeState(TypedDict, total=False):
    """State shape for future decision-oriented graph composition."""

    subject: str
    symbol: str | None
    trade_date: str | None
    extra_context: str | None
    overall_summary: str
    overall_confidence: str
    key_signals: list[str]
    portfolio_risks: list[str]
    cross_analyst_observations: list[str]
    analyst_results: list[dict[str, Any]]
    analyst_sequence: list[str]
    datasets: tuple[DatasetName, ...] | list[DatasetName] | None
    metadata_filter: dict[str, Any] | None
    max_documents: int | None
    messages: list[Any]
    decision_output: dict[str, Any]
