"""Rate limit for public nearby / map event search."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.redis import get_redis

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)

# Soft default — nearby/map are read-heavy but abuse-prone for scraping.
_DEFAULT_PER_MINUTE = 60


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _client_key(request: Request, *, prefix: str = "events:nearby") -> str:
    return f"{prefix}:{_client_ip(request)}"


def _limit_local(
    key: str,
    *,
    max_requests: int,
    window_seconds: int,
    detail: str,
) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail=detail)
        bucket.append(now)


def _limit_redis(
    key: str,
    *,
    max_requests: int,
    window_seconds: int,
    detail: str,
) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        pipe = client.pipeline()
        now = time.time()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 5)
        _, count, _, _ = pipe.execute()
        if int(count) >= max_requests:
            raise HTTPException(status_code=429, detail=detail)
        return True
    except HTTPException:
        raise
    except Exception:
        return False


def _rate_limit_events_geo(
    request: Request,
    *,
    prefix: str,
    detail: str,
) -> None:
    max_requests = _DEFAULT_PER_MINUTE
    try:
        from app.core.config import get_settings

        max_requests = int(
            getattr(get_settings(), "events_nearby_rate_limit_per_minute", None)
            or _DEFAULT_PER_MINUTE
        )
    except Exception:
        max_requests = _DEFAULT_PER_MINUTE
    window = 60
    key = _client_key(request, prefix=prefix)
    if _limit_redis(
        key, max_requests=max_requests, window_seconds=window, detail=detail
    ):
        return
    _limit_local(
        key, max_requests=max_requests, window_seconds=window, detail=detail
    )


async def rate_limit_nearby_events(request: Request) -> None:
    """Rate-limit GET /events/nearby by client IP."""
    _rate_limit_events_geo(
        request,
        prefix="events:nearby",
        detail="Nearby search rate limit exceeded. Try again shortly.",
    )


async def rate_limit_map_events(request: Request) -> None:
    """Rate-limit GET /events/map by client IP."""
    _rate_limit_events_geo(
        request,
        prefix="events:map",
        detail="Map search rate limit exceeded. Try again shortly.",
    )
