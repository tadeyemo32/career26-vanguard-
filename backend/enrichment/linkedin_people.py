"""People discovery via SerpAPI: multi-query by role, relevance scoring, dedup."""
from __future__ import annotations

from typing import Any

from enrichment.search_queries import get_search_queries_for_company
from enrichment.serp import serp_google_with_delay
from scoring.person_relevance import person_relevance_score


def _people_queries(
    conn: Any,
    company_number: str,
    company_name: str,
    linkedin_display_name: str | None,
    role_phrases: list[str],
    max_names: int = 2,
) -> list[str]:
    """Build queries: prefer pipeline search names, then official + LinkedIn display name."""
    search_names = get_search_queries_for_company(
        conn, company_number, company_name, max_queries=max_names, include_location=False
    )
    names = [n for n in search_names if (n or "").strip()][:max_names]
    if not names and company_name:
        names = [company_name]
    if linkedin_display_name and (linkedin_display_name or "").strip() and linkedin_display_name not in names:
        names.append(linkedin_display_name)
    queries = []
    for name in names:
        if not (name or "").strip():
            continue
        # One query per role group to maximise results
        role_part = " OR ".join(f'"{r}"' for r in role_phrases[:6])
        queries.append(f'"{name}" ({role_part}) site:linkedin.com/in')
    return queries[:5]


def run_linkedin_people_for_company(
    conn: Any,
    company_number: str,
    company_name: str,
    role_phrases: list[str],
    title_weights: dict[str, float],
    reject_titles: list[str],
    min_score: float,
    delay_seconds: float = 1.0,
) -> int:
    """
    Run SerpAPI people queries, score by title, insert into people_stage. Dedup by (company_number, full_name, source, source_identifier).
    Returns number of people inserted.
    """
    cur = conn.execute(
        "SELECT linkedin_display_name FROM linkedin_company_stage WHERE company_number = ?",
        (company_number,),
    )
    row = cur.fetchone()
    linkedin_display_name = row[0] if row else None

    queries = _people_queries(
        conn, company_number, company_name, linkedin_display_name, role_phrases
    )
    seen: set[tuple[str, str]] = set()
    inserted = 0

    for query in queries:
        results = serp_google_with_delay(query, delay_seconds)
        for r in results:
            link = (r.get("link") or "").strip()
            if "linkedin.com/in/" not in link:
                continue
            title = r.get("title") or ""
            snippet = r.get("snippet") or ""
            # Heuristic: title often "Name - Title | LinkedIn" or "Name - Title at Company"
            full_name = title.split(" - ")[0].strip() if " - " in title else title.split("|")[0].strip()
            if not full_name or len(full_name) < 2:
                continue
            score, role_cat = person_relevance_score(title, title_weights, reject_titles)
            if score < min_score:
                continue
            key = (full_name, link)
            if key in seen:
                continue
            seen.add(key)
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO people_stage
                       (company_number, full_name, title, relevance_score, source, source_identifier,
                        raw_snippet_or_excerpt, role_category)
                       VALUES (?, ?, ?, ?, 'linkedin_serp', ?, ?, ?)""",
                    (company_number, full_name, title, score, link, snippet[:500], role_cat or "other"),
                )
                inserted += 1
            except Exception:
                pass
    conn.commit()
    return inserted
