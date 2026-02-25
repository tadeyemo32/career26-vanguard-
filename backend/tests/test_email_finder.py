"""Tests for enrichment.email_finder: _name_to_first_last, _domain_from_url, run (no data = 0)."""
from __future__ import annotations

import pytest

from enrichment.email_finder import (
    _domain_from_url,
    _name_to_first_last,
    find_email_anymail,
    find_email_anymail_by_company,
    find_email_hunter,
    run_email_finder_for_company,
)


class TestNameToFirstLast:
    def test_full_name(self):
        assert _name_to_first_last("John Smith") == ("John", "Smith")

    def test_single_name(self):
        assert _name_to_first_last("Madonna") == ("Madonna", "")

    def test_three_part(self):
        assert _name_to_first_last("Jean Claude Van Damme") == ("Jean", "Claude Van Damme")

    def test_empty(self):
        assert _name_to_first_last("") == ("", "")
        assert _name_to_first_last("   ") == ("", "")


class TestDomainFromUrl:
    def test_https(self):
        assert _domain_from_url("https://example.com/path") == "example.com"

    def test_www_stripped(self):
        assert _domain_from_url("https://www.acme.co.uk") == "acme.co.uk"

    def test_empty(self):
        assert _domain_from_url("") == ""


def test_find_email_anymail_no_key_returns_none():
    """Without ANYMAIL_API_KEY, find_email_anymail returns (None, 0.0)."""
    import os
    prev = os.environ.pop("ANYMAIL_API_KEY", None)
    try:
        email, conf = find_email_anymail("John Smith", "example.com")
        assert email is None
        assert conf == 0.0
    finally:
        if prev is not None:
            os.environ["ANYMAIL_API_KEY"] = prev


def test_find_email_anymail_by_company_no_key_returns_none():
    """Without ANYMAIL_API_KEY, find_email_anymail_by_company returns (None, 0.0)."""
    import os
    prev = os.environ.pop("ANYMAIL_API_KEY", None)
    try:
        email, conf = find_email_anymail_by_company("John Smith", "Acme Corp")
        assert email is None
        assert conf == 0.0
    finally:
        if prev is not None:
            os.environ["ANYMAIL_API_KEY"] = prev


def test_find_email_hunter_no_key_returns_none():
    """Without HUNTER_API_KEY, find_email_hunter returns (None, 0.0)."""
    import os
    prev = os.environ.pop("HUNTER_API_KEY", None)
    try:
        email, conf = find_email_hunter("John", "Smith", "example.com")
        assert email is None
        assert conf == 0.0
    finally:
        if prev is not None:
            os.environ["HUNTER_API_KEY"] = prev


def test_run_email_finder_no_website_returns_zero(conn, sample_registry_row):
    """When company has no row in company_website_stage, run_email_finder_for_company returns 0."""
    conn.execute(
        """INSERT INTO company_registry
           (company_number, name, name_normalized, company_type, status, sic_codes, description,
            registered_address, incorporation_date, previous_names, asset_manager_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (*sample_registry_row,),
    )
    conn.commit()
    n = run_email_finder_for_company(conn, sample_registry_row[0], min_confidence=0.7)
    assert n == 0
