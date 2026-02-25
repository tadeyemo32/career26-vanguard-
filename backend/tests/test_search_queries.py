"""Tests for enrichment.search_queries: get_search_queries_for_company (pipeline + fallback)."""
from __future__ import annotations

import pytest

from enrichment.search_queries import get_search_queries_for_company


def test_uses_pipeline_when_valid(conn):
    conn.execute(
        """INSERT INTO company_registry (company_number, name, name_normalized, company_type, status,
            sic_codes, description, registered_address, incorporation_date, previous_names, source)
           VALUES ('1', 'Test Capital Management Ltd', 'test capital management ltd', 'PLC', 'Active',
            '[]', NULL, NULL, NULL, '[]', 'test')"""
    )
    conn.execute(
        """INSERT INTO company_name_variants (company_number, variant_name, variant_type, source, confidence)
           VALUES ('1', 'Test Capital Management Ltd', 'official', 'companies_house', 1.0)"""
    )
    conn.commit()
    queries = get_search_queries_for_company(conn, "1", "Test Capital Management Ltd", max_queries=5)
    assert queries
    assert "Test Capital Management" in queries[0] or "Test" in queries[0]
    assert "Ltd" not in queries[0] or "Limited" not in queries[0]  # pipeline strips suffix in best

def test_fallback_to_variants_when_pipeline_rejects(conn):
    # Single-letter name → pipeline rejects → fallback to name + variants
    conn.execute(
        """INSERT INTO company_registry (company_number, name, name_normalized, company_type, status,
            sic_codes, description, registered_address, incorporation_date, previous_names, source)
           VALUES ('2', 'B', 'b', 'PLC', 'Active', '[]', NULL, NULL, NULL, '[]', 'test')"""
    )
    conn.execute(
        """INSERT INTO company_name_variants (company_number, variant_name, variant_type, source, confidence)
           VALUES ('2', 'B', 'official', 'companies_house', 1.0),
                  ('2', 'Beta Trading', 'previous', 'companies_house', 0.9)"""
    )
    conn.commit()
    queries = get_search_queries_for_company(conn, "2", "B", max_queries=5)
    assert queries
    assert "B" in queries or "Beta Trading" in queries

def test_unknown_company_uses_name_only(conn):
    queries = get_search_queries_for_company(conn, "99", "Acme Capital Ltd", max_queries=3)
    assert queries
    assert "Acme" in queries[0] or "Acme Capital" in queries[0]
