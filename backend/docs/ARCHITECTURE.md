# Architecture: UK asset manager discovery pipeline

This document describes the **accuracy- and cost-optimised** design for identifying UK asset management firms and relevant senior staff from Companies House data. It is Python-first, stage-based, and idempotent.

---

## Design principles

- **Canonical company identity:** Company UUID/key = Companies House number. All stages key off this.
- **Confidence at every stage:** Asset manager, LinkedIn match, person relevance, and email confidence are scored; no binary filters only.
- **Cost control:** SerpAPI is used only after filtering to likely asset managers; one query per company where possible.
- **Ordering:** Company registry → asset-manager scoring → LinkedIn company → people (with role filter) → email discovery. Email discovery runs only after role filtering to avoid junk.
- **Idempotent & resumable:** Stages are append-only; re-runs do not duplicate work.

---

## What was wrong / suboptimal (corrected)

1. **SerpAPI too early**  
   Querying SerpAPI before knowing which companies are real asset managers wastes queries and increases false positives. **Fix:** Run SerpAPI only after `asset_manager_score >= threshold`.

2. **AnyMail / email discovery too late in the wrong sense**  
   Email discovery must happen **after** role filtering (CIO, PM, Partner, Head of Investments). Otherwise we harvest junk. **Fix:** People stage with relevance scoring first; email stage consumes only relevant people.

3. **No canonical company identity**  
   Everything must key off a single company key. **Fix:** Companies House number as primary key; Company UUID derived from it where needed.

4. **No confidence scoring**  
   We need scores at each stage for auditability and thresholding. **Fix:**  
   - `asset_manager_score`  
   - `linkedin_match_confidence`  
   - `person_relevance_score`  
   - `email_confidence`

---

## Stage diagram (data flow)

```text
Companies House CSV
        │
        ▼
┌─────────────────────────┐
│ company_registry (DB)    │
│ - company_number (PK)    │
│ - name, name_normalized  │
│ - sic_codes, description │
│ - previous_names         │
│ - asset_mgr_score        │
└─────────────────────────┘
        │  (score ≥ threshold)
        ├──────────────────────────────────┐
        ▼                                  ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│ company_name_variants   │    │ company_website_stage   │
│ (official, previous,    │    │ - url, discovery_source │
│  trading, acronym)      │    │ - confidence            │
└─────────────────────────┘    └─────────────────────────┘
        │                                  │
        ▼                                  │
┌─────────────────────────┐                │
│ linkedin_company_        │                │
│ candidates → stage      │                │
│ (disambiguate; store    │                │
│  size, industry,        │                │
│  description_snippet)   │                │
└─────────────────────────┘                │
        │                                  │
        ▼                                  ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│ people_stage             │◄───│ website_content_cache   │
│ (source: linkedin_serp   │    │ → LLM parse → names,    │
│  | website_llm)         │    │   titles, emails        │
└─────────────────────────┘    └─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ email_stage              │
│ - email, confidence      │
│ - source (incl. website_llm) │
└─────────────────────────┘
```

All stages are **append-only** and resumable. People and emails can come from **LinkedIn (SerpAPI)** and/or **website LLM**.

---

## Scoring methodology

### 1. Asset manager score

- **Do not** hard-filter; **score**.
- SIC whitelist (e.g. 66300 fund management, 64304 unit trusts) with weights.
- Keyword match on company description (e.g. "asset management", "hedge fund", "private equity") with weights.
- Sum weights, cap at 1.0. Promote with `WHERE asset_manager_score >= 0.6` (or configured threshold).

### 2. LinkedIn company match confidence

- Query: `"{company.name}" site:linkedin.com/company`.
- Score by: company name in result title, "asset" in snippet, domain = linkedin.com.
- Accept only `match_confidence >= 0.7`.

### 3. Person relevance score

- Query: `"{company.name}" ("CIO" OR "Portfolio Manager" OR "Managing Partner") site:linkedin.com/in`.
- Title weights (e.g. Chief Investment Officer 1.0, Portfolio Manager 0.9, etc.).
- Reject: recruiters, interns, analysts (unless small firm).

### 4. Email confidence

- Input: `(name, company_domain)`.
- Score: role seniority, domain match, MX validity.
- Do **not** store emails below confidence 0.7.

---

## Database schema (correctness and accuracy)

The canonical schema lives in **`db/schema.sql`**. Key guarantees:

- **Canonical key:** `company_number` (Companies House) is the only company key; every table that references a company uses it. No duplicate company identities.
- **Name variants:** `company_name_variants` stores official name, previous names, trading name, acronyms, and (after resolution) LinkedIn display name. Used for query generation and disambiguation so we never assume "government name = LinkedIn name".
- **LinkedIn disambiguation:** `linkedin_company_candidates` stores every SerpAPI result; we choose one and write to `linkedin_company_stage` with `chosen_candidate_id` and `disambiguation_reason`. Reduces risk of picking the wrong page.
- **Source and variance:** Every stage table has `source` and optional `source_metadata` (JSON). People and emails record `source` (e.g. `linkedin_serp`, `website_llm`) so we can audit and weight by origin.
- **People uniqueness:** `people_stage` has a unique constraint on `(company_number, full_name, source, source_identifier)` so we don’t duplicate the same person from the same source.
- **Email uniqueness:** One row per `(company_number, email)`; `person_id` links to `people_stage` when the email is person-specific.

