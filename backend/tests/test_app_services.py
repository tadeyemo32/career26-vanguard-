"""
Unit tests for app services used by the UI: parse_pasted_data, load_spreadsheet,
export_results_csv, save_env_keys. Ensures all UI-backed logic works as intended.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.services import (
    export_results_csv,
    load_spreadsheet,
    parse_pasted_data,
    save_env_keys,
)


class TestParsePastedData:
    """Parse pasted text (Ingest → Paste data)."""

    def test_empty_returns_error(self):
        rows, cols, err = parse_pasted_data("")
        assert err is not None
        assert "No data" in err or "past" in err.lower()
        assert rows == [] and cols == []

    def test_whitespace_only_returns_error(self):
        rows, cols, err = parse_pasted_data("   \n\n  ")
        assert err is not None
        assert rows == [] and cols == []

    def test_single_column_company_per_line(self):
        text = "Acme Ltd\nBeta Inc\nGamma Corp"
        rows, cols, err = parse_pasted_data(text)
        assert err is None
        assert cols == ["company"]
        assert len(rows) == 3
        assert rows[0]["company"] == "Acme Ltd"
        assert rows[2]["company"] == "Gamma Corp"

    def test_name_comma_company_per_line(self):
        # When first line has comma, CSV parser uses it as header; then we get name,company from explicit header
        text = "name,company\nJohn Smith,Acme Ltd\nJane Doe,Beta Inc"
        rows, cols, err = parse_pasted_data(text)
        assert err is None
        assert cols == ["name", "company"]
        assert len(rows) == 2
        assert rows[0]["name"] == "John Smith" and rows[0]["company"] == "Acme Ltd"
        assert rows[1]["name"] == "Jane Doe" and rows[1]["company"] == "Beta Inc"

    def test_csv_with_header(self):
        text = "name,company,role\nAlice,Acme,CEO\nBob,Beta,CTO"
        rows, cols, err = parse_pasted_data(text)
        assert err is None
        assert "name" in cols and "company" in cols and "role" in cols
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice" and rows[0]["company"] == "Acme"

    def test_tsv_with_header(self):
        text = "name\tcompany\nAlice\tAcme\nBob\tBeta"
        rows, cols, err = parse_pasted_data(text)
        assert err is None
        assert cols == ["name", "company"]
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice" and rows[0]["company"] == "Acme"


class TestLoadSpreadsheet:
    """Load CSV/Excel (Ingest / From file)."""

    def test_missing_file_returns_error(self, tmp_path: Path):
        path = tmp_path / "nonexistent.csv"
        rows, cols, err = load_spreadsheet(path)
        assert err is not None
        assert "not found" in err.lower() or "File" in err
        assert rows == [] and cols == []

    def test_csv_loads_correctly(self, tmp_path: Path):
        path = tmp_path / "test.csv"
        path.write_text("company,name\nAcme,Alice\nBeta,Bob", encoding="utf-8")
        rows, cols, err = load_spreadsheet(path)
        assert err is None
        assert cols == ["company", "name"]
        assert len(rows) == 2
        assert rows[0]["company"] == "Acme" and rows[0]["name"] == "Alice"

    def test_unsupported_format_returns_error(self, tmp_path: Path):
        path = tmp_path / "test.pdf"
        path.write_text("x")
        rows, cols, err = load_spreadsheet(path)
        assert err is not None
        assert "Unsupported" in err or ".pdf" in err
        assert rows == [] and cols == []


class TestExportResultsCsv:
    """Export CSV (Ingest, From file, People search)."""

    def test_no_rows_returns_error(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        err = export_results_csv([], out, ["a", "b"])
        assert err is not None
        assert "No rows" in err
        assert not out.exists()

    def test_export_writes_valid_csv(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        rows = [{"name": "Alice", "company": "Acme"}, {"name": "Bob", "company": "Beta"}]
        err = export_results_csv(rows, out, ["name", "company"])
        assert err is None
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "name,company" in content
        assert "Alice,Acme" in content
        assert "Bob,Beta" in content

    def test_export_with_columns_subset(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        rows = [{"name": "Alice", "company": "Acme", "extra": "x"}]
        err = export_results_csv(rows, out, ["name", "company"])
        assert err is None
        content = out.read_text(encoding="utf-8")
        assert "name,company" in content
        assert "extra" not in content


class TestSaveEnvKeys:
    """Save API keys to .env (Settings tab)."""

    _KEYS = ("SERPAPI_KEY", "OPENAI_API_KEY")

    def test_no_updates_does_not_write(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("OTHER=value\n")
        save_env_keys(env_path, self._KEYS, lambda k: "")
        content = env_path.read_text()
        assert "OTHER=value" in content
        assert "SERPAPI_KEY" not in content

    def test_adds_new_keys(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        save_env_keys(env_path, self._KEYS, lambda k: "secret" if k == "SERPAPI_KEY" else "")
        content = env_path.read_text()
        assert "SERPAPI_KEY=secret" in content

    def test_updates_existing_key_preserves_others(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("SERPAPI_KEY=old\nOTHER=keep\nOPENAI_API_KEY=old2\n")
        save_env_keys(env_path, self._KEYS, lambda k: "new" if k == "SERPAPI_KEY" else "")
        content = env_path.read_text()
        assert "SERPAPI_KEY=new" in content
        assert "OTHER=keep" in content
        assert "OPENAI_API_KEY=old2" in content

    def test_preserves_comments_and_unchanged_keys(self, tmp_path: Path):
        env_path = tmp_path / ".env"
        env_path.write_text("# comment\nSERPAPI_KEY=old\n# other\nANYMAIL=x\n")
        save_env_keys(env_path, ("SERPAPI_KEY",), lambda k: "updated")
        content = env_path.read_text()
        assert "SERPAPI_KEY=updated" in content
        assert "# comment" in content
        assert "ANYMAIL=x" in content
