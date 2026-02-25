"""Company website discovery: SerpAPI (and optional LinkedIn)."""
from __future__ import annotations

import re
from typing import Any

from enrichment.search_queries import get_search_queries_for_company
from enrichment.serp import serp_google_with_delay


def _is_likely_company_site(url: str, company_name: str) -> float:
    """Return confidence that this URL is the company's real site (not directory/social)."""
    url_lower = url.lower()
    if any(x in url_lower for x in ["linkedin.com", "facebook.com", "twitter.com", "wikipedia.org"]):
        return 0.0
    if any(x in url_lower for x in ["companieshouse.gov.uk", "duedil", "endole.co.uk"]):
        return 0.3
    # Prefer same domain as company name (e.g. acmecapital.com for Acme Capital)
    words = re.findall(r"[a-z]+", company_name.lower())
    for w in words:
        if len(w) > 2 and w in url_lower:
            return 0.9
    return 0.6


def run_company_website_for_company(
    conn: Any,
    company_number: str,
    company_name: str,
    delay_seconds: float = 1.0,
) -> bool:
    """
    Search for company website, store candidates, pick best, write to company_website_stage.
    Returns True if a URL was chosen.
    """
    cur = conn.execute(
        "SELECT 1 FROM company_website_stage WHERE company_number = ?",
        (company_number,),
    )
    if cur.fetchone():
        return True

    search_names = get_search_queries_for_company(
        conn, company_number, company_name, max_queries=2, include_location=False
    )
    search_name = (search_names[0] if search_names else "").strip() or company_name
    query = f'"{search_name}" UK'
    results = serp_google_with_delay(query, delay_seconds)
    best_url: str | None = None
    best_conf = 0.0

    for r in results:
        link = (r.get("link") or "").strip()
        if not link or not link.startswith("http"):
            continue
        conf = _is_likely_company_site(link, company_name)
        if conf < 0.5:
            continue
        try:
            conn.execute(
                """INSERT INTO company_website_candidates
                   (company_number, url, discovery_source, confidence, title_or_snippet)
                   VALUES (?, ?, 'serpapi', ?, ?)""",
                (company_number, link, conf, (r.get("title") or "")[:200]),
            )
        except Exception:
            pass
        if conf > best_conf:
            best_conf = conf
            best_url = link

    if not best_url:
        return False

    conn.execute(
        """INSERT OR REPLACE INTO company_website_stage
           (company_number, url, discovery_source, confidence, updated_at, source_metadata)
           VALUES (?, ?, 'serpapi', ?, datetime('now'), NULL)""",
        (company_number, best_url, best_conf),
    )
    conn.commit()
    return True
