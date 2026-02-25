"""Person relevance scoring. Title weights and reject list."""
from __future__ import annotations


def person_relevance_score(
    title: str | None,
    title_weights: dict[str, float] | None = None,
    reject_titles: list[str] | None = None,
) -> tuple[float, str | None]:
    """
    Score a person by job title. Returns (relevance_score in [0,1], role_category or None).
    role_category: 'cio' | 'pm' | 'partner' | 'director' | 'other'.
    """
    title_weights = title_weights or {}
    reject_titles = reject_titles or []
    t = (title or "").lower().strip()
    if not t:
        return (0.0, None)

    for reject in reject_titles:
        if reject.lower() in t:
            return (0.0, None)

    score = 0.0
    role_category = "other"
    for phrase, weight in title_weights.items():
        if phrase.lower() in t:
            if weight > score:
                score = weight
            if "chief investment" in t or "cio" in t:
                role_category = "cio"
            elif "portfolio manager" in t or " pm " in t:
                role_category = "pm"
            elif "partner" in t:
                role_category = "partner"
            elif "director" in t:
                role_category = "director"
            break

    return (min(score, 1.0), role_category if score >= 0.5 else None)
