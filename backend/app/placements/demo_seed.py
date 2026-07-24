"""Demo featured placements (Pàdéyá Picks) for local seed."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_EVENT_SLUG_PREFIX
from app.events.models import Event, EventCategory
from app.placements.constants import (
    PLACEMENT_AREA_PAGE,
    PLACEMENT_CATEGORY_PAGE,
    PLACEMENT_CITY_PAGE,
    PLACEMENT_HOMEPAGE,
    STATUS_ACTIVE,
    STATUS_DRAFT,
)
from app.placements.models import FeaturedPlacement
from app.placements.service import ensure_slots_for_placement
from app.taxonomy.models import Location
from app.users.models import User

# (placement_type, slot_number, event_key, category_slug|None)
# Lagos city placements use location_id of city:lagos.
DEMO_FEATURED_PLACEMENTS: list[tuple[str, int, str, str | None]] = [
    (PLACEMENT_HOMEPAGE, 1, "mainland-vibes-summer", None),  # Lagos Creative Market
    (PLACEMENT_HOMEPAGE, 2, "afrobeats-night-live", None),
    (PLACEMENT_CITY_PAGE, 1, "lagos-comedy-jam", None),  # Laugh Lagos Live
    (PLACEMENT_CITY_PAGE, 2, "founders-mixer-lagos", None),
    (PLACEMENT_AREA_PAGE, 1, "mainland-vibes-summer", None),
    (PLACEMENT_CATEGORY_PAGE, 1, "mainland-vibes-summer", "lifestyle"),
    (PLACEMENT_CATEGORY_PAGE, 1, "mainland-after-dark", "nightlife"),
    (PLACEMENT_CATEGORY_PAGE, 1, "product-builders-meetup", "tech"),
]


def apply_demo_featured_placements(db: Session) -> dict[str, int]:
    """Idempotently assign demo Pàdéyá Picks featured placements."""
    events = {
        e.slug[len(DEMO_EVENT_SLUG_PREFIX) :]: e
        for e in db.scalars(
            select(Event).where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
        ).all()
    }
    categories = {
        c.slug: c for c in db.scalars(select(EventCategory)).all()
    }
    lagos_city = db.scalar(
        select(Location).where(Location.kind == "city", Location.slug == "lagos")
    )
    lekki_area = db.scalar(
        select(Location).where(Location.kind == "area", Location.slug == "lekki")
    )
    admin = db.scalar(
        select(User).where(User.email == f"admin@{DEMO_EMAIL_DOMAIN}")
    )
    actor_id = admin.id if admin else None

    assigned = 0
    ensured = 0

    # Group by placement surface so we ensure slots once per key.
    surfaces: list[tuple[str, object | None, object | None, object | None]] = [
        (PLACEMENT_HOMEPAGE, None, None, None),
    ]
    if lagos_city is not None:
        surfaces.append((PLACEMENT_CITY_PAGE, lagos_city.id, None, None))
    if lekki_area is not None:
        surfaces.append((PLACEMENT_AREA_PAGE, None, None, lekki_area.id))
    for cat_slug in ("nightlife", "tech", "lifestyle"):
        cat = categories.get(cat_slug)
        if cat is not None:
            surfaces.append((PLACEMENT_CATEGORY_PAGE, None, cat.id, None))

    slots_by_surface: dict[tuple, list[FeaturedPlacement]] = {}
    for placement_type, city_id, category_id, area_id in surfaces:
        slots = ensure_slots_for_placement(
            db,
            placement_type=placement_type,
            city_id=city_id if placement_type == PLACEMENT_CITY_PAGE else None,
            area_id=area_id if placement_type == PLACEMENT_AREA_PAGE else None,
            category_id=category_id
            if placement_type == PLACEMENT_CATEGORY_PAGE
            else None,
            actor_id=actor_id,
        )
        ensured += len(slots)
        slots_by_surface[(placement_type, city_id, category_id, area_id)] = slots

    for placement_type, slot_number, event_key, category_slug in DEMO_FEATURED_PLACEMENTS:
        event = events.get(event_key)
        if event is None or event.status != "published":
            continue

        city_id = lagos_city.id if placement_type == PLACEMENT_CITY_PAGE and lagos_city else None
        area_id = (
            lekki_area.id if placement_type == PLACEMENT_AREA_PAGE and lekki_area else None
        )
        category_id = None
        if placement_type == PLACEMENT_CATEGORY_PAGE:
            cat = categories.get(category_slug or "")
            if cat is None:
                continue
            category_id = cat.id

        key = (
            placement_type,
            city_id if placement_type == PLACEMENT_CITY_PAGE else None,
            category_id if placement_type == PLACEMENT_CATEGORY_PAGE else None,
            area_id if placement_type == PLACEMENT_AREA_PAGE else None,
        )
        slots = slots_by_surface.get(key)
        if not slots:
            continue
        slot = next((s for s in slots if s.slot_number == slot_number), None)
        if slot is None:
            continue

        slot.event_id = event.id
        slot.status = STATUS_ACTIVE
        if actor_id:
            if slot.created_by is None:
                slot.created_by = actor_id
            slot.updated_by = actor_id
        assigned += 1

    # Leave unassigned slots as empty drafts (clear stale demo events if any).
    demo_event_ids = {e.id for e in events.values()}
    for slots in slots_by_surface.values():
        for slot in slots:
            if slot.event_id is None:
                slot.status = STATUS_DRAFT
                continue
            if slot.status == STATUS_ACTIVE and slot.event_id not in demo_event_ids:
                continue

    db.commit()
    return {
        "placement_slots_ensured": ensured,
        "placement_slots_assigned": assigned,
    }
