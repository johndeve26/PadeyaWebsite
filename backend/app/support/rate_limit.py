"""In-memory rate limit for public support submissions."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.support.constants import PUBLIC_RATE_LIMIT, PUBLIC_RATE_WINDOW_SECONDS

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "unknown")[:64]
    return "unknown"


def rate_limit_public_support(request: Request) -> None:
    key = f"support:public:{_client_ip(request)}"
    now = time.monotonic()
    cutoff = now - PUBLIC_RATE_WINDOW_SECONDS
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= PUBLIC_RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many support requests. Please try again later.",
            )
        bucket.append(now)
