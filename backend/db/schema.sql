-- Vanguard: UK asset manager discovery pipeline
-- Canonical key: company_number (Companies House). All stages key off this.
-- SQLite; idempotent, append-only where applicable.
--
-- For referential integrity, run before use: PRAGMA foreign_keys = ON;

-- =============================================================================
-- 1. Company registry (canonical from Companies House CSV)
-- =============================================================================
CREATE TABLE IF NOT EXISTS company_registry (
    company_number     TEXT NOT NULL PRIMARY KEY,
    name               TEXT NOT NULL,
    name_normalized    TEXT,                    -- lower, stripped, for matching
    company_type       TEXT,
    status             TEXT,
    sic_codes          TEXT,                    -- JSON array or comma-sep
    description        TEXT,                    -- from SIC or derived
    registered_address TEXT,
    incorporation_date TEXT,
    previous_names     TEXT,                    -- JSON array for name variants
    asset_manager_score REAL NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at         TEXT NOT NULL DEFAULT (datetime('now')),
    source             TEXT NOT NULL DEFAULT 'companies_house_csv',
    source_metadata    TEXT                    -- JSON: file path, row hash, etc.
);

CREATE INDEX IF NOT EXISTS idx_registry_asset_score
    ON company_registry(asset_manager_score);
CREATE INDEX IF NOT EXISTS idx_registry_name_normalized
    ON company_registry(name_normalized);

-- =============================================================================
-- 2. Company name variants (for query generation & LinkedIn disambiguation)
-- Government registered name often differs from trading name / LinkedIn name.
-- =============================================================================
CREATE TABLE IF NOT EXISTS company_name_variants (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    company_number     TEXT NOT NULL REFERENCES company_registry(company_number),
    variant_name       TEXT NOT NULL,
    variant_type       TEXT NOT NULL,          -- 'official' | 'previous' | 'trading' | 'acronym' | 'linkedin_display'
    source             TEXT,                  -- 'companies_house' | 'linkedin' | 'website' | 'manual'
    confidence         REAL DEFAULT 1.0,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(company_number, variant_name, variant_type)
);

CREATE INDEX IF NOT EXISTS idx_name_variants_company
    ON company_name_variants(company_number);

