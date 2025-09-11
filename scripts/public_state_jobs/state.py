"""SQLite-backed state store for incremental scraping and change detection.

Tasks 4.1–4.5 implement schema, upserts, fingerprint tracking, and selection
logic. This file starts by defining the schema (4.1).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Final, Iterable


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

