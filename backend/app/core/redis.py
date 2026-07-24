"""Redis connection for rate limits, messaging pub/sub, and response cache.

Response cache keys live under ``padeya:cache:`` (see ``app.core.cache``).
Do not FLUSHDB from application code — messaging and rate limits share this DB.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings

settings = get_settings()

_redis_client: Any | None = None


def get_redis() -> Any | None:
    """
    Lazily create a Redis client when redis-py is available and Redis is up.

    Returns None if Redis cannot be reached so local bootstrapping does not fail
    before infrastructure is running.
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        import redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        return None


def redis_health() -> dict[str, str]:
    client = get_redis()
    if client is None:
        return {"redis": "unavailable"}
    return {"redis": "ok"}
