"""Redis-backed assistant rate limits (fail-open to in-memory)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from uuid import UUID

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.redis import get_redis

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)

_WINDOW_SECONDS = 3600
_DETAIL = "Assistant rate limit exceeded. Please try again later."


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "unknown")[:64]
    return "unknown"


def _limits(*, authenticated: bool) -> int:
    settings = get_settings()
    if authenticated:
        return int(
            getattr(settings, "assistant_auth_rate_limit_per_hour", None) or 120
        )
    return int(
        getattr(settings, "assistant_anonymous_rate_limit_per_hour", None) or 30
    )


def _limit_local(key: str, *, max_requests: int) -> None:
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail=_DETAIL)
        bucket.append(now)


def _limit_redis(key: str, *, max_requests: int) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        pipe = client.pipeline()
        now = time.time()
        pipe.zremrangebyscore(key, 0, now - _WINDOW_SECONDS)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, _WINDOW_SECONDS + 5)
        _, count, _, _ = pipe.execute()
        if int(count) >= max_requests:
            raise HTTPException(status_code=429, detail=_DETAIL)
        return True
    except HTTPException:
        raise
    except Exception:
        return False


def check_assistant_rate_limit(
    request: Request,
    *,
    user_id: UUID | None = None,
    anonymous_session_id: str | None = None,
) -> None:
    """Enforce separate anonymous vs authenticated hourly budgets."""
    authenticated = user_id is not None
    max_requests = _limits(authenticated=authenticated)
    if authenticated:
        key = f"assistant:auth:{user_id}"
    else:
        anon = (anonymous_session_id or "").strip() or _client_ip(request)
        key = f"assistant:anon:{anon[:80]}"
    if _limit_redis(key, max_requests=max_requests):
        return
    _limit_local(key, max_requests=max_requests)
