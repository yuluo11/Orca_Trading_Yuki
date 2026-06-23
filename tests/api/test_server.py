from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.src.api import create_app
from backend.src.api import server
from backend.src.api.run_store import InMemoryRunStore
from backend.src.api.sqlite_run_store import SQLiteRunStore


def build_client() -> TestClient:
    return TestClient(create_app(store=InMemoryRunStore()))


def test_health_endpoint_reports_ok() -> None:
    client = build_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_origins_can_be_extended_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("ORCA_CORS_ORIGINS", "https://orca-trading-yuki-frontend.vercel.app")
    client = TestClient(create_app(store=InMemoryRunStore()))

    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://orca-trading-yuki-frontend.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://orca-trading-yuki-frontend.vercel.app"
    )


def test_default_store_uses_sqlite_without_database_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ORCA_DATABASE_URL", raising=False)
    monkeypatch.setenv("ORCA_RUNS_DB_PATH", str(tmp_path / "runs.db"))

    store = server._build_default_store()

    assert isinstance(store, SQLiteRunStore)


def test_default_store_uses_postgres_when_database_url_is_set(monkeypatch) -> None:
    created: dict[str, str] = {}

    class FakePostgresRunStore:
        def __init__(self, database_url: str) -> None:
            created["database_url"] = database_url

    monkeypatch.setenv("ORCA_DATABASE_URL", "postgresql://example.test/orca")
    monkeypatch.setattr(server, "PostgresRunStore", FakePostgresRunStore)

    store = server._build_default_store()

    assert isinstance(store, FakePostgresRunStore)
    assert created["database_url"] == "postgresql://example.test/orca"


def test_runs_endpoint_returns_frontend_history_contract() -> None:
    client = build_client()

    response = client.get("/api/runs")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 3
    assert {"id", "symbol", "tradeDate", "status", "createdAt"} <= set(payload[0])


def test_run_details_endpoint_returns_frontend_analysis_contract() -> None:
    client = build_client()

    response = client.get("/api/runs/run_001")

    assert response.status_code == 200
    payload = response.json()
    assert "analysts" in payload
    assert payload["decision"]["recommendation"] in {"BUY", "SELL", "HOLD"}
    assert isinstance(payload["decision"]["riskNotes"], list)
    assert payload["reflection"]["guidance"]


def test_run_details_endpoint_returns_404_for_unknown_run() -> None:
    client = build_client()

    response = client.get("/api/runs/unknown")

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"


def test_start_analysis_creates_history_run_and_details() -> None:
    client = build_client()

    start_response = client.post(
        "/api/analysis",
        json={
            "symbol": "msft",
            "tradeDate": "2026-06-07",
            "context": "watch for breakout confirmation",
        },
    )

    assert start_response.status_code == 200
    run_id = start_response.json()["runId"]

    runs_response = client.get("/api/runs")
    assert runs_response.status_code == 200
    created_run = next(run for run in runs_response.json() if run["id"] == run_id)
    assert created_run["symbol"] == "MSFT"
    assert created_run["recommendation"] == "BUY"

    details_response = client.get(f"/api/runs/{run_id}")
    assert details_response.status_code == 200
    assert details_response.json()["decision"]["recommendation"] == "BUY"


def test_web_page_context_endpoint_matches_frontend_contract() -> None:
    client = build_client()

    response = client.post(
        "/api/knowledge/web-page",
        json={"url": "https://example.com/a", "symbol": "NVDA", "persist": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "context_only"
    assert payload["persisted"] is False
    assert "extraContext" in payload
    assert payload["items"][0]["metadata"]["symbol"] == "NVDA"


def test_sqlite_store_persists_runs_across_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "runs.db"
    first_store = SQLiteRunStore(db_path=db_path, seed_if_empty=False)
    first_client = TestClient(create_app(store=first_store))

    start_response = first_client.post(
        "/api/analysis",
        json={
            "symbol": "amzn",
            "tradeDate": "2026-06-07",
            "context": "reduce if momentum fades",
        },
    )
    assert start_response.status_code == 200
    run_id = start_response.json()["runId"]

    second_store = SQLiteRunStore(db_path=db_path, seed_if_empty=False)
    second_client = TestClient(create_app(store=second_store))

    runs_response = second_client.get("/api/runs")
    assert runs_response.status_code == 200
    persisted_run = next(run for run in runs_response.json() if run["id"] == run_id)
    assert persisted_run["symbol"] == "AMZN"
    assert persisted_run["recommendation"] == "SELL"

    details_response = second_client.get(f"/api/runs/{run_id}")
    assert details_response.status_code == 200
    assert details_response.json()["decision"]["recommendation"] == "SELL"
