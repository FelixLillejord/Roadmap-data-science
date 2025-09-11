"""Detail page parsing utilities.

Extracts required fields from a detail-page HTML string using centralized
selectors. This module focuses on field extraction (5.2), leaving job-code and
salary parsing to later tasks.
"""

from __future__ import annotations

from typing import Iterable, Optional

from selectolax.parser import HTMLParser

from .selectors import DetailSelectors, DEFAULT_DETAIL_SELECTORS
from .org_match import normalize_org_text
from .config import get_logger


log = get_logger("detail_parse")


def _first_text(dom: HTMLParser, selector: Optional[str]) -> Optional[str]:
    if not selector:
        return None
    node = dom.css_first(selector)
    if not node:
        return None
    text = node.text(separator=" ", strip=True)
    return text or None


def _split_locations(text: Optional[str]) -> Optional[list[str]]:
    if not text:
        return None
    raw = [p.strip() for p in text.replace("/", ",").split(",")]
    vals = [p for p in raw if p]
    return vals or None


def parse_detail_fields(
    html: str,
    selectors: DetailSelectors | None = None,
) -> dict:
    """Parse core fields from a detail page.

    Returns a dict with keys:
    - title, job_title, employer_raw, employer_normalized
    - locations (list[str] or None), employment_type, extent
    - salary_text, published_at, updated_at, apply_deadline
    """
    sel = selectors or DEFAULT_DETAIL_SELECTORS
    dom = HTMLParser(html)

    title = _first_text(dom, sel.title)
    job_title = _first_text(dom, sel.job_title)
    employer_raw = _first_text(dom, sel.employer)
    employer_normalized = normalize_org_text(employer_raw or "") or None
    locations_text = _first_text(dom, sel.locations)
    locations = _split_locations(locations_text)
    employment_type = _first_text(dom, sel.employment_type)
    extent = _first_text(dom, sel.extent)
    salary_text = _first_text(dom, sel.salary_text)
    published_at = _first_text(dom, sel.published_at)
    updated_at = _first_text(dom, sel.updated_at)
    apply_deadline = _first_text(dom, sel.apply_deadline)

    return {
        "title": title,
        "job_title": job_title,
        "employer_raw": employer_raw,
        "employer_normalized": employer_normalized,
        "locations": locations,
        "employment_type": employment_type,
        "extent": extent,
        "salary_text": salary_text,
        "published_at": published_at,
        "updated_at": updated_at,
        "apply_deadline": apply_deadline,
    }

