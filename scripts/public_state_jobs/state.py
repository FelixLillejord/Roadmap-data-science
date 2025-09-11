"""SQLite-backed state store for incremental scraping and change detection.

Tasks 4.1–4.5 implement schema, upserts, fingerprint tracking, and selection
logic. This file starts by defining the schema (4.1).
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Final, Iterable, Optional

from .models import ListingSummary


DB_FILENAME: Final[str] = "public_state_jobs.sqlite3"


SCHEMA_SQL: Final[tuple[str, ...]] = (
    # Listing-level state for incremental scraping
    """
    CREATE TABLE IF NOT EXISTS listings (
        listing_id TEXT PRIMARY KEY,
        last_seen_at TEXT NOT NULL,
        updated_at TEXT,
        detail_fingerprint TEXT
    )
    """,
    # Auxiliary index for updated_at to speed up change detection queries
    """
    CREATE INDEX IF NOT EXISTS idx_listings_updated_at
    ON listings(updated_at)
    """,
)


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with safe defaults."""
    path = str(db_path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create required tables and indexes if they don't exist."""
    cur = conn.cursor()
    for stmt in SCHEMA_SQL:
        cur.executescript(stmt)
    conn.commit()


def ensure_db(db_dir: str | Path) -> Path:
    """Ensure the database file exists under the given directory.

    Returns the full path to the database file.
    """
    db_dir_path = Path(db_dir)
    db_dir_path.mkdir(parents=True, exist_ok=True)
    db_path = db_dir_path / DB_FILENAME
    # Create file and schema if missing
    with connect(db_path) as conn:
        init_db(conn)
    return db_path


# --- Upsert helpers (4.2) ---

def upsert_listing(
    conn: sqlite3.Connection,
    *,
    listing_id: str,
    last_seen_at: str,
    updated_at: Optional[str] = None,
    detail_fingerprint: Optional[str] = None,
) -> None:
    """Insert or update a listing's last seen and summary metadata.

    - Advances ``last_seen_at`` to the maximum (ISO8601 lexicographic)
    - Updates ``updated_at`` only when a non-null value is provided
    - Preserves existing ``detail_fingerprint`` unless a non-null value is provided
    """
    sql = (
        """
        INSERT INTO listings(listing_id, last_seen_at, updated_at, detail_fingerprint)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(listing_id) DO UPDATE SET
            last_seen_at = CASE
                WHEN excluded.last_seen_at > COALESCE(listings.last_seen_at, '')
                THEN excluded.last_seen_at ELSE listings.last_seen_at END,
            updated_at = COALESCE(excluded.updated_at, listings.updated_at),
            detail_fingerprint = COALESCE(excluded.detail_fingerprint, listings.detail_fingerprint)
        """
    )
    conn.execute(sql, (listing_id, last_seen_at, updated_at, detail_fingerprint))


def upsert_from_summaries(
    conn: sqlite3.Connection,
    summaries: Iterable[ListingSummary],
    *,
    seen_at: str,
) -> int:
    """Upsert a batch of list-page summaries with a common ``seen_at`` timestamp.

    Returns the number of rows processed.
    """
    count = 0
    for s in summaries:
        upsert_listing(
            conn,
            listing_id=s.listing_id,
            last_seen_at=seen_at,
            updated_at=s.updated_at,
        )
        count += 1
    conn.commit()
    return count


# --- Fingerprint computation and tracking (4.3) ---

def compute_detail_fingerprint(html: str) -> str:
    """Compute a stable fingerprint of detail HTML.

    Uses SHA1 of UTF-8 bytes. Upstream callers may pre-normalize if needed.
    """
    return hashlib.sha1(html.encode("utf-8")).hexdigest()


def get_detail_fingerprint(conn: sqlite3.Connection, listing_id: str) -> Optional[str]:
    cur = conn.execute("SELECT detail_fingerprint FROM listings WHERE listing_id = ?", (listing_id,))
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else None


def update_detail_fingerprint(
    conn: sqlite3.Connection,
    *,
    listing_id: str,
    detail_fingerprint: str,
) -> None:
    """Update the stored fingerprint for a given listing."""
    conn.execute(
        "UPDATE listings SET detail_fingerprint = ? WHERE listing_id = ?",
        (detail_fingerprint, listing_id),
    )
    conn.commit()
