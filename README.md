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

- Selectors: `scripts/public_state_jobs/selectors.py` (`DEFAULT_*_SELECTORS`)
- Discovery params: `scripts/public_state_jobs/config.py`
- Org matching knobs: `scripts/public_state_jobs/org_match.py` (`fuzzy_threshold` param to `match_org`)
- Salary parsing: `scripts/public_state_jobs/salary_parse.py` (≥6-digit inference, avoids job-code collisions)

## Development

- Run tests: `pytest -q`
- Linting: not configured; please keep changes minimal and consistent
- Update task list: see `tasks/tasks-rsd-public-sector-job-scraper.md`

## Caution

- Selectors are placeholders; adjust `DEFAULT_LIST_SELECTORS` and `DEFAULT_DETAIL_SELECTORS` to the real site
- Respect `robots.txt` and the target site’s terms of use

