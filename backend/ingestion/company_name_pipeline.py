"""
Production-grade NLP pipeline: legal company name → human search queries.

Converts Companies House legal names into 3–5 ranked search queries suitable for
LinkedIn/Crunchbase/website discovery. Deterministic, auditable, with hard rejection
when no plausible query can be produced.

Stages: Canonical preservation → Normalization → Legal stripping → Symbol removal
→ Linguistic validation → Humanization → (optional) Contextual enrichment → Scoring → Rejection gate.

Example before/after (worst-case inputs):
  Symbol-heavy + CIC  -> An Ideal Life
  Quote-corrupted LTD -> A B Capital (and variant with suffix)
  Single letter "B"   -> rejected
  Suffix-only "LTD"  -> rejected
  XYZ MANAGEMENT LIMITED -> Xyz Management, ...
  NFLECTION ADVISORY LTD -> Nflection Advisory, ...
  Foreign/unicode name   -> preserved or normalized
  Empty string        -> rejected
  Long boilerplate    -> Title-case, suffix stripped
  1ST CAPITAL PARTNERS LLP -> 1st Capital Partners, ...
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any

import regex as re

# Optional heavy deps (graceful fallback)
try:
    import rapidfuzz
    from rapidfuzz import fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False

try:
    from wordfreq import zipf_frequency
    _HAS_WORDFREQ = True
except ImportError:
    _HAS_WORDFREQ = False

try:
    from unidecode import unidecode
    _HAS_UNIDECODE = True
except ImportError:
    _HAS_UNIDECODE = False


# -----------------------------------------------------------------------------
# Output schema
# -----------------------------------------------------------------------------

@dataclass
class NameToSearchResult:
    company_number: str
    canonical_name: str
    search_queries: list[str] = field(default_factory=list)
    rejected: bool = False
    rejection_reason: str | None = None


# -----------------------------------------------------------------------------
# 1) Canonical preservation
# -----------------------------------------------------------------------------

def _canonical_name(company_name: str) -> str:
    """Preserve original exactly; never modify. For traceability only."""
    return (company_name or "").strip()


# -----------------------------------------------------------------------------
# 2) Aggressive normalization
# -----------------------------------------------------------------------------

_QUOTE_CHARS = frozenset(
    '"\''
    "\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f"
    "\u2032\u2033\u2034\u2035\u00ab\u00bb"
)
_EDGE_PUNCT = re.compile(r"^[\s\W_]+|[\s\W_]+$", re.UNICODE)
_MULTI_SPACE = re.compile(r"\s+", re.UNICODE)
_MULTI_QUOTE = re.compile(r'"+', re.UNICODE)


def _normalize_stage(s: str) -> str:
    """Unicode NFKC, control chars, quote collapse, whitespace canonicalization."""
    if not s:
        return ""
    s = "".join(c for c in s if unicodedata.category(c) != "Cc")
    s = unicodedata.normalize("NFKC", s)
    s = "".join(c if c not in _QUOTE_CHARS else " " for c in s)
    s = _MULTI_QUOTE.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    while True:
        t = _EDGE_PUNCT.sub("", s).strip()
        if t == s:
            break
        s = t
    return s


# -----------------------------------------------------------------------------
# 3) Legal & jurisdictional stripping (UK)
# -----------------------------------------------------------------------------

# UK legal suffixes: strip only at end; case-insensitive
_UK_SUFFIXES = re.compile(
    r"\s+(?:LTD\.?|LIMITED|PLC\.?|LLP\.?|LP\.?|CIC|INCORPORATED|CORPORATION|CORP\.?)$",
    re.IGNORECASE | re.UNICODE,
)


def _strip_legal_suffix(s: str) -> tuple[str, str]:
    """Strip legal suffix from end. Returns (stripped, suffix_removed)."""
    if not s:
        return "", ""
    m = _UK_SUFFIXES.search(s)
    if m:
        return s[: m.start()].strip(), m.group(0).strip()
    return s, ""


def _legal_variants(s: str) -> list[str]:
    """With and without suffix. Never emit suffix-only."""
    s = s.strip()
    if not s:
        return []
    out = [s]
    stripped, suffix = _strip_legal_suffix(s)
    if stripped and stripped.upper() not in ("LTD", "LIMITED", "PLC", "LLP", "LP", "CIC"):
        out.append(stripped)
    return list(dict.fromkeys(out))


# -----------------------------------------------------------------------------
# 4) Symbol & noise removal (search-only)
# -----------------------------------------------------------------------------

# Keep only letters, digits, spaces, and safe punct for display
_SEARCH_SAFE = re.compile(r"[^\w\s&'.\-,()]", re.UNICODE)
_REPEATED_SYMBOL = re.compile(r"([^\w\s])\1+", re.UNICODE)


def _symbol_removal_stage(s: str) -> str:
    """Remove/reduce symbols for search variant."""
    if not s:
        return ""
    s = _SEARCH_SAFE.sub(" ", s)
    s = _REPEATED_SYMBOL.sub(r"\1", s)
    s = " ".join(s.split())
    return _EDGE_PUNCT.sub("", s).strip()


# -----------------------------------------------------------------------------
# 5) Linguistic validation
# -----------------------------------------------------------------------------

_MIN_ALPHA_TOKENS = 2
_MIN_ZIPF = 1.0
_SINGLE_LETTER = re.compile(r"^[A-Za-z]$", re.UNICODE)
_NUMERIC_ONLY = re.compile(r"^[\d\s.,]+$", re.UNICODE)
# Looks like company number or address fragment
_LOOKS_LIKE_NUMBER = re.compile(r"^\d{5,}$", re.UNICODE)


def _tokenize_simple(s: str) -> list[str]:
    """Tokenize on non-alpha; keep only tokens that contain a letter."""
    if not s:
        return []
    tokens = re.split(r"[\s\W]+", s, flags=re.UNICODE)
    return [t for t in tokens if t and any(c.isalpha() for c in t)]


def _zipf_score(token: str) -> float:
    """Word frequency (zipf). Higher = more common word."""
    if not _HAS_WORDFREQ or not token:
        return 0.0
    try:
        return zipf_frequency(token.lower(), "en")
    except Exception:
        return 0.0


def _has_common_token(tokens: list[str], min_zipf: float = 1.0) -> bool:
    """At least one token has word frequency above threshold."""
    return any(_zipf_score(t) >= min_zipf for t in tokens)


def _is_valid_candidate(s: str) -> tuple[bool, str]:
    """
    Must: ≥2 alpha tokens, ≥1 common word, not single letter, not numeric-only,
    not company-number-like. Returns (valid, reason).
    """
    if not s or not s.strip():
        return False, "empty"
    s = s.strip()
    if _SINGLE_LETTER.match(s):
        return False, "single_letter"
    if _NUMERIC_ONLY.match(s):
        return False, "numeric_only"
    if _LOOKS_LIKE_NUMBER.match(s.replace(" ", "").replace(".", "")):
        return False, "looks_like_number"
    tokens = _tokenize_simple(s)
    if len(tokens) < _MIN_ALPHA_TOKENS:
        return False, "too_few_tokens"
    if _HAS_WORDFREQ and not _has_common_token(tokens, _MIN_ZIPF):
        return False, "no_common_word"
    return True, ""


# -----------------------------------------------------------------------------
# 6) Humanization (casing)
# -----------------------------------------------------------------------------

def _humanize_casing(s: str) -> str:
    """If >80% uppercase → Title Case; else leave as-is (already natural)."""
    if not s:
        return ""
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return s
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio > 0.8:
        return s.title()
    return s


# -----------------------------------------------------------------------------
# 7) Contextual enrichment (soft: append location, rank lower)
# -----------------------------------------------------------------------------

def _enrich_with_location(name: str, post_town: str | None, country: str | None) -> str:
    """Append location only if non-empty; for ranking lower later."""
    if not name:
        return ""
    parts = [name]
    if post_town and post_town.strip():
        parts.append(post_town.strip())
    if country and country.strip() and str(country).strip().upper() not in ("UK", "UNITED KINGDOM", "ENGLAND", "WALES", "SCOTLAND", "NORTHERN IRELAND"):
        parts.append(country.strip())
    if len(parts) == 1:
        return name
    return " ".join(parts)


# -----------------------------------------------------------------------------
# 8) Candidate scoring & ranking
# -----------------------------------------------------------------------------

def _score_candidate(
    query: str,
    has_suffix: bool,
    has_symbols: bool,
    is_title_case: bool,
    has_location: bool,
) -> int:
    """Score 0–12; higher = better for search."""
    score = 0
    tokens = _tokenize_simple(query)
    if not has_suffix:
        score += 2
    if not has_symbols:
        score += 3
    if is_title_case or (query and query[0].isupper() and not query.isupper()):
        score += 1
    if 2 <= len(tokens) <= 6:
        score += 2
    if _HAS_WORDFREQ and _has_common_token(tokens, 2.0):
        score += 2
    if has_location:
        score += 1
    return score


def _has_legal_suffix(s: str) -> bool:
    return _UK_SUFFIXES.search(s) is not None


def _has_symbols(s: str) -> bool:
    return bool(re.search(r"[^\w\s&'.\-,()]", s, re.UNICODE))


def _dedupe_candidates(candidates: list[str], threshold: int = 90) -> list[str]:
    """Deduplicate by fuzzy similarity (rapidfuzz). Keep first of similar pair."""
    if not _HAS_RAPIDFUZZ or len(candidates) <= 1:
        return list(dict.fromkeys(candidates))
    out = []
    for c in candidates:
        c = c.strip()
        if not c:
            continue
        if any(rapidfuzz.fuzz.ratio(c, o) >= threshold for o in out):
            continue
        out.append(c)
    return out


# -----------------------------------------------------------------------------
# 9) Hard rejection gate & main pipeline
# -----------------------------------------------------------------------------

def name_to_search(
    company_number: str,
    company_name: str,
    post_town: str | None = None,
    country: str | None = None,
    max_queries: int = 5,
    include_location_variants: bool = True,
) -> NameToSearchResult:
    """
    Convert legal company name to 3–5 ranked search queries.
    Deterministic, auditable. Rejects when no valid candidate exists.
    """
    canonical = _canonical_name(company_name)
    if not canonical:
        return NameToSearchResult(
            company_number=company_number,
            canonical_name=canonical,
            rejected=True,
            rejection_reason="Empty company name",
        )

    # 2) Normalize
    normalized = _normalize_stage(canonical)
    if not normalized:
        return NameToSearchResult(
            company_number=company_number,
            canonical_name=canonical,
            rejected=True,
            rejection_reason="Normalization produced empty string",
        )

    # 3) Legal variants (with/without suffix)
    base_variants = _legal_variants(normalized)

    # 4) Symbol removal for each variant
    search_variants = []
    for v in base_variants:
        cleaned = _symbol_removal_stage(v)
        if cleaned:
            search_variants.append(cleaned)
    search_variants = list(dict.fromkeys(search_variants))

    # 5) Linguistic validation
    valid = []
    for v in search_variants:
        ok, reason = _is_valid_candidate(v)
        if ok:
            valid.append(v)

    if not valid:
        return NameToSearchResult(
            company_number=company_number,
            canonical_name=canonical,
            rejected=True,
            rejection_reason="No plausible human-readable company name",
        )

    # 6) Humanization
    humanized = [_humanize_casing(v) for v in valid]
    humanized = list(dict.fromkeys(humanized))

    # 7) Optional location-enriched (ranked lower)
    if include_location_variants and (post_town or country):
        for v in humanized[:2]:
            enriched = _enrich_with_location(v, post_town, country)
            if enriched != v and _is_valid_candidate(enriched)[0]:
                humanized.append(enriched)

    # 8) Score & rank
    scored: list[tuple[str, int]] = []
    for q in humanized:
        has_suf = _has_legal_suffix(q)
        has_sym = _has_symbols(q)
        is_title = q == q.title() and len(q) > 1
        has_loc = bool(
            (post_town and post_town.strip() and post_town.strip() in q)
            or (country and str(country).strip() and str(country).strip() in q)
        )
        sc = _score_candidate(q, has_suf, has_sym, is_title, has_loc)
        scored.append((q, sc))
    scored.sort(key=lambda x: -x[1])
    deduped = _dedupe_candidates([q for q, _ in scored])
    top = deduped[:max_queries]

    if not top:
        return NameToSearchResult(
            company_number=company_number,
            canonical_name=canonical,
            rejected=True,
            rejection_reason="No valid candidates after scoring",
        )

    return NameToSearchResult(
        company_number=company_number,
        canonical_name=canonical,
        search_queries=top,
        rejected=False,
        rejection_reason=None,
    )


def name_to_search_from_record(
    record: dict[str, Any],
    max_queries: int = 5,
    include_location_variants: bool = True,
) -> dict[str, Any]:
    """
    Accept pipeline record: company_number, company_name, address { post_town, country }.
    Returns schema: company_number, canonical_name, search_queries, rejected, rejection_reason.
    """
    company_number = (record.get("company_number") or "").strip()
    company_name = (record.get("company_name") or "").strip()
    addr = record.get("address") or {}
    post_town = addr.get("post_town") if isinstance(addr, dict) else None
    country = addr.get("country") if isinstance(addr, dict) else None
    r = name_to_search(
        company_number=company_number,
        company_name=company_name,
        post_town=post_town,
        country=country,
        max_queries=max_queries,
        include_location_variants=include_location_variants,
    )
    return {
        "company_number": r.company_number,
        "canonical_name": r.canonical_name,
        "search_queries": r.search_queries,
        "rejected": r.rejected,
        "rejection_reason": r.rejection_reason,
    }
