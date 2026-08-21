"""Rate limiting — sliding window (in-memory; Redis-ready stub)."""

from __future__ import annotations

import time
from collections import defaultdict
from fastapi import HTTPException, Request

from ..config import settings

_hits: dict[str, list[float]] = defaultdict(list)


def _key_for_request(request: Request) -> str:
    # Prefer Authorization sub, else client host, else global
    auth = request.headers.get("authorization", "")
    if auth:
        return f"auth:{auth[:24]}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def check_rate_limit(request: Request, max_hits: int | None = None, window_s: int | None = None):
    max_hits = max_hits or settings.rate_limit_per_min
    window_s = window_s or settings.rate_limit_window_s
    key = _key_for_request(request)
    now = time.time()
    window = [t for t in _hits[key] if now - t < window_s]
    _hits[key] = window
    if len(window) >= max_hits:
        raise HTTPException(status_code=429, detail=f"rate limited: {max_hits}/{window_s}s")
    _hits[key].append(now)


def clear_rate_limits():
    _hits.clear()
