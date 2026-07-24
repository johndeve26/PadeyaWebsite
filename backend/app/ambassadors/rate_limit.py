"""Rate limit for Ambassadors track-click / referral-click endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.ambassadors.fraud import request_client_ip
from app.core.config import get_settings
from app.core.redis import get_redis

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _limit_local(key: str, *, max_requests: int, window_seconds: int) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Ambassador tracking rate limit exceeded. Try again shortly.",
            )
        bucket.append(now)


def _limit_redis(key: str, *, max_requests: int, window_seconds: int) -> bool:
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
            raise HTTPException(
                status_code=429,
                detail="Ambassador tracking rate limit exceeded. Try again shortly.",
            )
        return True
    except HTTPException:
        raise
    except Exception:
        return False


async def rate_limit_ambassador_track(request: Request) -> None:
    """Rate-limit public Ambassadors tracking by client IP (hashed key only)."""
    from app.core.database import SessionLocal
    from app.runtime_settings import get_runtime_setting

    db = SessionLocal()
    try:
        max_requests = int(
            get_runtime_setting("ambassador_track_rate_limit_per_minute", db=db) or 60
        )
    finally:
        db.close()
    window = 60
    ip = request_client_ip(request) or "unknown"
    key = f"ambassadors:track:{ip}"
    if _limit_redis(key, max_requests=max_requests, window_seconds=window):
        return
    _limit_local(key, max_requests=max_requests, window_seconds=window)
