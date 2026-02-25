# Git commit plan

This document defines the **recommended commit sequence** for building the asset-manager discovery pipeline. Use these messages and order so the git history stays accurate, auditable, and easy to review.

---

## Commit sequence

Apply in this order. Each commit should be **one logical unit** and **buildable** (no broken intermediate state).

| # | Commit message | Scope |
|---|----------------|--------|
| 1 | `feat: ingest companies house csv into canonical registry` | DB schema + ingestion only |
| 2 | `feat: probabilistic asset manager scoring` | Scoring module, no SerpAPI yet |
| 3 | `feat: company name variants for query and disambiguation` | name_variants table + population from registry/previous_names |
| 4 | `feat: linkedin company resolution via serpapi with disambiguation` | Candidates table, multi-query, choose one page per company |
| 5 | `feat: people discovery and relevance scoring` | Multi-query by role, dedup, source=linkedin_serp |
| 6 | `feat: company website discovery` | SerpAPI/LinkedIn/CH → company_website_stage |
| 7 | `feat: website LLM parsing for people and emails` | Fetch, LLM extract, people_stage + email_stage source=website_llm |
| 8 | `feat: email discovery with confidence scoring` | Hunter/Clearbit etc.; threshold; link to people_stage |
| 9 | `feat: end-to-end pipeline runner` | Orchestration: registry → scoring → variants → LinkedIn → people → website → LLM → email |
| 10 | `docs: architecture and scoring methodology` | ARCHITECTURE.md + GIT_COMMIT_PLAN.md |

---

## Rationale per commit

1. **ingest companies house csv into canonical registry**  
   Establishes the canonical company identity (Companies House number as PK), SQLite schema, and the first stage: load CSV → `company_registry`. No filtering yet; store everything. Schema includes name_normalized, previous_names, source/source_metadata.

2. **probabilistic asset manager scoring**  
   Add `asset_manager_score` and SIC/keyword logic. Enables filtering with `WHERE asset_manager_score >= threshold` so downstream stages only run on likely asset managers (cost control).

3. **company name variants for query and disambiguation**  
   Populate `company_name_variants` from registry name, previous_names, and (if available) trading/acronym. Ensures we never assume government name = LinkedIn/website name; multiple query shapes use these variants.

4. **linkedin company resolution via serpapi with disambiguation**  
   SerpAPI **after** asset-manager filter. Multiple queries per company (official name, variants). Store all results in `linkedin_company_candidates`; score and choose one into `linkedin_company_stage` with disambiguation_reason and linkedin_display_name. Reduces wrong-page risk.

5. **people discovery and relevance scoring**  
   People **after** LinkedIn company resolution. Multiple role-based queries; use both official name and linkedin_display_name. Dedup by (company_number, full_name, source, source_identifier). Relevance score and reject list (recruiters, interns). Source = linkedin_serp.

6. **company website discovery**  
   Discover company URL via SerpAPI, LinkedIn page, or Companies House. Store candidates then choose one into `company_website_stage` with confidence and discovery_source. Enables LLM parsing.

7. **website LLM parsing for people and emails**  
   Fetch website content (optional cache in website_content_cache). LLM extracts people (name, title) and optionally emails. Write to people_stage (source=website_llm) and email_stage (source=website_llm). Dedup; keep source for audit.

8. **email discovery with confidence scoring**  
   Email **after** people (LinkedIn + optional website LLM). Input: (name, company_domain). Hunter/Clearbit etc.; only store above confidence threshold (e.g. 0.7). Link to people_stage via person_id when applicable.

9. **end-to-end pipeline runner**  
   Orchestrates: registry → scoring filter → name variants → LinkedIn company (multi-query, disambiguate) → people (multi-query) → website discovery → website LLM parse → email. Idempotent, resumable, config-driven.

10. **docs: architecture and scoring methodology**  
    Add `docs/ARCHITECTURE.md` (and GIT_COMMIT_PLAN.md) with design, DB correctness, LinkedIn disambiguation, multi-query strategy, website discovery, LLM parsing, and people accuracy.

---

## One-liners for copy-paste

```text
feat: ingest companies house csv into canonical registry
feat: probabilistic asset manager scoring
feat: company name variants for query and disambiguation
feat: linkedin company resolution via serpapi with disambiguation
feat: people discovery and relevance scoring
feat: company website discovery
feat: website LLM parsing for people and emails
feat: email discovery with confidence scoring
feat: end-to-end pipeline runner
docs: architecture and scoring methodology
```

---

## Branch suggestion

Use a feature branch for the pipeline work, then squash or merge with a clear history:

```bash
git checkout -b feature/asset-manager-pipeline
# ... implement following the commit plan ...
git log --oneline  # should match the sequence above
```

---

See **ARCHITECTURE.md** for the full design, stage diagram, and scoring methodology.
