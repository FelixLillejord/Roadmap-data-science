"""Organization normalization and keyword matching utilities.

Implements normalization, synonym handling, and later heuristic/fuzzy matching
for Forsvar*, PST, and NSM.
"""

from __future__ import annotations

import re
import unicodedata as _ud
from typing import Final

__all__ = [
    "normalize_org_text",
    "ORG_FORSVAR",
    "ORG_PST",
    "ORG_NSM",
    "TOKEN_PREFIX_FORSVAR",
    "ORG_SYNONYMS",
    "tokenize_normalized",
    "match_org",
]


_WS_RE: Final[re.Pattern[str]] = re.compile(r"\s+")


def _strip_accents(text: str) -> str:
    """Remove diacritics, making text accent-insensitive.

    Uses NFKD normalization and drops combining marks.
    """
    decomposed = _ud.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if _ud.category(ch) != "Mn")


def _remove_punct_and_symbols(text: str) -> str:
    """Replace punctuation/symbols with spaces; keep letters, digits, whitespace."""
    out_chars = []
    for ch in text:
        cat = _ud.category(ch)
        if ch.isspace() or ch.isalnum():
            out_chars.append(ch)
        elif cat.startswith("P") or cat.startswith("S"):
            out_chars.append(" ")
        else:
            # Other categories (e.g., control) -> space
            out_chars.append(" ")
    return "".join(out_chars)


def normalize_org_text(text: str) -> str:
    """Normalize organization text for robust matching.

    Steps:
    - Strip accents/diacritics (accent-insensitive)
    - Lowercase
    - Replace punctuation/symbols with spaces
    - Collapse whitespace to single spaces and trim
    """
    if text is None:
        return ""
    t = _strip_accents(str(text))
    t = t.lower()
    # Norwegian-specific transliterations for better accent-insensitivity
    t = (
        t.replace("ø", "o")
        .replace("æ", "ae")
        .replace("å", "a")
    )
    t = _remove_punct_and_symbols(t)
    t = _WS_RE.sub(" ", t).strip()
    return t


# --- Keyword sets and synonyms (3.2) ---

# Canonical organization tags
ORG_FORSVAR: Final[str] = "forsvar"
ORG_PST: Final[str] = "pst"
ORG_NSM: Final[str] = "nsm"

# Token prefix rule for Forsvar*
TOKEN_PREFIX_FORSVAR: Final[str] = "forsvar"

# Synonyms map (normalized forms)
ORG_SYNONYMS: Final[dict[str, set[str]]] = {
    ORG_PST: {"pst", "politiets sikkerhetstjeneste"},
    ORG_NSM: {"nsm", "nasjonal sikkerhetsmyndighet"},
}


def tokenize_normalized(text: str) -> list[str]:
    """Normalize and split into tokens by spaces."""
    norm = normalize_org_text(text)
    return [tok for tok in norm.split(" ") if tok]


def _contains_any_phrase(haystack_norm: str, phrases_norm: set[str]) -> bool:
    for p in phrases_norm:
        if p and p in haystack_norm:
            return True
    return False


def _has_forsvar_prefix(tokens: list[str]) -> bool:
    return any(t.startswith(TOKEN_PREFIX_FORSVAR) for t in tokens)


try:
    # Prefer rapidfuzz if available
    from rapidfuzz.fuzz import token_set_ratio as _rf_token_set_ratio  # type: ignore
except Exception:  # pragma: no cover - safe fallback when rapidfuzz missing
    _rf_token_set_ratio = None  # type: ignore


def _token_set_ratio(a: str, b: str) -> float:
    """Return a 0..100 token-set similarity score.

    Uses rapidfuzz if installed, otherwise a simple Jaccard-like token overlap
    scaled to 0..100 as a lightweight fallback.
    """
    if _rf_token_set_ratio is not None:
        try:
            return float(_rf_token_set_ratio(a, b))
        except Exception:
            pass
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return 100.0 * inter / union


def _best_fuzzy(text_norm: str, phrases_norm: set[str]) -> float:
    return max((_token_set_ratio(text_norm, p) for p in phrases_norm), default=0.0)


def match_org(
    employer: str | None,
    title: str | None,
    *,
    state_sector_applied: bool = False,
    fuzzy_threshold: float | None = None,
) -> tuple[str | None, str]:
    """Match listing to an organization with priority rules.

    Priority:
    1) Employer field exact/prefix/synonyms
    2) If not matched and state-sector filter is applied: fallback to title
       tokens for Forsvar* prefix only.

    Returns (org_tag, provenance). org_tag is one of ORG_FORSVAR/ORG_PST/ORG_NSM
    or None when unmatched. Provenance is one of:
    - employer_synonym | employer_prefix | employer_exact
    - title_prefix_forsvar
    - employer_fuzzy_pst | employer_fuzzy_nsm | employer_fuzzy_forsvar
    - none
    """
    emp_norm = normalize_org_text(employer or "")
    emp_tokens = emp_norm.split() if emp_norm else []

    # Employer-based matching: exact tags first, then synonyms/prefix
    if emp_norm:
        # Exact equality to canonical short tags
        if emp_norm == ORG_PST:
            return ORG_PST, "employer_exact"
        if emp_norm == ORG_NSM:
            return ORG_NSM, "employer_exact"
        if emp_norm == ORG_FORSVAR:
            return ORG_FORSVAR, "employer_exact"

        # Synonym phrase containment
        if _contains_any_phrase(emp_norm, ORG_SYNONYMS[ORG_PST]):
            return ORG_PST, "employer_synonym"
        if _contains_any_phrase(emp_norm, ORG_SYNONYMS[ORG_NSM]):
            return ORG_NSM, "employer_synonym"

        # Forsvar* via token prefix
        if _has_forsvar_prefix(emp_tokens):
            return ORG_FORSVAR, "employer_prefix"

        # Optional fuzzy matching after exact/starts heuristics
        if fuzzy_threshold is not None:
            pst_score = _best_fuzzy(emp_norm, ORG_SYNONYMS[ORG_PST])
            nsm_score = _best_fuzzy(emp_norm, ORG_SYNONYMS[ORG_NSM])
            forsvar_score = _token_set_ratio(emp_norm, ORG_FORSVAR)
            best = max(pst_score, nsm_score, forsvar_score)
            if best >= (fuzzy_threshold * 100.0):
                if best == pst_score:
                    return ORG_PST, "employer_fuzzy_pst"
                if best == nsm_score:
                    return ORG_NSM, "employer_fuzzy_nsm"
                return ORG_FORSVAR, "employer_fuzzy_forsvar"

    # Title fallback: only Forsvar* and only when state-sector filter applied
    if state_sector_applied and title:
        title_tokens = tokenize_normalized(title)
        if _has_forsvar_prefix(title_tokens):
            return ORG_FORSVAR, "title_prefix_forsvar"

    return None, "none"
