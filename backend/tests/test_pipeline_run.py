"""Tests for pipeline.run_all: run() with different stages and error handling."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from db import ensure_db
from pipeline.run_all import run


def test_run_name_variants_only_no_crash(temp_db):
    """run() with stages=['name_variants'] completes without error (empty registry)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump({"db": {"path": temp_db}, "pipeline": {"stages": ["name_variants"]}}, f)
        config_path = f.name
    log_dir = Path(tempfile.gettempdir()) / "vanguard_test_run_logs"
    try:
        run(config_path=config_path, stages=["name_variants"], log_dir=log_dir)
    finally:
        Path(config_path).unlink(missing_ok=True)


def test_run_ingest_stage_missing_csv_logs_warning(temp_db):
    """run() with stages=['ingest'] and missing CSV does not raise; ingest is skipped (FileNotFoundError caught)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump({
            "db": {"path": temp_db},
            "ingestion": {"companies_house_csv": "/nonexistent/companies.csv"},
            "pipeline": {"stages": ["ingest"]},
        }, f)
        config_path = f.name
    log_dir = Path(tempfile.gettempdir()) / "vanguard_test_run_logs"
    try:
        run(config_path=config_path, stages=["ingest"], log_dir=log_dir)
    finally:
        Path(config_path).unlink(missing_ok=True)


def test_run_score_and_name_variants_with_one_company(temp_db, sample_registry_row):
    """run() with score_asset_manager + name_variants with one company in registry."""
    ensure_db(temp_db)
    conn = __import__("sqlite3").connect(temp_db)
    conn.execute(
        """INSERT INTO company_registry
           (company_number, name, name_normalized, company_type, status, sic_codes, description,
            registered_address, incorporation_date, previous_names, asset_manager_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.8, ?)""",
        (*sample_registry_row,),
    )
    conn.commit()
    conn.close()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump({
            "db": {"path": temp_db},
            "scoring": {"asset_manager": {"threshold": 0.5}},
            "pipeline": {"stages": ["score_asset_manager", "name_variants"]},
        }, f)
        config_path = f.name
    log_dir = Path(tempfile.gettempdir()) / "vanguard_test_run_logs"
    try:
        run(config_path=config_path, stages=["score_asset_manager", "name_variants"], log_dir=log_dir)
        conn = __import__("sqlite3").connect(temp_db)
        n = conn.execute("SELECT COUNT(*) FROM company_name_variants").fetchone()[0]
        conn.close()
        assert n >= 1
    finally:
        Path(config_path).unlink(missing_ok=True)
