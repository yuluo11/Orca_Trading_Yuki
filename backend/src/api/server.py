"""FastAPI server exposing the frontend-facing backend contract."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .contracts import (
    AnalysisRequest,
    AnalysisResponse,
    HistoryRun,
    StartAnalysisResponse,
    WebPageContextRequest,
    WebPageContextResponse,
)
from .run_store import InMemoryRunStore, RunNotFoundError


def create_app(store: InMemoryRunStore | None = None) -> FastAPI:
    run_store = store or InMemoryRunStore()
    api = FastAPI(title="Orca Trading Yuki API", version="0.1.0")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/api/analysis", response_model=StartAnalysisResponse)
    def start_analysis(request: AnalysisRequest) -> StartAnalysisResponse:
        try:
            run_id = run_store.create_analysis(request)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return StartAnalysisResponse(run_id=run_id)

    @api.get("/api/runs", response_model=list[HistoryRun])
    def list_runs() -> list[HistoryRun]:
        return run_store.list_runs()

    @api.get("/api/runs/{run_id}", response_model=AnalysisResponse)
    def get_run_details(run_id: str) -> AnalysisResponse:
        try:
            return run_store.get_run_details(run_id)
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="Run not found") from error

    @api.post("/api/knowledge/web-page", response_model=WebPageContextResponse)
    def collect_web_page_context(request: WebPageContextRequest) -> WebPageContextResponse:
        return run_store.collect_web_page_context(request)

    return api


app = create_app()
