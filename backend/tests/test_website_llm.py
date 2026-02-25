"""Tests for enrichment.website_llm: _content_hash, run when no URL / no content."""
from __future__ import annotations

import pytest

from enrichment.website_llm import _content_hash, run_website_llm_for_company


def test_content_hash_deterministic():
    assert _content_hash("hello") == _content_hash("hello")
    assert _content_hash("hello") != _content_hash("world")


def test_content_hash_hex_length():
    h = _content_hash("test")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_run_website_llm_no_url_handled(conn, sample_registry_row):
    """run_website_llm_for_company with empty URL does not crash (fetch returns empty)."""
    conn.execute(
        """INSERT INTO company_registry
           (company_number, name, name_normalized, company_type, status, sic_codes, description,
            registered_address, incorporation_date, previous_names, asset_manager_score, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (*sample_registry_row,),
    )
    conn.commit()
    n = run_website_llm_for_company(
        conn, sample_registry_row[0], "https://invalid.invalid.example.noexist",
        model="gpt-4o-mini", max_content_chars=1000, store_cache=False,
    )
    assert isinstance(n, int)
    assert n >= 0
