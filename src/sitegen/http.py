"""HTTP helpers. Every network call goes through get(), which never raises."""
from __future__ import annotations

import time

import requests

from sitegen.util import log

USER_AGENT = "Mozilla/5.0 (personal-website paper sync; github.com/timengelbracht)"
_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def get(url: str, *, params=None, timeout: float = 25, tries: int = 3, binary: bool = False):
    """GET with retries. Returns the response (or its bytes), or None on any failure."""
    for i in range(tries):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code == 429:  # rate limited: back off and retry
                time.sleep(5 * (i + 1))
                continue
            r.raise_for_status()
            return r.content if binary else r
        except requests.RequestException as e:
            if i == tries - 1:
                log("  ! failed", url, "-", e)
                return None
            time.sleep(2 * (i + 1))
    return None


def as_json(r) -> dict:
    """Parse a response as JSON; any error page (HTML, rate limit, empty) becomes {}."""
    if r is None:
        return {}
    try:
        data = r.json()
    except ValueError:
        log(f"  ! not JSON from {str(r.url)[:80]} (status {r.status_code}); skipping this source")
        return {}
    return data if isinstance(data, dict) else {}
