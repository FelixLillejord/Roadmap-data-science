# Public Sector Job Scraper (RSD)

A modular Python scraper for Norwegian public sector job listings with:
- Configurable discovery + pagination
- Incremental state (SQLite) with change detection
- Robust parsing of orgs, job codes, and salaries
- Exploded outputs to Parquet/CSV with stable schema
- CLI runner with polite networking, retries, and summaries

## Setup

1) Python 3.12+ recommended
2) Install dependencies:

```
pip3 install -r requirements.txt
```

## CLI Usage

Run a small crawl (site-specific base URL required):

```
python -m scripts.public_state_jobs.cli \
  --base-url https://<target-site>/search \
  --max-pages 1 \
  --out-dir data/public_state_jobs
```

Common flags:
- `--full`: Fetch details for all discovered listings, ignoring state
- `--debug`: Enable DEBUG logging
- `--max-pages N`: How many result pages to read (default 1)
- `--delay S`: Per-host politeness delay (seconds, default 1.0)
- `--no-robots`: Do not respect robots.txt (not recommended)
- `--no-parquet` / `--no-csv`: Control output formats

Outputs are written under `data/public_state_jobs/` by default, with a state DB:
- `public_state_jobs.sqlite3` (incremental state)
- `jobs_exploded.parquet` / `jobs_exploded.csv` (exploded dataset)
- `jobs_listings.parquet` / `jobs_listings.csv` (optional listing-level)

## Output Schema (Exploded Rows)

Each row corresponds to `listing_id × job_code`.

Columns:
- `listing_id`: string
- `job_code`: string
- `job_title`: string (optional)
- `employer_normalized`: string (normalized org/employer)
- `salary_min` / `salary_max`: Int64 (nullable annual NOK)
- `salary_text`: string (source text)
- `is_shared_salary`: boolean (True when taken from a global listing salary)
- `published_at` / `updated_at` / `apply_deadline`: string (ISO8601 UTC)
- `source_url`: string
- `scraped_at`: string (ISO8601 UTC)

See `scripts/public_state_jobs/models.py` for `EXPLODED_COLUMNS` and dtypes.

## How It Works (Brief)

- Discovery (`discovery.py`):
  - Build search URLs with state-sector and open-only filters
  - Paginate result pages
  - Extract `listing_id` via candidates/URL or stable hash
  - Collect list-page summaries (published/updated, source_url)
- State (`state.py`):
  - SQLite schema for incremental runs
  - Upsert summaries, compute detail fingerprints, select candidates (new/updated/no_fingerprint)
- Detail parsing (`detail_parse.py`):
  - Extract core fields (title, employer, locations, etc.) and dates
  - Parse job codes and per-code salary ranges (handles `kr`, dot/space thousand separators, en dash)
- Org matching (`org_match.py`):
  - Normalization, synonyms (PST/NSM), Forsvar* prefix, optional fuzzy
- Output (`io.py`):
  - Writers ensure stable order and pandas nullable dtypes

## Configuration Notes

- Selectors (centralized): `scripts/public_state_jobs/selectors.py`
  - `DEFAULT_LIST_SELECTORS`: `.item`, `.link`, optional `.published_at`/`.updated_at`, optional `id_candidates` selector
  - `DEFAULT_DETAIL_SELECTORS`: `title`, `employer`, `locations`, `employment_type`, `extent`, `salary_text`, `job_code_blocks`, `published_at`, `updated_at`, `apply_deadline`
  - Adjust these to the target site’s DOM; the rest of the pipeline remains stable

- Discovery/config: `scripts/public_state_jobs/config.py` and `discovery.py`
  - URL builder constants: `SEARCH_BASE_URL`, `PARAM_SECTOR`, `PARAM_OPEN_ONLY`, `PARAM_PAGE`, `PARAM_QUERY`
  - `build_search_url(params, extra)`: pass site‑specific params via `extra`
  - CLI flags: `--base-url`, `--max-pages`

- Org matching: `scripts/public_state_jobs/org_match.py`
  - Canonical tags: `ORG_FORSVAR`, `ORG_PST`, `ORG_NSM`
  - Synonyms map: `ORG_SYNONYMS` and prefix rule `TOKEN_PREFIX_FORSVAR`
  - Matching API: `match_org(employer, title, state_sector_applied=False, fuzzy_threshold=None)`
    - Set `fuzzy_threshold` (e.g., `0.8`) to enable optional fuzzy matching

- Salary parsing: `scripts/public_state_jobs/salary_parse.py`
  - ≥6‑digit inference: avoids collisions with 3–5 digit job codes
  - Handles ranges with hyphen/en dash; thousand separators (space, dot, comma, NBSP variants)
  - API: `parse_salary_text(text) -> (min|max|None)`, returns `(None, None)` for qualitative text (e.g., “etter avtale”)

- Networking: `scripts/public_state_jobs/net.py`
  - Session: `build_session(user_agent=None, headers=None)`
  - Retries: `get_with_retries(..., max_attempts=3, backoff_base=0.5, backoff_factor=2.0, jitter_max=0.25)`
  - Politeness/robots: `PoliteFetcher(session, delay_seconds=1.0, respect_robots=True)`; CLI `--delay`, `--no-robots`

- State DB: `scripts/public_state_jobs/state.py`
  - File name: `public_state_jobs.sqlite3` (created under `--out-dir`)
  - Core functions: `ensure_db`, `upsert_from_summaries`, `select_detail_candidates`, `compute_detail_fingerprint`

- Output: `scripts/public_state_jobs/io.py`
  - Exploded writers: `write_exploded_parquet/csv(rows, out_dir=..., filename=..., scraped_at=...)`
  - Optional listing‑level writers: `write_listings_parquet/csv(...)`
  - CLI flags: `--no-parquet`, `--no-csv`; default output dir `data/public_state_jobs/`

## Development

- Run tests: `pytest -q`
- Linting: not configured; please keep changes minimal and consistent
- Update task list: see `tasks/tasks-rsd-public-sector-job-scraper.md`

## Caution

- Selectors are placeholders; adjust `DEFAULT_LIST_SELECTORS` and `DEFAULT_DETAIL_SELECTORS` to the real site
- Respect `robots.txt` and the target site’s terms of use
