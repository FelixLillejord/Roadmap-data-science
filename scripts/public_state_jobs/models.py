"""Dataclass models for listing-level and exploded row schemas."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Iterable
import pandas as pd
from pandas import DataFrame


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


def explode_listing(
    *,
    listing_id: str,
    source_url: str,
    fields: Dict[str, Any],
    code_rows: Iterable[Dict[str, Any]],
    scraped_at: Optional[str] = None,
) -> List[ExplodedJobRow]:
    """Explode a listing into per-job-code rows using parsed fields and codes.

    - ``fields`` should come from parse_detail_fields
    - ``code_rows`` should come from parse_job_codes_and_salaries
    """
    rows: List[ExplodedJobRow] = []
    for cr in code_rows:
        rows.append(
            ExplodedJobRow(
                listing_id=listing_id,
                job_code=str(cr.get("job_code")),
                job_title=cr.get("job_title"),
                employer_normalized=fields.get("employer_normalized"),
                salary_min=cr.get("salary_min"),
                salary_max=cr.get("salary_max"),
                salary_text=cr.get("salary_text"),
                is_shared_salary=bool(cr.get("is_shared_salary", False)),
                published_at=fields.get("published_at"),
                updated_at=fields.get("updated_at"),
                apply_deadline=fields.get("apply_deadline"),
                source_url=source_url,
                scraped_at=scraped_at,
            )
        )
    return rows


# ---- Schema utilities for exploded rows (7.3) ----

EXPLODED_COLUMNS: List[str] = [
    "listing_id",
    "job_code",
    "job_title",
    "employer_normalized",
    "salary_min",
    "salary_max",
    "salary_text",
    "is_shared_salary",
    "published_at",
    "updated_at",
    "apply_deadline",
    "source_url",
    "scraped_at",
]

EXPLODED_DTYPES: Dict[str, Any] = {
    "listing_id": "string",
    "job_code": "string",
    "job_title": "string",
    "employer_normalized": "string",
    "salary_min": "Int64",
    "salary_max": "Int64",
    "salary_text": "string",
    "is_shared_salary": "boolean",
    "published_at": "string",
    "updated_at": "string",
    "apply_deadline": "string",
    "source_url": "string",
    "scraped_at": "string",
}


def to_exploded_dataframe(rows: Iterable[Dict[str, Any] | ExplodedJobRow]) -> DataFrame:
    """Create a pandas DataFrame with stable column order and dtypes.

    Accepts dictionaries or ExplodedJobRow objects. Missing columns are added
    with NA values and dtypes are coerced to pandas nullable types.
    """
    dict_rows: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, ExplodedJobRow):
            dict_rows.append(r.to_dict())
        else:
            dict_rows.append(dict(r))

    df = pd.DataFrame(dict_rows)
    # Add any missing columns
    for col in EXPLODED_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    # Reorder
    df = df[EXPLODED_COLUMNS]

    # Coerce dtypes
    for col, dtype in EXPLODED_DTYPES.items():
        if dtype == "Int64":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif dtype == "boolean":
            df[col] = df[col].astype("boolean")
        elif dtype == "string":
            df[col] = df[col].astype("string")
        else:
            df[col] = df[col].astype(dtype)
    return df
