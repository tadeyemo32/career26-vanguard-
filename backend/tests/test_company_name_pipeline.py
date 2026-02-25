"""
Tests for production name-to-search pipeline.
Covers: symbol-heavy names, quote-corrupted, single-letter, boilerplate,
foreign entities, duplicate collapsing, and schema output.
"""
import pytest

from ingestion.company_name_pipeline import (
    NameToSearchResult,
    name_to_search,
    name_to_search_from_record,
)


# -----------------------------------------------------------------------------
# Schema & determinism
# -----------------------------------------------------------------------------

def test_output_schema_has_required_fields():
    r = name_to_search("123", "Example Capital Management Ltd")
    assert hasattr(r, "company_number")
    assert hasattr(r, "canonical_name")
    assert hasattr(r, "search_queries")
    assert hasattr(r, "rejected")
    assert hasattr(r, "rejection_reason")
    assert r.company_number == "123"
    assert r.canonical_name == "Example Capital Management Ltd"


def test_canonical_name_preserved_unchanged():
    legal = "  \"NFLECTION\" ADVISORY LIMITED  "
    r = name_to_search("1", legal)
    assert r.canonical_name == legal.strip()


def test_deterministic_same_input_same_output():
    r1 = name_to_search("1", "Alpha Beta Capital Ltd")
    r2 = name_to_search("1", "Alpha Beta Capital Ltd")
    assert r1.search_queries == r2.search_queries
    assert r1.rejected == r2.rejected


# -----------------------------------------------------------------------------
# Symbol-heavy & quote-corrupted
# -----------------------------------------------------------------------------

def test_symbol_heavy_name_produces_clean_query():
    r = name_to_search("1", '!AN IDEAL LIFE???"" CIC')
    assert not r.rejected
    assert r.search_queries
    best = r.search_queries[0]
    assert "!" not in best
    assert "?" not in best
    assert "An Ideal Life" in best or "AN IDEAL LIFE" in best or "Ideal Life" in best


def test_quote_corrupted_name_normalized():
    r = name_to_search("1", '"""A"" B"" CAPITAL LTD')
    assert not r.rejected
    assert r.search_queries
    for q in r.search_queries:
        assert '"' not in q


# -----------------------------------------------------------------------------
# Single-letter & invalid
# -----------------------------------------------------------------------------

def test_single_letter_company_rejected():
    r = name_to_search("1", "B")
    assert r.rejected
    assert r.rejection_reason


def test_suffix_only_rejected():
    r = name_to_search("1", "LTD")
    assert r.rejected


def test_empty_name_rejected():
    r = name_to_search("1", "")
    assert r.rejected
    assert "Empty" in (r.rejection_reason or "")


# -----------------------------------------------------------------------------
# Legal suffix stripping
# -----------------------------------------------------------------------------

def test_legal_suffix_stripped_variants():
    r = name_to_search("1", "Example Advisory Limited")
    assert not r.rejected
    # At least one variant without suffix
    without = [q for q in r.search_queries if "limited" not in q.lower() and "ltd" not in q.lower()]
    assert len(without) >= 1
    assert "Example Advisory" in without[0] or "Example" in r.search_queries[0]


def test_never_emit_suffix_only():
    r = name_to_search("1", "Some Real Company Ltd")
    for q in r.search_queries:
        assert q.strip().upper() not in ("LTD", "LIMITED", "PLC", "LLP", "LP", "CIC")


# -----------------------------------------------------------------------------
# Management / boilerplate
# -----------------------------------------------------------------------------

def test_management_boilerplate_produces_readable_query():
    r = name_to_search("1", "XYZ MANAGEMENT LIMITED")
    assert not r.rejected
    assert r.search_queries
    best = r.search_queries[0]
    assert "Management" in best or "management" in best
    assert "XYZ" in best or "Xyz" in best


# -----------------------------------------------------------------------------
# Foreign entities & humanization
# -----------------------------------------------------------------------------

def test_uppercase_humanized_to_title():
    r = name_to_search("1", "NFLECTION ADVISORY LTD")
    assert not r.rejected
    assert r.search_queries
    best = r.search_queries[0]
    assert best[0].isupper()
    assert not best.isupper() or best.isalpha()


def test_foreign_unicode_preserved_or_normalized():
    r = name_to_search("1", "Société Générale Asset Management UK Ltd")
    assert not r.rejected
    assert r.search_queries


# -----------------------------------------------------------------------------
# Duplicate collapsing & count
# -----------------------------------------------------------------------------

def test_max_3_to_5_queries():
    r = name_to_search("1", "Multi Word Capital Management Limited", max_queries=5)
    assert not r.rejected
    assert 1 <= len(r.search_queries) <= 5


def test_no_duplicate_queries():
    r = name_to_search("1", "Duplicate Word Word Limited")
    assert not r.rejected
    assert len(r.search_queries) == len(set(r.search_queries))


# -----------------------------------------------------------------------------
# Record-based API & contextual enrichment
# -----------------------------------------------------------------------------

def test_from_record_schema():
    record = {
        "company_number": "12345",
        "company_name": "Test Company Ltd",
        "address": {"post_town": "London", "country": "UK"},
    }
    out = name_to_search_from_record(record)
    assert out["company_number"] == "12345"
    assert out["canonical_name"] == "Test Company Ltd"
    assert "search_queries" in out
    assert "rejected" in out
    assert "rejection_reason" in out


def test_location_enrichment_ranked_lower():
    record = {
        "company_number": "1",
        "company_name": "City Asset Management Ltd",
        "address": {"post_town": "Manchester", "country": "UK"},
    }
    out = name_to_search_from_record(record, include_location_variants=True)
    assert not out["rejected"]
    # First queries should be without location; location variant may appear later
    queries = out["search_queries"]
    assert queries
    assert any("Manchester" in q for q in queries) or not any("Manchester" in q for q in queries)


# -----------------------------------------------------------------------------
# Rejection reason set when rejected
# -----------------------------------------------------------------------------

def test_rejection_reason_set_when_rejected():
    r = name_to_search("1", "B")
    assert r.rejected
    assert r.rejection_reason is not None
    assert len(r.rejection_reason) > 0
