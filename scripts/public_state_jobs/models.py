"""Dataclass models for listing-level and exploded row schemas."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any


@dataclass(frozen=True)
class ListingSummary:
    """Summary information captured from list pages.

    Times are represented as ISO 8601 strings (UTC) if available.
    """

    listing_id: str
    source_url: str
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    provenance: Optional[str] = None


@dataclass(frozen=True)
class ListingRecord:
    """Listing-level normalized record parsed from a detail page.

    The fields reflect outputs from detail parsing (task 5.x). Timestamps are
    ISO8601 strings (UTC) where present. ``locations`` is a list of strings or
    None when not specified.
    """

    listing_id: str
    source_url: str

    title: Optional[str] = None
    job_title: Optional[str] = None
    employer_raw: Optional[str] = None
    employer_normalized: Optional[str] = None
    locations: Optional[List[str]] = None
    employment_type: Optional[str] = None
    extent: Optional[str] = None
    salary_text: Optional[str] = None

    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    apply_deadline: Optional[str] = None

    scraped_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExplodedJobRow:
    """Exploded row schema: one row per (listing_id × job_code)."""

    listing_id: str
    job_code: str
    job_title: Optional[str]

    employer_normalized: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_text: Optional[str]
    is_shared_salary: bool

    published_at: Optional[str]
    updated_at: Optional[str]
    apply_deadline: Optional[str]
    source_url: str

    scraped_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
