"""LinkedIn company resolution via SerpAPI: multi-query, store candidates, disambiguate."""
from __future__ import annotations

from typing import Any

from enrichment.name_variants import get_variant_names
from enrichment.search_queries import get_search_queries_for_company
from enrichment.serp import serp_google_with_delay
from scoring.linkedin_match import extract_linkedin_slug, linkedin_match_score


def _build_company_queries(
    conn: Any,
    company_number: str,
    company_name: str,
    max_queries: int,
) -> list[str]:
    """Build multiple search queries from name-to-search pipeline (or fallback to name + variants)."""
    search_names = get_search_queries_for_company(
        conn, company_number, company_name, max_queries=max_queries, include_location=False
    )
    seen: set[str] = set()
    queries: list[str] = []
    for name in search_names:
        n = (name or "").strip()
        if not n or len(n) < 2 or n in seen:
            continue
        seen.add(n)
        queries.append(f'"{n}" site:linkedin.com/company')
        if len(queries) >= max_queries:
            break
    if not queries:
        queries.append(f'"{company_name}" site:linkedin.com/company')
    return queries[:max_queries]


def run_linkedin_company_for_company(
    conn: Any,
    company_number: str,
    company_name: str,
    delay_seconds: float = 1.0,
    min_confidence: float = 0.7,
    max_queries: int = 5,
) -> bool:
    """
    Run SerpAPI queries for this company, store all candidates, pick best, write to
    linkedin_company_stage. Idempotent: if linkedin_company_stage already has this company, skip.
    Returns True if a page was chosen and written.
    """
    cur = conn.execute(
        "SELECT 1 FROM linkedin_company_stage WHERE company_number = ?",
        (company_number,),
    )
    if cur.fetchone():
        return True  # already done

    variant_names = get_variant_names(conn, company_number)
    if not variant_names and company_name:
        variant_names = [company_name]

    queries = _build_company_queries(conn, company_number, company_name, max_queries)
    all_candidates: list[tuple[str, str, str, int, float, str]] = []

    for query in queries:
        results = serp_google_with_delay(query, delay_seconds)
        for r in results:
            link = (r.get("link") or "").strip()
            if "linkedin.com/company/" not in link:
                continue
            slug = extract_linkedin_slug(link)
            if not slug:
                continue
            title = r.get("title") or ""
            snippet = r.get("snippet") or ""
            pos = r.get("position") or 0
            conf, name_match = linkedin_match_score(
                company_name,
                variant_names,
                title,
                snippet,
                "linkedin.com",
            )
            if conf < min_confidence:
                continue
            all_candidates.append((link, slug, title, pos, conf, name_match))

    # Dedup by slug
    by_slug: dict[str, tuple[str, str, int, float, str]] = {}
    for link, slug, title, pos, conf, name_match in all_candidates:
        if slug not in by_slug or by_slug[slug][3] < conf:
            by_slug[slug] = (link, title, pos, conf, name_match)

    if not by_slug:
        return False

    # Insert all candidates
    for slug, (link, title, pos, conf, name_match) in by_slug.items():
        conn.execute(
            """INSERT OR IGNORE INTO linkedin_company_candidates
               (company_number, linkedin_url, linkedin_slug, result_title, result_snippet,
                result_position, query_used, name_match_type, match_confidence, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'serpapi')""",
            (company_number, link, slug, title, None, pos, queries[0], name_match, conf),
        )

    # Pick best: highest confidence, then lowest position
    best_slug = max(
        by_slug.keys(),
        key=lambda s: (by_slug[s][3], -by_slug[s][2]),
    )
    link, title, pos, conf, name_match = by_slug[best_slug]

    # Get candidate id
    cur = conn.execute(
        "SELECT id FROM linkedin_company_candidates WHERE company_number = ? AND linkedin_slug = ?",
        (company_number, best_slug),
    )
    row = cur.fetchone()
    candidate_id = row[0] if row else None

    conn.execute(
        """INSERT OR REPLACE INTO linkedin_company_stage
           (company_number, linkedin_url, linkedin_slug, linkedin_display_name, size, industry,
            description_snippet, match_confidence, chosen_candidate_id, disambiguation_reason, source)
           VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, 'serpapi')""",
        (
            company_number,
            link,
            best_slug,
            title,
            conf,
            candidate_id,
            f"best match: {name_match} confidence={conf:.2f} position={pos}",
        ),
    )
    conn.commit()
    return True
