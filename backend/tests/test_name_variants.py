"""Tests for enrichment.name_variants: populate_name_variants, get_variant_names."""
from __future__ import annotations

import pytest

from enrichment.name_variants import get_variant_names, populate_name_variants


class TestPopulateNameVariants:
    """populate_name_variants: inserts official + previous names from registry."""

    def test_inserts_official_name(self, conn, sample_registry_row):
        conn.execute(
            """INSERT INTO company_registry
               (company_number, name, name_normalized, company_type, status, sic_codes, description,
                registered_address, incorporation_date, previous_names, asset_manager_score, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (*sample_registry_row,),
        )
        conn.commit()
        n = populate_name_variants(conn)
        assert n >= 1
        row = conn.execute(
            "SELECT variant_name, variant_type FROM company_name_variants WHERE company_number = ?",
            (sample_registry_row[0],),
        ).fetchone()
        assert row is not None
        assert row[1] == "official"

    def test_inserts_previous_names(self, conn, sample_registry_row):
        prev = '["Old Name One Ltd", "Old Name Two Ltd"]'
        row_list = list(sample_registry_row)
        # previous_names is index 9
        row_list[9] = prev
        conn.execute(
            """INSERT INTO company_registry
               (company_number, name, name_normalized, company_type, status, sic_codes, description,
                registered_address, incorporation_date, previous_names, asset_manager_score, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            tuple(row_list),
        )
        conn.commit()
        n = populate_name_variants(conn)
        assert n >= 3  # official + 2 previous
        rows = conn.execute(
            "SELECT variant_type FROM company_name_variants WHERE company_number = ?",
            (sample_registry_row[0],),
        ).fetchall()
        types = [r[0] for r in rows]
        assert "official" in types
        assert "previous" in types

    def test_idempotent_ignore_duplicate(self, conn, sample_registry_row):
        conn.execute(
            """INSERT INTO company_registry
               (company_number, name, name_normalized, company_type, status, sic_codes, description,
                registered_address, incorporation_date, previous_names, asset_manager_score, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (*sample_registry_row,),
        )
        conn.commit()
        populate_name_variants(conn)
        cur = conn.execute(
            "SELECT COUNT(*) FROM company_name_variants WHERE company_number = ?",
            (sample_registry_row[0],),
        )
        count_after_first = cur.fetchone()[0]
        populate_name_variants(conn)
        cur = conn.execute(
            "SELECT COUNT(*) FROM company_name_variants WHERE company_number = ?",
            (sample_registry_row[0],),
        )
        count_after_second = cur.fetchone()[0]
        assert count_after_second == count_after_first  # no extra rows (OR IGNORE)


class TestGetVariantNames:
    """get_variant_names: returns list of variant_name for company."""

    def test_returns_official_first(self, conn, sample_registry_row):
        conn.execute(
            """INSERT INTO company_registry
               (company_number, name, name_normalized, company_type, status, sic_codes, description,
                registered_address, incorporation_date, previous_names, asset_manager_score, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (*sample_registry_row,),
        )
        conn.execute(
            """INSERT INTO company_name_variants (company_number, variant_name, variant_type, source, confidence)
               VALUES (?, 'Official Name Ltd', 'official', 'companies_house', 1.0),
                      (?, 'Previous Ltd', 'previous', 'companies_house', 0.9)""",
            (sample_registry_row[0], sample_registry_row[0]),
        )
        conn.commit()
        names = get_variant_names(conn, sample_registry_row[0])
        assert "Official Name Ltd" in names
        assert "Previous Ltd" in names

    def test_unknown_company_returns_empty(self, conn):
        assert get_variant_names(conn, "nonexistent") == []
