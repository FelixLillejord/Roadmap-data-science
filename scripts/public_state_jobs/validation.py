"""Validation helpers for parsing success metrics and incremental efficiency."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from .models import (
    EXPLODED_COLUMNS,
    EXPLODED_DTYPES,
    to_exploded_dataframe,
)
from .state import (
    select_detail_candidates,
    upsert_from_summaries,
    update_detail_fingerprint,
)


def compute_exploded_metrics(rows_or_df: Iterable[Dict[str, Any]] | pd.DataFrame) -> Dict[str, Any]:
    """Compute basic success metrics on exploded rows.

    Returns counts and percentages for job_code presence and salary presence,
    along with a schema_ok flag after coercion.
    """
    if isinstance(rows_or_df, pd.DataFrame):
        df = rows_or_df.copy()
        # Coerce to schema to verify consistency
        df = to_exploded_dataframe(df.to_dict(orient="records"))
    else:
        # Normalize input to dictionaries
        dicts: List[Dict[str, Any]] = []
        for r in rows_or_df:  # type: ignore[assignment]
            if is_dataclass(r):
                dicts.append(asdict(r))
            elif isinstance(r, dict):
                dicts.append(r)
            else:
                dicts.append(dict(r))
        df = to_exploded_dataframe(dicts)

    total = int(len(df))
    codes_present = int(df["job_code"].notna().sum())
    # Salary presence if either bound is present
    salary_any = int((df["salary_min"].notna() | df["salary_max"].notna()).sum())

    return {
        "total_rows": total,
        "codes_present": codes_present,
        "codes_pct": (codes_present / total) if total else 0.0,
        "salary_any_present": salary_any,
        "salary_any_pct": (salary_any / total) if total else 0.0,
        "schema_ok": list(df.columns) == EXPLODED_COLUMNS and [str(t) for t in df.dtypes] == [EXPLODED_DTYPES[c] for c in EXPLODED_COLUMNS],
    }


def measure_incremental_efficiency(
    conn,
    run1_summaries,
    run2_summaries,
    *,
    seen_at_run1: str,
    seen_at_run2: str,
    fingerprint_ids_run1: Optional[Iterable[str]] = None,
    full: bool = False,
) -> Dict[str, Any]:
    """Measure change in detail selection between two runs using existing state.

    Returns a dict with counts for run1 and run2 selections and a reduction
    ratio (1 - run2/run1) when run1 > 0.
    """
    # Run 1: select then upsert
    cand1 = select_detail_candidates(conn, run1_summaries, full=full)
    upsert_from_summaries(conn, run1_summaries, seen_at=seen_at_run1)

    if fingerprint_ids_run1:
        for lid in fingerprint_ids_run1:
            update_detail_fingerprint(conn, listing_id=lid, detail_fingerprint="fp1")

    # Run 2: select then upsert
    cand2 = select_detail_candidates(conn, run2_summaries, full=full)
    upsert_from_summaries(conn, run2_summaries, seen_at=seen_at_run2)

    n1 = len(cand1)
    n2 = len(cand2)
    reduction = (1.0 - (n2 / n1)) if n1 > 0 else None
    return {
        "run1_candidates": n1,
        "run2_candidates": n2,
        "reduction_ratio": reduction,
    }

