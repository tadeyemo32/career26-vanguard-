"""Ingest Companies House CSV into company_registry. Idempotent, batched."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable

from db import get_connection, init_schema, log_run
from ingestion.text_cleaner import clean_company_name, clean_text


def _norm(s: str | None) -> str:
    if s is None:
        return ""
    return " ".join(str(s).strip().split())


def _get_cell(row: dict[str, str], col_key: str) -> str | None:
    """
    Get cell value matching Companies House CSV layout. Tries exact key, stripped key,
    and leading-space variant (some exports use ' CompanyNumber' etc.).
    """
    v = row.get(col_key)
    if v is not None and str(v).strip() != "":
        return v
    v = row.get(col_key.strip())
    if v is not None and str(v).strip() != "":
        return v
    v = row.get(" " + col_key.strip())
    if v is not None and str(v).strip() != "":
        return v
    return None


def _normalize_name(name: str) -> str:
    return _norm(name).lower()


def is_company_active(status: str | None, allowed_statuses: list[str] | None = None) -> bool:
    """
    True if company status is considered active (e.g. not Dissolved/Liquidation).
    allowed_statuses: e.g. ["Active"] → status must be "Active" or start with "Active ".
    """
    if not status or not str(status).strip():
        return False
    allowed = allowed_statuses or ["Active"]
    s = str(status).strip()
    for prefix in allowed:
        if s == prefix or s.startswith(prefix + " "):
            return True
    return False


def _collect_sic(row: dict[str, str], col_keys: list[str]) -> list[str]:
    """Collect SIC values from SICCode.SicText_1..4. CSV format: 'CODE - Description' per cell."""
    out: list[str] = []
    for k in col_keys:
        v = _get_cell(row, k)
        if v and _norm(v):
            out.append(clean_text(_norm(v)))
    return out


def _sic_codes_to_json(sic_list: list[str]) -> str:
    return json.dumps(sic_list) if sic_list else "[]"


def _sic_to_description(sic_list: list[str]) -> str:
    return " | ".join(sic_list) if sic_list else ""


def _previous_names(row: dict[str, str], col_keys: list[str]) -> str:
    names: list[str] = []
    seen: set[str] = set()
    for k in col_keys:
        v = _get_cell(row, k)
        n = clean_company_name(_norm(v)) if v else ""
        if n and n not in seen:
            names.append(n)
            seen.add(n)
    return json.dumps(names) if names else "[]"


def _address_line(
    row: dict[str, str],
    line1: str,
    town: str,
    county: str,
    country: str,
    post_code: str,
) -> str:
    parts = [
        clean_text(_norm(_get_cell(row, line1) or "")),
        clean_text(_norm(_get_cell(row, town) or "")),
        clean_text(_norm(_get_cell(row, county) or "")),
        clean_text(_norm(_get_cell(row, country) or "")),
        clean_text(_norm(_get_cell(row, post_code) or "")),
    ]
    return ", ".join(p for p in parts if p)


def row_to_registry(
    row: dict[str, str],
    cols: dict[str, str],
    prev_name_cols: list[str],
) -> tuple[str, str, str | None, str, str, str, str, str, str, str, str]:
    """
    Map one CSV row to company_registry. Columns must match Companies House bulk product:
    CompanyName, CompanyNumber, CompanyCategory, CompanyStatus, IncorporationDate,
    SICCode.SicText_1..4, RegAddress.*, PreviousName_1.CompanyName .. PreviousName_10.CompanyName.
    SIC cells are 'CODE - Description' (e.g. '66300 - Fund management activities').
    All text is cleaned (no stray quotes or random characters).
    """
    raw_name = _norm(_get_cell(row, cols["name"]) or "")
    name = clean_company_name(raw_name)
    company_number = _norm(_get_cell(row, cols["company_number"]) or "")
    if not company_number or not name:
        raise ValueError("missing company_number or name")

    sic_cols = [cols["sic_1"], cols["sic_2"], cols["sic_3"], cols["sic_4"]]
    sic_list = _collect_sic(row, sic_cols)
    sic_codes_json = _sic_codes_to_json(sic_list)
    description = _sic_to_description(sic_list)

    company_type = clean_text(_norm(_get_cell(row, cols["company_category"]) or ""))
    status = clean_text(_norm(_get_cell(row, cols["status"]) or ""))
    incorporation_date = clean_text(_norm(_get_cell(row, cols["incorporation_date"]) or ""))
    registered_address = _address_line(
        row,
        cols["address_line1"],
        cols["post_town"],
        cols["county"],
        cols["country"],
        cols["post_code"],
    )
    previous_names_json = _previous_names(row, prev_name_cols)

    return (
        company_number,
        name,
        _normalize_name(name) or None,
        company_type or None,
        status or None,
        sic_codes_json,
        description or None,
        registered_address or None,
        incorporation_date or None,
        previous_names_json,
        "companies_house_csv",
    )


def ingest_csv(
    db_path: str | Path,
    csv_path: str | Path,
    batch_size: int = 5000,
    column_config: dict[str, str] | None = None,
    previous_name_columns: list[str] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    active_only: bool = True,
    allowed_company_statuses: list[str] | None = None,
) -> int:
    """
    Stream Companies House CSV and insert into company_registry.
    Uses INSERT OR REPLACE so re-runs are idempotent (same company_number overwritten).
    If active_only is True, only rows with status in allowed_company_statuses (e.g. "Active")
    are ingested; dissolved and other non-active firms are skipped.
    progress_callback(batch_index: int, total_rows: int) is called after each batch.
    If should_stop() returns True, ingestion stops and returns rows processed so far.
    Returns total rows processed.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    cols = column_config or {}
    prev_name_cols = previous_name_columns or []
    conn = get_connection(db_path)
    init_schema(conn)

    total = 0
    batch_index = 0
    batch: list[tuple[str, str, str | None, str, str, str, str, str, str, str, str]] = []

    sql = """
    INSERT OR REPLACE INTO company_registry
    (company_number, name, name_normalized, company_type, status, sic_codes, description,
     registered_address, incorporation_date, previous_names, source)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def stop() -> bool:
        return should_stop() if callable(should_stop) else False

    try:
        with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                if stop():
                    break
                try:
                    t = row_to_registry(row, cols, prev_name_cols)
                    if active_only and not is_company_active(t[4], allowed_company_statuses):
                        continue
                    batch.append(t)
                except (ValueError, KeyError):
                    continue
                if len(batch) >= batch_size:
                    conn.executemany(sql, batch)
                    conn.commit()
                    total += len(batch)
                    batch_index += 1
                    if callable(progress_callback):
                        progress_callback(batch_index, total)
                    batch = []
            if stop():
                pass  # already broke or finishing
        if batch:
            conn.executemany(sql, batch)
            conn.commit()
            total += len(batch)
            batch_index += 1
            if callable(progress_callback):
                progress_callback(batch_index, total)
        log_run(conn, "ingest", None, "completed", total, None, None)
    except Exception as e:
        log_run(conn, "ingest", None, "failed", total, str(e), None)
        raise

    return total
