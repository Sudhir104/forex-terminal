from __future__ import annotations

import time
from typing import Any, Optional

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; ForexTerminal/1.0; private research dashboard)"

# Tests inject an httpx.MockTransport here.
_transport: Optional[httpx.BaseTransport] = None
RETRY_BACKOFF = 0.6


def set_transport(transport: Optional[httpx.BaseTransport]) -> None:
    global _transport, RETRY_BACKOFF
    _transport = transport
    RETRY_BACKOFF = 0.0 if transport is not None else 0.6


def client(timeout: float = 20.0) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        transport=_transport,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        follow_redirects=True,
    )


def get(url: str, params: Optional[dict[str, Any]] = None, headers: Optional[dict[str, str]] = None,
        retries: int = 2, timeout: float = 20.0, allow_304: bool = False) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with client(timeout) as c:
                r = c.get(url, params=params, headers=headers)
            if allow_304 and r.status_code == 304:
                return r
            if r.status_code >= 500 or r.status_code == 429:
                raise httpx.HTTPStatusError(f"{r.status_code} from {url}", request=r.request, response=r)
            r.raise_for_status()
            return r
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            last = e
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status is not None and status < 500 and status != 429:
                raise
            if attempt < retries:
                time.sleep(RETRY_BACKOFF * (attempt + 1))
    assert last is not None
    raise last


def post_json(url: str, json: Any, headers: Optional[dict[str, str]] = None, timeout: float = 60.0) -> httpx.Response:
    with client(timeout) as c:
        r = c.post(url, json=json, headers=headers)
    r.raise_for_status()
    return r
