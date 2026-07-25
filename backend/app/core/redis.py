"""Redis connection for rate limits, messaging pub/sub, and response cache.

Response cache keys live under ``padeya:cache:`` (see ``app.core.cache``).
Do not FLUSHDB from application code — messaging and rate limits share this DB.

Socket timeouts keep disposable cache / health checks from hanging the API forever.
Cache callers must remain fail-open (see ``app.core.cache``).
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings

settings = get_settings()

# Conservative hang protection for Upstash/network blips (seconds).
REDIS_SOCKET_CONNECT_TIMEOUT = 3.0
REDIS_SOCKET_TIMEOUT = 3.0
# After a failed connect/ping, skip reconnect attempts briefly.
REDIS_UNAVAILABLE_COOLDOWN_S = 5.0

_redis_client: Any | None = None
_redis_unavailable_until = 0.0


def reset_redis_client_for_tests() -> None:
    """Test helper — drop cached client/unavailable sticky flag."""
    global _redis_client, _redis_unavailable_until
    _redis_client = None
    _redis_unavailable_until = 0.0


def get_redis() -> Any | None:
    """
    Lazily create a Redis client when redis-py is available and Redis is up.

    Returns None if Redis cannot be reached so local bootstrapping does not fail
    before infrastructure is running. Fail-open for cache; callers must tolerate None.
    """
    global _redis_client, _redis_unavailable_until

    if _redis_client is not None:
        return _redis_client
    if time.monotonic() < _redis_unavailable_until:
        return None

    try:
        import redis

        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        _redis_unavailable_until = time.monotonic() + REDIS_UNAVAILABLE_COOLDOWN_S
        return None


def redis_health() -> dict[str, str]:
    """Cheap status for liveness/readiness — no hostnames or URLs."""
    client = get_redis()
    if client is None:
        return {"redis": "unavailable"}
    try:
        client.ping()
        return {"redis": "ok"}
    except Exception:
        return {"redis": "unavailable"}
