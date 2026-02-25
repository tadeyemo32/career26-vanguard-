"""Tests for enrichment.serp: serp_google (no key = empty), serp_google_with_delay."""
from __future__ import annotations

import os

import pytest

from enrichment.serp import serp_google, serp_google_with_delay


def test_serp_google_no_api_key_returns_empty():
    """Without SERPAPI_KEY, serp_google returns [] (no exception)."""
    prev = os.environ.pop("SERPAPI_KEY", None)
    try:
        result = serp_google("test query")
        assert result == []
    finally:
        if prev is not None:
            os.environ["SERPAPI_KEY"] = prev


def test_serp_google_with_delay_returns_same_as_serp_google():
    """serp_google_with_delay returns same structure as serp_google (empty when no key)."""
    prev = os.environ.pop("SERPAPI_KEY", None)
    try:
        result = serp_google_with_delay("test", delay_seconds=0)
        assert isinstance(result, list)
        assert result == []
    finally:
        if prev is not None:
            os.environ["SERPAPI_KEY"] = prev
