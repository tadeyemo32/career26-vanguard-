# Vanguard

UK asset manager discovery pipeline: Companies House CSV → canonical registry → asset-manager scoring → LinkedIn company/people (SerpAPI) → company website discovery → LLM website parsing → email discovery.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Optional API keys: copy `.env.example` to `.env` and set values (or export in the shell). The pipeline loads `.env` from the project root.

- `SERPAPI_KEY` – LinkedIn/company search
- `OPENAI_API_KEY` – website LLM extraction
- `HUNTER_API_KEY` – email finder

## Database

Schema is in `db/schema.sql`. It is applied automatically on first run.

```bash
# Create DB and run schema manually (optional)
sqlite3 data/vanguard.db < db/schema.sql
```

## Desktop app (Mac, Linux, Windows)

A native desktop UI runs on all platforms and architectures (x64 and arm64):

```bash
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
python run_app.py
# or: PYTHONPATH=. python -m app.main
```

**Four tabs:**

1. **Pipeline** – Run tests first, use existing DB, limit companies; run full pipeline with live log.
2. **From spreadsheet** – Load CSV or Excel (company data), set contact filters (job titles), run from file; results are shown and **exportable (CSV)**.
3. **Email lookup** – **Full name + company** → find email via Anymail (API). Optional “Resolve company to domain” for better matching (SerpAPI). Result shown in-app.
4. **People search** – Natural-language search (e.g. *senior IB bankers in London partner*). Searches LinkedIn via SerpAPI, then finds emails with Anymail. Results in a table, **exportable (CSV)**.

Requires `customtkinter` and `openpyxl` (in `requirements.txt`) and a Python build with **tkinter** (usually included on Windows/macOS; on Linux install `python3-tk`).

## Run pipeline (CLI)

Run the **interactive script** (no flags; it asks for options):

```bash
./run.sh
```

You will be prompted for:

1. **Run tests first?** [Y/n] – run the test suite before the pipeline (default: yes).
2. **Use existing database?** [y/N] – **y**: skip ingest and run from score_asset_manager onward. **N** (or Enter): run full pipeline including ingest.
3. **Limit companies** (number or Enter/all for no limit) – cap how many companies to enrich.

Config is read from `config.yaml` by default.

If the database already has data, the pipeline will ask: **Proceed with current DB?** [y/N].

Logs: `data/logs/pipeline_<timestamp>.log` (DEBUG) and `data/logs/run_<timestamp>.log` (full stdout).

Stages (in order): `ingest` → `score_asset_manager` → `name_variants` → `linkedin_company` → `linkedin_people` → `company_website` → `website_llm` → `email_finder`.

## Testing

When you run `./run.sh`, you can choose to run tests first (default: yes). To run **only tests** (no pipeline):

```bash
pytest tests/ -v
# or: python -m pytest tests/ -v -k "rejected"
```

Tests cover every pipeline segment and key error paths:

| Area | Tests |
|------|--------|
| **Config** | `test_config_loader.py` – load_config, missing file, invalid YAML |
| **DB** | `test_db.py` – get_connection, init_schema, ensure_db, log_run |
| **Ingestion** | `test_companies_house.py`, `test_ingest_integration.py` – _get_cell, is_company_active, row_to_registry, ingest_csv (file not found, empty file, one row, active_only) |
| **Scoring** | `test_asset_manager.py` – SIC extraction, asset_manager_score, update_registry_scores |
| **Name pipeline** | `test_company_name_pipeline.py`, `test_search_queries.py` – name→search, rejection, fallback |
| **Name variants** | `test_name_variants.py` – populate, get_variant_names, idempotent |
| **Pipeline** | `test_pipeline_run.py` – run() with name_variants only, missing CSV, score+name_variants |
| **SerpAPI** | `test_serp.py` – no API key returns [] |
| **LinkedIn** | `test_linkedin_module.py` – already-in-stage skip, query building, match score |
| **Company website** | `test_company_website_module.py` – _is_likely_company_site, already-in-stage skip |
| **Email** | `test_email_finder.py` – _name_to_first_last, _domain_from_url, no website → 0 |
| **Website LLM** | `test_website_llm.py` – _content_hash, run with invalid URL |
| **Text cleaning** | `test_text_cleaner.py` – clean_company_name, clean_text |

Fixtures: `temp_db`, `conn`, `sample_registry_row`, `default_column_config`, `sample_csv_row` (see `tests/conftest.py`). No external API calls in tests.

## Config

`config.yaml`:

- **db.path** – SQLite path (default `data/vanguard.db`).
- **ingestion** – CSV path, batch size, column names, previous-name columns.
- **scoring.asset_manager** – threshold, SIC whitelist, keywords.
- **scoring.linkedin_match** – min confidence for LinkedIn company.
- **scoring.person_relevance** – title weights, reject list, min score.
- **enrichment** – SerpAPI delay, role phrases, email min confidence, LLM model.

## Design

- **Canonical key:** `company_number` (Companies House).
- **Idempotent:** Re-runs overwrite or skip; no duplicate rows.
- **Resumable:** Enrichment skips companies already in each stage.
- **Confidence:** Asset manager, LinkedIn match, person relevance, and email confidence are scored; thresholds in config.

See `docs/ARCHITECTURE.md` and `docs/GIT_COMMIT_PLAN.md`.
# career26-vanguard-
