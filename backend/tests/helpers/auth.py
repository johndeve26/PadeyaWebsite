"""Shared auth helpers for API tests."""

from __future__ import annotations

import re


def username_from_email(email: str) -> str:
    """Derive a stable per-email username so registrations do not collide."""
    local = email.split("@", 1)[0].lower()
    username = re.sub(r"[^a-z0-9_]", "_", local).strip("_")
    return username[:30] or "test_user"


def register_json(
    *,
    email: str,
    password: str = "securepass1",
    full_name: str = "Test User",
    **extra: object,
) -> dict[str, object]:
    """Build a register payload with an explicit unique username."""
    payload: dict[str, object] = {
        "email": email,
        "password": password,
        "full_name": full_name,
        "username": username_from_email(email),
    }
    payload.update(extra)
    return payload
