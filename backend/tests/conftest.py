"""
Shared pytest fixtures for pipeline and app tests.
Run from project root: pytest or python -m pytest (pytest.ini sets pythonpath = .).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from db import ensure_db, get_connection


@pytest.fixture
def temp_db():
    """Create a temporary SQLite DB with full schema; yield path then cleanup."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn = ensure_db(path)
        conn.close()
        yield path
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.fixture
def conn(temp_db):
    """Connection to temp DB with schema already applied."""
    conn = get_connection(temp_db)
    yield conn
    conn.close()


@pytest.fixture
def sample_registry_row():
    """Minimal company_registry row for inserts: (company_number, name, ..., previous_names, source)."""
    return (
        "12345678",
        "Test Capital Management Ltd",
        "test capital management ltd",
        "Private Limited Company",
        "Active",
        '["66300 - Fund management activities"]',
        "66300 - Fund management activities",
        "1 Street, London, UK",
        "2020-01-15",
        "[]",
        "companies_house_csv",
    )


@pytest.fixture
def default_column_config():
    """Companies House CSV column mapping (matches config.sample.yaml style)."""
    return {
        "name": "CompanyName",
        "company_number": "CompanyNumber",
        "company_category": "CompanyCategory",
        "status": "CompanyStatus",
        "incorporation_date": "IncorporationDate",
        "sic_1": "SICCode.SicText_1",
        "sic_2": "SICCode.SicText_2",
        "sic_3": "SICCode.SicText_3",
        "sic_4": "SICCode.SicText_4",
        "address_line1": "RegAddress.AddressLine1",
        "post_town": "RegAddress.PostTown",
        "county": "RegAddress.County",
        "country": "RegAddress.Country",
        "post_code": "RegAddress.PostCode",
    }


@pytest.fixture
def sample_csv_row(default_column_config):
    """One CSV row as DictReader would produce (with optional leading-space key)."""
    cols = default_column_config
    return {
        cols["name"]: "  Test Capital Management Ltd  ",
        cols["company_number"]: "12345678",
        cols["company_category"]: "Private Limited Company",
        cols["status"]: "Active",
        cols["incorporation_date"]: "2020-01-15",
        cols["sic_1"]: "66300 - Fund management activities",
        cols["sic_2"]: "",
        cols["sic_3"]: "",
        cols["sic_4"]: "",
        cols["address_line1"]: "1 Street",
        cols["post_town"]: "London",
        cols["county"]: "",
        cols["country"]: "United Kingdom",
        cols["post_code"]: "SW1A 1AA",
    }
