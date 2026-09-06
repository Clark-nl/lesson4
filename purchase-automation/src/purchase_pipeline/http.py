"""Shared HTTP session with retry/backoff for every network-calling connector.

A scheduled pipeline that fails outright on one transient 502 or a
momentary connection drop wastes the whole day's run. `get_session()`
returns a `requests.Session` that automatically retries idempotent
requests (GET, and POST here since every POST use in this codebase is
either safe to repeat or explicitly guarded) a few times with
exponential backoff before giving up.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_RETRY_TOTAL = 3
DEFAULT_BACKOFF_FACTOR = 0.5
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


def get_session(
    total: int = DEFAULT_RETRY_TOTAL,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def next_page_url(resp: requests.Response) -> str | None:
    """Shopify Admin API cursor pagination: the next page's URL, or None."""
    link = resp.headers.get("Link", "")
    for part in link.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip(" <>")
    return None
