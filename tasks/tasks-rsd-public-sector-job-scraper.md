## Relevant Files

- `scripts/public_state_jobs/cli.py` - CLI entrypoint handling args (`--full`, `--debug`, `--out-dir`).
- `scripts/public_state_jobs/config.py` - Centralized configuration (org keywords, selectors, regex patterns, retry settings).
  Includes logging setup (INFO default, DEBUG toggle).
  Provides default output dir and ensure helper.
- `scripts/public_state_jobs/selectors.py` - CSS/XPath selectors for list and detail pages grouped in one place.
- `scripts/public_state_jobs/org_match.py` - Normalization + fuzzy/heuristic organization matching utilities.
- `scripts/public_state_jobs/salary_parse.py` - Salary parsing and normalization to annual NOK min/max.
- `scripts/public_state_jobs/jobcode_parse.py` - Job code extraction (e.g., `kode\\s*(\\d{3,5})`) and mapping to titles if present.
- `scripts/public_state_jobs/discovery.py` - Listing discovery, filters (state-sector), pagination, stable `listing_id` extraction.
  Adds URL builder with state-sector and open-only filters (2.1).
- `scripts/public_state_jobs/detail_parse.py` - Detail page fetch + extraction of required fields; per-code salary mapping.
- `scripts/public_state_jobs/state.py` - SQLite state store for incremental scraping, fingerprints, and change detection.
- `scripts/public_state_jobs/models.py` - Dataclass models for listing-level and exploded row schemas.
- `scripts/public_state_jobs/io.py` - Writers for Parquet/CSV and optional listing-level outputs.
- `scripts/public_state_jobs/net.py` - Requests session, headers, robots check, rate limiting, retries with backoff/jitter.
- `scripts/public_state_jobs/__init__.py` - Package initializer, version placeholder.
- `requirements.txt` - Project dependencies for scraping, parsing, IO, and tests.
- `tests/public_state_jobs/test_salary_parse.py` - Unit tests for salary parsing examples from the RSD.
- `tests/public_state_jobs/test_jobcode_parse.py` - Unit tests for job code extraction and mapping.
- `tests/public_state_jobs/test_org_match.py` - Unit tests for normalization and matching rules (Forsvar*, PST, NSM).
- `tests/public_state_jobs/test_discovery.py` - Tests for URL building, pagination logic, `listing_id` stability (with fixtures).
- `tests/public_state_jobs/test_detail_parse.py` - Tests for field extraction and exploded mapping on representative HTML snippets.
- `data/public_state_jobs/` - Output directory for `jobs_exploded.parquet/csv` and optional listing-level outputs.

### Notes

- Unit tests colocated under `tests/` using `pytest`. Run with `pytest -q`.
- Keep selectors and regex patterns centralized for maintenance in `selectors.py` and `config.py`.
- Use `python -m scripts.public_state_jobs.cli` to run the scraper locally.

## Tasks

 - [x] 1.0 Project setup and structure
  - [x] 1.1 Create package skeleton under `scripts/public_state_jobs/` with modules listed in Relevant Files.
  - [x] 1.2 Add `requirements.txt` (requests, selectolax or bs4+lxml, pandas, pyarrow, charset-normalizer, rapidfuzz [optional], pytest).
  - [x] 1.3 Initialize basic logging config (INFO default, DEBUG toggle).
  - [x] 1.4 Prepare `data/public_state_jobs/` output directory (ensure exists at runtime).
  - [x] 1.5 Configure `pytest.ini` and minimal test scaffolding.

- [x] 2.0 Listing discovery with state-sector filtering and pagination
  - [x] 2.1 Document search URL and query params; add builder to apply state-sector filter and open-listings filter.
  - [x] 2.2 Implement pagination loop to enumerate all result pages.
  - [x] 2.3 Extract `listing_id` (prefer site ID/UUID); else derive stable hash from `source_url`.
  - [x] 2.4 Capture summary fields from list pages (e.g., updated/published dates) when available.
  - [x] 2.5 Unit tests for pagination and ID stability using HTML fixtures.

- [x] 3.0 Organization keyword matching and normalization rules
  - [x] 3.1 Implement normalization: lowercase, whitespace collapse, punctuation removal, accent-insensitive.
  - [x] 3.2 Define keyword sets and synonyms: `Forsvar*` token prefix, `PST`/`Politiets sikkerhetstjeneste`, `NSM`/`Nasjonal sikkerhetsmyndighet`.
  - [x] 3.3 Implement matching priority: employer field first; title token fallback for `forsvar*` when state filter is applied.
  - [x] 3.4 Add optional fuzzy threshold (e.g., token set ratio ~0.8) after exact/startswith heuristics.
  - [x] 3.5 Unit tests covering typical and edge variants.

