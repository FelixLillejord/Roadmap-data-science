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


_TITLE_AFTER_CODE_RE = re.compile(r"\b(?:stillingskode|kode)\s*(?P<code>\d{3,5})\s*[-:–]\s*(?P<title>[^\n\r]+)", re.IGNORECASE)


def extract_code_titles(text: str) -> List[Tuple[str, Optional[str]]]:
    """Extract (code, maybe_title) pairs from text when code-title formatting appears.

    Falls back to (code, None) for codes without an obvious title suffix.
    """
    pairs: list[Tuple[str, Optional[str]]] = []
    codes = extract_job_codes(text)
    title_map: dict[str, Optional[str]] = {c: None for c in codes}

    for m in _TITLE_AFTER_CODE_RE.finditer(text):
        code = m.group("code")
        title = (m.group("title") or "").strip()
        if code in title_map:
            title_map[code] = title or None

    for c in codes:
        pairs.append((c, title_map.get(c)))
    return pairs

