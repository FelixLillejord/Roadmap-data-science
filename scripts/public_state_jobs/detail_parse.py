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
from .jobcode_parse import extract_code_titles
from .salary_parse import parse_salary_text


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


def parse_job_codes_and_salaries(
    html: str,
    selectors: DetailSelectors | None = None,
) -> list[dict]:
    """Extract job codes and per-code salary ranges from detail HTML.

    Returns a list of dicts with keys: job_code, job_title, salary_min, salary_max, salary_text.
    """
    sel = selectors or DEFAULT_DETAIL_SELECTORS
    dom = HTMLParser(html)
    blocks = []
    if sel.job_code_blocks:
        blocks = [n.text(separator=" ", strip=True) for n in dom.css(sel.job_code_blocks)]
    if not blocks:
        # fallback: consider whole page text (coarse)
        blocks = [dom.text(separator=" ", strip=True)]

    results: list[dict] = []
    global_salary_text = _first_text(dom, sel.salary_text)
    for block in blocks:
        pairs = extract_code_titles(block)
        if not pairs:
            continue
        # Try salary in the same block; else fallback to global
        s_min, s_max = parse_salary_text(block)
        if s_min is None and s_max is None and global_salary_text:
            s_min, s_max = parse_salary_text(global_salary_text)
        for code, maybe_title in pairs:
            results.append(
                {
                    "job_code": code,
                    "job_title": maybe_title,
                    "salary_min": s_min,
                    "salary_max": s_max,
                    "salary_text": global_salary_text or block,
                }
            )
    return results
