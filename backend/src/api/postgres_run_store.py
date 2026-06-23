"""Postgres run storage for deployed API environments."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from .contracts import (
    AnalysisRequest,
    AnalysisResponse,
    HistoryRun,
)
from .run_store import InMemoryRunStore, RunNotFoundError


class PostgresRunStore(InMemoryRunStore):
    """Postgres-backed store for frontend-facing run history and details."""

    def __init__(self, database_url: str, *, seed_if_empty: bool = True) -> None:
        self.database_url = database_url
        self._init_db()
        if seed_if_empty:
            self._seed_if_empty()

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError(
                "Postgres storage requires the psycopg dependency. "
                "Install backend dependencies before using ORCA_DATABASE_URL."
            ) from error

        if "sslmode=" in self.database_url.lower():
            return psycopg.connect(self.database_url, row_factory=dict_row)
        return psycopg.connect(self.database_url, sslmode="require", row_factory=dict_row)

    def _init_db(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS runs (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        trade_date TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        recommendation TEXT
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_details (
                        run_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
                        response_json JSONB NOT NULL
                    )
                    """
                )
            conn.commit()

    def list_runs(self) -> list[HistoryRun]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM runs ORDER BY created_at DESC")
                rows = cursor.fetchall()

        return [
            HistoryRun(
                id=row["id"],
                symbol=row["symbol"],
                trade_date=row["trade_date"],
                status=row["status"],
                created_at=row["created_at"],
                recommendation=row["recommendation"],
            )
            for row in rows
        ]

    def get_run_details(self, run_id: str) -> AnalysisResponse:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT response_json FROM run_details WHERE run_id = %s",
                    (run_id,),
                )
                row = cursor.fetchone()

        if row is None:
            raise RunNotFoundError(run_id)

        data = _decode_json(row["response_json"])
        return AnalysisResponse(**data)

    def create_analysis(self, request: AnalysisRequest) -> str:
        symbol = request.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        recommendation = self._choose_recommendation(symbol=symbol, context=request.context)
        created_at = datetime.now(timezone.utc).isoformat()
        details = self._build_analysis_response(
            run_id=run_id,
            symbol=symbol,
            trade_date=request.trade_date,
            context=request.context,
            recommendation=recommendation,
        )

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO runs (id, symbol, trade_date, status, created_at, recommendation)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (run_id, symbol, request.trade_date, "completed", created_at, recommendation),
                )
                cursor.execute(
                    """
                    INSERT INTO run_details (run_id, response_json)
                    VALUES (%s, %s::jsonb)
                    """,
                    (run_id, details.model_dump_json(by_alias=True)),
                )
            conn.commit()

        return run_id

    def _seed_if_empty(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS count FROM runs")
                run_count = cursor.fetchone()["count"]

        if run_count:
            return

        seed_requests = [
            ("run_001", "NVDA", "2024-03-20", "BUY", "2024-03-20T08:00:00+00:00"),
            ("run_002", "TSLA", "2024-03-19", None, "2024-03-19T10:30:00+00:00"),
            ("run_003", "AAPL", "2024-03-18", "HOLD", "2024-03-18T14:15:00+00:00"),
        ]
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for run_id, symbol, trade_date, recommendation, created_at in seed_requests:
                    status = "failed" if recommendation is None else "completed"
                    details = self._build_analysis_response(
                        run_id=run_id,
                        symbol=symbol,
                        trade_date=trade_date,
                        context="Seeded API shell run.",
                        recommendation=recommendation or "HOLD",
                    )
                    cursor.execute(
                        """
                        INSERT INTO runs (id, symbol, trade_date, status, created_at, recommendation)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (run_id, symbol, trade_date, status, created_at, recommendation),
                    )
                    cursor.execute(
                        """
                        INSERT INTO run_details (run_id, response_json)
                        VALUES (%s, %s::jsonb)
                        """,
                        (run_id, details.model_dump_json(by_alias=True)),
                    )
            conn.commit()


def _decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)