- [x] 4.0 Incremental scraping state store (SQLite) and change detection
  - [x] 4.1 Define SQLite schema: `listing_id` PK, `last_seen_at`, `detail_fingerprint`, `updated_at`.
  - [x] 4.2 Implement upsert on discovery to update `last_seen_at` and record summary metadata.
  - [x] 4.3 Compute `detail_fingerprint` (e.g., HTML hash) and track for change detection.
  - [x] 4.4 Select detail pages to fetch: new IDs, changed `updated_at`, or mismatched fingerprints; support `--full` override.
  - [x] 4.5 Unit tests for change selection logic using an in-memory SQLite DB.

- [x] 5.0 Detail page parsing for required fields
  - [x] 5.1 Centralize selectors for detail fields in `selectors.py`.
  - [x] 5.2 Extract: listing title, job title (if separate), employer (raw/normalized), locations, employment type/extent.
  - [x] 5.3 Extract all job codes and titles; parse per-code salary bounds and `salary_text`.
  - [x] 5.4 Extract dates: published, updated (if present), application deadline/expiry; capture `source_url`.
  - [x] 5.5 Tolerate missing fields; log selector misses in DEBUG; return structured defaults.
  - [x] 5.6 Unit tests with representative HTML snippets for all three orgs.

- [x] 6.0 Salary and job code parsing utilities
  - [x] 6.1 Implement regex patterns covering hyphen/en dash, `kr/kr.`, spaces/dots as thousand separators, optional punctuation.
  - [x] 6.2 Normalize to integers (NOK annual) and handle ranges; set nulls when qualitative only ("etter avtale").
  - [x] 6.3 Implement job code regex `kode\\s*(\\d{3,5})` with title capture when nearby.
  - [x] 6.4 Map shared salary ranges across multiple codes with `is_shared_salary = true` when no explicit mapping.
  - [x] 6.5 Unit tests using examples from the RSD acceptance criteria.

- [ ] 7.0 Exploded data model and output schema
  - [x] 7.1 Define dataclasses/models for listing-level and exploded rows (`listing_id` × `job_code`).
  - [x] 7.2 Implement transform to explode per job code with correct salary mapping.
  - [x] 7.3 Validate schema consistency and dtypes across runs.

- [ ] 8.0 Writers for Parquet and CSV outputs
  - [x] 8.1 Implement writers for `jobs_exploded.parquet` and `jobs_exploded.csv` under `data/public_state_jobs/`.
  - [x] 8.2 Ensure stable column order and types; handle timezone-aware timestamps (UTC ISO for `scraped_at`).
  - [x] 8.3 Optional: emit listing-level dataset for debugging.

- [ ] 9.0 Networking: rate limiting, retries, headers, robots check
  - [x] 9.1 Create session with headers and reasonable user-agent.
  - [x] 9.2 Implement retries with exponential backoff and jitter for 429/5xx/timeouts (max 3 attempts).
  - [x] 9.3 Add politeness delay and respect `robots.txt` if accessible; avoid fetching blocked paths.
  - [x] 9.4 Log and skip permanently failing pages; continue processing others.

- [ ] 10.0 CLI interface and configuration options (e.g., --full, --debug)
  - [x] 10.1 Implement `argparse` CLI with `--full`, `--debug`, `--out-dir`.
  - [x] 10.2 Wire CLI to discovery, incremental selection, detail parsing, and writers.
  - [x] 10.3 Add exit codes and error messages for common failures.

- [ ] 11.0 Logging and run summaries
  - [ ] 11.1 Implement INFO-level summary: discovered, new, updated, unchanged, failed.
  - [ ] 11.2 Add DEBUG logs for selector misses and parsing fallbacks.

- [ ] 12.0 Unit tests for parsing and core logic
  - [ ] 12.1 Add fixtures for representative list/detail HTML.
  - [ ] 12.2 Tests for org matching, salary parsing, job code extraction, and explosion logic.
  - [ ] 12.3 Basic integration test for a small mocked crawl.

- [ ] 13.0 Validation against success metrics
  - [ ] 13.1 Implement a validation helper to compute parsing success on a sample (codes/salaries presence, schema validity).
  - [ ] 13.2 Measure incremental efficiency on second run (detail fetch reduction) with cached state.

- [ ] 14.0 Documentation: usage, config, maintenance notes
  - [ ] 14.1 Write README with setup, CLI usage, and output schema.
  - [ ] 14.2 Document configuration knobs (keywords, fuzzy threshold, selectors, regexes).
  - [ ] 14.3 Add maintenance tips for updating selectors and tests when site changes.
