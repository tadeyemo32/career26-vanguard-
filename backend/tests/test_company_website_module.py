"""Tests for enrichment.company_website: _is_likely_company_site, run when already in stage."""
from __future__ import annotations

import pytest

from enrichment.company_website import _is_likely_company_site, run_company_website_for_company


class TestIsLikelyCompanySite:
    """_is_likely_company_site returns 0 for social/directory, higher for matching domain."""

    def test_linkedin_returns_zero(self):
        assert _is_likely_company_site("https://linkedin.com/company/foo", "Acme") == 0.0

    def test_facebook_returns_zero(self):
        assert _is_likely_company_site("https://facebook.com/bar", "Acme") == 0.0

    def test_companies_house_low_confidence(self):
        assert _is_likely_company_site("https://companieshouse.gov.uk/company/123", "Acme") == 0.3

    def test_company_name_in_domain_high_confidence(self):
        assert _is_likely_company_site("https://acmecapital.com", "Acme Capital Ltd") >= 0.8

    def test_generic_returns_mid(self):
        # URL with no name words in domain returns default 0.6
        conf = _is_likely_company_site("https://example.org", "Acme Capital")
        assert conf == 0.6


def test_run_company_website_already_in_stage_returns_true(conn, sample_registry_row):
    """If company already in company_website_stage, run_company_website_for_company returns True (skip)."""
    conn.execute(
        """INSERT INTO company_registry
           (company_number, name, name_normalized, company_type, status, sic_codes, description,
            registered_address, incorporation_date, previous_names, asset_manager_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (*sample_registry_row,),
    )
    conn.execute(
        """INSERT INTO company_website_stage (company_number, url, discovery_source, confidence, updated_at, source_metadata)
           VALUES (?, 'https://example.com', 'test', 0.9, datetime('now'), NULL)""",
        (sample_registry_row[0],),
    )
    conn.commit()
    ok = run_company_website_for_company(conn, sample_registry_row[0], sample_registry_row[1], delay_seconds=0)
    assert ok is True
