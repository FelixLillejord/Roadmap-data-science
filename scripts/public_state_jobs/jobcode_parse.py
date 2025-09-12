"""Job code extraction and mapping utilities.

Extracts job codes (e.g., patterns like ``kode 1234`` or ``stillingskode 1234``)
and nearby titles when present.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

CODE_PATTERNS = (
    r"(?:stillingskode|kode)\s*(?P<code>\d{3,5})\b",
    r"\b(?P<code>\d{3,5})\b",
)

_CODE_RES = [re.compile(p, flags=re.IGNORECASE) for p in CODE_PATTERNS]
_KEYED_CODE_RE = re.compile(r"(?:stillingskode|kode)\s*(?P<code>\d{3,5})\b", re.IGNORECASE)


def extract_job_codes(text: str) -> List[str]:
    """Extract distinct job codes from free text.

    Returns codes as strings preserving leading zeros if present.
    """
    seen: set[str] = set()
    for rx in _CODE_RES:
        for m in rx.finditer(text):
            code = m.group("code")
            if code:
                seen.add(code)
    return sorted(seen)


_TITLE_AFTER_CODE_RE = re.compile(
    r"\b(?:stillingskode|kode)\s*(?P<code>\d{3,5})\s*[-:–]\s*(?P<title>.*?)(?=(?:\s*(?:stillingskode|kode)\s*\d{3,5}\b|$))",
    re.IGNORECASE | re.DOTALL,
)


def extract_code_titles(text: str) -> List[Tuple[str, Optional[str]]]:
    """Extract (code, maybe_title) pairs from text when code-title formatting appears.

    Falls back to (code, None) for codes without an obvious title suffix.
    """
    # Prefer explicit code-title matches
    pairs: list[Tuple[str, Optional[str]]] = []
    seen: set[str] = set()
    for m in _TITLE_AFTER_CODE_RE.finditer(text):
        code = m.group("code")
        title = (m.group("title") or "").strip()
        if code not in seen:
            pairs.append((code, title or None))
            seen.add(code)
    if pairs:
        return pairs

    # Fallback: codes preceded by known keywords, without titles
    codes = []
    for m in _KEYED_CODE_RE.finditer(text):
        code = m.group("code")
        if code not in seen:
            codes.append(code)
            seen.add(code)
    return [(c, None) for c in codes]
