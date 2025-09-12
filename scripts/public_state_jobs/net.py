"""HTTP networking utilities: session, headers, retries, and robots checks."""

from __future__ import annotations

import platform
import random
import time
from typing import Dict, Optional

import requests
from requests import Response
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from .config import get_logger
from . import __version__ as pkg_version
from urllib.parse import urlparse
import urllib.robotparser as robotparser


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


def get_with_retries(
    session: requests.Session,
    url: str,
    *,
    method: str = "GET",
    timeout: float = 10.0,
    max_attempts: int = 3,
    backoff_base: float = 0.5,
    backoff_factor: float = 2.0,
    jitter_max: float = 0.25,
    respect_retry_after: bool = True,
    **kwargs,
) -> Response:
    """Perform an HTTP request with retries for 429/5xx/timeouts.

    Exponential backoff with jitter up to ``jitter_max`` seconds. Honors
    ``Retry-After`` on 429 when ``respect_retry_after`` is True.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = session.request(method=method, url=url, timeout=timeout, **kwargs)
        except (Timeout, ReadTimeout, ConnectionError) as exc:
            retriable = True
            status = None
        else:
            status = resp.status_code
            retriable = status == 429 or (500 <= status < 600)
            if not retriable:
                return resp

        if attempt >= max_attempts:
            if status is not None:
                log.warning("http_retry_exhausted: %s %s status=%s attempts=%d", method, url, status, attempt)
                # Return last response if we have it (caller can handle status)
                if 'resp' in locals():
                    return resp
            # Raise a generic timeout/connection error if no response
            raise

        # Compute delay: prefer Retry-After for 429
        delay = backoff_base * (backoff_factor ** (attempt - 1))
        if status == 429 and respect_retry_after and 'resp' in locals():
            ra = resp.headers.get("Retry-After")
            if ra:
                try:
                    delay = max(delay, float(ra))
                except ValueError:
                    pass
        delay += random.random() * jitter_max
        log.info("http_retry: %s %s attempt=%d status=%s sleeping=%.2fs", method, url, attempt, status, delay)
        time.sleep(delay)


class RobotsCache:
    """Cache and evaluate robots.txt per host using requests session."""

    def __init__(self, session: requests.Session, user_agent: str, timeout: float = 5.0):
        self._session = session
        self._ua = user_agent
        self._timeout = timeout
        self._cache: Dict[str, Optional[robotparser.RobotFileParser]] = {}

    def _fetch_robots(self, origin: str) -> Optional[robotparser.RobotFileParser]:
        # origin like "https://example.com"
        url = origin.rstrip("/") + "/robots.txt"
        try:
            resp = get_with_retries(self._session, url, timeout=self._timeout)
        except Exception as exc:
            log.info("robots_fetch_failed: %s (%s)", url, exc)
            return None
        if resp.status_code != 200 or not resp.text:
            return None
        rp = robotparser.RobotFileParser()
        rp.set_url(url)
        rp.parse(resp.text.splitlines())
        return rp

    def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._cache:
            self._cache[origin] = self._fetch_robots(origin)
        rp = self._cache.get(origin)
        if rp is None:
            # No robots available or failed to fetch; default allow
            return True
        return rp.can_fetch(self._ua, url)


class PoliteFetcher:
    """Fetcher that enforces politeness delay and robots.txt disallow rules."""

    def __init__(
        self,
        session: requests.Session,
        *,
        delay_seconds: float = 1.0,
        respect_robots: bool = True,
        user_agent: Optional[str] = None,
    ) -> None:
        self.session = session
        self.delay_seconds = max(0.0, delay_seconds)
        self.respect_robots = respect_robots
        self.user_agent = user_agent or session.headers.get("User-Agent", default_user_agent())
        self._last_by_host: Dict[str, float] = {}
        self._robots = RobotsCache(session, self.user_agent)

    def _sleep_if_needed(self, host: str) -> None:
        if self.delay_seconds <= 0:
            return
        now = time.monotonic()
        last = self._last_by_host.get(host)
        if last is not None:
            elapsed = now - last
            remaining = self.delay_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_by_host[host] = time.monotonic()

    def get(self, url: str, **kwargs) -> Optional[Response]:
        parsed = urlparse(url)
        host = parsed.netloc
        if self.respect_robots and not self._robots.is_allowed(url):
            log.info("robots_disallow_skip: %s", url)
            return None
        self._sleep_if_needed(host)
        return get_with_retries(self.session, url, **kwargs)
