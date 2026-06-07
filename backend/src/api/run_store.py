"""In-memory run storage used by the first HTTP API shell."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

from .contracts import (
    AnalysisRequest,
    AnalysisResponse,
    AnalystResult,
    DecisionOutput,
    HistoryRun,
    Recommendation,
    ReflectionOutput,
    WebPageContextItem,
    WebPageContextRequest,
    WebPageContextResponse,
)


class RunNotFoundError(KeyError):
    """Raised when a requested analysis run does not exist."""


class InMemoryRunStore:
    """Small process-local store until persistence and job orchestration land."""

    def __init__(self) -> None:
        self._runs: dict[str, HistoryRun] = {}
        self._details: dict[str, AnalysisResponse] = {}
        self._seed()

    def list_runs(self) -> list[HistoryRun]:
        return sorted(
            self._runs.values(),
            key=lambda run: run.created_at,
            reverse=True,
        )

    def get_run_details(self, run_id: str) -> AnalysisResponse:
        try:
            return self._details[run_id]
        except KeyError as error:
            raise RunNotFoundError(run_id) from error

    def create_analysis(self, request: AnalysisRequest) -> str:
        symbol = request.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        recommendation = self._choose_recommendation(symbol=symbol, context=request.context)
        created_at = datetime.now(timezone.utc).isoformat()

        self._runs[run_id] = HistoryRun(
            id=run_id,
            symbol=symbol,
            trade_date=request.trade_date,
            status="completed",
            created_at=created_at,
            recommendation=recommendation,
        )
        self._details[run_id] = self._build_analysis_response(
            run_id=run_id,
            symbol=symbol,
            trade_date=request.trade_date,
            context=request.context,
            recommendation=recommendation,
        )
        return run_id

    def collect_web_page_context(self, request: WebPageContextRequest) -> WebPageContextResponse:
        host = urlparse(request.url).netloc or "unknown-source"
        symbol = request.symbol.strip().upper() if request.symbol else None
        title = f"{symbol} URL Context" if symbol else "Collected URL Context"
        category = request.category or "web_page"
        extra_context = (
            f"[Collected context] {title} | {request.url}"
            f"{f' | {symbol}' if symbol else ''} | {category}\n"
            f"HTTP API shell registered {host} as temporary analysis context."
        )

        return WebPageContextResponse(
            mode="persist" if request.persist else "context_only",
            persisted=request.persist,
            extra_context=extra_context,
            items=[
                WebPageContextItem(
                    name=f"web_{host.replace('.', '_').replace(':', '_')}",
                    text=extra_context,
                    metadata={
                        "source_url": request.url,
                        "title": title,
                        "category": category,
                        **({"symbol": symbol} if symbol else {}),
                    },
                )
            ],
        )

    def _seed(self) -> None:
        seed_requests = [
            ("run_001", "NVDA", "2024-03-20", "BUY", "2024-03-20T08:00:00+00:00"),
            ("run_002", "TSLA", "2024-03-19", None, "2024-03-19T10:30:00+00:00"),
            ("run_003", "AAPL", "2024-03-18", "HOLD", "2024-03-18T14:15:00+00:00"),
        ]
        for run_id, symbol, trade_date, recommendation, created_at in seed_requests:
            status = "failed" if recommendation is None else "completed"
            self._runs[run_id] = HistoryRun(
                id=run_id,
                symbol=symbol,
                trade_date=trade_date,
                status=status,
                created_at=created_at,
                recommendation=recommendation,
            )
            self._details[run_id] = self._build_analysis_response(
                run_id=run_id,
                symbol=symbol,
                trade_date=trade_date,
                context="Seeded API shell run.",
                recommendation=recommendation or "HOLD",
            )

    def _build_analysis_response(
        self,
        *,
        run_id: str,
        symbol: str,
        trade_date: str,
        context: str,
        recommendation: Recommendation,
    ) -> AnalysisResponse:
        return AnalysisResponse(
            analysts=[
                AnalystResult(
                    analyst="Market Analyst",
                    summary=f"{symbol} showed a reviewable setup for {trade_date}.",
                    details={
                        "run_id": run_id,
                        "source": "http_api_shell",
                        "context_preview": context[:160],
                    },
                ),
                AnalystResult(
                    analyst="Risk Analyst",
                    summary=f"Risk posture for {symbol} should be checked before execution.",
                    details={"primary_risk": "API shell uses placeholder analysis until live jobs are wired."},
                ),
            ],
            decision=DecisionOutput(
                recommendation=recommendation,
                confidence=0.72,
                reasoning=(
                    f"Generated by the backend API shell for run {run_id}. "
                    "Replace this with the decision workflow once persistence and jobs are connected."
                ),
                risk_notes=[
                    "This response is deterministic shell data, not live financial advice.",
                    "Connect the workflow runner before using this for production decisions.",
                ],
            ),
            reflection=ReflectionOutput(
                insights=[f"{symbol} has a completed run record available through the HTTP API."],
                guidance="Use this endpoint contract to validate the frontend integration path.",
            ),
        )

    def _choose_recommendation(self, *, symbol: str, context: str) -> Recommendation:
        normalized = f"{symbol} {context}".lower()
        if "sell" in normalized or "reduce" in normalized:
            return "SELL"
        if "buy" in normalized or "breakout" in normalized:
            return "BUY"
        return "HOLD"
