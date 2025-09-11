# Requirement Specification Document (RSD): Public-State Job Scraper for arbeidsplassen.nav.no

## 1. Introduction / Overview

We need a script that scrapes state-sector job listings from arbeidsplassen.nav.no, limited to open listings and further filtered to a small set of public organizations of interest. The output supports downstream analysis by producing clean, structured data, including all public sector job codes per listing and their corresponding salary bounds.

Primary objective: Extract all open, state-sector job listings matching organization keywords ["Forsvaret", "Politiets sikkerhetstjeneste" (PST), "Nasjonal sikkerhetsmyndighet" (NSM)], capture key fields (including multiple job codes per listing with correct salary ranges), and store the data in convenient, analysis-ready formats (Parquet and CSV). The script should run on-demand and minimize network usage via incremental updates using listing IDs.

## 2. Goals

- Coverage: Capture 100% of currently open, state-sector listings from target orgs.
- Accuracy: Parse all job codes per listing and tie salary bounds to the correct code.
- Efficiency: Use incremental scraping (ID + last-seen) to fetch only new/updated listings.
- Usability: Output both Parquet and CSV in a stable, consistent schema for analysis.
- Robustness: Tolerate minor HTML changes and missing salary values without failing runs.

## 3. User Stories

- As a data analyst, I want a fresh, deduplicated dataset of state-sector jobs for the target orgs so I can analyze roles, codes, and salaries.
- As a data engineer, I want incremental scraping so that reruns are fast and bandwidth-light.
- As a researcher, I want multiple job codes and their salary bounds preserved per listing so I don’t lose detail.
- As a maintainer, I want clear logs and simple configuration to adjust organization matching rules.

## 4. Functional Requirements

1) Scope and filtering
   - The scraper must include only open listings in the public state sector (Statlig). Use the site’s public-sector/state filters if present on the search page.
   - After state-sector filtering, the scraper must further include only listings matching organization keywords (case-insensitive, fuzzy):
     - Forsvaret and sub-units (token-based match: any word starting with "forsvar"), including examples like "Forsvarets", "Forsvarsstaben", "Cyberforsvaret", "Forsvarets personell- og vernepliktssenter" (FPVS), etc. Title-only fallback allowed (see below).
     - Politiets sikkerhetstjeneste (synonyms/variants: "PST", "Politiets sikkerhetstjeneste").
     - Nasjonal sikkerhetsmyndighet (synonyms/variants: "NSM", "Nasjonal sikkerhetsmyndighet").
   - Matching must primarily target the organization/employer field; secondarily, when the state-sector filter is applied, listings with titles containing tokens starting with "forsvar" (e.g., "forsvar", "forsvaret") should be considered in-scope even if the employer string is a sub-unit or variant.
   - Implement normalized, accent-insensitive matching with whitespace collapse and punctuation removal.

2) Listing discovery and pagination
   - The scraper must enumerate all result pages for open, state-sector listings.
   - For each result, extract a stable `listing_id` (prefer a site-provided ID/UUID). If unavailable, construct a stable hash from `source_url`.
   - Collect summary fields available on the list page that aid incremental updates (e.g., updated/published dates if shown).

3) Incremental scraping
   - Maintain a local state store keyed by `listing_id` with fields: `last_seen_at`, `detail_fingerprint` (e.g., an HTML hash or ETag/Last-Modified if available), and `updated_at` if present on the page.
   - On each run, only fetch detail pages for new IDs or IDs with changed `updated_at` or mismatched `detail_fingerprint`.
   - Provide a `--full` option to force a full refresh (fetch all detail pages regardless of cache).

4) Detail extraction
   - From each listing detail page, extract:
     - Listing title
     - Job title (if separate from listing title)
     - Organization/employer name (raw and normalized)
     - All public-sector job codes ("stillingskode"), including code and title if available
     - Salary bounds per job code when stated, preserving the code-to-salary mapping
     - Salary free-text (for context; e.g., "lønn etter avtale")
     - Locations (if multiple, capture all)
     - Employment type/extent (e.g., full-time/part-time, permanent/temporary)
     - Published date, application deadline/expiry, and updated date (if present)
     - Source URL

