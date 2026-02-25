"""Email discovery: Anymail Finder API (primary), Hunter.io (fallback). Input (name, domain); output with confidence."""
from __future__ import annotations

import os
from typing import Any

import requests


def find_email_anymail(
    full_name: str,
    domain: str,
    api_key: str | None = None,
    timeout: int = 60,
) -> tuple[str | None, float]:
    """
    Anymail Finder API: find person's email by full name and company domain.
    Returns (email or None, confidence 0-1). Only returns valid emails with confidence 1.0;
    risky/not_found/blacklisted return (None, 0.0) or (email, 0.5) for risky.
    """
    key = api_key or os.environ.get("ANYMAIL_API_KEY")
    if not key:
        return (None, 0.0)
    full_name = (full_name or "").strip()
    if not full_name or not domain:
        return (None, 0.0)
    domain = domain.replace("www.", "").split("/")[0]

    url = "https://api.anymailfinder.com/v5.1/find-email/person"
    headers = {"Authorization": key, "Content-Type": "application/json"}
    payload = {"domain": domain, "full_name": full_name}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json() or {}
        status = data.get("email_status", "")
        valid_email = data.get("valid_email")
        email = data.get("email")
        if status == "valid" and (valid_email or email):
            return (valid_email or email, 1.0)
        if status == "risky" and email:
            return (email, 0.5)
        return (None, 0.0)
    except Exception:
        return (None, 0.0)


def find_email_anymail_by_company(
    full_name: str,
    company_name: str,
    api_key: str | None = None,
    timeout: int = 60,
) -> tuple[str | None, float]:
    """
    Anymail Finder API: find person's email by full name and company name (no domain needed).
    API resolves company name to domain. Returns (email or None, confidence 0-1).
    """
    key = api_key or os.environ.get("ANYMAIL_API_KEY")
    if not key:
        return (None, 0.0)
    full_name = (full_name or "").strip()
    company_name = (company_name or "").strip()
    if not full_name or not company_name:
        return (None, 0.0)

    url = "https://api.anymailfinder.com/v5.1/find-email/person"
    headers = {"Authorization": key, "Content-Type": "application/json"}
    payload = {"company_name": company_name, "full_name": full_name}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json() or {}
        status = data.get("email_status", "")
        valid_email = data.get("valid_email")
        email = data.get("email")
        if status == "valid" and (valid_email or email):
            return (valid_email or email, 1.0)
        if status == "risky" and email:
            return (email, 0.5)
        return (None, 0.0)
    except Exception:
        return (None, 0.0)


def find_email_hunter(first_name: str, last_name: str, domain: str, api_key: str | None = None) -> tuple[str | None, float]:
    """
    Hunter.io domain search / email finder. Returns (email or None, confidence 0-1).
    Used as fallback when Anymail Finder API key is not set.
    """
    key = api_key or os.environ.get("HUNTER_API_KEY")
    if not key or not domain:
        return (None, 0.0)

    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "domain": domain.replace("www.", "").split("/")[0],
        "first_name": first_name,
        "last_name": last_name,
        "api_key": key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("data") or {}
        email = data.get("email")
        score = data.get("score", 0) / 100.0 if data.get("score") else 0.5
        return (email, min(score, 1.0))
    except Exception:
        return (None, 0.0)


def _name_to_first_last(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], " ".join(parts[1:]))


def _domain_from_url(url: str) -> str:
    if not url:
        return ""
    url = url.replace("https://", "").replace("http://", "").split("/")[0]
    return url.replace("www.", "")


def run_email_finder_for_company(
    conn: Any,
    company_number: str,
    min_confidence: float = 0.7,
) -> int:
    """
    For each person in people_stage for this company (without email in email_stage),
    try to find email via Hunter; insert into email_stage if confidence >= min_confidence.
    Uses company website domain from company_website_stage.
    Returns number of emails inserted.
    """
    cur = conn.execute(
        "SELECT url FROM company_website_stage WHERE company_number = ?",
        (company_number,),
    )
    row = cur.fetchone()
    if not row:
        return 0
    domain = _domain_from_url(row[0])
    if not domain:
        return 0

    cur = conn.execute(
        """SELECT id, full_name FROM people_stage WHERE company_number = ? AND source IN ('linkedin_serp', 'website_llm')""",
        (company_number,),
    )
    people = cur.fetchall()
    existing = set()
    cur = conn.execute("SELECT email FROM email_stage WHERE company_number = ?", (company_number,))
    for r in cur.fetchall():
        existing.add(r[0])

    # Prefer Anymail Finder API if key is set; else Hunter
    use_anymail = bool(os.environ.get("ANYMAIL_API_KEY"))

    inserted = 0
    for person_id, full_name in people:
        full_name = (full_name or "").strip()
        if not full_name:
            continue
        if use_anymail:
            email, conf = find_email_anymail(full_name, domain)
            source = "anymail"
        else:
            first, last = _name_to_first_last(full_name)
            if not first:
                continue
            email, conf = find_email_hunter(first, last, domain)
            source = "hunter"
        if email and conf >= min_confidence and email not in existing:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO email_stage (company_number, person_id, email, confidence, source, source_metadata)
                       VALUES (?, ?, ?, ?, ?, NULL)""",
                    (company_number, person_id, email, conf, source),
                )
                inserted += 1
                existing.add(email)
            except Exception:
                pass
    conn.commit()
    return inserted
