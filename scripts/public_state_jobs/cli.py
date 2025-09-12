"""CLI entrypoint for the public sector job scraper.

Wires together discovery, state selection, detail parsing, and writers.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Callable, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from .config import configure_logging, ensure_output_dir, get_logger, DEFAULT_OUTPUT_DIR
from .discovery import (
    SearchParams,
    build_search_url,
    paginate_search,
    extract_list_summaries,
)
from .selectors import DEFAULT_LIST_SELECTORS
from .net import build_session, PoliteFetcher
from .state import (
    ensure_db,
    connect,
    select_detail_candidates,
    upsert_from_summaries,
    compute_detail_fingerprint,
    update_detail_fingerprint,
)
from .detail_parse import parse_detail_fields, parse_job_codes_and_salaries
from .models import ListingRecord, explode_listing
from .io import write_exploded_parquet, write_exploded_csv, write_listings_parquet, write_listings_csv
from .validation import compute_exploded_metrics


log = get_logger("cli")


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_item_extractor(base_url: str) -> Callable[[str], Iterable[Mapping[str, object]]]:
    sel = DEFAULT_LIST_SELECTORS

    def extractor(html: str) -> Iterable[Mapping[str, object]]:
        dom = HTMLParser(html)
        for item in dom.css(sel.item):
            link = item.css_first(sel.link) if sel.link else None
            href = link.attributes.get("href") if link else None
            if not href:
                continue
            source_url = urljoin(base_url, href)
            pub = item.css_first(sel.published_at).text(strip=True) if sel.published_at and item.css_first(sel.published_at) else None
            upd = item.css_first(sel.updated_at).text(strip=True) if sel.updated_at and item.css_first(sel.updated_at) else None
            # Extract common data-* attributes that may carry IDs
            id_candidates = []
            if sel.id_candidates:
                for n in item.css(sel.id_candidates):
                    for k, v in n.attributes.items():
                        if k.startswith("data-") and v:
                            id_candidates.append(v)
            yield {
                "source_url": source_url,
                "published_at": pub,
                "updated_at": upd,
                "id_candidates": tuple(id_candidates) if id_candidates else None,
            }

    return extractor


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="public-state-jobs")
    p.add_argument("--full", action="store_true", help="Fetch details for all discovered listings, ignoring state")
    p.add_argument("--debug", action="store_true", help="Enable DEBUG logging")
    p.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for datasets and state DB")
    p.add_argument("--base-url", default="https://example.invalid", help="Base URL for search/discovery (site-specific)")
    p.add_argument("--max-pages", type=int, default=1, help="Maximum number of result pages to crawl")
    p.add_argument("--delay", type=float, default=1.0, help="Per-host politeness delay in seconds")
    p.add_argument("--no-robots", action="store_true", help="Do not respect robots.txt (not recommended)")
    p.add_argument("--no-parquet", action="store_true", help="Skip writing Parquet output")
    p.add_argument("--no-csv", action="store_true", help="Skip writing CSV output")
    p.add_argument("--validate", action="store_true", help="Compute and log parsing metrics for exploded rows")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    configure_logging(debug=args.debug)

    out_dir = ensure_output_dir(args.out_dir)
    db_path = ensure_db(out_dir)
    log.info("output_dir: %s | state_db: %s", out_dir, db_path)

    # Networking utilities
    session = build_session()
    fetcher = PoliteFetcher(session, delay_seconds=args.delay, respect_robots=not args.no_robots)

    # Build discovery and extract summaries
    seen_at = _now_utc_iso()
    item_extractor = make_item_extractor(args.base_url)

    def fetch_html(url: str) -> str:
        resp = fetcher.get(url)
        if resp is None:
            return ""
        return resp.text

    # For now, use the configured base URL and default params
    params = SearchParams()
    discovered_pages = 0
    summaries = []
    for page, url, html in paginate_search(fetch_html, params=params, max_pages=args.max_pages):
        discovered_pages += 1
        if not html:
            log.warning("discovery_page_failed: %s", url)
            continue
        page_summaries = list(extract_list_summaries(html, item_extractor=item_extractor))
        summaries.extend(page_summaries)
    log.info("discovered_pages=%d summaries=%d", discovered_pages, len(summaries))

    # State selection BEFORE upsert
    conn = connect(db_path)
    candidates = select_detail_candidates(conn, summaries, full=args.full)
    # Upsert discovery summaries
    upsert_from_summaries(conn, summaries, seen_at=seen_at)
    # Compute discovery summary counts
    reason_counts = {}
    for _id, reason in candidates:
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    new_count = reason_counts.get("new", 0)
    updated_count = reason_counts.get("updated_at_changed", 0)
    pending_fp_count = reason_counts.get("no_fingerprint", 0)
    full_count = reason_counts.get("full", 0)
    unchanged = max(0, len(summaries) - (new_count + updated_count + pending_fp_count + full_count))
    log.info(
        "discovery_summary: discovered=%d new=%d updated=%d unchanged=%d pending_fp=%d candidates=%d",
        len(summaries),
        new_count,
        updated_count,
        unchanged,
        pending_fp_count,
        len(candidates),
    )

    # Fetch detail pages for candidates
    exploded_rows = []
    listing_records: List[ListingRecord] = []
    failures = 0
    for listing_id, reason in candidates:
        # find source_url from summaries
        src = next((s.source_url for s in summaries if s.listing_id == listing_id), None)
        if not src:
            log.warning("missing_source_url_for_candidate: %s", listing_id)
            failures += 1
            continue
        resp = fetcher.get(src)
        if resp is None:
            log.warning("detail_fetch_failed: %s", src)
            failures += 1
            continue
        html = resp.text
        # Update fingerprint
        fp = compute_detail_fingerprint(html)
        update_detail_fingerprint(conn, listing_id=listing_id, detail_fingerprint=fp)
        # Parse fields and codes
        fields = parse_detail_fields(html, source_url=src)
        codes = parse_job_codes_and_salaries(html)
        record = ListingRecord(
            listing_id=listing_id,
            source_url=src,
            title=fields.get("title"),
            job_title=fields.get("job_title"),
            employer_raw=fields.get("employer_raw"),
            employer_normalized=fields.get("employer_normalized"),
            locations=fields.get("locations"),
            employment_type=fields.get("employment_type"),
            extent=fields.get("extent"),
            salary_text=fields.get("salary_text"),
            published_at=fields.get("published_at"),
            updated_at=fields.get("updated_at"),
            apply_deadline=fields.get("apply_deadline"),
            scraped_at=seen_at,
        )
        listing_records.append(record)
        exploded_rows.extend(
            explode_listing(
                listing_id=listing_id,
                source_url=src,
                fields=fields,
                code_rows=codes,
                scraped_at=seen_at,
            )
        )

    # Write outputs
    if not args.no_parquet:
        write_exploded_parquet([r.to_dict() for r in exploded_rows], out_dir=out_dir, scraped_at=seen_at)
        write_listings_parquet([r.to_dict() for r in listing_records], out_dir=out_dir, scraped_at=seen_at)
    if not args.no_csv:
        write_exploded_csv([r.to_dict() for r in exploded_rows], out_dir=out_dir, scraped_at=seen_at)
        write_listings_csv([r.to_dict() for r in listing_records], out_dir=out_dir, scraped_at=seen_at)

    # Optional validation metrics on in-memory rows
    if args.validate:
        metrics = compute_exploded_metrics([r.to_dict() for r in exploded_rows])
        log.info(
            "metrics: total=%d codes_present=%d(%.1f%%) salary_any=%d(%.1f%%) schema_ok=%s",
            metrics["total_rows"],
            metrics["codes_present"],
            metrics["codes_pct"] * 100.0,
            metrics["salary_any_present"],
            metrics["salary_any_pct"] * 100.0,
            metrics["schema_ok"],
        )

    # Summary and exit code
    log.info(
        "run_summary: pages=%d discovered=%d new=%d updated=%d unchanged=%d failures=%d rows=%d",
        discovered_pages,
        len(summaries),
        new_count,
        updated_count,
        unchanged,
        failures,
        len(exploded_rows),
    )
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