5) Multiple job codes and salary mapping
   - If a listing has multiple job codes, the scraper must produce one output row per `listing_id` × `job_code` with the correct salary bounds for that code.
   - If a single shared salary range applies to multiple codes and no explicit per-code mapping is present, apply the shared range to each code and set `is_shared_salary = true`.
   - If salary is missing or only qualitative (e.g., "etter avtale"), set `salary_min_nok_annual` and `salary_max_nok_annual` to null and preserve the qualitative text in `salary_text`.

6) Salary parsing and normalization
   - Parse NOK annual salary ranges across common Norwegian formats, including (non-exhaustive):
     - `kr 540 000–650 000`, `kr 516 867- 573 256` (spaces around dash permitted)
     - `fra kr. 540.000 til kr. 650.000` (dot thousand separators, optional `kr.`)
     - `850.000-950.000`, `500 - 650 000` (mixed separators, optional currency tokens)
     - `kr. 725 600 til kr. 783 800`
     - Trailing punctuation tolerated: e.g., `... - 1 085 801.`
   - Extract and normalize to integers in NOK per year: `salary_min_nok_annual`, `salary_max_nok_annual`.
   - Strip non-breaking spaces and punctuation; accept `kr`, `kr.`, `NOK`.
   - If a job code is referenced alongside a salary statement, tie the parsed range to that specific code; otherwise, treat as a shared range for the listing and mark `is_shared_salary = true` for each code.
   - When only frameworks/agreements are specified (e.g., `Lønn etter Verkstedoverenskomsten for Forsvaret (VO/F) som Fagarbeider kode 5111`) with no explicit numeric range, leave min/max null, capture `salary_text` verbatim, extract `job_code = 5111`, and set optional `salary_framework` (see schema).

7) Output data model and files
   - Primary, exploded dataset (one row per `listing_id` × `job_code`):
     - `schema_version` (string, e.g., "1.0")
     - `scraped_at` (UTC ISO timestamp)
     - `source_url` (string)
     - `listing_id` (string)
     - `listing_title` (string, nullable)
     - `job_title` (string, nullable)
     - `organization_name` (string)
     - `organization_normalized` (string; lowercased, trimmed, collapsed whitespace)
     - `matched_org_keyword` (string from the configured list)
     - `match_confidence` (float 0–1)
     - `job_code` (string)
     - `job_code_title` (string, nullable)
     - `salary_min_nok_annual` (int, nullable)
     - `salary_max_nok_annual` (int, nullable)
     - `salary_text` (string, nullable)
     - `salary_framework` (string, nullable; e.g., "Verkstedoverenskomsten for Forsvaret (VO/F)")
     - `is_shared_salary` (bool)
     - `location` (string or array serialized to JSON)
     - `employment_type` (string, nullable)
     - `published_at` (date/datetime, nullable)
     - `expires_at` (date/datetime, nullable)
     - `updated_at` (date/datetime, nullable)
     - `state_filter_applied` (bool)
   - Secondary, listing-level dataset (one row per listing; optional for convenience): include listing-level data and aggregated job codes/salary info as JSON arrays.
   - File outputs per run (default paths):
     - Parquet: `data/public_state_jobs/jobs_exploded.parquet`
     - CSV: `data/public_state_jobs/jobs_exploded.csv`
     - Optional listing-level: `data/public_state_jobs/jobs_listings.parquet/csv`
   - Outputs must be deduplicated by (`listing_id`, `job_code`).

8) Deduplication key
   - Prefer the site’s `listing_id`/UUID when discoverable. If none, use a stable hash of the canonical `source_url`.
   - For the exploded dataset, the composite key is (`listing_id`, `job_code`).

9) Runtime and interfaces
   - Implement in Python 3.10+ using `requests` and an HTML parser (`selectolax` or `beautifulsoup4` + `lxml`).
   - Provide a simple CLI interface (plain script) with flags:
     - `--full`: ignore cache and fetch details for all discovered listings.
     - `--out-dir`: override output directory (default `data/public_state_jobs`).
     - `--state-path`: override cache path (default `state/seen.sqlite`).
   - Default behavior: incremental run with cache.

10) Local state for incremental runs
   - Use a lightweight SQLite store at `state/seen.sqlite` with tables:
     - `seen(listing_id TEXT PRIMARY KEY, updated_at TEXT, detail_fingerprint TEXT, last_seen_at TEXT)`
   - Update `last_seen_at` each run; update `updated_at`/`detail_fingerprint` when changes are detected.

