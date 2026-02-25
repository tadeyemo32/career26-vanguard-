"""Tests for ingestion.companies_house: _get_cell, is_company_active, row_to_registry."""
from __future__ import annotations

import pytest

from ingestion.companies_house import (
    _get_cell,
    is_company_active,
    row_to_registry,
)


class TestGetCell:
    """_get_cell: exact key, stripped key, leading-space key."""

    def test_exact_key(self):
        row = {"CompanyName": "Acme", "CompanyNumber": "123"}
        assert _get_cell(row, "CompanyName") == "Acme"
        assert _get_cell(row, "CompanyNumber") == "123"

    def test_stripped_key(self):
        row = {"CompanyName": "Acme"}
        assert _get_cell(row, "  CompanyName  ") == "Acme"

    def test_leading_space_header(self):
        row = {" CompanyNumber": "123"}
        assert _get_cell(row, "CompanyNumber") == "123"

    def test_missing_returns_none(self):
        row = {"Other": "x"}
        assert _get_cell(row, "CompanyName") is None

    def test_empty_string_returns_none(self):
        row = {"CompanyName": "  "}
        assert _get_cell(row, "CompanyName") is None


class TestIsCompanyActive:
    """is_company_active: status must match allowed (e.g. Active, Active - Proposal to Strike off)."""

    @pytest.mark.parametrize(
        "status,allowed,expected",
        [
            ("Active", ["Active"], True),
            ("Active - Proposal to Strike off", ["Active"], True),
            ("Dissolved", ["Active"], False),
            ("Liquidation", ["Active"], False),
            ("", ["Active"], False),
            (None, ["Active"], False),
        ],
    )
    def test_status(self, status, allowed, expected):
        assert is_company_active(status, allowed) == expected


class TestRowToRegistry:
    """row_to_registry: maps CSV row to registry tuple; uses clean_company_name and clean_text."""

    def test_minimal_row(self, sample_csv_row, default_column_config):
        prev_cols = []
        t = row_to_registry(sample_csv_row, default_column_config, prev_cols)
        assert t[0] == "12345678"
        assert "Test Capital Management" in t[1]
        assert t[4] == "Active"
        assert "66300" in (t[5] or "")

    def test_missing_name_raises(self, default_column_config, sample_csv_row):
        sample_csv_row[default_column_config["name"]] = ""
        with pytest.raises(ValueError, match="missing"):
            row_to_registry(sample_csv_row, default_column_config, [])

    def test_previous_names_collected(self, default_column_config, sample_csv_row):
        prev_cols = ["PreviousName_1.CompanyName"]
        sample_csv_row["PreviousName_1.CompanyName"] = "Old Name Ltd"
        t = row_to_registry(sample_csv_row, default_column_config, prev_cols)
        assert "previous_names" in str(t).lower() or "Old Name" in (t[9] or "")
