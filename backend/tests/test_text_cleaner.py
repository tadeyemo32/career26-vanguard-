"""Tests for ingestion.text_cleaner: clean_company_name and clean_text."""
from __future__ import annotations

import pytest

from ingestion.text_cleaner import clean_company_name, clean_text


class TestCleanCompanyName:
    """clean_company_name: no quotes, no leading/trailing junk, name-safe chars only."""

    def test_empty(self):
        assert clean_company_name("") == ""
        assert clean_company_name(None) == ""

    def test_strips_quotes(self):
        assert clean_company_name('"Acme" Ltd') == "Acme Ltd"
        assert clean_company_name("'Smith & Co'") == "Smith & Co"
        assert clean_company_name("\u201cAlpha\u201d Beta") == "Alpha Beta"

    def test_leading_trailing_punctuation(self):
        assert clean_company_name("!!! Acme Ltd ???") == "Acme Ltd"
        assert clean_company_name("  __  Test  __  ") == "Test"

    def test_name_safe_only(self):
        # Trailing punct is stripped by strip_edges, so "Smith & Co." -> "Smith & Co"
        assert clean_company_name("Smith & Co.") == "Smith & Co"
        assert clean_company_name("St. James Capital") == "St. James Capital"
        assert clean_company_name("No. 1 Ltd") == "No. 1 Ltd"
        # Junk symbols removed
        assert "@" not in clean_company_name("Acme@Ltd")
        assert "#" not in clean_company_name("Test #1")

    def test_collapse_spaces(self):
        assert clean_company_name("  Alpha   Beta   Ltd  ") == "Alpha Beta Ltd"

    def test_unicode_normalized(self):
        # NFKC: fullwidth/weird spaces normalized
        s = clean_company_name("\u3000Alpha\u3000Beta\u3000")
        assert "\u3000" not in s
        assert "Alpha" in s and "Beta" in s


class TestCleanText:
    """clean_text: general text (addresses); no name_safe_only so / etc. kept."""

    def test_empty(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_strips_quotes_and_edges(self):
        assert clean_text('  "1 High Street"  ') == "1 High Street"
        assert clean_text("London, UK") == "London, UK"

    def test_collapse_spaces(self):
        assert clean_text("1   Street\n  London") == "1 Street London"

    def test_address_style_unchanged(self):
        # Addresses can keep numbers and slashes
        out = clean_text("1/2 High Street, London SW1")
        assert "1" in out and "2" in out
        assert "High Street" in out
