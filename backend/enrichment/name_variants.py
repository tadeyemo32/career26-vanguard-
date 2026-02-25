"""Populate company_name_variants from company_registry (official + previous_names)."""
from __future__ import annotations

import json
from typing import Any


def _norm(s: str | None) -> str:
    if s is None:
        return ""
    return " ".join(str(s).strip().split())


def populate_name_variants(conn: Any) -> int:
    """
    For each company in registry: insert official name and any previous names into
    company_name_variants. Idempotent (INSERT OR IGNORE on unique).
    Returns number of variant rows inserted.
    """
    cur = conn.execute(
        "SELECT company_number, name, previous_names FROM company_registry"
    )
    count = 0
    for row in cur.fetchall():
        company_number, name, previous_names_json = row[0], row[1], row[2]
        # Official
        official = _norm(name)
        if official:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO company_name_variants
                       (company_number, variant_name, variant_type, source, confidence)
                       VALUES (?, ?, 'official', 'companies_house', 1.0)""",
                    (company_number, official),
                )
                count += 1
            except Exception:
                pass
        # Previous names
        if previous_names_json:
            try:
                prev = json.loads(previous_names_json)
            except json.JSONDecodeError:
                prev = []
            for p in prev:
                pn = _norm(p) if isinstance(p, str) else _norm(str(p))
                if pn and pn != official:
                    try:
                        conn.execute(
                            """INSERT OR IGNORE INTO company_name_variants
                               (company_number, variant_name, variant_type, source, confidence)
                               VALUES (?, ?, 'previous', 'companies_house', 0.9)""",
                            (company_number, pn),
                        )
                        count += 1
                    except Exception:
                        pass
    conn.commit()
    return count


def get_variant_names(conn: Any, company_number: str) -> list[str]:
    """Return all variant names (official + previous + trading + acronym + linkedin_display) for a company."""
    cur = conn.execute(
        """SELECT variant_name FROM company_name_variants
           WHERE company_number = ?
           ORDER BY variant_type = 'official' DESC, confidence DESC""",
        (company_number,),
    )
    return [row[0] for row in cur.fetchall() if row[0]]
