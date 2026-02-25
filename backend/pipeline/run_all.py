"""
End-to-end pipeline runner. Runs stages in order; idempotent and resumable.
Usage: from project root:
  PYTHONPATH=. python pipeline/run_all.py [--config config.yaml] [--limit N] [--stages ingest,score_asset_manager,...]
  Or: ./run.sh [--config config.sample.yaml] [--limit 1]
"""
from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Set by signal handler; checked in loops for graceful shutdown
_shutdown_requested = False


def _handle_shutdown(signum: int, frame: object) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    sig = "SIGINT" if signum == signal.SIGINT else "SIGTERM" if signum == signal.SIGTERM else signum
    # Log will happen on next check; avoid doing much in handler
    sys.stdout.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] Received {sig}, shutting down after current step...\n")
    sys.stdout.flush()

# Ensure project root on path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env from project root so SERPAPI_KEY, OPENAI_API_KEY, HUNTER_API_KEY are set
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


class _FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after each emit so output appears immediately."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        if self.stream:
            try:
                self.stream.flush()
            except Exception:
                pass


def _setup_logging(log_dir: Path | None = None) -> logging.Logger:
    """Configure logging: console (INFO) and file (DEBUG) with detailed format."""
    log = logging.getLogger("vanguard.pipeline")
    log.setLevel(logging.DEBUG)
    log.handlers.clear()

    fmt_console = "%(asctime)s | %(levelname)s | %(message)s"
    fmt_file = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    ch = _FlushingStreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt_console, date_fmt))
    log.addHandler(ch)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"pipeline_{ts}.log"
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(fmt_file, date_fmt))
        log.addHandler(fh)
        log.info("Log file: %s", log_path)

    return log