11) Rate limits and etiquette
   - Respect robots.txt. Do not fetch disallowed paths.
   - Conservative rate: ~1 request/second average with small jitter; exponential backoff on errors.

12) Error handling and retries
   - Retry transient failures (HTTP 429/5xx, timeouts) up to 3 attempts with exponential backoff and jitter.
   - Log and skip permanently failing pages; continue processing others.

13) Logging and observability
   - INFO-level summary per run: total discovered, new, updated, unchanged, failed.
   - DEBUG mode prints selector misses and parsing fallbacks for troubleshooting.

14) Configuration
   - Provide a small configuration section in the script with:
     - Organization keyword list and synonyms, including token-based matching for prefixes like `forsvar*` and title-fallback rules when state filter is applied.
     - Fuzzy matching settings (e.g., normalized Levenshtein or token set ratio threshold ~0.8) applied after exact/starts-with heuristics.
     - CSS selectors/XPaths for list and detail pages (grouped in one place for easy maintenance).
     - Regex patterns for salary detection (covering hyphen/en dash, `kr/kr.`, space or dot thousands, optional trailing punctuation) and job-code detection (e.g., `kode\s*(\d{3,5})`).

## 5. Non-Goals (Out of Scope)

- Scraping non-state public sector (municipal/county) or private listings.
- Using a headless browser (e.g., Playwright); keep to HTTP requests + HTML parsing.
- Building a production-grade API or database; outputs remain local Parquet/CSV files.
- Guaranteeing perfect extraction for free-form salary text beyond best-effort parsing.
- Scheduling/automation (runs are manual on demand).

## 6. Design Considerations

- Favor resilient CSS selectors anchored on stable attributes or semantics; keep all selectors centralized.
- Implement organization matching with normalization (lowercasing, collapsing whitespace, removing punctuation) and synonym lists to handle common variations and abbreviations (e.g., PST, NSM).
- Produce an exploded dataset to support code-level analysis without denormalization hassles.

## 7. Technical Considerations

- Language and libraries: Python 3.10+, `requests`, `selectolax` or `beautifulsoup4`+`lxml`, `pandas`, `pyarrow`.
- If discoverable and allowed by robots, opportunistically use JSON/XHR endpoints for list pages to reduce HTML parsing and bandwidth, while keeping the fallback HTML parsing path.
- Cache: SQLite chosen for durability and simple querying; alternative JSONL cache is possible but less robust.
- Character handling: be robust to Norwegian locale (e.g., non-breaking spaces, thousand separators, diacritics).

## 8. Success Metrics

- Discovery success: ≥ 99% of target-org state listings present in the site index are discovered.
- Code parsing success: ≥ 95% of listings with job codes yield at least one code.
- Salary parsing success: ≥ 80% of listings with numeric salaries parsed into min/max values.
- Incremental efficiency: ≥ 80% reduction in detail-page fetches on subsequent runs versus first full run.
- Data quality: Duplicate rate ≤ 0.5% (by composite key), schema validity = 100%.

## 9. Open Questions

- Confirm presence and stability of a site-provided `listing_id` and updated timestamp field in list or detail pages.
- Confirm exact selectors/structure for job code and salary mapping on the detail pages for the three organizations.
- Should we include additional metadata (e.g., contact person, department, security clearance requirements) if available?
- Do we need regional/branch breakdown for organizations like Forsvaret when the employer string includes sub-units?

## 10. Acceptance Criteria

- Running the script once produces `data/public_state_jobs/jobs_exploded.parquet` and `.csv` with the specified schema.
- The dataset contains only open, state-sector listings that match the configured organization keywords.
- Listings with multiple job codes appear as multiple rows with correctly mapped salary bounds; missing salary appears as null with `salary_text` preserved.
- Re-running without `--full` performs an incremental update and fetches details only for new/updated listings.
- Logs show run summary and no unhandled exceptions.
- Test strings parse as expected (examples): `500 - 650 000`, `kr. 725 600 til kr. 783 800`, `850.000-950.000`, `kr. 516 867- 573 256`, `kr. 896 156 - 1 085 801.`; framework-only strings record `salary_text` and `job_code` (e.g., `... kode 5111`).
