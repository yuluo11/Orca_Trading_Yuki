"""SQLite run storage used by the HTTP API shell."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .contracts import (
    AnalysisRequest,
    AnalysisResponse,
    HistoryRun,
)
from .run_store import InMemoryRunStore, RunNotFoundError


class SQLiteRunStore(InMemoryRunStore):
    """SQLite-backed store for frontend-facing run history and details."""

    def __init__(self, db_path: str | Path = "runs.db", *, seed_if_empty: bool = True) -> None:
        self.db_path = str(db_path)
        self._init_db()
        if seed_if_empty:
            self._seed_if_empty()

    def _init_db(self) -> None:
        """Initialize the SQLite database and create tables if they do not exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
                    run_id TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()

    def list_runs(self) -> list[HistoryRun]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs ORDER BY created_at DESC")
            rows = cursor.fetchall()

            runs = []
            for row in rows:
                runs.append(
                    HistoryRun(
                        id=row["id"],
                        symbol=row["symbol"],
                        trade_date=row["trade_date"],
                        status=row["status"],
                        created_at=row["created_at"],
                        recommendation=row["recommendation"],
                    )
                )
            return runs

    def get_run_details(self, run_id: str) -> AnalysisResponse:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT response_json FROM run_details WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()

            if row is None:
                raise RunNotFoundError(run_id)

            data = json.loads(row["response_json"])
            return AnalysisResponse(**data)

    def create_analysis(self, request: AnalysisRequest) -> str:
        symbol = request.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")

        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        recommendation = self._choose_recommendation(symbol=symbol, context=request.context)
        created_at = datetime.now(timezone.utc).isoformat()

        # Build detailed response (reuse logic from InMemoryRunStore)
        details = self._build_analysis_response(
            run_id=run_id,
            symbol=symbol,
            trade_date=request.trade_date,
            context=request.context,
            recommendation=recommendation,
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO runs (id, symbol, trade_date, status, created_at, recommendation)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, symbol, request.trade_date, "completed", created_at, recommendation),
            )
            cursor.execute(
                """
                INSERT INTO run_details (run_id, response_json)
                VALUES (?, ?)
                """,
                (run_id, details.model_dump_json(by_alias=True)),
            )
            conn.commit()

        return run_id

    def _seed_if_empty(self) -> None:
        """Seed development sample runs only when the SQLite database is empty."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM runs")
            run_count = cursor.fetchone()[0]

        if run_count:
            return

        seed_requests = [
            ("run_001", "NVDA", "2024-03-20", "BUY", "2024-03-20T08:00:00+00:00"),
            ("run_002", "TSLA", "2024-03-19", None, "2024-03-19T10:30:00+00:00"),
            ("run_003", "AAPL", "2024-03-18", "HOLD", "2024-03-18T14:15:00+00:00"),
        ]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (run_id, symbol, trade_date, status, created_at, recommendation),
                )
                cursor.execute(
                    """
                    INSERT INTO run_details (run_id, response_json)
                    VALUES (?, ?)
                    """,
                    (run_id, details.model_dump_json(by_alias=True)),
                )
            conn.commit()
