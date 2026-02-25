"""Tests for db: get_connection, init_schema, ensure_db, log_run."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from db import ensure_db, get_connection, init_schema, log_run


def test_get_connection_creates_connection():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn = get_connection(path)
        conn.execute("SELECT 1")
        conn.close()
    finally:
        Path(path).unlink(missing_ok=True)


def test_init_schema_creates_tables(conn):
    """Schema creates company_registry and pipeline_runs (and others)."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('company_registry', 'pipeline_runs')"
    )
    names = [row[0] for row in cur.fetchall()]
    assert "company_registry" in names
    assert "pipeline_runs" in names


def test_ensure_db_creates_parent_dir_and_schema():
    """ensure_db creates parent directory and applies full schema."""
    tmp = tempfile.gettempdir()
    db_path = Path(tmp) / "vanguard_test_ensure_db" / "sub" / "test.db"
    try:
        conn = ensure_db(db_path)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        assert "company_registry" in tables
        assert "pipeline_runs" in tables
        conn.close()
    finally:
        if db_path.exists():
            db_path.unlink()
        for p in [db_path.parent, db_path.parent.parent]:
            if p.exists() and p != Path(tmp):
                try:
                    p.rmdir()
                except OSError:
                    pass


def test_log_run_inserts_row(conn):
    """log_run inserts a row into pipeline_runs."""
    log_run(
        conn,
        stage_name="test_stage",
        company_number="123",
        status="completed",
        rows_affected=10,
        error_message=None,
        source_metadata=None,
    )
    cur = conn.execute(
        "SELECT stage_name, company_number, status, rows_affected FROM pipeline_runs WHERE stage_name = 'test_stage'"
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "test_stage"
    assert row[1] == "123"
    assert row[2] == "completed"
    assert row[3] == 10


def test_log_run_with_error_message(conn):
    """log_run stores error_message when stage fails."""
    log_run(
        conn,
        stage_name="ingest",
        company_number=None,
        status="failed",
        rows_affected=None,
        error_message="File not found",
        source_metadata=None,
    )
    cur = conn.execute(
        "SELECT error_message FROM pipeline_runs WHERE stage_name = 'ingest' AND status = 'failed'"
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "File not found"
