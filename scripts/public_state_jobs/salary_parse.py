"""Salary parsing and normalization utilities.

Parses salary text to annual NOK min/max, handling ranges, separators, and
qualitative cases like "etter avtale" by returning ``(None, None)``.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

# Patterns tolerate hyphen or en dash and various thousand separators
_NUM = r"\d{1,3}(?:[ .]\d{3})+|\d{4,}"
_RANGE_RE = re.compile(rf"(?P<lo>{_NUM})\s*[-–]\s*(?P<hi>{_NUM})")
_SINGLE_RE = re.compile(rf"(?P<only>{_NUM})")


def _to_int(num: str) -> int:
    return int(num.replace(" ", "").replace(".", ""))


def parse_salary_text(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse free-text salary into (min, max) NOK annual if possible.

    Returns (None, None) when no numeric info or clearly qualitative.
    """
    if not text:
        return None, None
    t = text.lower()
    if "etter avtale" in t or "etter avtale." in t:
        return None, None

    m = _RANGE_RE.search(t)
    if m:
        lo = _to_int(m.group("lo"))
        hi = _to_int(m.group("hi"))
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi

    m = _SINGLE_RE.search(t)
    if m:
        val = _to_int(m.group("only"))
        return val, val

    return None, None

