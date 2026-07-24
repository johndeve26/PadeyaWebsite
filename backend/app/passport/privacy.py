"""Privacy helpers for public Fan Passport surfaces."""

from __future__ import annotations

import re

from app.events.models import Event

VISIBILITY_PRIVATE = "private"
VISIBILITY_UNLISTED = "unlisted"
VISIBILITY_PUBLIC = "public"
ALLOWED_VISIBILITY = frozenset(
    {VISIBILITY_PRIVATE, VISIBILITY_UNLISTED, VISIBILITY_PUBLIC}
)

# City may appear on public passport only for these location visibility modes.
_PUBLIC_LOCATION = frozenset(
    {
        "full_public",
        "approximate_public",
        "city_only",
        "online_only",
    }
)

_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


def is_valid_passport_username(username: str) -> bool:
    return bool(_USERNAME_RE.match(username or ""))


def normalize_username(raw: str) -> str:
    return (raw or "").strip().lower().lstrip("@")


def is_publicly_reachable(visibility: str) -> bool:
    """Public + unlisted are reachable by username; private is not."""
    return visibility in {VISIBILITY_PUBLIC, VISIBILITY_UNLISTED}


def event_is_safe_for_public_passport(
    event: Event, *, hide_private_events_always: bool = True
) -> bool:
    """Whether attendance at this event may appear on a public Fan Passport."""
    if not hide_private_events_always:
        # Still never expose secret-location or unlisted/private events.
        pass
    visibility = (event.visibility or "listed").lower()
    event_type = (event.event_type or "public").lower()
    if visibility not in {"listed"}:
        return False
    if event_type in {"secret_location", "invite_only", "private"}:
        return False
    if event.status not in {"published", "completed", "ended"}:
        # Allow completed past nights that stayed published/completed.
        if event.status not in {"published", "completed"}:
            return False
    return True


def public_city_for_event(event: Event) -> str | None:
    loc = (event.location_visibility or "full_public").lower()
    if loc not in _PUBLIC_LOCATION:
        return None
    return event.city


def slugify_username_from_name(name: str, fallback: str = "fan") -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    if len(base) < 3:
        base = fallback
    return base[:32]