def _git_commit_info(repo_path: Path) -> str:
    """Return current git commit hash, branch, and subject for traceability. Empty if not a repo."""
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if rev.returncode != 0 or not rev.stdout:
            return ""
        commit = rev.stdout.strip()[:12]
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch_str = branch.stdout.strip() if branch.returncode == 0 and branch.stdout else ""
        subject = subprocess.run(
            ["git", "log", "-1", "--oneline", "--no-decorate"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        subject_str = subject.stdout.strip() if subject.returncode == 0 and subject.stdout else ""
        parts = [f"commit={commit}"]
        if branch_str:
            parts.append(f"branch={branch_str}")
        if subject_str:
            parts.append(subject_str)
        return " | ".join(parts)
    except Exception:
        return ""


from config_loader import load_config
from db import ensure_db, get_connection, init_schema, log_run
from enrichment.company_website import run_company_website_for_company
from enrichment.email_finder import run_email_finder_for_company
from enrichment.linkedin_company import run_linkedin_company_for_company
from enrichment.linkedin_people import run_linkedin_people_for_company
from enrichment.name_variants import populate_name_variants
from ingestion.companies_house import ingest_csv
from scoring.asset_manager import update_registry_scores
from enrichment.website_llm import run_website_llm_for_company


def run(
    config_path: str | Path | None = None,
    limit: int | None = None,
    stages: list[str] | None = None,
    log_dir: Path | str | None = None,
    db_path_override: str | Path | None = None,
) -> None:
    global _shutdown_requested
    _shutdown_requested = False
    signal.signal(signal.SIGINT, _handle_shutdown)
    try:
        signal.signal(signal.SIGTERM, _handle_shutdown)
    except (AttributeError, ValueError):
        pass  # SIGTERM not available on all platforms

    log_dir_path = Path(log_dir) if log_dir else _ROOT / "data" / "logs"
    log = _setup_logging(log_dir_path)

    def should_stop() -> bool:
        return _shutdown_requested

    git_info = _git_commit_info(_ROOT)
    if git_info:
        log.info("Git %s", git_info)
    log.info("Pipeline starting | config=%s limit=%s (Ctrl+C to stop gracefully)", config_path or "default", limit)
    cfg = load_config(config_path)
    if db_path_override is not None:
        db_path = Path(db_path_override)
        if not db_path.is_absolute():
            db_path = _ROOT / db_path
    else:
        db_path = cfg.get("db", {}).get("path", "data/vanguard.db")
        db_path = _ROOT / db_path if not Path(db_path).is_absolute() else Path(db_path)
    log.info("Database: %s", db_path)
    conn = ensure_db(db_path)

    stage_list = stages or cfg.get("pipeline", {}).get("stages") or [
        "ingest",
        "score_asset_manager",
        "name_variants",
        "linkedin_company",
        "linkedin_people",
        "company_website",
        "website_llm",
        "email_finder",
    ]
    log.info("Stages: %s", ", ".join(stage_list))

    # If DB already has data and we're running ingest, ask to proceed
    use_existing = "ingest" not in stage_list
    if not use_existing:
        try:
            cur = conn.execute("SELECT COUNT(*) FROM company_registry")
            count = cur.fetchone()[0] if cur else 0
        except Exception:
            count = 0
        if count > 0:
            if sys.stdin.isatty():
                sys.stdout.write(
                    f"Database already contains {count:,} companies. Proceed with current DB? [y/N] "
                )
                sys.stdout.flush()
                try:
                    reply = sys.stdin.readline().strip().lower()
                except Exception:
                    reply = ""
                if reply not in ("y", "yes"):
                    log.info("Aborted by user (proceed with existing DB declined).")
                    sys.exit(0)
            else:
                log.info("Database has %d companies; non-interactive (no prompt).", count)

    ingest_cfg = cfg.get("ingestion", {})
    scoring_cfg = cfg.get("scoring", {})
    enrich_cfg = cfg.get("enrichment", {})
    log_every = cfg.get("pipeline", {}).get("log_every_n_companies", 100)

    # ---- Ingest ----
    if "ingest" in stage_list:
        log.info("Stage starting: ingest (batch progress below)")
        csv_path = ingest_cfg.get("companies_house_csv", "data/companies.csv")
        csv_path = _ROOT / csv_path if not Path(csv_path).is_absolute() else Path(csv_path)
        cols = ingest_cfg.get("columns", {})
        prev_cols = ingest_cfg.get("previous_name_columns", [])
        batch_size = ingest_cfg.get("batch_size", 5000)

        def ingest_progress(batch_index: int, total_rows: int) -> None:
            log.info("ingest batch %d | rows so far=%d", batch_index, total_rows)

        try:
            active_only = ingest_cfg.get("active_only", True)
            allowed_statuses = ingest_cfg.get("allowed_company_statuses") or ["Active"]
            n = ingest_csv(
                db_path,
                csv_path,
                batch_size=batch_size,
                column_config=cols,
                previous_name_columns=prev_cols,
                progress_callback=ingest_progress,
                should_stop=should_stop,
                active_only=active_only,
                allowed_company_statuses=allowed_statuses,
            )
            if _shutdown_requested:
                log.warning("ingest stopped by user | rows_processed=%d", n)
            else:
                log.info("ingest completed | rows=%d | file=%s", n, csv_path)
        except FileNotFoundError as e:
            log.warning("ingest skipped (file not found) | path=%s | error=%s", csv_path, e)
        except Exception as e:
            log.exception("ingest failed | error=%s", e)
            log_run(conn, "ingest", None, "failed", None, str(e), None)
            raise
        if _shutdown_requested:
            log.warning("Shutting down gracefully (ingest stage). Exiting.")
            return
        log.debug("ingest stage finished")

    # ---- Score asset manager ----
    if "score_asset_manager" in stage_list:
        log.info("Stage starting: score_asset_manager (progress every 1000 companies)")
        am = scoring_cfg.get("asset_manager", {})
        try:
            def score_progress(current: int, total: int) -> None:
                log.info("score_asset_manager | %d / %d companies", current, total)

            n = update_registry_scores(
                conn,
                am.get("sic_whitelist") or {},
                am.get("keywords") or {},
                progress_callback=score_progress,
                should_stop=should_stop,
            )
            if _shutdown_requested:
                log.warning("score_asset_manager stopped by user | companies_updated=%d", n)
            else:
                log.info("score_asset_manager completed | companies_updated=%d", n)
        except Exception as e:
            log.exception("score_asset_manager failed | error=%s", e)
            log_run(conn, "score_asset_manager", None, "failed", None, str(e), None)
            raise
        if _shutdown_requested:
            log.warning("Shutting down gracefully (after score stage). Exiting.")
            return

    # ---- Name variants ----
    if "name_variants" in stage_list:
        log.info("Stage starting: name_variants")
        try:
            n = populate_name_variants(conn)
            log.info("name_variants completed | variant_rows=%d", n)
        except Exception as e:
            log.exception("name_variants failed | error=%s", e)
            log_run(conn, "name_variants", None, "failed", None, str(e), None)
            raise

    if _shutdown_requested:
        log.warning("Shutting down gracefully. Exiting.")
        return

    # Companies to process (asset_manager_score >= threshold, active only)
    threshold = (scoring_cfg.get("asset_manager") or {}).get("threshold", 0.6)
    active_only = ingest_cfg.get("active_only", True)
    allowed_statuses = ingest_cfg.get("allowed_company_statuses") or ["Active"]
    if active_only and allowed_statuses:
        placeholders = " OR ".join(["(status = ? OR status LIKE ?)" for _ in allowed_statuses])
        sql = (
            "SELECT company_number, name FROM company_registry "
            "WHERE asset_manager_score >= ? AND (" + placeholders + ") ORDER BY company_number"
        )
        params = (threshold,) + tuple(p for prefix in allowed_statuses for p in (prefix, prefix + " %"))
        log.info("Enrichment: active firms only (status in %s)", allowed_statuses)
    else:
        sql = "SELECT company_number, name FROM company_registry WHERE asset_manager_score >= ? ORDER BY company_number"
        params = (threshold,)
    cur = conn.execute(sql, params)
    companies = cur.fetchall()
    if limit:
        companies = companies[:limit]
    total = len(companies)
    log.info("Enrichment phase | companies=%d | threshold=%.2f (one line per company)", total, threshold)

    serp_delay = (enrich_cfg.get("serpapi") or {}).get("rate_limit_delay_seconds", 1.0)
    max_queries_linkedin = (enrich_cfg.get("serpapi") or {}).get("max_queries_per_company_linkedin", 5)
    linkedin_min = (scoring_cfg.get("linkedin_match") or {}).get("min_confidence", 0.7)
    person_cfg = scoring_cfg.get("person_relevance") or {}
    role_phrases = enrich_cfg.get("linkedin_people_roles") or [
        "Chief Investment Officer", "CIO", "Portfolio Manager", "Managing Partner",
        "Head of Investments", "Investment Director",
    ]
    title_weights = person_cfg.get("title_weights") or {}
    reject_titles = person_cfg.get("reject_titles") or []
    person_min = person_cfg.get("min_score", 0.5)
    email_min = (enrich_cfg.get("email") or {}).get("min_confidence", 0.7)
    llm_model = (enrich_cfg.get("website_llm") or {}).get("model", "gpt-4o-mini")
    llm_max_chars = (enrich_cfg.get("website_llm") or {}).get("max_content_chars", 50000)

    processed = 0
    for i, (company_number, name) in enumerate(companies):
        if _shutdown_requested:
            log.warning("Shutting down gracefully | processed=%d | remaining=%d", processed, total - processed)
            break
        name_short = (name or "")[:50]
        # Constant terminal output: one line per company
        log.info("[%d/%d] %s | %s", i + 1, total, company_number, name_short or "(no name)")
        log.debug("company_number=%s name=%s", company_number, name_short)
        processed = i + 1

        # ---- LinkedIn company ----
        if "linkedin_company" in stage_list:
            try:
                ok = run_linkedin_company_for_company(
                    conn, company_number, name or "",
                    delay_seconds=serp_delay,
                    min_confidence=linkedin_min,
                    max_queries=max_queries_linkedin,
                )
                log.debug("linkedin_company | company_number=%s ok=%s", company_number, ok)
            except Exception as e:
                log.exception("linkedin_company failed | company_number=%s error=%s", company_number, e)
                log_run(conn, "linkedin_company", company_number, "failed", None, str(e), None)

        # ---- LinkedIn people ----
        if "linkedin_people" in stage_list:
            try:
                n_people = run_linkedin_people_for_company(
                    conn, company_number, name or "",
                    role_phrases=role_phrases,
                    title_weights=title_weights,
                    reject_titles=reject_titles,
                    min_score=person_min,
                    delay_seconds=serp_delay,
                )
                log.debug("linkedin_people | company_number=%s people_added=%d", company_number, n_people)
            except Exception as e:
                log.exception("linkedin_people failed | company_number=%s error=%s", company_number, e)
                log_run(conn, "linkedin_people", company_number, "failed", None, str(e), None)

        # ---- Company website ----
        if "company_website" in stage_list:
            try:
                ok = run_company_website_for_company(conn, company_number, name or "", delay_seconds=serp_delay)
                log.debug("company_website | company_number=%s ok=%s", company_number, ok)
            except Exception as e:
                log.exception("company_website failed | company_number=%s error=%s", company_number, e)
                log_run(conn, "company_website", company_number, "failed", None, str(e), None)

        # ---- Website LLM ----
        if "website_llm" in stage_list:
            cur2 = conn.execute("SELECT url FROM company_website_stage WHERE company_number = ?", (company_number,))
            row = cur2.fetchone()
            if row:
                try:
                    n_llm = run_website_llm_for_company(
                        conn, company_number, row[0],
                        model=llm_model,
                        max_content_chars=llm_max_chars,
                    )
                    log.debug("website_llm | company_number=%s people_from_llm=%d", company_number, n_llm)
                except Exception as e:
                    log.exception("website_llm failed | company_number=%s error=%s", company_number, e)
                    log_run(conn, "website_llm", company_number, "failed", None, str(e), None)

        # ---- Email finder ----
        if "email_finder" in stage_list:
            try:
                n_email = run_email_finder_for_company(conn, company_number, min_confidence=email_min)
                log.debug("email_finder | company_number=%s emails_added=%d", company_number, n_email)
            except Exception as e:
                log.exception("email_finder failed | company_number=%s error=%s", company_number, e)
                log_run(conn, "email_finder", company_number, "failed", None, str(e), None)

    if _shutdown_requested:
        log.warning("Pipeline stopped by user | companies_processed=%d (of %d)", processed, total)
    else:
        log.info("Pipeline run complete | companies_processed=%d", total)


def main() -> None:
    p = argparse.ArgumentParser(description="Vanguard pipeline: ingest → score → enrich")
    p.add_argument("--config", default=None, help="Path to config.yaml")
    p.add_argument("--limit", type=int, default=None, help="Max companies to enrich (default: all above threshold)")
    p.add_argument("--stages", type=str, default=None, help="Comma-separated stages to run (default: all)")
    p.add_argument("--log-dir", default=None, help="Directory for log files (default: data/logs)")
    p.add_argument("--db-path", default=None, help="Override database path (from config)")
    args = p.parse_args()
    stages = [s.strip() for s in args.stages.split(",")] if args.stages else None
    run(config_path=args.config, limit=args.limit, stages=stages, log_dir=args.log_dir, db_path_override=args.db_path)


if __name__ == "__main__":
    main()
