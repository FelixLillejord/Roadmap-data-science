"""Dataclass models for listing-level and exploded row schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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

