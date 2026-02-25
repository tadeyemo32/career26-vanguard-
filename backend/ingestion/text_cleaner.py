"""
Clean text from Companies House CSV: remove CSV/encoding artifacts and random characters.
Produces display-ready names and text (no stray quotes, symbols, or control chars).
"""
from __future__ import annotations

import re
import unicodedata


# All quote-like characters (ASCII and Unicode) to remove from text
_QUOTE_CHARS = frozenset(
    '"'  # ASCII double quote
    "'"  # ASCII apostrophe
    "\u2018\u2019\u201a\u201b"  # left/right single quotes, single low-9
    "\u201c\u201d\u201e\u201f"  # left/right double quotes, double low-9
    "\u2032\u2033\u2034\u2035"  # prime, double prime, etc.
    "\u00ab\u00bb"  # guillemets
    "\u275b\u275c\u275d\u275e\u275f"  # heavy quotes
)

# Leading/trailing: strip runs of whitespace and punctuation/symbols
_LEADING_TRAILING_PUNCT = re.compile(
    r"^[\s\W_]+|[\s\W_]+$",
    re.UNICODE,
)

# For company names: keep only letters, digits, and safe punctuation
# Safe: space, & ' . - , ( ) for names like "Smith & Co.", "St. James", "No. 1 Ltd"
# Hyphen at start of class so it's literal
_NAME_SAFE_PATTERN = re.compile(
    r"[^-\w\s&'.,()]",
    re.UNICODE,
)


def _normalize_unicode(s: str) -> str:
    """Remove control characters and normalize to NFKC."""
    if not s:
        return ""
    s = "".join(c for c in s if unicodedata.category(c) != "Cc")
    return unicodedata.normalize("NFKC", s)


def _remove_quotes(s: str) -> str:
    """Remove all quote characters (ASCII and Unicode)."""
    if not s:
        return ""
    return "".join(c for c in s if c not in _QUOTE_CHARS)


def _strip_edges(s: str) -> str:
    """Strip leading/trailing whitespace and punctuation (repeat until stable)."""
    if not s:
        return ""
    prev = None
    while prev != s:
        prev = s
        s = _LEADING_TRAILING_PUNCT.sub("", s).strip()
    return s


def _collapse_spaces(s: str) -> str:
    """Collapse runs of whitespace to single space."""
    if not s:
        return ""
    return " ".join(s.split())


def _name_safe_only(s: str) -> str:
    """Replace any character not allowed in a clean company name with space."""
    if not s:
        return ""
    # Keep letters (any script), digits, space, & ' . - , ( )
    return _NAME_SAFE_PATTERN.sub(" ", s)


def clean_company_name(raw: str) -> str:
    """
    Return a clean company name: no quotes, no leading/trailing junk, no random symbols.
    Keeps only letters, digits, spaces, and safe punctuation (& ' . - , ( )).
    """
    if not raw:
        return ""
    s = str(raw)
    s = _normalize_unicode(s)
    s = _remove_quotes(s)
    s = _name_safe_only(s)
    s = _collapse_spaces(s)
    s = _strip_edges(s)
    return s


def clean_text(raw: str) -> str:
    """
    Clean general text (addresses, descriptions): normalize Unicode, remove quotes,
    strip edges, collapse spaces. Does not apply name_safe_only so addresses can
    keep numbers and symbols like /.
    """
    if not raw:
        return ""
    s = str(raw)
    s = _normalize_unicode(s)
    s = _remove_quotes(s)
    s = _collapse_spaces(s)
    s = _strip_edges(s)
    return s