Apply the schema once; migrations can add columns or tables later without breaking existing data.

---

## LinkedIn page disambiguation (avoid wrong company page)

**Problem:** The government-registered company name often differs from the name on the LinkedIn company page (trading name, abbreviation, "Ltd" vs "Limited", etc.). A single query on the official name can return the wrong company or no results.

**Approach:**

1. **Build query inputs from multiple names:** Use `company_registry.name`, `company_registry.previous_names`, and `company_name_variants` (trading, acronym) so we never rely on a single string.
2. **Run multiple SerpAPI queries per company** (see "Multiple query variations" below). Each query may return different candidates.
3. **Store all candidates** in `linkedin_company_candidates` with the exact `query_used`, `result_title`, `result_snippet`, `match_confidence`, and `name_match_type` (exact / partial / fuzzy / variant).
4. **Disambiguate and choose one:** Score candidates by: name overlap with registry + variants, snippet relevance (e.g. "asset", "investment"), and SERP position. Write the chosen page to `linkedin_company_stage` with `chosen_candidate_id` and `disambiguation_reason` (e.g. "best name match + industry snippet").
5. **Persist LinkedIn display name:** Store `linkedin_display_name` from the chosen page and insert it into `company_name_variants` with `variant_type = 'linkedin_display'` so future people queries can use it.

This way we **never assume** company name = LinkedIn page name; we **explicitly match** and record why we chose a page.

---

## Multiple query variations (maximize result guarantee)

To maximise the chance of getting **description, size, and people** (even when names differ), run **several query shapes** per company and merge results.

### LinkedIn company (description, size, industry)

- **Query set (run all until we have a confident match):**
  - `"{official_name}" site:linkedin.com/company`
  - `"{trading_name}" site:linkedin.com/company` (if different)
  - `"{previous_name}" site:linkedin.com/company` for recent previous names
  - `"{acronym}" site:linkedin.com/company` if acronym exists and is distinct
  - `"{official_name}" companies house site:linkedin.com/company` (to tie to registry)
- **Result handling:** All results go into `linkedin_company_candidates`. After scoring and disambiguation, the **chosen** page is the single source for `size`, `industry`, `description_snippet` in `linkedin_company_stage`. If the first query returns nothing, the next variants often do.

### People (names and titles)

- **Query set (multiple role variations):**
  - `"{company_name}" ("Chief Investment Officer" OR "CIO") site:linkedin.com/in`
  - `"{company_name}" ("Portfolio Manager" OR "PM") site:linkedin.com/in`
  - `"{company_name}" ("Managing Partner" OR "Partner") site:linkedin.com/in`
  - `"{company_name}" ("Head of Investments" OR "Investment Director") site:linkedin.com/in`
  - Use **both** official name and `linkedin_display_name` (if we have it) in these queries, to catch profiles that mention the brand name as shown on LinkedIn.
- **Deduplication:** Merge by profile URL (and normalised name) into `people_stage` with `source = 'linkedin_serp'`. One row per person per company per source.

Running multiple queries **does not** guarantee 100% recall (SerpAPI and index coverage are limited), but it **maximises** the chance of getting description, size, and people; the DB and disambiguation logic keep results correct and auditable.

---

## Other sources of variance (accounted for)

- **Trading name vs registered name:** Stored in `company_name_variants` with `variant_type = 'trading'`; used in LinkedIn and website queries.
- **Previous company names:** From Companies House `previous_names`; parsed and stored as variants; used in company (and optionally people) query variations.
- **Acronyms / short names:** Derived or manual; stored as `variant_type = 'acronym'`; used when they differ from the full name.
- **LinkedIn display name:** After we resolve the correct LinkedIn company page, we store its display name as a variant so people queries can use the name that actually appears on LinkedIn.
- **DBA / "doing business as":** Can be added to `company_name_variants` if we have a source (e.g. website, manual).

All variance is **keyed by `company_number`** so we never mix companies. Query-generation logic should pull from registry + variants and emit the full set of query strings for each stage.

---

## Company website discovery

Before we can parse a site with an LLM, we need a **company website URL**. Support multiple discovery methods and record source.

1. **SerpAPI:** Query e.g. `"{company_name}" UK` or `"{company_name}" asset management UK`; take organic results with confident domain (not social, not directories). Store in `company_website_candidates` with `discovery_source = 'serpapi'`.
2. **LinkedIn company page:** If we have a chosen LinkedIn company page, SerpAPI or a permitted API may expose a website link; add it as a candidate with `discovery_source = 'linkedin_page'`.
3. **Companies House / registry:** If the CSV or another CH source provides a website field, add with `discovery_source = 'companies_house'`.
4. **Choose one URL per company:** Score candidates (e.g. domain matches company name, HTTPS, not a generic CMS). Write the chosen URL to `company_website_stage` with `confidence` and `discovery_source`.