-- =============================================================================
-- 3. LinkedIn company candidates (all SerpAPI results before picking one)
-- Reduces risk of choosing wrong page: store candidates, then disambiguate.
-- =============================================================================
CREATE TABLE IF NOT EXISTS linkedin_company_candidates (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    company_number         TEXT NOT NULL REFERENCES company_registry(company_number),
    linkedin_url           TEXT NOT NULL,
    linkedin_slug          TEXT,               -- last segment of URL for dedup
    result_title           TEXT,
    result_snippet         TEXT,
    result_position        INTEGER,           -- rank in SERP
    query_used             TEXT NOT NULL,     -- exact query that returned this
    name_match_type        TEXT,              -- 'exact' | 'partial' | 'fuzzy' | 'variant'
    match_confidence       REAL NOT NULL,
    disambiguation_notes   TEXT,              -- why chosen or rejected
    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source                 TEXT NOT NULL DEFAULT 'serpapi',
    source_metadata        TEXT                -- JSON: serp request id, etc.
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_linkedin_candidates_company_slug
    ON linkedin_company_candidates(company_number, linkedin_slug);
CREATE INDEX IF NOT EXISTS idx_linkedin_candidates_company_confidence
    ON linkedin_company_candidates(company_number, match_confidence DESC);

-- =============================================================================
-- 4. LinkedIn company stage (chosen page per company; one per company)
-- =============================================================================
CREATE TABLE IF NOT EXISTS linkedin_company_stage (
    company_number         TEXT NOT NULL PRIMARY KEY REFERENCES company_registry(company_number),
    linkedin_url           TEXT NOT NULL,
    linkedin_slug          TEXT NOT NULL,
    linkedin_display_name  TEXT,               -- name as shown on LinkedIn (may differ from registry)
    size                   TEXT,               -- e.g. "11-50 employees"
    industry               TEXT,
    description_snippet    TEXT,
    match_confidence       REAL NOT NULL,
    chosen_candidate_id    INTEGER REFERENCES linkedin_company_candidates(id),
    disambiguation_reason  TEXT,               -- how we chose this over other candidates
    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source                 TEXT NOT NULL DEFAULT 'serpapi',
    source_metadata        TEXT
);

-- =============================================================================
-- 5. Company website discovery (multiple sources; best URL per company)
-- =============================================================================
CREATE TABLE IF NOT EXISTS company_website_candidates (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    company_number     TEXT NOT NULL REFERENCES company_registry(company_number),
    url                TEXT NOT NULL,
    discovery_source   TEXT NOT NULL,          -- 'serpapi' | 'linkedin_page' | 'companies_house' | 'manual'
    confidence         REAL NOT NULL,
    title_or_snippet   TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    source_metadata    TEXT
);

CREATE TABLE IF NOT EXISTS company_website_stage (
    company_number     TEXT NOT NULL PRIMARY KEY REFERENCES company_registry(company_number),
    url                TEXT NOT NULL,
    discovery_source   TEXT NOT NULL,
    confidence         REAL NOT NULL,
    last_fetched_at    TEXT,
    content_hash       TEXT,                  -- for cache invalidation
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at         TEXT NOT NULL DEFAULT (datetime('now')),
    source_metadata    TEXT
);

CREATE INDEX IF NOT EXISTS idx_website_candidates_company
    ON company_website_candidates(company_number);

-- =============================================================================
-- 6. People stage (unified: from LinkedIn SerpAPI and/or website LLM)
-- =============================================================================
CREATE TABLE IF NOT EXISTS people_stage (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    company_number         TEXT NOT NULL REFERENCES company_registry(company_number),
    full_name              TEXT NOT NULL,
    title                  TEXT,
    relevance_score        REAL NOT NULL,
    source                 TEXT NOT NULL,     -- 'linkedin_serp' | 'website_llm'
    source_identifier      TEXT,              -- LinkedIn profile URL or page URL
    raw_snippet_or_excerpt TEXT,              -- for audit
    role_category          TEXT,              -- 'cio' | 'pm' | 'partner' | 'director' | 'other'
    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    source_metadata        TEXT,              -- JSON: model used, prompt hash for LLM
    UNIQUE(company_number, full_name, source, source_identifier)
);

CREATE INDEX IF NOT EXISTS idx_people_company
    ON people_stage(company_number);
CREATE INDEX IF NOT EXISTS idx_people_relevance
    ON people_stage(company_number, relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_people_source
    ON people_stage(source);

-- =============================================================================
-- 7. Email stage (per person or per company contact)
-- =============================================================================
CREATE TABLE IF NOT EXISTS email_stage (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    company_number     TEXT NOT NULL REFERENCES company_registry(company_number),
    person_id          INTEGER REFERENCES people_stage(id),  -- NULL if company-level only
    email              TEXT NOT NULL,
    confidence         REAL NOT NULL,
    source             TEXT NOT NULL,         -- 'hunter' | 'clearbit' | 'website_llm' | 'manual'
    source_metadata    TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(company_number, email)
);

CREATE INDEX IF NOT EXISTS idx_email_company
    ON email_stage(company_number);
CREATE INDEX IF NOT EXISTS idx_email_person
    ON email_stage(person_id);
CREATE INDEX IF NOT EXISTS idx_email_confidence
    ON email_stage(confidence DESC);

-- =============================================================================
-- 8. Website content cache (for LLM parsing; optional)
-- =============================================================================
CREATE TABLE IF NOT EXISTS website_content_cache (
    url                TEXT NOT NULL PRIMARY KEY,
    content_type       TEXT,                  -- 'html' | 'text'
    content_hash       TEXT NOT NULL,
    fetched_at         TEXT NOT NULL,
    byte_size          INTEGER,
    source_metadata    TEXT
);

-- =============================================================================
-- 9. Pipeline run log (resumability and audit)
-- =============================================================================
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_name         TEXT NOT NULL,
    company_number     TEXT,
    status             TEXT NOT NULL,         -- 'started' | 'completed' | 'failed' | 'skipped'
    rows_affected      INTEGER,
    error_message     TEXT,
    started_at         TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at       TEXT,
    source_metadata    TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_stage
    ON pipeline_runs(stage_name);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_company
    ON pipeline_runs(company_number);
