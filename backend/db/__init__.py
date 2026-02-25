"""Database connection and schema init. Canonical key: company_number."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Return a connection with foreign keys enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Run schema.sql (idempotent)."""
    sql = _SCHEMA_PATH.read_text()
    conn.executescript(sql)
    conn.commit()


def ensure_db(db_path: str | Path) -> sqlite3.Connection:
    """Create DB file if needed, run schema, return connection."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    init_schema(conn)
    return conn


def log_run(
    conn: sqlite3.Connection,
    stage_name: str,
    company_number: str | None,
    status: str,
    rows_affected: int | None = None,
    error_message: str | None = None,
    source_metadata: str | None = None,
) -> None:
    """Append a pipeline run log row."""
    conn.execute(
        """
        INSERT INTO pipeline_runs
        (stage_name, company_number, status, rows_affected, error_message, completed_at, source_metadata)
        VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """,
        (stage_name, company_number, status, rows_affected, error_message, source_metadata),
    )
    conn.commit()
