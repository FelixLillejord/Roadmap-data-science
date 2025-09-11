"""Listing discovery utilities.

This module contains helpers for building search URLs with the state-sector
filter and "open listings only" filter, pagination support, and later the
logic to extract stable `listing_id` values.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Callable, Iterable, Iterator, Mapping, MutableMapping, Optional, Tuple
from urllib.parse import urlencode, urljoin, urlparse, parse_qsl, urlunparse

from .config import (
    PARAM_OPEN_ONLY,
    PARAM_PAGE,
    PARAM_QUERY,
    PARAM_SECTOR,
    SEARCH_BASE_URL,
    SECTOR_STATE_VALUE,
)
from .models import ListingSummary


@dataclass(frozen=True)
class SearchParams:
    """Parameters to build the search URL.

    - sector: currently supports "state" via centralized constants
    - open_only: include only open/active listings
    - page: 1-based page index for pagination
    - query: optional free-text query
    """

    sector: str = SECTOR_STATE_VALUE
    open_only: bool = True
    page: int = 1
    query: str | None = None


def build_search_url(
    base_url: str = SEARCH_BASE_URL,
    params: SearchParams | None = None,
    extra: Mapping[str, str] | None = None,
) -> str:
    """Construct a search URL with state-sector and open-only filters.

    `extra` can be used to pass through site-specific parameters without
    coupling logic here, keeping the builder generic.
    """
    p = params or SearchParams()
    q: MutableMapping[str, str] = {
        PARAM_SECTOR: p.sector,
        PARAM_OPEN_ONLY: "true" if p.open_only else "false",
        PARAM_PAGE: str(max(1, p.page)),
    }
    if p.query:
        q[PARAM_QUERY] = p.query
    if extra:
        q.update(extra)
    return urljoin(base_url, "?" + urlencode(q))


Html = str
FetchFunc = Callable[[str], Html]
HasNextFunc = Callable[[Html, int], bool]


def paginate_search(
    fetch: FetchFunc,
    *,
    params: SearchParams | None = None,
    extra: Mapping[str, str] | None = None,
    start_page: int = 1,
    max_pages: Optional[int] = None,
    has_next: Optional[HasNextFunc] = None,
) -> Iterator[Tuple[int, str, Html]]:
    """Enumerate search result pages and yield (page, url, html).

    There are two modes:
    - Bounded: pass ``max_pages`` to loop pages ``start_page..max_pages``.
    - Unbounded with sentinel: pass ``has_next`` to decide whether to continue
      after each fetched page based on its HTML.

    If neither ``max_pages`` nor ``has_next`` is given, only the first page is
    fetched to avoid accidental infinite loops.
    """
    p = params or SearchParams()
    page = max(1, start_page)

    while True:
        current_params = SearchParams(
            sector=p.sector,
            open_only=p.open_only,
            page=page,
            query=p.query,
        )
        url = build_search_url(params=current_params, extra=extra)
        html = fetch(url)
        yield page, url, html

        if max_pages is not None:
            if page >= max_pages:
                break
            page += 1
            continue

        if has_next is not None:
            if not has_next(html, page):
                break
            page += 1
            continue

        # Default: single page when bounds are unknown
        break


# TODO: Implement ID extraction and summary capture in tasks 2.3-2.4
IDCandidate = str


_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_NUMERIC_ID_RE = re.compile(r"(?<!\d)(\d{6,})(?!\d)")

_QUERY_ID_KEYS = (
    "id",
    "jobId",
    "job_id",
    "listingId",
    "listing_id",
    "uuid",
)

_TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def normalize_source_url(url: str) -> str:
    """Canonicalize a source URL for stable hashing.

    - Strips fragments
    - Sorts query parameters and drops common tracking params
    - Preserves scheme, host, path, and relevant query
    - Removes trailing slash from path (except root)
    """
    parsed = urlparse(url)
    path = parsed.path
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    query_items = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in _TRACKING_QUERY_KEYS]
    query_items.sort()
    query = urlencode(query_items)
    return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))


def _first_match(pattern: re.Pattern[str], text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(0) if m else None


def extract_site_id_from_url(url: str) -> Optional[str]:
    """Try to extract a site-provided identifier from the URL.

    Heuristics:
    - Prefer UUID-like tokens in the path or query
    - Then numeric IDs with 6+ digits in path segments
    - Then known query parameter keys like `id`, `jobId`, etc.
    """
    # UUID anywhere
    hit = _first_match(_UUID_RE, url)
    if hit:
        return hit.lower()

    # Numeric ID in path
    hit = _first_match(_NUMERIC_ID_RE, url)
    if hit:
        return hit

    # Explicit ID in query params
    parsed = urlparse(url)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in _QUERY_ID_KEYS:
        if key in qs and qs[key]:
            return qs[key]
    return None


def derive_listing_id(
    source_url: str,
    *,
    id_candidates: Optional[Tuple[IDCandidate, ...]] = None,
) -> Tuple[str, str]:
    """Return a stable listing_id and a provenance tag.

    Order of precedence:
    1) Any `id_candidates` provided by the caller (e.g., data attributes)
    2) Site ID parsed from the URL (UUID, numeric, query key)
    3) SHA1 hash of the normalized source URL

    Returns a tuple of (listing_id, provenance), where provenance is one of
    "candidate", "url_uuid", "url_numeric", "url_query", or "sha1_url".
    """
    # 1) Provided candidates
    if id_candidates:
        for c in id_candidates:
            c_str = str(c).strip()
            if c_str:
                return c_str, "candidate"

    # 2) Parse from URL with provenance detail
    parsed = urlparse(source_url)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))

    uuid_hit = _first_match(_UUID_RE, source_url)
    if uuid_hit:
        return uuid_hit.lower(), "url_uuid"

    numeric_hit = _first_match(_NUMERIC_ID_RE, parsed.path)
    if numeric_hit:
        return numeric_hit, "url_numeric"

    for key in _QUERY_ID_KEYS:
        val = qs.get(key)
        if val:
            return val, "url_query"

    # 3) Stable hash of normalized URL
    norm = normalize_source_url(source_url)
    digest = hashlib.sha1(norm.encode("utf-8")).hexdigest()
    return digest, "sha1_url"


# ---- Summary extraction from list pages ----

SummaryItem = Mapping[str, Any]
ItemExtractor = Callable[[str], Iterable[SummaryItem]]


def extract_list_summaries(
    html: str,
    *,
    item_extractor: ItemExtractor,
) -> Iterable[ListingSummary]:
    """Parse a list page's HTML into ListingSummary items.

    This function is site-agnostic and relies on ``item_extractor`` to
    understand the page structure. The extractor should yield dicts with:

    - "source_url" (str): absolute or relative URL to the detail page
    - "id_candidates" (Iterable[str], optional): ids found in data attrs
    - "published_at" (str, optional): ISO8601 publish date
    - "updated_at" (str, optional): ISO8601 update date
    """
    for item in item_extractor(html):
        source_url = str(item.get("source_url", "")).strip()
        if not source_url:
            continue
        candidates = item.get("id_candidates")
        if candidates is not None:
            try:
                id_tuple: Tuple[str, ...] = tuple(str(c) for c in candidates)  # type: ignore[arg-type]
            except Exception:
                id_tuple = tuple()
        else:
            id_tuple = tuple()

        listing_id, prov = derive_listing_id(source_url, id_candidates=id_tuple)
        yield ListingSummary(
            listing_id=listing_id,
            source_url=source_url,
            published_at=item.get("published_at"),
            updated_at=item.get("updated_at"),
            provenance=prov,
        )
