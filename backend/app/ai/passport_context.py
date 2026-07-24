"""Safe context for fan.passport.bio — no tickets, spend, or private graph data."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.context_scrubber import scrub_context
from app.passport.public_service import favorite_cities_for_user
from app.passport.service import ensure_passport, list_my_badges
from app.users.models import User


PASSPORT_BIO_SAFE_KEYS = frozenset(
    {
        "display_name",
        "username",
        "existing_bio",
        "public_interests",
        "visible_badges",
        "public_city",
        "public_area",
        "user_notes",
    }
)


def build_fan_passport_bio_context(
    db: Session,
    *,
    user: User,
    notes: str | None,
    extra: dict[str, Any] | None,
) -> tuple[dict[str, str], list[str]]:
    from app.users.restrictions import assert_can_edit_passport

    assert_can_edit_passport(db, user)
    passport = ensure_passport(db, user)

    existing_bio = (passport.bio or "").strip()
    if extra:
        draft_bio = extra.get("bio") or extra.get("existing_bio")
        if draft_bio is not None and str(draft_bio).strip():
            existing_bio = str(draft_bio).strip()[:2000]

    interests = [
        str(c).strip()
        for c in (passport.favorite_categories or [])
        if str(c).strip()
    ]

    visible_badges: list[str] = []
    if passport.show_badges:
        for row in list_my_badges(db, user):
            if not row.get("earned"):
                continue
            name = row.get("name")
            if name:
                visible_badges.append(str(name)[:120])

    public_city = ""
    public_area = ""
    if passport.show_city_category_stats:
        cities = favorite_cities_for_user(db, passport.user_id)
        if cities:
            public_city = cities[0][:80]
        if len(cities) > 1:
            public_area = cities[1][:80]

    user_notes = (notes or "").strip()
    if extra and extra.get("user_notes"):
        user_notes = str(extra.get("user_notes")).strip()[:2000]

    raw: dict[str, Any] = {
        "display_name": (passport.display_name or user.full_name or "")[:200],
        "username": (passport.username or "")[:64],
        "existing_bio": existing_bio[:2000],
        "public_interests": ", ".join(interests[:12])[:500],
        "visible_badges": ", ".join(visible_badges[:8])[:500],
        "public_city": public_city,
        "public_area": public_area,
        "user_notes": user_notes[:2000],
    }

    scrubbed, redactions = scrub_context(
        raw,
        location_visibility="full_public",
        allowlist=PASSPORT_BIO_SAFE_KEYS,
    )
    scrubbed["display_name"] = raw["display_name"]
    scrubbed["username"] = raw["username"]
    return scrubbed, redactions
