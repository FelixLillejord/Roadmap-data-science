"""Writers for Parquet/CSV outputs and optional listing-level export."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Union

import pandas as pd

from .config import ensure_output_dir, DEFAULT_OUTPUT_DIR
from .models import to_exploded_dataframe


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rows_to_dicts(rows: Iterable[object]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        if is_dataclass(r):
            out.append(asdict(r))
        elif isinstance(r, dict):
            out.append(r)
        else:
            out.append(dict(r))  # attempt mapping-like
    return out


def _apply_scraped_at(df: pd.DataFrame, scraped_at: str | None) -> pd.DataFrame:
    when = scraped_at or _now_utc_iso()
    if "scraped_at" in df.columns:
        df["scraped_at"] = df["scraped_at"].fillna(when).astype("string")
    else:
        df["scraped_at"] = when
    return df


def write_exploded_parquet(
    rows: Iterable[object],
    *,
    out_dir: Union[str, Path] | None = None,
    filename: str = "jobs_exploded.parquet",
    scraped_at: str | None = None,
) -> Path:
    """Write exploded rows to a Parquet file with stable schema and dtypes."""
    dicts = _rows_to_dicts(rows)
    df = to_exploded_dataframe(dicts)
    df = _apply_scraped_at(df, scraped_at)

    target_dir = ensure_output_dir(out_dir or DEFAULT_OUTPUT_DIR)
    out_path = Path(target_dir) / filename
    df.to_parquet(out_path, index=False)
    return out_path


def write_exploded_csv(
    rows: Iterable[object],
    *,
    out_dir: Union[str, Path] | None = None,
    filename: str = "jobs_exploded.csv",
    scraped_at: str | None = None,
) -> Path:
    """Write exploded rows to a CSV file with stable column order."""
    dicts = _rows_to_dicts(rows)
    df = to_exploded_dataframe(dicts)
    df = _apply_scraped_at(df, scraped_at)

    target_dir = ensure_output_dir(out_dir or DEFAULT_OUTPUT_DIR)
    out_path = Path(target_dir) / filename
    df.to_csv(out_path, index=False)
    return out_path

