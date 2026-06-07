"""Pydantic contracts exposed by the HTTP API layer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Recommendation = Literal["BUY", "SELL", "HOLD"]
RunStatus = Literal["completed", "failed", "running"]


class CamelModel(BaseModel):
    """Base model that accepts Python names while emitting frontend aliases."""

    model_config = ConfigDict(populate_by_name=True)


class AnalysisRequest(CamelModel):
    symbol: str
    trade_date: str = Field(alias="tradeDate")
    context: str = ""


class StartAnalysisResponse(CamelModel):
    run_id: str = Field(alias="runId")


class AnalystResult(CamelModel):
    analyst: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class DecisionOutput(CamelModel):
    recommendation: Recommendation
    confidence: float
    reasoning: str
    risk_notes: list[str] = Field(default_factory=list, alias="riskNotes")


class ReflectionOutput(CamelModel):
    insights: list[str] = Field(default_factory=list)
    guidance: str


class AnalysisResponse(CamelModel):
    analysts: list[AnalystResult] = Field(default_factory=list)
    decision: DecisionOutput
    reflection: ReflectionOutput | None = None


class HistoryRun(CamelModel):
    id: str
    symbol: str
    trade_date: str = Field(alias="tradeDate")
    status: RunStatus
    created_at: str = Field(alias="createdAt")
    recommendation: Recommendation | None = None


class WebPageContextRequest(CamelModel):
    url: str
    symbol: str | None = None
    category: str | None = None
    persist: bool = False


class WebPageContextItem(CamelModel):
    name: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebPageContextResponse(CamelModel):
    mode: Literal["context_only", "persist"]
    persisted: bool
    extra_context: str = Field(alias="extraContext")
    items: list[WebPageContextItem] = Field(default_factory=list)
