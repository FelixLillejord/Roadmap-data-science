"""Centralized selectors for list and detail pages.

This module hosts structured, site-specific selectors for HTML extraction. By
keeping selectors here, the rest of the scraper can remain stable when the
site changes.

Note: The concrete values below are placeholders and should be populated when
targeting the real site. The shapes are stable for downstream use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ListSelectors:
    """Selectors for the search/list results page.

    - ``item``: CSS selector for each result card/row
    - ``link``: CSS selector to the detail link inside an item (href)
    - ``published_at`` / ``updated_at``: selectors for summary dates when present
    - ``id_candidates``: optional selector extracting data-* attributes with site IDs
    """

    item: str = ".result-item"
    link: str = "a.result-link"
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    id_candidates: Optional[str] = None


@dataclass(frozen=True)
class DetailSelectors:
    """Selectors for the detail page fields.

    Fields intentionally mirror the extraction requirements in task 5.x.
    """

    title: Optional[str] = None
    job_title: Optional[str] = None
    employer: Optional[str] = None
    locations: Optional[str] = None
    employment_type: Optional[str] = None
    extent: Optional[str] = None
    salary_text: Optional[str] = None
    job_code_blocks: Optional[str] = None
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    apply_deadline: Optional[str] = None


# Placeholders to be adjusted for the real target site
DEFAULT_LIST_SELECTORS = ListSelectors()
DEFAULT_DETAIL_SELECTORS = DetailSelectors(
    title="h1.job-title",
    employer=".employer-name",
    locations=".job-locations",
    employment_type=".employment-type",
    extent=".employment-extent",
    salary_text=".salary",
    job_code_blocks=".job-codes",
    published_at="time.published",
    updated_at="time.updated",
    apply_deadline="time.deadline",
)

