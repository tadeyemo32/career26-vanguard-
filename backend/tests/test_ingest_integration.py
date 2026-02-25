"""Tests for ingestion: ingest_csv (integration) and error paths."""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from ingestion.companies_house import ingest_csv, row_to_registry


def test_ingest_csv_file_not_found_raises(temp_db):
    """ingest_csv raises FileNotFoundError when CSV path does not exist."""
    with pytest.raises(FileNotFoundError, match="not found|CSV"):
        ingest_csv(temp_db, Path("/nonexistent/companies.csv"), batch_size=100)


def test_ingest_csv_empty_file_zero_rows(temp_db, default_column_config):
    """Empty CSV (header only) results in 0 rows ingested."""
    with tempfile.NamedTemporaryFile(mode="w", newline="", suffix=".csv", delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=list(default_column_config.values()))
        writer.writeheader()
        path = Path(f.name)
    try:
        n = ingest_csv(
            temp_db,
            path,
            batch_size=100,
            column_config=default_column_config,
            previous_name_columns=[],
            active_only=False,
        )
        assert n == 0
    finally:
        path.unlink(missing_ok=True)


def test_ingest_csv_one_row_integration(temp_db, default_column_config, sample_csv_row):
    """One valid row is ingested into company_registry."""
    with tempfile.NamedTemporaryFile(mode="w", newline="", suffix=".csv", delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=list(default_column_config.values()))
        writer.writeheader()
        writer.writerow(sample_csv_row)
        path = Path(f.name)
    try:
        n = ingest_csv(
            temp_db,
            path,
            batch_size=100,
            column_config=default_column_config,
            previous_name_columns=[],
            active_only=False,
        )
        assert n == 1
        conn = __import__("sqlite3").connect(temp_db)
        cur = conn.execute("SELECT company_number, name FROM company_registry")
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "12345678"
        assert "Test Capital" in (row[1] or "")
    finally:
        path.unlink(missing_ok=True)


def test_ingest_csv_active_only_skips_dissolved(temp_db, default_column_config, sample_csv_row):
    """When active_only=True, dissolved companies are not ingested."""
    with tempfile.NamedTemporaryFile(mode="w", newline="", suffix=".csv", delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=list(default_column_config.values()))
        writer.writeheader()
        dissolved_row = dict(sample_csv_row)
        dissolved_row[default_column_config["status"]] = "Dissolved"
        dissolved_row[default_column_config["company_number"]] = "99999999"
        dissolved_row[default_column_config["name"]] = "Dissolved Company Ltd"
        writer.writerow(dissolved_row)
        path = Path(f.name)
    try:
        n = ingest_csv(
            temp_db,
            path,
            batch_size=100,
            column_config=default_column_config,
            previous_name_columns=[],
            active_only=True,
            allowed_company_statuses=["Active"],
        )
        assert n == 0
        conn = __import__("sqlite3").connect(temp_db)
        cur = conn.execute("SELECT 1 FROM company_registry WHERE company_number = '99999999'")
        assert cur.fetchone() is None
        conn.close()
    finally:
        path.unlink(missing_ok=True)


def test_row_to_registry_missing_company_number_raises(default_column_config, sample_csv_row):
    """row_to_registry raises ValueError when company_number or name is missing."""
    sample_csv_row[default_column_config["company_number"]] = ""
    with pytest.raises(ValueError, match="missing"):
        row_to_registry(sample_csv_row, default_column_config, [])
