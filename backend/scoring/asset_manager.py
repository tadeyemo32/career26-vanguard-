"""
Probabilistic asset manager scoring. SIC whitelist + keyword weights.

Matches Companies House CSV layout: SIC cells are stored as "CODE - Description"
(e.g. "66300 - Fund management activities", "64304 - Activities of open-ended
investment companies"). We extract the numeric code and score from sic_whitelist.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable


def _extract_sic_code(cell: str) -> str | None:
    """
    Extract numeric SIC code from a single cell. Companies House format:
    "CODE - Description" (e.g. "66300 - Fund management activities") or "CODE".
    Handles " - ", " -", "- " and plain "CODE".
    """
    if not cell or not cell.strip():
        return None
    cell = cell.strip()
    # Split on space-hyphen-space, space-hyphen, or hyphen-space
    parts = re.split(r"\s*-\s*", cell, maxsplit=1)
    code_part = (parts[0] or "").strip()
    code = "".join(c for c in code_part if c.isdigit())
    return code if code else None


def asset_manager_score(
    sic_codes_json: str | None,
    description: str | None,
    sic_whitelist: dict[str, float] | None = None,
    keywords: dict[str, float] | None = None,
) -> float:
    """
    Return a score in [0, 1]. Do not hard-filter; use threshold (e.g. 0.6) downstream.
    sic_codes_json: JSON array of strings as in CSV (e.g. ["66300 - Fund management activities"]).
    description: " | ".join of same SIC strings, used for keyword matching.
    """
    sic_whitelist = sic_whitelist or {}
    keywords = keywords or {}

    score = 0.0

    # SIC: parse as in Companies House layout (JSON array of "CODE - Description" strings)
    added_codes: set[str] = set()
    if sic_codes_json:
        try:
            if sic_codes_json.strip().startswith("["):
                codes = json.loads(sic_codes_json)
            else:
                codes = [p.strip() for p in sic_codes_json.split("|") if p.strip()]
        except json.JSONDecodeError:
            codes = [p.strip() for p in sic_codes_json.split("|") if p.strip()]
        if not isinstance(codes, list):
            codes = [codes] if codes else []
        for item in codes:
            cell = item if isinstance(item, str) else str(item)
            code = _extract_sic_code(cell)
            if code and code in sic_whitelist and code not in added_codes:
                score += sic_whitelist[code]
                added_codes.add(code)
        # Fallback: raw substring match only for codes not already added (e.g. malformed JSON)
        for k, w in sic_whitelist.items():
            if k not in added_codes and k in (sic_codes_json or ""):
                score += w

    desc = (description or "").lower()
    for phrase, weight in keywords.items():
        if phrase.lower() in desc:
            score += weight

    return min(score, 1.0)


def update_registry_scores(
    conn: Any,
    sic_whitelist: dict[str, float],
    keywords: dict[str, float],
    progress_callback: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> int:
    """Update asset_manager_score for all rows in company_registry. Returns count updated."""
    cur = conn.execute(
        "SELECT company_number, sic_codes, description FROM company_registry"
    )
    rows = cur.fetchall()
    total = len(rows)
    count = 0
    for i, row in enumerate(rows):
        if callable(should_stop) and should_stop():
            break
        company_number, sic_codes, description = row[0], row[1], row[2]
        score = asset_manager_score(sic_codes, description, sic_whitelist, keywords)
        conn.execute(
            "UPDATE company_registry SET asset_manager_score = ?, updated_at = datetime('now') WHERE company_number = ?",
            (score, company_number),
        )
        count += 1
        if callable(progress_callback) and (count % 5000 == 0 or count == total):
            progress_callback(count, total)
    conn.commit()
    return count
