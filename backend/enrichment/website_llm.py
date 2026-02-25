"""Fetch company website, parse with LLM to extract people (names, titles) and emails."""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

import httpx

# Optional: openai for extraction
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _fetch_text(url: str, max_chars: int = 50000) -> str:
    """Fetch URL and return plain text (strip HTML tags)."""
    try:
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
    except Exception:
        return ""
    # Simple tag strip
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


EXTRACT_PEOPLE_SYSTEM = """You are a data extractor. From the given company webpage text, extract only people who appear to be in senior investment/asset management roles (e.g. Chief Investment Officer, Portfolio Manager, Managing Partner, Director, Head of Investments). For each person output: full_name, job_title, and email if clearly stated. Output valid JSON only, as a single object with key "people" and value an array of objects with keys: full_name, job_title, email (or null). Exclude generic contacts like "info@", "team@" unless clearly tied to a named person. If no such people found, return {"people": []}."""


def _extract_people_llm(text: str, model: str = "gpt-4o-mini") -> list[dict[str, Any]]:
    """Call OpenAI to extract people from text. Returns list of {full_name, job_title, email}."""
    if not text or len(text) < 100:
        return []
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return []

    client = OpenAI(api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACT_PEOPLE_SYSTEM},
                {"role": "user", "content": text[:30000]},
            ],
            temperature=0,
        )
        content = (resp.choices[0].message.content or "").strip()
        # Parse JSON (handle markdown code block)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:].strip()
        data = json.loads(content)
        people = data.get("people") or []
        return [p for p in people if isinstance(p, dict) and p.get("full_name")]
    except Exception:
        return []


def run_website_llm_for_company(
    conn: Any,
    company_number: str,
    url: str,
    model: str = "gpt-4o-mini",
    max_content_chars: int = 50000,
    store_cache: bool = True,
) -> int:
    """
    Fetch URL, optionally cache, run LLM extraction, insert into people_stage and email_stage.
    Returns number of people inserted.
    """
    text = _fetch_text(url, max_content_chars)
    if not text:
        return 0

    content_hash_val = _content_hash(text)
    if store_cache:
        conn.execute(
            """INSERT OR REPLACE INTO website_content_cache (url, content_type, content_hash, fetched_at, byte_size)
               VALUES (?, 'text', ?, datetime('now'), ?)""",
            (url, content_hash_val, len(text)),
        )
        conn.commit()

    people = _extract_people_llm(text, model)
    inserted = 0
    for p in people:
        full_name = (p.get("full_name") or "").strip()
        job_title = (p.get("job_title") or "").strip() or None
        email = (p.get("email") or "").strip() or None
        if not full_name:
            continue
        try:
            conn.execute(
                """INSERT OR IGNORE INTO people_stage
                   (company_number, full_name, title, relevance_score, source, source_identifier,
                    raw_snippet_or_excerpt, role_category, source_metadata)
                   VALUES (?, ?, ?, 0.7, 'website_llm', ?, NULL, 'other', ?)""",
                (company_number, full_name, job_title, url, json.dumps({"model": model})),
            )
            inserted += 1
        except Exception:
            pass

        if email and "@" in email and email != "null":
            try:
                person_id_cur = conn.execute(
                    "SELECT id FROM people_stage WHERE company_number = ? AND full_name = ? AND source = 'website_llm' AND source_identifier = ?",
                    (company_number, full_name, url),
                )
                person_row = person_id_cur.fetchone()
                person_id = person_row[0] if person_row else None
                conn.execute(
                    """INSERT OR IGNORE INTO email_stage (company_number, person_id, email, confidence, source, source_metadata)
                       VALUES (?, ?, ?, 0.8, 'website_llm', ?)""",
                    (company_number, person_id, email, json.dumps({"model": model})),
                )
            except Exception:
                pass

    conn.commit()
    return inserted
