"""
Resolve company to human search queries for SerpAPI (LinkedIn, website, etc.).
Uses the production name-to-search pipeline when it yields valid queries;
otherwise falls back to raw name + DB variants.
"""
from __future__ import annotations

from typing import Any

from ingestion.company_name_pipeline import name_to_search_from_record


def get_search_queries_for_company(
    conn: Any,
    company_number: str,
    company_name: str,
    max_queries: int = 5,
    include_location: bool = False,
) -> list[str]:
    """
    Return 1–max_queries human-style search strings for this company.
    Prefer pipeline output; if rejected, fall back to official name + variants from DB.
    """
    record: dict[str, Any] = {
        "company_number": company_number,
        "company_name": company_name,
        "address": {},
    }
    if include_location:
        row = conn.execute(
            "SELECT registered_address FROM company_registry WHERE company_number = ?",
            (company_number,),
        ).fetchone()
        if row and row[0]:
            # We only have a single address string; no structured post_town/country
            record["address"] = {"post_town": None, "country": "UK"}
    result = name_to_search_from_record(
        record,
        max_queries=max_queries,
        include_location_variants=include_location,
    )
    if not result["rejected"] and result.get("search_queries"):
        return result["search_queries"][:max_queries]
    # Fallback: raw name + variants from DB
    from enrichment.name_variants import get_variant_names
    names = [company_name] if (company_name or "").strip() else []
    for v in get_variant_names(conn, company_number):
        v = (v or "").strip()
        if v and v not in names:
            names.append(v)
    return names[:max_queries] if names else [company_name or ""]
