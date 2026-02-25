"""Tests for scoring.asset_manager: SIC extraction and asset_manager_score."""
from __future__ import annotations

import pytest

from scoring.asset_manager import (
    _extract_sic_code,
    asset_manager_score,
    update_registry_scores,
)


class TestExtractSicCode:
    """_extract_sic_code: Companies House format 'CODE - Description' or 'CODE'."""

    @pytest.mark.parametrize(
        "cell,expected",
        [
            ("66300 - Fund management activities", "66300"),
            ("64304 - Activities of open-ended investment companies", "64304"),
            ("70221 - Financial management", "70221"),
            ("66300", "66300"),
            (" 66300 - Something ", "66300"),
            ("", None),
            ("   ", None),
        ],
    )
    def test_extract(self, cell, expected):
        assert _extract_sic_code(cell) == expected

    def test_malformed_returns_none_or_code(self):
        assert _extract_sic_code("No code here") is None
        assert _extract_sic_code("123 - X") == "123"


class TestAssetManagerScore:
    """asset_manager_score: SIC whitelist + keywords, cap at 1.0."""

    def test_empty_inputs(self):
        assert asset_manager_score(None, None, {}, {}) == 0.0
        assert asset_manager_score("[]", "", {}, {}) == 0.0

    def test_sic_whitelist_json_array(self):
        sic_json = '["66300 - Fund management activities", "64304 - Activities of OEICs"]'
        whitelist = {"66300": 0.5, "64304": 0.4}
        score = asset_manager_score(sic_json, None, whitelist, {})
        assert score == 0.9

    def test_sic_whitelist_no_double_count(self):
        sic_json = '["66300 - Fund management activities"]'
        whitelist = {"66300": 0.8}
        score = asset_manager_score(sic_json, None, whitelist, {})
        assert score == 0.8

    def test_keywords_in_description(self):
        desc = "66300 - Fund management activities | 70221 - Financial management"
        keywords = {"fund management": 0.3, "financial": 0.2}
        score = asset_manager_score("[]", desc, {}, keywords)
        assert score == 0.5

    def test_cap_at_one(self):
        sic_json = '["66300 - X", "64304 - Y", "70221 - Z"]'
        whitelist = {"66300": 0.5, "64304": 0.5, "70221": 0.5}
        score = asset_manager_score(sic_json, None, whitelist, {})
        assert score == 1.0

    def test_pipe_separated_sic_fallback(self):
        sic_str = "66300 - Fund management | 64304 - OEICs"
        whitelist = {"66300": 0.4, "64304": 0.3}
        score = asset_manager_score(sic_str, sic_str, whitelist, {})
        assert score >= 0.6


class TestUpdateRegistryScores:
    """update_registry_scores: updates DB rows."""

    def test_updates_scores(self, conn):
        conn.execute(
            """INSERT INTO company_registry
               (company_number, name, name_normalized, company_type, status, sic_codes, description,
                registered_address, incorporation_date, previous_names, asset_manager_score, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (
                "1",
                "Test Ltd",
                "test ltd",
                "PLC",
                "Active",
                '["66300 - Fund management"]',
                "66300 - Fund management",
                None,
                None,
                "[]",
                "test",
            ),
        )
        conn.commit()
        from scoring.asset_manager import update_registry_scores
        n = update_registry_scores(conn, {"66300": 0.7}, {})
        assert n == 1
        row = conn.execute(
            "SELECT asset_manager_score FROM company_registry WHERE company_number = '1'"
        ).fetchone()
        assert row[0] == 0.7
