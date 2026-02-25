"""Tests for enrichment.linkedin_company and linkedin_people: already-done skip, query building."""
from __future__ import annotations

import pytest

from enrichment.linkedin_company import _build_company_queries, run_linkedin_company_for_company
from enrichment.linkedin_people import _people_queries
from scoring.linkedin_match import linkedin_match_score


def test_linkedin_company_already_in_stage_returns_true(conn, sample_registry_row):
    """If linkedin_company_stage already has this company, run returns True (skip)."""
    conn.execute(
        """INSERT INTO company_registry
           (company_number, name, name_normalized, company_type, status, sic_codes, description,
            registered_address, incorporation_date, previous_names, asset_manager_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (*sample_registry_row,),
    )
    conn.execute(
        """INSERT INTO linkedin_company_stage
           (company_number, linkedin_url, linkedin_slug, linkedin_display_name, match_confidence, chosen_candidate_id, source)
           VALUES (?, 'https://linkedin.com/company/foo', 'foo', 'Test Capital', 0.9, NULL, 'serpapi')""",
        (sample_registry_row[0],),
    )
    conn.commit()
    ok = run_linkedin_company_for_company(
        conn, sample_registry_row[0], sample_registry_row[1],
        delay_seconds=0, min_confidence=0.7, max_queries=5,
    )
    assert ok is True


def test_build_company_queries_uses_search_pipeline(conn, sample_registry_row):
    """_build_company_queries returns list of site:linkedin.com/company queries."""
    conn.execute(
        """INSERT INTO company_registry
           (company_number, name, name_normalized, company_type, status, sic_codes, description,
            registered_address, incorporation_date, previous_names, asset_manager_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (*sample_registry_row,),
    )
    conn.commit()
    queries = _build_company_queries(conn, sample_registry_row[0], sample_registry_row[1], 5)
    assert len(queries) >= 1
    assert all("site:linkedin.com/company" in q for q in queries)


def test_people_queries_structure(conn, sample_registry_row):
    """_people_queries returns list of queries with role phrases and site:linkedin.com/in."""
    conn.execute(
        """INSERT INTO company_registry
           (company_number, name, name_normalized, company_type, status, sic_codes, description,
            registered_address, incorporation_date, previous_names, asset_manager_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (*sample_registry_row,),
    )
    conn.commit()
    queries = _people_queries(
        conn, sample_registry_row[0], sample_registry_row[1],
        None, ["Chief Investment Officer", "CIO"], max_names=2,
    )
    assert isinstance(queries, list)
    assert all("site:linkedin.com/in" in q for q in queries)


class TestLinkedinMatchScore:
    def test_exact_match(self):
        conf, typ = linkedin_match_score("Acme Capital", [], "Acme Capital | LinkedIn", "", "linkedin.com")
        assert conf >= 0.5
        assert typ in ("exact", "partial", "variant")

    def test_no_match(self):
        conf, typ = linkedin_match_score("Acme Capital", [], "Other Company", "", "linkedin.com")
        assert conf <= 0.6
