"""Salary parsing and normalization utilities.

Parses salary text to annual NOK min/max, handling ranges, separators, and
qualitative cases like "etter avtale" by returning ``(None, None)``.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

# Patterns tolerate hyphen or en dash and various thousand separators
# Accept optional currency markers like "kr" or "kr." before numbers
_NUM = r"\d{1,3}(?:[ .\u00A0\u202F\u2009]\d{3})+|\d{4,}"
_CURR_OPT = r"(?:kr\.?|nok)?\s*"
_RANGE_RE = re.compile(rf"{_CURR_OPT}(?P<lo>{_NUM})\s*[-–]\s*{_CURR_OPT}(?P<hi>{_NUM})", re.IGNORECASE)
_SINGLE_RE = re.compile(rf"{_CURR_OPT}(?P<only>{_NUM})", re.IGNORECASE)


def _to_int(num: str) -> int:
    # Remove common thousand separators: space, dot, NBSP, narrow NBSP, thin space, comma
    for ch in (" ", ".", ",", "\u00A0", "\u202F", "\u2009"):
        num = num.replace(ch, "")
    return int(num)


def parse_salary_text(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse free-text salary into (min, max) NOK annual if possible.

    Returns (None, None) when no numeric info or clearly qualitative.
    """
    if not text:
        return None, None
    t = text.lower()
    if "etter avtale" in t or "etter avtale." in t:
        return None, None
    # Heuristic: avoid treating job codes as salary by requiring currency context
    if "kr" not in t and "nok" not in t:
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