The chosen URL is then used for fetching content and LLM parsing.

---

## LLM website parsing (people and emails from website)

Use the company website as an **additional source** of people and (optionally) emails to improve coverage and accuracy.

1. **Fetch:** For the URL in `company_website_stage`, fetch the page (and optionally key subpages, e.g. /team, /about). Store raw content or a cleaned text version in `website_content_cache` (with `content_hash`, `fetched_at`) to avoid re-fetching and to make parsing reproducible.
2. **LLM extract:** Send content (or chunks) to an LLM with a **structured prompt** that asks for:
   - List of people: full name, job title, (optional) email.
   - Only people in relevant roles (e.g. leadership, investments, portfolio management); exclude generic "Team" or "Contact" if not role-specific.
3. **Normalise and score:** Map LLM output to our schema. Assign a **relevance score** (e.g. from role keywords). Set `source = 'website_llm'` and `source_identifier` = page URL (or chunk id).
4. **Write to DB:** Insert into `people_stage` (and, when the LLM returns emails, into `email_stage` with `source = 'website_llm'` and `person_id` if we can match to a person). Enforce uniqueness so we don’t duplicate the same person from the same page.
5. **Deduplicate with LinkedIn:** The same person may appear in both `linkedin_serp` and `website_llm`. Keep both rows with different `source`; downstream (e.g. outreach) can prefer one source or merge by name + company.

This path **directly** returns names, titles, and sometimes emails from the website, and the DB keeps them correct and attributable via `source` and `source_metadata` (e.g. model name, prompt hash).

---

## People accuracy (correctness of discovered people)

- **Relevance scoring:** Every person has `relevance_score` and optional `role_category`. Apply title weights and reject list (recruiters, interns, junior analysts unless small firm); only store above threshold.
- **Source tracking:** `people_stage.source` is always set (`linkedin_serp` or `website_llm`). We can audit and filter by source.
- **Deduplication:** Unique on `(company_number, full_name, source, source_identifier)` so the same profile or same page does not create duplicate rows.
- **Raw snippet / excerpt:** `raw_snippet_or_excerpt` keeps a trace of where the name/title came from for manual review.
- **Cross-check:** When both LinkedIn and website LLM return the same name, we have two independent signals; we do not merge automatically but we can surface "high confidence" when multiple sources agree.

---

## Repo structure (Python)

```text
vanguard/
├── ingestion/
│   └── companies_house.py
├── scoring/
│   ├── asset_manager.py
│   ├── linkedin_match.py
│   └── person_relevance.py
├── enrichment/
│   ├── linkedin_company.py   # multi-query, candidates, disambiguation
│   ├── linkedin_people.py   # multi-query by role, dedup by profile URL
│   ├── company_website.py   # discover URL (SerpAPI, LinkedIn, CH)
│   ├── website_llm.py       # fetch, LLM parse → people + emails
│   └── email_finder.py
├── db/
│   └── schema.sql
├── pipeline/
│   └── run_all.py
├── config.yaml
└── docs/
    ├── ARCHITECTURE.md
    └── GIT_COMMIT_PLAN.md
```

---

## Implementation constraints

- **Input:** Companies House CSV.
- **Database:** SQLite; schema in `db/schema.sql` is the single source of truth for correctness (canonical key, variants, candidates, source tracking).
- **Asset manager classification:** Probabilistic (scored), not binary.
- **LinkedIn:** Discovery via SerpAPI only; no scraping (ToS compliance). Use multiple query variations and store candidates; disambiguate before writing the chosen page.
- **People:** Relevance scoring required; role filter before email. People can come from LinkedIn SerpAPI and/or website LLM; both stored with `source` and deduplicated.
- **Email:** Discovery must include confidence scores; threshold (e.g. 0.7) for storage. Emails may come from finder APIs or from LLM website parsing.
- **Company website:** Discover via SerpAPI, LinkedIn page, or registry; then optionally parse with LLM to extract people (names, titles) and emails directly.

---

## Cursor prompt (reference)

For implementation, use this as the engineering brief:

> You are a senior Python data engineer.  
> Build an end-to-end, resumable data pipeline for identifying UK asset management firms and relevant senior staff.  
> **Constraints:** Input: Companies House CSV. Use SQLite. Asset manager classification must be probabilistic, not binary. LinkedIn discovery via SerpAPI only (no scraping). People relevance scoring required. Email discovery must include confidence scores.  
> **Requirements:** Modular Python package. Typed functions. Deterministic outputs. Idempotent stages.  
> Start by implementing the database schema and Companies House ingestion module.

---

## Next steps (optional)

- **Async rate-limited SerpAPI:** Wire with backoff and rate limits; run multiple query variations per company.
- **LLM integration:** Choose model and prompt for website parsing; store prompt hash in `source_metadata` for reproducibility.
- **Production outreach engine:** Queues, retries, and delivery tracking.

See **`db/schema.sql`** for the full schema. See **GIT_COMMIT_PLAN.md** for the recommended commit sequence and rationale.
