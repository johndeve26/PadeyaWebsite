"""Short-lived maintenance decision cache (process memory).

When the platform is fully off (mode=off, no active section windows), ordinary
requests skip opening a DB session for maintenance. Admin/schedule changes
invalidate the cache; TTL also bounds how long an auto-schedule can lag.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

# Fast enough for admin toggles; long enough to cut per-request DB tax.
DEFAULT_TTL_SECONDS = 15.0


@dataclass
class _CacheEntry:
    expires_at: float
    allow_without_db: bool
    mode: str


_lock = threading.Lock()
_entry: _CacheEntry | None = None


def invalidate_maintenance_decision_cache() -> None:
    """Call after settings/section/schedule mutations."""
    global _entry
    with _lock:
        _entry = None


def get_cached_off_allow() -> bool | None:
    """Return True if cached 'off' allow, False if cached deny-path, None if miss."""
    with _lock:
        if _entry is None:
            return None
        if time.monotonic() >= _entry.expires_at:
            return None
        return _entry.allow_without_db


def store_off_allow(*, mode: str, ttl: float = DEFAULT_TTL_SECONDS) -> None:
    """Cache that maintenance can be skipped (mode off / no active sections)."""
    global _entry
    with _lock:
        _entry = _CacheEntry(
            expires_at=time.monotonic() + max(1.0, float(ttl)),
            allow_without_db=True,
            mode=mode,
        )


def store_requires_db(*, mode: str, ttl: float = DEFAULT_TTL_SECONDS) -> None:
    """Cache that the next requests must evaluate maintenance via DB.

    We do not skip DB when this is set — only the positive off-allow short-circuit
    avoids DB. This entry exists so callers can record mode for observability.
    """
    global _entry
    with _lock:
        _entry = _CacheEntry(
            expires_at=time.monotonic() + max(1.0, float(ttl)),
            allow_without_db=False,
            mode=mode,
        )


def cache_snapshot() -> dict[str, Any]:
    with _lock:
        if _entry is None:
            return {"cached": False}
        return {
            "cached": True,
            "allow_without_db": _entry.allow_without_db,
            "mode": _entry.mode,
            "ttl_remaining_s": max(0.0, _entry.expires_at - time.monotonic()),
        }
