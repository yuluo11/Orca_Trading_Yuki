"""Optional FastAPI adapter for knowledge route handlers.

The knowledge routes stay framework-neutral in ``backend.src.routes``. This
module is only the HTTP boundary, so importing the backend does not require
FastAPI unless this adapter is explicitly created.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..knowledge.collectors import HtmlFetcher
from ..knowledge.repository import KnowledgeRepository
from ..knowledge.source_governance import DynamicSourceGovernancePolicy
from ..routes.knowledge import (
    collect_rss_feed_payload,
    collect_web_page_payload,
    get_processed_record_payload,
    evaluate_knowledge_payload,
    list_dynamic_sources_payload,
    list_processed_records_payload,
    register_dynamic_source_payload,
    run_due_dynamic_sources_payload,
    run_dynamic_source_payload,
    search_knowledge_payload,
)

RouteHandler = Callable[..., dict[str, Any]]


def create_knowledge_api(
    *,
    repository: KnowledgeRepository | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
    web_page_fetcher: HtmlFetcher | None = None,
    rss_fetcher: HtmlFetcher | None = None,
    due_source_fetchers: dict[str, HtmlFetcher] | None = None,
) -> Any:
    """Create the optional FastAPI app for knowledge operations.

    FastAPI is intentionally imported inside this factory. The rest of the
    backend can run in pure Python environments where the HTTP server is not
    installed yet.
    """

    try:
        from fastapi import FastAPI, HTTPException
    except ModuleNotFoundError as exc:
        if exc.name == "fastapi":
            raise ModuleNotFoundError(
                "fastapi is required for the knowledge HTTP API. "
                "Install the backend API extra, for example: "
                "pip install -e 'backend[api]'"
            ) from exc
        raise

    app = FastAPI(
        title="Orca Trading Yuki Knowledge API",
        version="0.1.0",
        description=(
            "Optional HTTP adapter over the framework-neutral knowledge route "
            "handlers."
        ),
    )

    def call_route(handler: RouteHandler, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        try:
            return handler(payload or {}, **kwargs)
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "knowledge-api"}

    @app.post("/knowledge/collect/web-page")
    def collect_web_page(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            collect_web_page_payload,
            payload,
            repository=repository,
            fetcher=web_page_fetcher,
            source_policy=source_policy,
        )

    @app.post("/knowledge/collect/rss-feed")
    def collect_rss_feed(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            collect_rss_feed_payload,
            payload,
            repository=repository,
            fetcher=rss_fetcher,
            source_policy=source_policy,
        )

    @app.post("/knowledge/records/list")
    def list_processed_records(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            list_processed_records_payload,
            payload,
            repository=repository,
        )

    @app.post("/knowledge/records/get")
    def get_processed_record(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            get_processed_record_payload,
            payload,
            repository=repository,
        )

    @app.post("/knowledge/search")
    def search_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            search_knowledge_payload,
            payload,
            repository=repository,
        )

    @app.post("/knowledge/evaluate")
    def evaluate_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            evaluate_knowledge_payload,
            payload,
            repository=repository,
        )

    @app.post("/knowledge/sources/register")
    def register_dynamic_source(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            register_dynamic_source_payload,
            payload,
            repository=repository,
            source_policy=source_policy,
        )

    @app.post("/knowledge/sources/list")
    def list_dynamic_sources(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            list_dynamic_sources_payload,
            payload,
            repository=repository,
        )

    @app.post("/knowledge/sources/run")
    def run_dynamic_source(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            run_dynamic_source_payload,
            payload,
            repository=repository,
            fetcher=web_page_fetcher,
            source_policy=source_policy,
        )

    @app.post("/knowledge/sources/run-due")
    def run_due_dynamic_sources(payload: dict[str, Any]) -> dict[str, Any]:
        return call_route(
            run_due_dynamic_sources_payload,
            payload,
            repository=repository,
            fetchers=due_source_fetchers,
            source_policy=source_policy,
        )

    return app


create_app = create_knowledge_api
