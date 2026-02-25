"""LinkedIn company match confidence. Used to score SerpAPI candidates."""
from __future__ import annotations


def linkedin_match_score(
    company_name: str,
    variant_names: list[str],
    result_title: str | None,
    result_snippet: str | None,
    result_domain: str = "linkedin.com",
) -> tuple[float, str]:
    """
    Score a SerpAPI result for LinkedIn company page.
    Returns (confidence in [0,1], name_match_type: 'exact' | 'partial' | 'fuzzy' | 'variant').
    """
    title = (result_title or "").lower()
    snippet = (result_snippet or "").lower()
    score = 0.0
    name_match_type = "fuzzy"

    all_names = [company_name] + variant_names
    norm_company = company_name.lower().strip()
    for name in all_names:
        n = name.lower().strip()
        if not n:
            continue
        if n in title or title in n:
            score += 0.5
            name_match_type = "exact" if n == norm_company else "variant"
            break
        # Partial: significant substring
        if len(n) > 3 and n in title:
            score += 0.4
            name_match_type = "partial"
            break
        words = set(n.split())
        title_words = set(title.split())
        if words & title_words:
            score += 0.3
            name_match_type = "partial"
            break

    if "asset" in snippet or "investment" in snippet or "fund" in snippet:
        score += 0.2
    if result_domain in (result_domain or "").lower():
        score += 0.3

    return (min(score, 1.0), name_match_type)


def extract_linkedin_slug(url: str) -> str:
    """Last path segment of linkedin.com/company/XXX."""
    url = (url or "").strip().rstrip("/")
    if "linkedin.com/company/" in url:
        return url.split("linkedin.com/company/")[-1].split("/")[0].split("?")[0] or ""
    if "/company/" in url:
        return url.split("/company/")[-1].split("/")[0].split("?")[0] or ""
    return ""
