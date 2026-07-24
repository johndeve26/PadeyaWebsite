"""Public response cache utilities (Redis-backed, namespaced).

Uses prefix ``padeya:cache:`` so keys never collide with messaging pub/sub
channels or rate-limit counters in the same Redis DB.

When Redis is unavailable, reads miss and writes no-op — callers always
compute a fresh value (safe for local/dev and pytest).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.config import get_settings
from app.core.redis import get_redis

logger = logging.getLogger("padeya.cache")

T = TypeVar("T")

CACHE_PREFIX = "padeya:cache:"

# --- TTL policy (seconds) — see docs/PERFORMANCE_CACHING_AUDIT.md ---
TTL_FEATURED = 120
TTL_LIST = 90
TTL_DETAIL = 180
TTL_CALENDAR_MAP = 120
TTL_PROFILE = 180
TTL_TAXONOMY = 1800  # 30m
TTL_CONTENT = 3600  # 1h (blog/help/FAQ/CMS; FE may ISR longer)
TTL_PRICING = 600
TTL_AVAILABILITY = 60  # capacity-sensitive public fields


class CacheTTL:
    featured = TTL_FEATURED
    list = TTL_LIST
    detail = TTL_DETAIL
    calendar_map = TTL_CALENDAR_MAP
    profile = TTL_PROFILE
    taxonomy = TTL_TAXONOMY
    content = TTL_CONTENT
    pricing = TTL_PRICING
    availability = TTL_AVAILABILITY


# Process-local fallback for tests / Redis-down (bounded, best-effort).
_MEMORY: dict[str, tuple[float, str]] = {}
_MEMORY_MAX = 512


def _debug_enabled() -> bool:
    try:
        return bool(get_settings().debug)
    except Exception:
        return False


def cache_key(namespace: str, *parts: Any, **params: Any) -> str:
    """Build a stable Redis key including filters/query params."""
    raw_parts = [str(p) for p in parts if p is not None and p != ""]
    if params:
        items = sorted((k, "" if v is None else str(v)) for k, v in params.items())
        raw_parts.append("&".join(f"{k}={v}" for k, v in items))
    digest = ""
    joined = ":".join(raw_parts)
    if len(joined) > 180:
        digest = ":" + hashlib.sha256(joined.encode()).hexdigest()[:16]
        joined = joined[:120]
    return f"{CACHE_PREFIX}{namespace}:{joined}{digest}"


def cache_get(key: str) -> Any | None:
    """Return deserialized JSON value or None on miss / error."""
    client = get_redis()
    if client is not None:
        try:
            raw = client.get(key)
            if raw is None:
                if _debug_enabled():
                    logger.debug("cache miss redis key=%s", key)
                return None
            if _debug_enabled():
                logger.debug("cache hit redis key=%s", key)
            return json.loads(raw)
        except Exception:
            logger.debug("cache get failed key=%s", key, exc_info=True)
            return None

    entry = _MEMORY.get(key)
    if entry is None:
        if _debug_enabled():
            logger.debug("cache miss memory key=%s", key)
        return None
    expires_at, raw = entry
    if expires_at < time.monotonic():
        _MEMORY.pop(key, None)
        return None
    if _debug_enabled():
        logger.debug("cache hit memory key=%s", key)
    try:
        return json.loads(raw)
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int) -> bool:
    """Store JSON-serializable value. Returns True if stored."""
    if ttl <= 0:
        return False
    try:
        raw = json.dumps(value, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        logger.debug("cache set serialize failed key=%s", key, exc_info=True)
        return False

    client = get_redis()
    if client is not None:
        try:
            client.setex(key, int(ttl), raw)
            return True
        except Exception:
            logger.debug("cache set redis failed key=%s", key, exc_info=True)
            # fall through to memory

    if len(_MEMORY) >= _MEMORY_MAX:
        # Drop an arbitrary expired or oldest-ish entry.
        now = time.monotonic()
        stale = [k for k, (exp, _) in _MEMORY.items() if exp < now]
        for k in stale[:64]:
            _MEMORY.pop(k, None)
        if len(_MEMORY) >= _MEMORY_MAX:
            for k in list(_MEMORY.keys())[:64]:
                _MEMORY.pop(k, None)
    _MEMORY[key] = (time.monotonic() + float(ttl), raw)
    return True


def cache_delete(key: str) -> int:
    """Delete one key. Returns number deleted (0 or 1)."""
    deleted = 0
    if key in _MEMORY:
        _MEMORY.pop(key, None)
        deleted = 1
    client = get_redis()
    if client is None:
        return deleted
    try:
        return int(client.delete(key)) or deleted
    except Exception:
        logger.debug("cache delete failed key=%s", key, exc_info=True)
        return deleted


def cache_delete_pattern(pattern: str) -> int:
    """Delete keys matching a glob pattern (``padeya:cache:events:*``).

    Uses SCAN so we never block Redis with KEYS on large DBs.
    """
    if not pattern.startswith(CACHE_PREFIX):
        pattern = f"{CACHE_PREFIX}{pattern.lstrip('*')}"
        if not pattern.endswith("*") and ":" in pattern:
            # allow callers to pass namespace prefixes like "events:list"
            pass

    # Memory store
    mem_deleted = 0
    for k in list(_MEMORY.keys()):
        if _glob_match(pattern, k):
            _MEMORY.pop(k, None)
            mem_deleted += 1

    client = get_redis()
    if client is None:
        return mem_deleted

    deleted = 0
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                deleted += int(client.delete(*keys))
            if cursor == 0:
                break
    except Exception:
        logger.debug("cache delete_pattern failed pattern=%s", pattern, exc_info=True)
        return mem_deleted
    return deleted + mem_deleted


def _glob_match(pattern: str, key: str) -> bool:
    """Minimal ``*`` glob match for in-memory invalidation."""
    if pattern == key:
        return True
    if "*" not in pattern:
        return pattern == key
    # Trailing * alone: prefix match (``events:list*`` matches ``events:list``).
    if pattern.endswith("*") and pattern.count("*") == 1:
        return key.startswith(pattern[:-1])
    parts = pattern.split("*")
    if not key.startswith(parts[0]):
        return False
    rest = key[len(parts[0]) :]
    for i, part in enumerate(parts[1:]):
        if part == "":
            if i == len(parts) - 2:
                return True
            continue
        idx = rest.find(part)
        if idx < 0:
            return False
        rest = rest[idx + len(part) :]
    return True


def get_or_set(
    key: str,
    ttl: int,
    producer: Callable[[], T],
    *,
    skip_cache: bool = False,
) -> T:
    """Return cached value or compute, store, and return."""
    if not skip_cache:
        hit = cache_get(key)
        if hit is not None:
            return hit  # type: ignore[return-value]
    value = producer()
    # Pydantic / list-of-models: normalize to JSON-compatible
    stored: Any = value
    if hasattr(value, "model_dump"):
        stored = value.model_dump(mode="json")
    elif isinstance(value, list) and value and hasattr(value[0], "model_dump"):
        stored = [v.model_dump(mode="json") for v in value]
    cache_set(key, stored, ttl)
    return value


def clear_memory_cache() -> None:
    """Test helper — wipe process-local fallback store."""
    _MEMORY.clear()
