"""Rate limits and idempotency for Blog AI Studio."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import HTTPException

# Tunable limits (tests may monkeypatch)
STUDIO_AI_PER_MINUTE = 10
MAX_SIMULTANEOUS_GENERATIONS = 1
MAX_OUTLINE_SECTIONS = 20
MAX_BODY_CHARS = 50_000
MAX_SOURCE_TEXT = 8_000
IDEMPOTENCY_TTL_SECONDS = 120

_lock = threading.Lock()
_minute_hits: dict[str, deque[float]] = defaultdict(deque)
_in_flight: dict[str, int] = defaultdict(int)
_idempotency: dict[str, tuple[float, Any]] = {}


def reset_studio_rate_limits() -> None:
    """Test helper — clear in-memory rate/idempotency state."""
    with _lock:
        _minute_hits.clear()
        _in_flight.clear()
        _idempotency.clear()


def _prune_hits(q: deque[float], now: float) -> None:
    while q and now - q[0] > 60.0:
        q.popleft()


def check_studio_rate_limit(admin_user_id: str) -> None:
    now = time.monotonic()
    with _lock:
        q = _minute_hits[admin_user_id]
        _prune_hits(q, now)
        if len(q) >= STUDIO_AI_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Blog AI Studio rate limit exceeded "
                    f"({STUDIO_AI_PER_MINUTE}/minute). Try again shortly."
                ),
            )
        if _in_flight[admin_user_id] >= MAX_SIMULTANEOUS_GENERATIONS:
            raise HTTPException(
                status_code=429,
                detail="A Blog AI Studio generation is already in progress. Wait for it to finish.",
            )
        q.append(now)


def acquire_generation_slot(admin_user_id: str) -> None:
    with _lock:
        if _in_flight[admin_user_id] >= MAX_SIMULTANEOUS_GENERATIONS:
            raise HTTPException(
                status_code=429,
                detail="A Blog AI Studio generation is already in progress. Wait for it to finish.",
            )
        _in_flight[admin_user_id] += 1


def release_generation_slot(admin_user_id: str) -> None:
    with _lock:
        _in_flight[admin_user_id] = max(0, _in_flight[admin_user_id] - 1)


def get_idempotent(admin_user_id: str, client_request_id: str | None) -> Any | None:
    if not client_request_id:
        return None
    key = f"{admin_user_id}:{client_request_id}"
    now = time.monotonic()
    with _lock:
        hit = _idempotency.get(key)
        if not hit:
            return None
        ts, payload = hit
        if now - ts > IDEMPOTENCY_TTL_SECONDS:
            _idempotency.pop(key, None)
            return None
        return payload


def store_idempotent(admin_user_id: str, client_request_id: str | None, payload: Any) -> None:
    if not client_request_id:
        return
    key = f"{admin_user_id}:{client_request_id}"
    with _lock:
        # Prune expired opportunistically
        now = time.monotonic()
        expired = [k for k, (ts, _) in _idempotency.items() if now - ts > IDEMPOTENCY_TTL_SECONDS]
        for k in expired:
            _idempotency.pop(k, None)
        _idempotency[key] = (now, payload)


def assert_outline_section_limit(count: int) -> None:
    if count > MAX_OUTLINE_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Outline exceeds max sections ({MAX_OUTLINE_SECTIONS}).",
        )


def assert_body_limit(body: str | None) -> None:
    if body is not None and len(body) > MAX_BODY_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Body exceeds max length ({MAX_BODY_CHARS} characters).",
        )


def assert_source_text_limit(text: str | None) -> None:
    if text is not None and len(text) > MAX_SOURCE_TEXT:
        raise HTTPException(
            status_code=400,
            detail=f"Source/reference text exceeds max length ({MAX_SOURCE_TEXT} characters).",
        )
