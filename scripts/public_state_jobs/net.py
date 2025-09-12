"""HTTP networking utilities: session, headers, retries, and robots checks."""

from __future__ import annotations

import platform
from typing import Dict, Optional

import requests

from .config import get_logger
from . import __version__ as pkg_version


log = get_logger("net")


def default_user_agent(app_name: str = "public-state-jobs") -> str:
    """Build a descriptive default User-Agent string."""
    py = platform.python_version()
    sysname = platform.system()
    arch = platform.machine() or "unknown"
    return f"{app_name}/{pkg_version} (+https://example.invalid) Python/{py} {sysname}/{arch}"


def build_session(
    *,
    user_agent: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> requests.Session:
    """Create a requests Session with sensible default headers.

    Does not configure retries or rate limiting (handled in later tasks).
    """
    session = requests.Session()
    base_headers: Dict[str, str] = {
        "User-Agent": user_agent or default_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,nb;q=0.8",
        "Connection": "keep-alive",
    }
    if headers:
        base_headers.update(headers)
    session.headers.update(base_headers)
    log.debug("session_initialized: ua=%s", base_headers.get("User-Agent"))
    return session

