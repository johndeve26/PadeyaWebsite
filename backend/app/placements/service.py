"""Featured placements — Primary/Secondary Spotlight per discovery surface."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event, EventCategory
from app.events.service import serialize_event
from app.placements.constants import (
    CATEGORY_CONTEXTS,
    CONTEXT_AREA,
    CONTEXT_CATEGORY,
    CONTEXT_CITY,
    CONTEXT_CITY_CATEGORY,
    CONTEXT_COUNTRY,
    CONTEXT_GLOBAL,
    CONTEXT_STATE,
    LEGACY_CONTEXT_TO_PLACEMENT,
    LOCATION_CONTEXTS,
    PLACEMENT_AREA_PAGE,
    PLACEMENT_CATEGORY_PAGE,
    PLACEMENT_CITY_CATEGORY_PAGE,
    PLACEMENT_CITY_PAGE,
    PLACEMENT_COUNTRY_PAGE,
    PLACEMENT_EVENTS_PAGE,
    PLACEMENT_HOMEPAGE,
    PLACEMENT_LABELS,
    PLACEMENT_STATE_PAGE,
    PLACEMENT_TYPES,
    PUBLIC_LIVE_STATUSES,
    SLOT_LABELS,
    SLOT_NUMBERS,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_EXPIRED,
    STATUS_SCHEDULED,
)
from app.placements.models import FeaturedPlacement
from app.taxonomy.models import Location
from app.taxonomy.service import location_ancestors
from app.users.models import User
from app.users.service import user_has_permission


def normalize_placement_type(raw: str | None) -> str:
    key = (raw or PLACEMENT_EVENTS_PAGE).strip().lower()
    mapped = LEGACY_CONTEXT_TO_PLACEMENT.get(key)
    if mapped is None:
        raise HTTPException(status_code=400, detail="Invalid placement_type / context")
    return mapped


def placement_context_type(placement_type: str) -> str:
    return {
        PLACEMENT_HOMEPAGE: CONTEXT_GLOBAL,
        PLACEMENT_EVENTS_PAGE: CONTEXT_GLOBAL,
        PLACEMENT_COUNTRY_PAGE: CONTEXT_COUNTRY,
        PLACEMENT_STATE_PAGE: CONTEXT_STATE,
        PLACEMENT_CITY_PAGE: CONTEXT_CITY,
        PLACEMENT_AREA_PAGE: CONTEXT_AREA,
        PLACEMENT_CATEGORY_PAGE: CONTEXT_CATEGORY,
        PLACEMENT_CITY_CATEGORY_PAGE: CONTEXT_CITY_CATEGORY,
    }[placement_type]


def build_placement_key(
    placement_type: str,
    *,
    country_id: uuid.UUID | None = None,
    state_id: uuid.UUID | None = None,
    city_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
) -> str:
    if placement_type in {PLACEMENT_HOMEPAGE, PLACEMENT_EVENTS_PAGE}:
        return placement_type
    if placement_type == PLACEMENT_COUNTRY_PAGE:
        if country_id is None:
            raise HTTPException(status_code=400, detail="country_id is required")
        return f"country_page:{country_id}"
    if placement_type == PLACEMENT_STATE_PAGE:
        if state_id is None:
            raise HTTPException(status_code=400, detail="state_id is required")
        return f"state_page:{state_id}"
    if placement_type == PLACEMENT_CITY_PAGE:
        if city_id is None:
            raise HTTPException(status_code=400, detail="city_id is required")
        return f"city_page:{city_id}"
    if placement_type == PLACEMENT_AREA_PAGE:
        if area_id is None:
            raise HTTPException(status_code=400, detail="area_id is required")
        return f"area_page:{area_id}"
    if placement_type == PLACEMENT_CATEGORY_PAGE:
        if category_id is None:
            raise HTTPException(status_code=400, detail="category_id is required")
        return f"category_page:{category_id}"
    if placement_type == PLACEMENT_CITY_CATEGORY_PAGE:
        if city_id is None or category_id is None:
            raise HTTPException(
                status_code=400,
                detail="city_id and category_id are required for city_category_page",
            )
        return f"city_category_page:{city_id}:{category_id}"
    raise HTTPException(status_code=400, detail=f"Invalid placement_type: {placement_type}")


def _ancestor_map(db: Session, location: Location) -> dict[str, Location]:
    ancestors = location_ancestors(db, location)
    by_kind: dict[str, Location] = {a.kind: a for a in ancestors}
    by_kind[location.kind] = location
    return by_kind


def resolve_location_ids(
    db: Session,
    *,
    placement_type: str,
    location_id: uuid.UUID | None,
) -> tuple[
    uuid.UUID | None,
    uuid.UUID | None,
    uuid.UUID | None,
    uuid.UUID | None,
    Location | None,
]:
    """Return country/state/city/area ids + primary location for a placement."""
    if placement_type not in LOCATION_CONTEXTS and placement_type not in {
        "country",
        "state",
        "city",
        "area",
        "city_category",
        PLACEMENT_COUNTRY_PAGE,
        PLACEMENT_STATE_PAGE,
        PLACEMENT_CITY_PAGE,
        PLACEMENT_AREA_PAGE,
        PLACEMENT_CITY_CATEGORY_PAGE,
    }:
        return None, None, None, None, None

    if location_id is None:
        raise HTTPException(status_code=400, detail="location_id is required")

    location = db.get(Location, location_id)
    if location is None or not location.is_active:
        raise HTTPException(status_code=404, detail="Location not found")

    expected = {
        PLACEMENT_COUNTRY_PAGE: "country",
        PLACEMENT_STATE_PAGE: "state",
        PLACEMENT_CITY_PAGE: "city",
        PLACEMENT_AREA_PAGE: "area",
        PLACEMENT_CITY_CATEGORY_PAGE: "city",
        "country": "country",
        "state": "state",
        "city": "city",
        "area": "area",
        "city_category": "city",
    }.get(placement_type)
    if expected and location.kind != expected:
        raise HTTPException(
            status_code=400,
            detail=f"Location kind must be {expected} for {placement_type}",
        )

    by_kind = _ancestor_map(db, location)
    return (
        by_kind.get("country").id if by_kind.get("country") else None,
        by_kind.get("state").id if by_kind.get("state") else None,
        by_kind.get("city").id if by_kind.get("city") else None,
        by_kind.get("area").id if by_kind.get("area") else None,
        location,
    )


def validate_category(db: Session, category_id: uuid.UUID | None) -> EventCategory | None:
    if category_id is None:
        return None
    category = db.get(EventCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if getattr(category, "is_active", True) is False:
        raise HTTPException(status_code=400, detail="Category is inactive")
    return category


def picks_display_title(
    *,
    placement_type: str,
    location_name: str | None = None,
    category_name: str | None = None,
    title_override: str | None = None,
) -> str:
    if title_override:
        return title_override
    if placement_type in {PLACEMENT_HOMEPAGE, PLACEMENT_EVENTS_PAGE}:
        return "Global Pàdéyá Picks"
    if placement_type in {
        PLACEMENT_COUNTRY_PAGE,
        PLACEMENT_STATE_PAGE,
        PLACEMENT_CITY_PAGE,
        PLACEMENT_AREA_PAGE,
    }:
        return f"{(location_name or 'Location').strip()} Pàdéyá Picks"
    if placement_type == PLACEMENT_CATEGORY_PAGE:
        return f"{(category_name or 'Category').strip()} Pàdéyá Picks"
    if placement_type == PLACEMENT_CITY_CATEGORY_PAGE:
        place = (location_name or "City").strip()
        cat = (category_name or "Category").strip()
        return f"{place} {cat} Pàdéyá Picks"
    return "Pàdéyá Picks"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def compute_status(
    *,
    event_id: uuid.UUID | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
    requested: str | None = None,
    now: datetime | None = None,
) -> str:
    if requested == STATUS_ARCHIVED:
        return STATUS_ARCHIVED
    if event_id is None:
        return STATUS_DRAFT
    moment = _as_utc(now) or datetime.now(UTC)
    ends = _as_utc(ends_at)
    starts = _as_utc(starts_at)
    if ends and ends <= moment:
        return STATUS_EXPIRED
    if starts and starts > moment:
        return STATUS_SCHEDULED
    if requested in {STATUS_ACTIVE, STATUS_SCHEDULED, STATUS_DRAFT, None}:
        return STATUS_ACTIVE if not (starts and starts > moment) else STATUS_SCHEDULED
    return requested or STATUS_ACTIVE


def refresh_row_status(row: FeaturedPlacement, *, now: datetime | None = None) -> None:
    # Preserve explicit editorial states; only auto-shift live schedule windows.
    if row.status in {STATUS_ARCHIVED, STATUS_DRAFT}:
        return
    row.status = compute_status(
        event_id=row.event_id,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        now=now,
    )


def ensure_slots_for_placement(
    db: Session,
    *,
    placement_type: str,
    country_id: uuid.UUID | None = None,
    state_id: uuid.UUID | None = None,
    city_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
) -> list[FeaturedPlacement]:
    placement_type = normalize_placement_type(placement_type)
    if placement_type not in PLACEMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid placement_type")

    needs_location = placement_type in {
        PLACEMENT_COUNTRY_PAGE,
        PLACEMENT_STATE_PAGE,
        PLACEMENT_CITY_PAGE,
        PLACEMENT_AREA_PAGE,
        PLACEMENT_CITY_CATEGORY_PAGE,
    }
    needs_category = placement_type in {
        PLACEMENT_CATEGORY_PAGE,
        PLACEMENT_CITY_CATEGORY_PAGE,
    }

    primary_location_id = {
        PLACEMENT_COUNTRY_PAGE: country_id,
        PLACEMENT_STATE_PAGE: state_id,
        PLACEMENT_CITY_PAGE: city_id,
        PLACEMENT_AREA_PAGE: area_id,
        PLACEMENT_CITY_CATEGORY_PAGE: city_id,
    }.get(placement_type)

    if needs_location:
        country_id, state_id, city_id, area_id, _loc = resolve_location_ids(
            db,
            placement_type=placement_type,
            location_id=primary_location_id,
        )
    else:
        country_id = state_id = city_id = area_id = None

    category = None
    if needs_category:
        if category_id is None:
            raise HTTPException(status_code=400, detail="category_id is required")
        category = validate_category(db, category_id)
    elif category_id is not None:
        raise HTTPException(
            status_code=400,
            detail=f"category_id is not used for {placement_type}",
        )

    context_type = placement_context_type(placement_type)
    context_id = {
        CONTEXT_GLOBAL: None,
        CONTEXT_COUNTRY: country_id,
        CONTEXT_STATE: state_id,
        CONTEXT_CITY: city_id,
        CONTEXT_AREA: area_id,
        CONTEXT_CATEGORY: category.id if category else None,
        CONTEXT_CITY_CATEGORY: city_id,
    }[context_type]

    key = build_placement_key(
        placement_type,
        country_id=country_id,
        state_id=state_id,
        city_id=city_id,
        area_id=area_id,
        category_id=category.id if category else category_id,
    )

    existing = {
        s.slot_number: s
        for s in db.scalars(
            select(FeaturedPlacement).where(FeaturedPlacement.placement_key == key)
        ).all()
    }
    created = False
    for num in SLOT_NUMBERS:
        if num in existing:
            continue
        db.add(
            FeaturedPlacement(
                placement_key=key,
                placement_type=placement_type,
                context_type=context_type,
                context_id=context_id,
                country_id=country_id,
                state_id=state_id,
                city_id=city_id,
                area_id=area_id,
                category_id=category.id if category else None,
                event_id=None,
                slot_number=num,
                status=STATUS_DRAFT,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
        created = True
    if created:
        db.commit()
    rows = list(
        db.scalars(
            select(FeaturedPlacement)
            .where(FeaturedPlacement.placement_key == key)
            .order_by(FeaturedPlacement.slot_number)
        ).all()
    )
    for row in rows:
        refresh_row_status(row)
    db.commit()
    return rows


def ensure_default_global_rows(db: Session) -> None:
    for ptype in (PLACEMENT_HOMEPAGE, PLACEMENT_EVENTS_PAGE):
        ensure_slots_for_placement(db, placement_type=ptype)


def list_slots_for_context(
    db: Session,
    *,
    context_type: str,
    location_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
) -> list[FeaturedPlacement]:
    """Admin/public helper — accepts legacy context aliases or placement_type."""
    placement_type = normalize_placement_type(context_type)
    country_id = state_id = city_id = area_id = None
    if placement_type == PLACEMENT_COUNTRY_PAGE:
        country_id = location_id
    elif placement_type == PLACEMENT_STATE_PAGE:
        state_id = location_id
    elif placement_type in {PLACEMENT_CITY_PAGE, PLACEMENT_CITY_CATEGORY_PAGE}:
        city_id = location_id
    elif placement_type == PLACEMENT_AREA_PAGE:
        area_id = location_id
    return ensure_slots_for_placement(
        db,
        placement_type=placement_type,
        country_id=country_id,
        state_id=state_id,
        city_id=city_id,
        area_id=area_id,
        category_id=category_id,
    )


def list_configured_contexts(
    db: Session, *, include_archived: bool = False
) -> list[dict]:
    ensure_default_global_rows(db)
    q = select(FeaturedPlacement).order_by(
        FeaturedPlacement.placement_type,
        FeaturedPlacement.placement_key,
        FeaturedPlacement.slot_number,
    )
    if not include_archived:
        q = q.where(FeaturedPlacement.status != STATUS_ARCHIVED)
    rows = list(db.scalars(q).all())
    by_key: dict[str, list[FeaturedPlacement]] = {}
    for row in rows:
        by_key.setdefault(row.placement_key, []).append(row)

    result: list[dict] = []
    for key, slots in by_key.items():
        sample = slots[0]
        primary = next((s for s in slots if s.slot_number == 1), sample)
        primary_loc_id = (
            sample.area_id or sample.city_id or sample.state_id or sample.country_id
        )
        location = db.get(Location, primary_loc_id) if primary_loc_id else None
        category = (
            db.get(EventCategory, sample.category_id) if sample.category_id else None
        )
        loc_name = location.name if location else None
        cat_name = category.name if category else None
        # Prefer shared overrides from primary slot; fall back to any slot.
        title_override = next(
            (s.title_override for s in slots if s.title_override), None
        )
        subtitle_override = next(
            (s.subtitle_override for s in slots if s.subtitle_override), None
        )
        badge_text = next((s.badge_text for s in slots if s.badge_text), None)
        starts_at = next((s.starts_at for s in slots if s.starts_at), None)
        ends_at = next((s.ends_at for s in slots if s.ends_at), None)
        # Aggregate status: archived if all archived; else worst live state.
        statuses = {s.status for s in slots}
        if statuses == {STATUS_ARCHIVED}:
            set_status = STATUS_ARCHIVED
        elif STATUS_ACTIVE in statuses:
            set_status = STATUS_ACTIVE
        elif STATUS_SCHEDULED in statuses:
            set_status = STATUS_SCHEDULED
        elif STATUS_EXPIRED in statuses:
            set_status = STATUS_EXPIRED
        else:
            set_status = STATUS_DRAFT
        result.append(
            {
                "id": primary.id,
                "context_key": key,
                "placement_key": key,
                "context_type": sample.placement_type,
                "placement_type": sample.placement_type,
                "context_label": PLACEMENT_LABELS.get(
                    sample.placement_type, sample.placement_type
                ),
                "location_id": primary_loc_id,
                "country_id": sample.country_id,
                "state_id": sample.state_id,
                "city_id": sample.city_id,
                "area_id": sample.area_id,
                "category_id": sample.category_id,
                "location_name": loc_name,
                "location_slug": location.slug if location else None,
                "location_kind": location.kind if location else None,
                "category_name": cat_name,
                "category_slug": category.slug if category else None,
                "display_title": picks_display_title(
                    placement_type=sample.placement_type,
                    location_name=loc_name,
                    category_name=cat_name,
                    title_override=title_override,
                ),
                "status": set_status,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "title_override": title_override,
                "subtitle_override": subtitle_override,
                "badge_text": badge_text,
                "slots": [slot_to_public(db, s) for s in slots],
            }
        )
    return result


def get_set_by_id(db: Session, set_id: uuid.UUID) -> dict:
    anchor = db.get(FeaturedPlacement, set_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail="Placement set not found")
    sets = list_configured_contexts(db, include_archived=True)
    match = next(
        (row for row in sets if row["placement_key"] == anchor.placement_key),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Placement set not found")
    return match


def upsert_placement_set(
    db: Session,
    *,
    user: User,
    context_type: str,
    location_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    slot_1_event_id: uuid.UUID | None,
    slot_2_event_id: uuid.UUID | None,
    title_override: str | None = None,
    subtitle_override: str | None = None,
    badge_text: str | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    status: str | None = None,
) -> dict:
    _require_admin(user)
    if (
        slot_1_event_id
        and slot_2_event_id
        and slot_1_event_id == slot_2_event_id
    ):
        raise HTTPException(
            status_code=409,
            detail="Primary and Secondary Spotlight must use different events",
        )

    requested_status = status
    # Clear both slots first so Primary/Secondary swaps do not hit the
    # same-event-in-context uniqueness check mid-update.
    for slot_number in (1, 2):
        assign_slot(
            db,
            user=user,
            slot_index=slot_number,
            context_type=context_type,
            location_id=location_id,
            category_id=category_id,
            event_id=None,
            status=STATUS_DRAFT,
        )

    # Apply shared metadata + events to both slots.
    for slot_number, event_id in ((1, slot_1_event_id), (2, slot_2_event_id)):
        slot_status = requested_status
        if event_id is None and requested_status not in {STATUS_ARCHIVED}:
            # Keep empty slot as draft unless whole set is archived.
            slot_status = STATUS_DRAFT if requested_status != STATUS_ACTIVE else STATUS_DRAFT
        assign_slot(
            db,
            user=user,
            slot_index=slot_number,
            context_type=context_type,
            location_id=location_id,
            category_id=category_id,
            event_id=event_id,
            title_override=title_override,
            subtitle_override=subtitle_override,
            badge_text=badge_text,
            starts_at=starts_at,
            ends_at=ends_at,
            status=slot_status if event_id or requested_status == STATUS_ARCHIVED else STATUS_DRAFT,
        )

    # Re-apply shared schedule/status onto slots that have events when activating.
    slots = list_slots_for_context(
        db,
        context_type=context_type,
        location_id=location_id,
        category_id=category_id,
    )
    for slot in slots:
        if requested_status == STATUS_ARCHIVED:
            slot.status = STATUS_ARCHIVED
            slot.event_id = None
        elif slot.event_id:
            slot.title_override = title_override
            slot.subtitle_override = subtitle_override
            slot.badge_text = badge_text
            slot.starts_at = starts_at
            slot.ends_at = ends_at
            slot.status = compute_status(
                event_id=slot.event_id,
                starts_at=starts_at,
                ends_at=ends_at,
                requested=requested_status or STATUS_ACTIVE,
            )
        else:
            slot.title_override = title_override
            slot.subtitle_override = subtitle_override
            slot.badge_text = badge_text
            slot.starts_at = starts_at
            slot.ends_at = ends_at
            slot.status = STATUS_DRAFT
        slot.updated_by = user.id
    db.commit()

    primary = next((s for s in slots if s.slot_number == 1), slots[0])
    return get_set_by_id(db, primary.id)


def update_set_status(
    db: Session,
    *,
    user: User,
    set_id: uuid.UUID,
    status: str,
) -> dict:
    _require_admin(user)
    if status not in {STATUS_ACTIVE, STATUS_DRAFT, STATUS_ARCHIVED}:
        raise HTTPException(
            status_code=400,
            detail="status must be active, draft, or archived",
        )
    anchor = db.get(FeaturedPlacement, set_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail="Placement set not found")
    slots = list(
        db.scalars(
            select(FeaturedPlacement).where(
                FeaturedPlacement.placement_key == anchor.placement_key
            )
        ).all()
    )
    for slot in slots:
        if status == STATUS_ARCHIVED:
            slot.status = STATUS_ARCHIVED
        elif status == STATUS_DRAFT:
            slot.status = STATUS_DRAFT if not slot.event_id else STATUS_DRAFT
        else:
            # activate
            if not slot.event_id:
                slot.status = STATUS_DRAFT
            else:
                slot.status = compute_status(
                    event_id=slot.event_id,
                    starts_at=slot.starts_at,
                    ends_at=slot.ends_at,
                    requested=STATUS_ACTIVE,
                )
        slot.updated_by = user.id
    write_audit_log(
        db,
        action=f"placements.set_{status}",
        actor_user_id=user.id,
        resource_type="featured_placement_set",
        resource_id=str(set_id),
        details={
            "placement_key": anchor.placement_key,
            "status": status,
        },
    )
    db.commit()
    try:
        from app.core.cache_invalidation import invalidate_event_caches

        invalidate_event_caches(slug=None, event_id=None, host_id=None)
    except Exception:
        pass
    return get_set_by_id(db, set_id)


def _require_admin(user: User) -> None:
    if not (
        user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "events.approve")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")


def _load_event(db: Session, event_id: uuid.UUID) -> Event:
    from app.events.service import get_event_by_id

    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event must be published")
    if event.visibility not in {"listed", "approval_required"}:
        raise HTTPException(status_code=400, detail="Event must be publicly listed")
    return event


def assign_slot(
    db: Session,
    *,
    user: User,
    slot_index: int,
    context_type: str,
    location_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    event_id: uuid.UUID | None,
    title_override: str | None = None,
    subtitle_override: str | None = None,
    badge_text: str | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    status: str | None = None,
) -> FeaturedPlacement:
    _require_admin(user)
    if slot_index not in SLOT_NUMBERS:
        raise HTTPException(status_code=400, detail="slot_number must be 1 or 2")

    slots = list_slots_for_context(
        db,
        context_type=context_type,
        location_id=location_id,
        category_id=category_id,
    )
    slot = next((s for s in slots if s.slot_number == slot_index), None)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")

    key = slot.placement_key
    if event_id is not None:
        _load_event(db, event_id)
        other = db.scalar(
            select(FeaturedPlacement).where(
                FeaturedPlacement.placement_key == key,
                FeaturedPlacement.event_id == event_id,
                FeaturedPlacement.slot_number != slot_index,
                FeaturedPlacement.status != STATUS_ARCHIVED,
            )
        )
        if other is not None:
            raise HTTPException(
                status_code=409,
                detail="Event is already assigned to the other spotlight in this context",
            )

    if event_id is None and status != STATUS_ARCHIVED:
        # Clear → draft empty slot
        slot.event_id = None
        slot.status = STATUS_DRAFT
    else:
        slot.event_id = event_id
        if title_override is not None:
            slot.title_override = title_override
        if subtitle_override is not None:
            slot.subtitle_override = subtitle_override
        if badge_text is not None:
            slot.badge_text = badge_text
        if starts_at is not None:
            slot.starts_at = starts_at
        if ends_at is not None:
            slot.ends_at = ends_at
        if status == STATUS_ARCHIVED:
            slot.status = STATUS_ARCHIVED
            slot.event_id = None
        else:
            slot.status = compute_status(
                event_id=slot.event_id,
                starts_at=slot.starts_at,
                ends_at=slot.ends_at,
                requested=status,
            )

    if slot.created_by is None:
        slot.created_by = user.id
    slot.updated_by = user.id
    write_audit_log(
        db,
        action="placements.assign" if event_id else "placements.clear",
        actor_user_id=user.id,
        resource_type="featured_placement",
        resource_id=str(slot.id),
        details={
            "slot_number": slot_index,
            "slot_label": SLOT_LABELS[slot_index],
            "placement_type": slot.placement_type,
            "placement_key": key,
            "status": slot.status,
            "event_id": str(event_id) if event_id else None,
        },
    )
    db.commit()
    db.refresh(slot)
    try:
        from app.core.cache_invalidation import invalidate_event_caches

        # Picks share the events:picks* namespace cleared by event invalidation.
        invalidate_event_caches(
            slug=None,
            event_id=event_id,
            host_id=None,
        )
    except Exception:
        pass
    return slot


def resolve_public_context(
    db: Session,
    *,
    context_type: str | None,
    location_kind: str | None,
    location_slug: str | None,
    category_slug: str | None,
) -> tuple[str, uuid.UUID | None, uuid.UUID | None, str, str | None, str | None]:
    placement_type = normalize_placement_type(context_type)
    location_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    location_name: str | None = None
    category_name: str | None = None

    if placement_type in {
        PLACEMENT_COUNTRY_PAGE,
        PLACEMENT_STATE_PAGE,
        PLACEMENT_CITY_PAGE,
        PLACEMENT_AREA_PAGE,
        PLACEMENT_CITY_CATEGORY_PAGE,
    }:
        expected = {
            PLACEMENT_COUNTRY_PAGE: "country",
            PLACEMENT_STATE_PAGE: "state",
            PLACEMENT_CITY_PAGE: "city",
            PLACEMENT_AREA_PAGE: "area",
            PLACEMENT_CITY_CATEGORY_PAGE: "city",
        }[placement_type]
        if not location_kind or not location_slug:
            raise HTTPException(
                status_code=400,
                detail="location_kind and location_slug are required",
            )
        if location_kind != expected:
            raise HTTPException(
                status_code=400,
                detail=f"location_kind must be {expected} for {placement_type}",
            )
        location = db.scalar(
            select(Location).where(
                Location.kind == location_kind,
                Location.slug == location_slug,
                Location.is_active.is_(True),
            )
        )
        if location is None:
            raise HTTPException(status_code=404, detail="Location not found")
        location_id = location.id
        location_name = location.name

    if placement_type in {PLACEMENT_CATEGORY_PAGE, PLACEMENT_CITY_CATEGORY_PAGE}:
        if not category_slug:
            raise HTTPException(status_code=400, detail="category is required")
        category = db.scalar(
            select(EventCategory).where(EventCategory.slug == category_slug)
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        category_id = category.id
        category_name = category.name

    title = picks_display_title(
        placement_type=placement_type,
        location_name=location_name,
        category_name=category_name,
    )
    return (
        placement_type,
        location_id,
        category_id,
        title,
        location_name,
        category_name,
    )


def list_padeya_picks(
    db: Session,
    *,
    context_type: str = PLACEMENT_EVENTS_PAGE,
    location_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
) -> list[Event]:
    """Public Pàdéyá Picks — live Primary/Secondary events in slot order."""
    slots = list_slots_for_context(
        db,
        context_type=context_type,
        location_id=location_id,
        category_id=category_id,
    )
    now = datetime.now(UTC)
    picks: list[Event] = []
    for slot in slots:
        refresh_row_status(slot, now=now)
        if slot.status not in PUBLIC_LIVE_STATUSES:
            continue
        starts = _as_utc(slot.starts_at)
        ends = _as_utc(slot.ends_at)
        if starts and starts > now:
            continue
        if ends and ends <= now:
            continue
        if not slot.event_id:
            continue
        from app.events.service import get_event_by_id

        event = get_event_by_id(db, slot.event_id)
        if (
            event
            and event.status == "published"
            and event.visibility in {"listed", "approval_required"}
        ):
            picks.append(event)
    db.commit()
    return picks


def slot_to_public(db: Session, slot: FeaturedPlacement) -> dict:
    from app.events.schemas import EventPublic, TicketTypePublic

    primary_loc_id = slot.area_id or slot.city_id or slot.state_id or slot.country_id
    data = {
        "id": slot.id,
        "placement_key": slot.placement_key,
        "context_key": slot.placement_key,
        "placement_type": slot.placement_type,
        "context_type": slot.placement_type,
        "context_id": slot.context_id,
        "location_id": primary_loc_id,
        "country_id": slot.country_id,
        "state_id": slot.state_id,
        "city_id": slot.city_id,
        "area_id": slot.area_id,
        "category_id": slot.category_id,
        "slot_number": slot.slot_number,
        "slot_index": slot.slot_number,
        "slot_label": SLOT_LABELS.get(slot.slot_number, f"Slot {slot.slot_number}"),
        "event_id": slot.event_id,
        "title_override": slot.title_override,
        "subtitle_override": slot.subtitle_override,
        "badge_text": slot.badge_text,
        "starts_at": slot.starts_at,
        "ends_at": slot.ends_at,
        "status": slot.status,
        "created_by": slot.created_by,
        "updated_by": slot.updated_by,
        "created_at": slot.created_at,
        "updated_at": slot.updated_at,
        "event": None,
    }
    if slot.event_id:
        from app.events.service import get_event_by_id

        event = get_event_by_id(db, slot.event_id)
        if event:
            payload = serialize_event(event, access="public")
            payload["ticket_types"] = [
                TicketTypePublic.model_validate(tt).model_copy(
                    update={"access_code": None}
                )
                for tt in event.ticket_types
                if tt.visibility == "public"
            ]
            data["event"] = EventPublic.model_validate(payload)
    return data


LISTING_PICK_CONTEXTS = frozenset({PLACEMENT_HOMEPAGE, PLACEMENT_EVENTS_PAGE})


def _normalize_listing_pick_context(context_type: str | None) -> str:
    placement_type = normalize_placement_type(context_type or PLACEMENT_HOMEPAGE)
    if placement_type not in LISTING_PICK_CONTEXTS:
        raise HTTPException(
            status_code=400,
            detail="Listing Pàdéyá Picks only support homepage or events_page",
        )
    return placement_type


def event_padeya_pick_slots(
    db: Session,
    *,
    event_id: uuid.UUID,
    context_type: str | None = None,
) -> list[FeaturedPlacement]:
    """Active (non-archived) placement rows that currently hold this event."""
    stmt = select(FeaturedPlacement).where(
        FeaturedPlacement.event_id == event_id,
        FeaturedPlacement.status != STATUS_ARCHIVED,
    )
    if context_type:
        placement_type = _normalize_listing_pick_context(context_type)
        stmt = stmt.where(FeaturedPlacement.placement_type == placement_type)
    else:
        stmt = stmt.where(FeaturedPlacement.placement_type.in_(LISTING_PICK_CONTEXTS))
    rows = list(db.scalars(stmt).all())
    rows.sort(key=lambda r: (r.placement_type, r.slot_number))
    return rows


def set_event_as_padeya_pick(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    context_type: str = PLACEMENT_HOMEPAGE,
    slot_number: int | None = None,
) -> FeaturedPlacement:
    """Assign a published listing into a global Pàdéyá Pick slot (listing admin)."""
    _require_admin(user)
    placement_type = _normalize_listing_pick_context(context_type)
    _load_event(db, event_id)

    slots = list_slots_for_context(
        db,
        context_type=placement_type,
        location_id=None,
        category_id=None,
    )
    existing = next((s for s in slots if s.event_id == event_id), None)
    if existing is not None:
        if existing.status not in PUBLIC_LIVE_STATUSES:
            return assign_slot(
                db,
                user=user,
                slot_index=existing.slot_number,
                context_type=placement_type,
                location_id=None,
                category_id=None,
                event_id=event_id,
                status=STATUS_ACTIVE,
            )
        return existing

    target: int | None = slot_number
    if target is None:
        empty = next((s for s in slots if s.event_id is None), None)
        if empty is not None:
            target = empty.slot_number
        else:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Both Pàdéyá Pick slots are filled for this context. "
                    "Clear a slot first or pass slot_number to replace one."
                ),
            )
    elif target not in SLOT_NUMBERS:
        raise HTTPException(status_code=400, detail="slot_number must be 1 or 2")

    return assign_slot(
        db,
        user=user,
        slot_index=target,
        context_type=placement_type,
        location_id=None,
        category_id=None,
        event_id=event_id,
        status=STATUS_ACTIVE,
    )


def clear_event_padeya_pick(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    context_type: str = PLACEMENT_HOMEPAGE,
) -> list[FeaturedPlacement]:
    """Remove a listing from global Pàdéyá Pick slots for a context."""
    _require_admin(user)
    placement_type = _normalize_listing_pick_context(context_type)
    held = event_padeya_pick_slots(
        db, event_id=event_id, context_type=placement_type
    )
    cleared: list[FeaturedPlacement] = []
    for row in held:
        cleared.append(
            assign_slot(
                db,
                user=user,
                slot_index=row.slot_number,
                context_type=placement_type,
                location_id=None,
                category_id=None,
                event_id=None,
                status=STATUS_DRAFT,
            )
        )
    return cleared


def swap_padeya_pick_slots(
    db: Session,
    *,
    user: User,
    context_type: str = PLACEMENT_HOMEPAGE,
) -> list[FeaturedPlacement]:
    """Swap Primary/Secondary listing picks for a global context."""
    _require_admin(user)
    placement_type = _normalize_listing_pick_context(context_type)
    slots = list_slots_for_context(
        db,
        context_type=placement_type,
        location_id=None,
        category_id=None,
    )
    by_num = {s.slot_number: s for s in slots}
    primary = by_num.get(1)
    secondary = by_num.get(2)
    if primary is None or secondary is None:
        raise HTTPException(status_code=404, detail="Placement slots not found")

    e1, e2 = primary.event_id, secondary.event_id
    s1, s2 = primary.status, secondary.status
    # Clear first to avoid unique-event conflict within the placement key.
    assign_slot(
        db,
        user=user,
        slot_index=1,
        context_type=placement_type,
        location_id=None,
        category_id=None,
        event_id=None,
        status=STATUS_DRAFT,
    )
    assign_slot(
        db,
        user=user,
        slot_index=2,
        context_type=placement_type,
        location_id=None,
        category_id=None,
        event_id=None,
        status=STATUS_DRAFT,
    )
    if e2 is not None:
        assign_slot(
            db,
            user=user,
            slot_index=1,
            context_type=placement_type,
            location_id=None,
            category_id=None,
            event_id=e2,
            status=STATUS_ACTIVE if s2 in PUBLIC_LIVE_STATUSES else s2,
        )
    if e1 is not None:
        assign_slot(
            db,
            user=user,
            slot_index=2,
            context_type=placement_type,
            location_id=None,
            category_id=None,
            event_id=e1,
            status=STATUS_ACTIVE if s1 in PUBLIC_LIVE_STATUSES else s1,
        )
    write_audit_log(
        db,
        action="placements.swap_slots",
        actor_user_id=user.id,
        resource_type="featured_placement_set",
        resource_id=str(primary.id),
        details={
            "placement_type": placement_type,
            "from": {"1": str(e1) if e1 else None, "2": str(e2) if e2 else None},
            "to": {"1": str(e2) if e2 else None, "2": str(e1) if e1 else None},
        },
    )
    db.commit()
    return list_slots_for_context(
        db,
        context_type=placement_type,
        location_id=None,
        category_id=None,
    )


# Legacy name used by older imports
ensure_slots_for_context = list_slots_for_context
