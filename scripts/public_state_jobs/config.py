"""Centralized configuration for the public sector job scraper.

Holds constants, organization keywords, selectors/regex patterns, logging
configuration, and runtime settings like retry/backoff and timeouts.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Final

# Package-wide logger base name
PACKAGE_LOGGER_NAME: Final[str] = "public_state_jobs"

# Logging format and date format
LOG_FORMAT: Final[str] = (
    "%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
DATE_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%SZ"


def configure_logging(debug: bool = False) -> None:
    """Initialize logging with INFO by default and DEBUG when requested.

    This function is idempotent: if handlers are already configured on the
    root logger, it updates the level and formatter instead of adding new
    handlers.
    """
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()

    if root.handlers:
        root.setLevel(level)
        for handler in root.handlers:
            try:
                handler.setLevel(level)
            except Exception:
                pass
            handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    else:
        logging.basicConfig(
            level=level,
            format=LOG_FORMAT,
            datefmt=DATE_FORMAT,
            stream=sys.stderr,
        )

    # Quiet noisy third-party loggers at INFO level
    for noisy in ("urllib3", "charset_normalizer", "chardet"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a namespaced logger under the package logger name."""
    full_name = PACKAGE_LOGGER_NAME if not name else f"{PACKAGE_LOGGER_NAME}.{name}"
    return logging.getLogger(full_name)


# TODO: Populate additional runtime/configuration knobs in subsequent tasks.

# Default output directory for datasets
DEFAULT_OUTPUT_DIR: Final[Path] = Path("data/public_state_jobs")


def ensure_output_dir(path: str | Path | None = None) -> Path:
    """Ensure output directory exists and return it as a Path.

    If ``path`` is None, uses ``DEFAULT_OUTPUT_DIR``.
    """
    out = Path(path) if path is not None else DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    return out
