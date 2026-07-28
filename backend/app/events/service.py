"""Event, media, and ticket type services."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, object_session, selectinload

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.media import get_public_media_storage
from app.core.media_folders import event_public_folder, host_public_folder
from app.events.models import (
    Event,
    EventAgendaItem,
    EventCategory,
    EventCheckoutQuestion,
    EventMedia,
    EventPerson,
    EventVenue,
    TicketType,
)
from app.events.privacy import AccessLevel, apply_location_privacy
from app.events.schemas import (
    EventCreate,
    EventMediaCreate,
    EventPublishChecklist,
    EventRejectRequest,
    EventUpdate,
    TicketTypeCreate,
    TicketTypeUpdate,
)
from app.hosts.models import Host
from app.hosts.team_access import (
    require_host_event_permission,
    require_host_for_permission,
)
from app.users.models import User
from app.users.service import user_has_permission, user_has_role

NESTED_EXCLUDE = {
    "venue",
    "agenda_items",
    "people",
    "checkout_questions",
    "gallery_urls",
}

AUTO_PUBLISH_REVIEW_FLAG_REASON = "Auto-published — pending post-publish review"
EDIT_AFTER_PUBLISH_FLAG_REASON = "Edited after publish — review when ready"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "event"


def unique_event_slug(db: Session, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    i = 2
    while db.scalar(select(Event.id).where(Event.slug == candidate)):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


# Safe max page for public marketplace list (external API still returns a list).
PUBLIC_EVENTS_LIST_MAX = 100


def _event_query():
    """Full event graph for detail / host / admin paths."""
    return select(Event).options(
        selectinload(Event.category),
        selectinload(Event.location),
        selectinload(Event.venue),
        selectinload(Event.media),
        selectinload(Event.ticket_types),
        selectinload(Event.agenda_items),
        selectinload(Event.people),
        selectinload(Event.checkout_questions),
        selectinload(Event.host),
    )


def _event_list_query():
    """Lean graph for marketplace cards — no agenda/people/checkout/media/venue."""
    return select(Event).options(
        selectinload(Event.category),
        selectinload(Event.location),
        selectinload(Event.ticket_types),
        selectinload(Event.host),
    )


def get_event_by_id(db: Session, event_id: uuid.UUID) -> Event | None:
    return db.scalar(_event_query().where(Event.id == event_id))


def get_event_by_slug(db: Session, slug: str) -> Event | None:
    return db.scalar(_event_query().where(Event.slug == slug))


def _invalidate_public_event_cache(event: Event | None) -> None:
    """Drop public discovery caches after event mutations."""
    if event is None:
        return
    try:
        from app.core.cache_invalidation import invalidate_event_caches

        invalidate_event_caches(
            slug=event.slug,
            event_id=event.id,
            host_id=event.host_id,
        )
    except Exception:
        # Cache is best-effort — never fail a write path.
        pass


def _commit_refresh_event(db: Session, event_id: uuid.UUID) -> Event:
    db.commit()
    refreshed = get_event_by_id(db, event_id)
    _invalidate_public_event_cache(refreshed)
    assert refreshed is not None
    return refreshed


def build_publish_checklist(event: Event, *, preview_checked: bool = False) -> EventPublishChecklist:
    basics = bool(
        event.title
        and event.description
        and len(event.description) >= 10
    )
    category = bool(event.category_id)
    venue = bool(
        (event.venue_name or (event.venue and event.venue.name))
        or event.location_visibility == "online_only"
        or event.public_location_label
        or event.location_id
    )
    date_ok = bool(event.start_datetime and event.end_datetime and event.timezone)
    has_ticket = bool(event.ticket_types)
    # Listing cards always have brand/demo placeholders when no banner is set.
    banner = True
    refund = bool(event.refund_policy_type or event.refund_policy)
    check_in = bool(event.check_in_start_time or event.doors_open_datetime or event.start_datetime)
    seo = bool(event.seo_title or event.title) and bool(
        event.seo_description or event.short_tagline or event.description
    )
    ready = all(
        [
            basics,
            category,
            venue,
            date_ok,
            has_ticket,
            banner,
            refund,
            check_in,
            seo,
            preview_checked,
        ]
    )
    return EventPublishChecklist(
        basics_complete=basics,
        category_complete=category,
        venue_privacy_complete=venue,
        date_complete=date_ok,
        has_ticket_type=has_ticket,
        banner_ready=banner,
        refund_policy_selected=refund,
        check_in_settings_complete=check_in,
        seo_complete=seo,
        preview_checked=preview_checked,
        ready_to_submit=ready,
    )


def serialize_event(
    event: Event,
    *,
    access: AccessLevel = "host",
    include_checklist: bool = False,
    preview_checked: bool = False,
    list_mode: bool = False,
) -> dict[str, Any]:
    description = event.description or ""
    if list_mode and len(description) > 160:
        # Hover preview only needs a short blurb; keep EventPublic.description required.
        description = description[:157].rstrip() + "..."

    data: dict[str, Any] = {
        "id": event.id,
        "title": event.title,
        "slug": event.slug,
        "description": description,
        "short_tagline": getattr(event, "short_tagline", None),
        "vibe": getattr(event, "vibe", None),
        "event_type": getattr(event, "event_type", None) or "public",
        "visibility": getattr(event, "visibility", None) or "listed",
        "category_id": event.category_id,
        "primary_category_id": getattr(event, "primary_category_id", None),
        "host_id": event.host_id,
        "start_datetime": event.start_datetime,
        "end_datetime": event.end_datetime,
        "doors_open_datetime": getattr(event, "doors_open_datetime", None),
        "timezone": getattr(event, "timezone", None) or "Africa/Lagos",
        "venue_name": event.venue_name,
        "venue_type": getattr(event, "venue_type", None),
        "address": event.address,
        "city": event.city,
        "state": event.state,
        "country": getattr(event, "country", None),
        "area": getattr(event, "area", None),
        "postcode": getattr(event, "postcode", None),
        "latitude": getattr(event, "latitude", None),
        "longitude": getattr(event, "longitude", None),
        "google_place_id": getattr(event, "google_place_id", None),
        "formatted_address": getattr(event, "formatted_address", None),
        "google_maps_share_url": getattr(event, "google_maps_share_url", None),
        "google_maps_place_url": getattr(event, "google_maps_place_url", None),
        "location_id": getattr(event, "location_id", None),
        "location": None,
        "public_location_label": getattr(event, "public_location_label", None),
        "approximate_latitude": getattr(event, "approximate_latitude", None),
        "approximate_longitude": getattr(event, "approximate_longitude", None),
        "approximate_map_label": getattr(event, "approximate_map_label", None),
        "location_visibility": getattr(event, "location_visibility", None) or "full_public",
        "reveal_timing": getattr(event, "reveal_timing", None) or "immediately",
        "reveal_note": getattr(event, "reveal_note", None),
        "online_event_url": getattr(event, "online_event_url", None),
        "online_url_reveal_rule": getattr(event, "online_url_reveal_rule", None)
        or "after_payment",
        "location_map_mode": "none",
        "map_latitude": None,
        "map_longitude": None,
        "map_label": None,
        "map_open_url": None,
        "banner_url": event.banner_url,
        "mobile_banner_url": getattr(event, "mobile_banner_url", None),
        "teaser_video_url": getattr(event, "teaser_video_url", None),
        "social_share_image_url": getattr(event, "social_share_image_url", None),
        "brand_accent_override": getattr(event, "brand_accent_override", None),
        "sponsor_logo_urls": getattr(event, "sponsor_logo_urls", None),
        "capacity": event.capacity,
        "refund_policy": event.refund_policy,
        "refund_policy_type": getattr(event, "refund_policy_type", None),
        "refund_policy_text": getattr(event, "refund_policy_text", None),
        "cancellation_policy": getattr(event, "cancellation_policy", None),
        "age_restriction": event.age_restriction,
        "id_required": bool(getattr(event, "id_required", False)),
        "safety_notice": getattr(event, "safety_notice", None),
        "terms_acknowledgement": getattr(event, "terms_acknowledgement", None),
        "door_sales_allowed": bool(getattr(event, "door_sales_allowed", True)),
        "allow_merch_only_checkout": bool(
            getattr(event, "allow_merch_only_checkout", False)
        ),
        "open_ambassadors_enabled": bool(
            getattr(event, "open_ambassadors_enabled", False)
        ),
        "open_ambassador_commission_percent": getattr(
            event, "open_ambassador_commission_percent", Decimal("5.00")
        ),
        "re_entry_allowed": bool(getattr(event, "re_entry_allowed", False)),
        "check_in_start_time": getattr(event, "check_in_start_time", None),
        "check_in_end_time": getattr(event, "check_in_end_time", None),
        "dress_code": getattr(event, "dress_code", None),
        "accessibility_notes": getattr(event, "accessibility_notes", None),
        "parking_info": getattr(event, "parking_info", None),
        "what_to_expect": getattr(event, "what_to_expect", None),
        "what_to_bring": getattr(event, "what_to_bring", None),
        "prohibited_items": getattr(event, "prohibited_items", None),
        "entry_requirements": getattr(event, "entry_requirements", None),
        "status": event.status,
        "featured": event.featured,
        "seo_title": event.seo_title,
        "seo_description": event.seo_description,
        "social_share_title": getattr(event, "social_share_title", None),
        "social_share_description": getattr(event, "social_share_description", None),
        "hashtags": getattr(event, "hashtags", None),
        "discoverable_keywords": getattr(event, "discoverable_keywords", None),
        "rejection_reason": event.rejection_reason,
        "admin_flagged": bool(getattr(event, "admin_flagged_at", None)),
        "admin_flagged_at": getattr(event, "admin_flagged_at", None),
        "admin_flag_reason": (
            getattr(event, "admin_flag_reason", None)
            if access in {"admin", "host"}
            else None
        ),
        "published_at": event.published_at,
        "created_at": event.created_at,
        "category": event.category,
        "venue": None if list_mode else event.venue,
        "media": [] if list_mode else (event.media or []),
        "ticket_types": event.ticket_types or [],
        "agenda_items": []
        if list_mode
        else (getattr(event, "agenda_items", None) or []),
        "people": [] if list_mode else (getattr(event, "people", None) or []),
        "checkout_questions": []
        if list_mode
        else [
            q
            for q in (getattr(event, "checkout_questions", None) or [])
            if access in {"host", "admin"}
            or getattr(q, "status", "active") == "active"
        ],
        "host_display_name": event.host.display_name if event.host else None,
        "host_slug": event.host.slug if event.host else None,
    }
    loc = getattr(event, "location", None)
    if loc is not None:
        ancestors: list[dict[str, str]] = []
        # List cards only need kind/name/slug — skip ancestor walk (extra queries).
        if not list_mode:
            session = object_session(event) or object_session(loc)
            if session is not None:
                from app.taxonomy.service import location_ancestors

                ancestors = [
                    {"slug": a.slug, "name": a.name, "kind": a.kind}
                    for a in location_ancestors(session, loc)
                ]
        data["location"] = {
            "slug": loc.slug,
            "name": loc.name,
            "kind": loc.kind,
            "ancestors": ancestors,
        }
    apply_location_privacy(event, data, access=access)
    # Never expose place_id / formatted street publicly (can reverse to exact venue).
    if access == "public":
        data["google_place_id"] = None
        data["formatted_address"] = None
    if access in {"host", "admin"}:
        from app.events.geo import event_has_valid_coordinates

        data["has_valid_coordinates"] = event_has_valid_coordinates(event)
    if include_checklist or access in {"host", "admin"}:
        data["publish_checklist"] = build_publish_checklist(
            event, preview_checked=preview_checked
        )
    else:
        data["publish_checklist"] = None
    return data


def user_has_paid_ticket(db: Session, user: User | None, event_id: uuid.UUID) -> bool:
    if user is None:
        return False
    from app.tickets.models import Ticket

    ticket_id = db.scalar(
        select(Ticket.id).where(
            Ticket.event_id == event_id,
            Ticket.buyer_user_id == user.id,
            Ticket.status.in_(("active", "checked_in")),
        )
    )
    return ticket_id is not None


def resolve_event_access(
    db: Session,
    event: Event,
    user: User | None,
) -> AccessLevel:
    if user is None:
        return "public"
    if user_has_role(user, "super_admin") or user_has_permission(
        user, "events.approve"
    ) or user_has_permission(user, "admin.full_access"):
        return "admin"
    host = get_host_for_user_optional(db, user)
    if host is not None and host.id == event.host_id:
        return "host"
    if user_has_paid_ticket(db, user, event.id):
        return "buyer"
    return "public"


def list_categories(db: Session) -> list[EventCategory]:
    return list(
        db.scalars(
            select(EventCategory)
            .where(EventCategory.is_active.is_(True))
            .order_by(EventCategory.name)
        )
    )


def list_admin_categories(db: Session, *, include_inactive: bool = False) -> list[EventCategory]:
    q = select(EventCategory)
    if not include_inactive:
        q = q.where(EventCategory.is_active.is_(True))
    return list(db.scalars(q.order_by(EventCategory.name)))


def create_category(
    db: Session,
    *,
    user: User,
    name: str,
    slug: str | None = None,
    description: str | None = None,
) -> EventCategory:
    base = (slug or name).strip().lower().replace(" ", "-")
    if db.scalar(select(EventCategory.id).where(EventCategory.slug == base)):
        raise HTTPException(status_code=409, detail="Category slug already exists")
    row = EventCategory(
        name=name.strip(),
        slug=base,
        description=description,
        is_active=True,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="events.category_create",
        actor_user_id=user.id,
        resource_type="event_category",
        resource_id=str(row.id),
        details={"name": row.name},
    )
    db.commit()
    db.refresh(row)
    try:
        from app.core.cache_invalidation import invalidate_taxonomy_caches

        invalidate_taxonomy_caches()
    except Exception:
        pass
    return row


def update_category(
    db: Session,
    *,
    user: User,
    category_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
) -> EventCategory:
    row = db.get(EventCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if name is not None:
        row.name = name.strip()
    if description is not None:
        row.description = description
    write_audit_log(
        db,
        action="events.category_update",
        actor_user_id=user.id,
        resource_type="event_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    try:
        from app.core.cache_invalidation import invalidate_taxonomy_caches

        invalidate_taxonomy_caches()
    except Exception:
        pass
    return row


def deactivate_category(db: Session, *, user: User, category_id: uuid.UUID) -> EventCategory:
    row = db.get(EventCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")
    row.is_active = False
    write_audit_log(
        db,
        action="events.category_deactivate",
        actor_user_id=user.id,
        resource_type="event_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_category(db: Session, *, user: User, category_id: uuid.UUID) -> EventCategory:
    row = db.get(EventCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")
    row.is_active = True
    write_audit_log(
        db,
        action="events.category_restore",
        actor_user_id=user.id,
        resource_type="event_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def set_event_featured(
    db: Session, *, user: User, event_id: uuid.UUID, featured: bool
) -> Event:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event.featured = featured
    write_audit_log(
        db,
        action="events.feature" if featured else "events.unfeature",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"featured": featured},
    )
    return _commit_refresh_event(db, event_id)


def _apply_location_dual_write(db: Session, event: Event) -> None:
    """When location_id is set, fill city/state/public labels from taxonomy."""
    from app.taxonomy.models import Location
    from app.taxonomy.service import location_ancestors

    if not event.location_id:
        return
    loc = db.get(Location, event.location_id)
    if loc is None or not loc.is_active:
        raise HTTPException(status_code=400, detail="Unknown or inactive location")
    ancestors = location_ancestors(db, loc)
    by_kind = {a.kind: a for a in ancestors}
    by_kind[loc.kind] = loc
    if loc.kind == "area":
        event.city = by_kind.get("city", loc).name
        event.state = by_kind["state"].name if "state" in by_kind else event.state
        if not event.public_location_label:
            event.public_location_label = loc.name
    elif loc.kind == "city":
        event.city = loc.name
        event.state = by_kind["state"].name if "state" in by_kind else event.state
        if not event.public_location_label:
            event.public_location_label = loc.name
    elif loc.kind == "state":
        event.state = loc.name
        if not event.city:
            event.city = loc.name
        if not event.public_location_label:
            event.public_location_label = loc.name
    elif loc.kind == "country":
        if not event.public_location_label:
            event.public_location_label = loc.name


def _apply_category_dual_write(db: Session, event: Event) -> None:
    """Mirror legacy event_categories onto taxonomy primary_category_id (by slug).

    Safe no-op when taxonomy is empty or slug is missing — preserves existing
    demo/events that only have category_id set.
    """
    from app.taxonomy.models import TaxonomyCategory

    if not event.category_id:
        return
    legacy = db.get(EventCategory, event.category_id)
    if legacy is None:
        return
    tax = db.scalar(
        select(TaxonomyCategory).where(
            TaxonomyCategory.slug == legacy.slug,
            TaxonomyCategory.is_active.is_(True),
        )
    )
    if tax is not None:
        event.primary_category_id = tax.id


def _city_slug_expr():
    """SQL equivalent of Python city slugify used by discovery filters."""
    return func.replace(
        func.replace(
            func.lower(func.trim(func.coalesce(Event.city, ""))),
            " ",
            "-",
        ),
        "_",
        "-",
    )


def _state_slug_expr():
    return func.replace(
        func.replace(
            func.lower(func.trim(func.coalesce(Event.state, ""))),
            " ",
            "-",
        ),
        "_",
        "-",
    )


def list_published_events(
    db: Session,
    *,
    q: str | None = None,
    category_slug: str | None = None,
    city_slug: str | None = None,
    location_kind: str | None = None,
    location_slug: str | None = None,
    weekend: bool = False,
    paid: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
) -> list[Event]:
    """Published listed events with SQL filters, order, and limit (marketplace LIST)."""
    from datetime import UTC, datetime, timedelta

    from app.taxonomy.service import (
        descendant_location_ids,
        get_location_by_kind_slug,
    )

    now = datetime.now(UTC)
    try:
        lim = int(limit) if limit is not None else PUBLIC_EVENTS_LIST_MAX
    except (TypeError, ValueError):
        lim = PUBLIC_EVENTS_LIST_MAX
    lim = max(1, min(lim, PUBLIC_EVENTS_LIST_MAX))

    stmt = (
        _event_list_query()
        .where(Event.status == "published")
        .where(Event.visibility.in_(("listed", "approval_required")))
        .where(Event.end_datetime.is_not(None))
        .where(Event.end_datetime >= now)
    )

    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Event.title).like(needle),
                func.lower(func.coalesce(Event.city, "")).like(needle),
                func.lower(func.coalesce(Event.venue_name, "")).like(needle),
                func.lower(func.coalesce(Event.description, "")).like(needle),
            )
        )

    if category_slug:
        stmt = stmt.join(Event.category).where(EventCategory.slug == category_slug)

    if location_kind and location_slug:
        node = get_location_by_kind_slug(
            db, kind=location_kind, slug=location_slug, active_only=True
        )
        if node is None:
            return []
        allowed = list(descendant_location_ids(db, node))
        free_text = []
        if node.kind in {"city", "area"}:
            free_text.append(
                and_(
                    Event.location_id.is_(None),
                    or_(
                        _city_slug_expr() == node.slug,
                        _city_slug_expr()
                        == func.replace(
                            func.replace(
                                func.lower(func.trim(node.name)), " ", "-"
                            ),
                            "_",
                            "-",
                        ),
                    ),
                )
            )
        elif node.kind == "state":
            name_slug = func.replace(
                func.replace(func.lower(func.trim(node.name)), " ", "-"),
                "_",
                "-",
            )
            free_text.append(
                and_(
                    Event.location_id.is_(None),
                    or_(
                        _state_slug_expr() == node.slug,
                        _state_slug_expr() == name_slug,
                        _city_slug_expr() == node.slug,
                        _city_slug_expr() == name_slug,
                    ),
                )
            )
        loc_clause = Event.location_id.in_(allowed) if allowed else False
        if free_text:
            stmt = stmt.where(or_(loc_clause, *free_text))
        elif allowed:
            stmt = stmt.where(loc_clause)
        else:
            return []
    elif city_slug:
        stmt = stmt.where(_city_slug_expr() == city_slug.strip().lower())

    if weekend:
        day = now.weekday()
        days_to_fri = (4 - day) % 7
        start = (now + timedelta(days=days_to_fri)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=3)
        stmt = stmt.where(
            Event.start_datetime.is_not(None),
            Event.start_datetime >= start,
            Event.start_datetime < end,
        )

    if paid in {"free", "paid"}:
        tt = TicketType
        price_pred = tt.price <= 0 if paid == "free" else tt.price > 0
        stmt = stmt.where(
            exists(
                select(tt.id).where(
                    tt.event_id == Event.id,
                    tt.visibility == "public",
                    price_pred,
                )
            )
        )

    if sort == "newest":
        stmt = stmt.order_by(
            func.coalesce(
                Event.published_at, Event.created_at, Event.start_datetime
            ).desc()
        )
    elif sort == "featured":
        stmt = stmt.order_by(Event.featured.desc(), Event.start_datetime.asc())
    else:
        stmt = stmt.order_by(Event.start_datetime.asc())

    stmt = stmt.limit(lim)
    # join(category) may duplicate rows — unique() on the Result.
    return list(db.scalars(stmt).unique().all())


def serialize_event_list_item(event: Event) -> dict[str, Any]:
    """Marketplace card payload — EventPublic-compatible without detail nests."""
    data = serialize_event(event, access="public", list_mode=True)
    for key in (
        "what_to_expect",
        "what_to_bring",
        "prohibited_items",
        "entry_requirements",
        "parking_info",
        "accessibility_notes",
        "safety_notice",
        "terms_acknowledgement",
        "refund_policy",
        "refund_policy_text",
        "cancellation_policy",
        "seo_title",
        "seo_description",
        "social_share_title",
        "social_share_description",
        "teaser_video_url",
        "sponsor_logo_urls",
    ):
        data[key] = None
    data["ticket_types"] = [
        tt
        for tt in (event.ticket_types or [])
        if getattr(tt, "visibility", "public") == "public"
    ]
    return data


def auto_complete_due_events(
    db: Session,
    *,
    host_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
) -> int:
    """Mark published/paused events past end_datetime as completed.

    Lazy lifecycle so hosts see status ``completed`` (not lingering published
    under a date-based Past bucket) without a manual Mark completed click.
    """
    now = datetime.now(UTC)
    stmt = select(Event).where(
        Event.status.in_(("published", "paused")),
        Event.end_datetime.is_not(None),
        Event.end_datetime < now,
    )
    if host_id is not None:
        stmt = stmt.where(Event.host_id == host_id)
    if event_id is not None:
        stmt = stmt.where(Event.id == event_id)

    events = list(db.scalars(stmt).all())
    if not events:
        return 0

    from app.legacy.service import refresh_host_legacy_score
    from app.memories.service import ensure_event_memory

    host_ids: set[uuid.UUID] = set()
    for event in events:
        event.status = "completed"
        write_audit_log(
            db,
            action="events.auto_complete",
            actor_user_id=None,
            resource_type="event",
            resource_id=str(event.id),
            details={"reason": "end_datetime_passed"},
        )
        ensure_event_memory(db, event)
        host_ids.add(event.host_id)
        _invalidate_public_event_cache(event)

    for hid in host_ids:
        refresh_host_legacy_score(
            db, hid, reason="event_completed", force_history=True
        )

    db.commit()
    return len(events)


def list_host_events(db: Session, host: Host) -> list[Event]:
    auto_complete_due_events(db, host_id=host.id)
    return list(
        db.scalars(
            _event_query()
            .where(Event.host_id == host.id)
            .order_by(Event.created_at.desc())
        )
    )


def list_pending_events(db: Session) -> list[Event]:
    """Events awaiting admin attention: manual review queue or post-publish flags."""
    return list(
        db.scalars(
            _event_query()
            .where(
                or_(
                    Event.status == "pending_review",
                    Event.admin_flagged_at.isnot(None),
                )
            )
            .order_by(Event.created_at.asc())
        )
    )


def list_admin_events(db: Session) -> list[Event]:
    auto_complete_due_events(db)
    return list(db.scalars(_event_query().order_by(Event.created_at.desc())))


def _sync_venue(event: Event, venue_data) -> None:
    if venue_data is None:
        return
    payload = venue_data.model_dump()
    # Prefer event-level coords when hosts set them on the Studio form.
    if getattr(event, "latitude", None) and not payload.get("latitude"):
        payload["latitude"] = event.latitude
    if getattr(event, "longitude", None) and not payload.get("longitude"):
        payload["longitude"] = event.longitude
    if getattr(event, "country", None) and not payload.get("country"):
        payload["country"] = event.country
    if event.venue is None:
        event.venue = EventVenue(event_id=event.id, **payload)
    else:
        for key, value in payload.items():
            setattr(event.venue, key, value)
    event.venue_name = event.venue_name or payload.get("name")
    event.address = event.address or payload.get("address")
    event.city = event.city or payload.get("city")
    event.state = event.state or payload.get("state")
    if payload.get("country"):
        event.country = event.country or payload.get("country")
    if payload.get("latitude"):
        event.latitude = event.latitude or payload.get("latitude")
    if payload.get("longitude"):
        event.longitude = event.longitude or payload.get("longitude")


def _item_payload(item: Any, *, index: int) -> dict[str, Any]:
    payload = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    payload.setdefault("sort_order", index)
    return payload


def _upsert_children(
    event: Event,
    attr: str,
    model_cls: type,
    items: list[Any],
    *,
    updatable_fields: set[str],
) -> None:
    """Create/update/delete nested rows by optional id (preserve stable IDs)."""
    sess = object_session(event)
    existing = {row.id: row for row in list(getattr(event, attr) or [])}
    seen: set[uuid.UUID] = set()
    next_rows: list[Any] = []

    for index, item in enumerate(items or []):
        payload = _item_payload(item, index=index)
        row_id = payload.pop("id", None)
        if row_id and row_id in existing:
            row = existing[row_id]
            for key in updatable_fields:
                if key in payload:
                    setattr(row, key, payload[key])
            row.sort_order = payload.get("sort_order", index)
            seen.add(row_id)
            next_rows.append(row)
            continue
        # Unknown id or new row — create fresh (ignore stale client ids).
        create_payload = {
            key: payload[key]
            for key in updatable_fields
            if key in payload
        }
        create_payload["sort_order"] = payload.get("sort_order", index)
        next_rows.append(model_cls(event_id=event.id, **create_payload))

    for row_id, row in existing.items():
        if row_id in seen:
            continue
        if sess is not None:
            sess.delete(row)

    setattr(event, attr, next_rows)


def _question_has_answers(sess: Session | None, question_id: uuid.UUID) -> bool:
    if sess is None:
        return False
    from app.payments.models import OrderCheckoutAnswer

    return (
        sess.scalar(
            select(OrderCheckoutAnswer.id)
            .where(OrderCheckoutAnswer.question_id == question_id)
            .limit(1)
        )
        is not None
    )


def _sync_checkout_questions(event: Event, items: list[Any]) -> None:
    """Upsert questions; archive answered ones instead of hard-deleting."""
    sess = object_session(event)
    existing = {row.id: row for row in list(event.checkout_questions or [])}
    seen: set[uuid.UUID] = set()
    next_rows: list[EventCheckoutQuestion] = []
    now = datetime.now(UTC)

    for index, item in enumerate(items or []):
        payload = _item_payload(item, index=index)
        row_id = payload.pop("id", None)
        status = payload.get("status") or "active"
        if row_id and row_id in existing:
            row = existing[row_id]
            row.label = payload["label"]
            row.type = payload.get("type") or row.type
            row.required = bool(payload.get("required", False))
            row.options = payload.get("options")
            row.help_text = payload.get("help_text")
            row.sort_order = payload.get("sort_order", index)
            if status == "archived" and row.status != "archived":
                row.status = "archived"
                row.archived_at = now
            elif status == "active":
                row.status = "active"
                row.archived_at = None
            seen.add(row_id)
            next_rows.append(row)
            continue
        next_rows.append(
            EventCheckoutQuestion(
                event_id=event.id,
                label=payload["label"],
                type=payload.get("type") or "short_text",
                required=bool(payload.get("required", False)),
                options=payload.get("options"),
                help_text=payload.get("help_text"),
                sort_order=payload.get("sort_order", index),
                status="active",
            )
        )

    for row_id, row in existing.items():
        if row_id in seen:
            continue
        if getattr(row, "status", "active") == "archived":
            next_rows.append(row)
            continue
        if _question_has_answers(sess, row_id):
            row.status = "archived"
            row.archived_at = now
            next_rows.append(row)
        elif sess is not None:
            sess.delete(row)

    next_rows.sort(key=lambda q: (0 if q.status == "active" else 1, q.sort_order))
    event.checkout_questions = next_rows


def _sync_gallery_urls(event: Event, gallery: list[str]) -> None:
    """Add/remove gallery media by URL while preserving other media types."""
    sess = object_session(event)
    non_gallery = [m for m in list(event.media or []) if m.media_type != "gallery"]
    existing_gallery = {
        m.url: m for m in list(event.media or []) if m.media_type == "gallery"
    }
    urls = [u.strip() for u in gallery if u and str(u).strip()]
    next_gallery: list[EventMedia] = []
    for index, url in enumerate(urls):
        if url in existing_gallery:
            row = existing_gallery[url]
            row.sort_order = index
            next_gallery.append(row)
        else:
            next_gallery.append(
                EventMedia(
                    event_id=event.id,
                    url=url,
                    media_type="gallery",
                    sort_order=index,
                )
            )
    keep_urls = set(urls)
    for url, row in existing_gallery.items():
        if url not in keep_urls and sess is not None:
            sess.delete(row)
    event.media = non_gallery + next_gallery


def _sync_studio_nested(event: Event, payload: EventCreate | EventUpdate, *, replace: bool) -> None:
    _ = replace
    if getattr(payload, "venue", None) is not None:
        _sync_venue(event, payload.venue)

    if getattr(payload, "agenda_items", None) is not None:
        _upsert_children(
            event,
            "agenda_items",
            EventAgendaItem,
            payload.agenda_items,
            updatable_fields={
                "title",
                "description",
                "start_time",
                "end_time",
                "type",
                "sort_order",
            },
        )

    if getattr(payload, "people", None) is not None:
        _upsert_children(
            event,
            "people",
            EventPerson,
            payload.people,
            updatable_fields={
                "name",
                "role",
                "bio",
                "image_url",
                "social_url",
                "performance_time",
                "sort_order",
            },
        )

    if getattr(payload, "checkout_questions", None) is not None:
        _sync_checkout_questions(event, payload.checkout_questions)

    gallery = getattr(payload, "gallery_urls", None)
    if gallery is not None:
        _sync_gallery_urls(event, list(gallery))


def _normalize_refund_fields(data: dict[str, Any]) -> None:
    if data.get("refund_policy_type") and not data.get("refund_policy"):
        data["refund_policy"] = data["refund_policy_type"]
    if data.get("refund_policy") and not data.get("refund_policy_type"):
        # Back-compat: free-text refund_policy still accepted
        known = {
            "no_refunds",
            "refund_until_7_days_before",
            "refund_until_24_hours_before",
            "partial_refund_only",
            "cancelled_event_only",
            "admin_controlled",
            "custom",
        }
        if data["refund_policy"] in known:
            data["refund_policy_type"] = data["refund_policy"]


def create_event(
    db: Session,
    *,
    user: User,
    payload: EventCreate,
    host_id: uuid.UUID | None = None,
) -> Event:
    from app.users.restrictions import assert_can_create_events

    assert_can_create_events(db, user)

    if user_has_role(user, "super_admin"):
        host, _ = require_host_for_permission(
            db, user=user, host_id=host_id, permission="events.create"
        )
    else:
        host, _ = require_host_for_permission(
            db, user=user, host_id=host_id, permission="events.create"
        )

    data = payload.model_dump(exclude=NESTED_EXCLUDE)
    _normalize_refund_fields(data)
    event = Event(
        **data,
        host_id=host.id,
        slug=unique_event_slug(db, payload.title),
        status="draft",
    )
    db.add(event)
    db.flush()
    _apply_location_dual_write(db, event)
    _apply_category_dual_write(db, event)
    _sync_studio_nested(event, payload, replace=True)
    write_audit_log(
        db,
        action="events.create",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"title": event.title, "status": event.status},
    )
    refreshed = _commit_refresh_event(db, event.id)
    _notify_admin_event_lifecycle(db, refreshed, published=False)
    return refreshed


def _admin_event_context(db: Session, event: Event) -> dict[str, str]:
    from app.hosts.models import Host

    host = db.get(Host, event.host_id)
    host_name = host.display_name if host else "Host"
    when = event.start_datetime.isoformat() if event.start_datetime else ""
    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "host_name": host_name,
        "event_date": when,
        "status": event.status,
        "city": event.city or "",
    }


def _notify_admin_event_lifecycle(db: Session, event: Event, *, published: bool) -> None:
    from app.email.admin_triggers import admin_notify_new_event

    ctx = _admin_event_context(db, event)
    admin_notify_new_event(
        db,
        event_id=event.id,
        event_title=ctx["event_title"],
        host_name=ctx["host_name"],
        event_date=ctx["event_date"],
        status=ctx["status"],
        city=ctx["city"],
        published=published,
    )


def assert_can_manage_event(
    db: Session,
    user: User,
    event: Event,
    host: Host | None = None,
    *,
    permission: str | tuple[str, ...] = "events.edit",
) -> Host:
    """Allow host owner or team member with ``permission`` on this event."""
    acting_host, _ = require_host_event_permission(
        db,
        user=user,
        event_id=event.id,
        permission=permission,
        host_id=host.id if host is not None else None,
    )
    return acting_host


def _is_event_admin(user: User) -> bool:
    return user_has_permission(user, "events.approve") or user_has_permission(
        user, "admin.full_access"
    )


def _require_event_lifecycle(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    permission: str | tuple[str, ...] = "events.edit",
) -> Event:
    """Host owner, team member, or admin may perform lifecycle actions."""
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if _is_event_admin(user):
        return event
    assert_can_manage_event(db, user, event, permission=permission)
    return event


def update_event(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    payload: EventUpdate,
) -> Event:
    from app.users.restrictions import assert_can_manage_events

    assert_can_manage_events(db, user)

    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(db, user, event)

    if event.status in {"completed", "cancelled", "archived"}:
        raise HTTPException(
            status_code=400,
            detail="Completed/cancelled/archived events cannot be edited",
        )

    data = payload.model_dump(exclude_unset=True, exclude=NESTED_EXCLUDE)
    _normalize_refund_fields(data)
    if "capacity" in data:
        from app.payments.capacity import event_admission_committed

        locked = db.scalar(
            select(Event).where(Event.id == event.id).with_for_update()
        )
        if locked is None:
            raise HTTPException(status_code=404, detail="Event not found")
        event = locked
        new_cap = data["capacity"]
        if new_cap is not None:
            committed = event_admission_committed(
                db, event_id=event.id, lock_rows=True
            )
            if int(new_cap) < committed:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Cannot reduce capacity below committed seats "
                        f"({committed} sold/reserved)"
                    ),
                )
    next_start = data.get("start_datetime", event.start_datetime)
    next_end = data.get("end_datetime", event.end_datetime)
    if next_start is not None and next_end is not None and next_end <= next_start:
        raise HTTPException(
            status_code=400,
            detail="end_datetime must be after start_datetime",
        )
    explicit_slug = data.pop("slug", None)
    if explicit_slug:
        desired = slugify(str(explicit_slug))
        conflict = db.scalar(
            select(Event.id).where(Event.slug == desired, Event.id != event.id)
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Event slug already exists")
        event.slug = desired
    elif "title" in data and data["title"] and data["title"] != event.title:
        event.slug = unique_event_slug(db, data["title"])
    for key, value in data.items():
        setattr(event, key, value)
    if "location_id" in data:
        _apply_location_dual_write(db, event)
    if "category_id" in data:
        _apply_category_dual_write(db, event)
    _sync_studio_nested(event, payload, replace=False)

    # Editing a published event flags it for admin review (or sends back to queue).
    if event.status == "published":
        if get_settings().events_auto_publish_on_submit:
            event.admin_flagged_at = datetime.now(UTC)
            event.admin_flag_reason = EDIT_AFTER_PUBLISH_FLAG_REASON
            event.admin_flagged_by_user_id = None
        else:
            event.status = "pending_review"
            event.published_at = None

    write_audit_log(
        db,
        action="events.update",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
    )
    return _commit_refresh_event(db, event.id)


def _event_has_sales(event: Event) -> bool:
    return any((tt.quantity_sold or 0) > 0 for tt in (event.ticket_types or []))


def pause_event(db: Session, *, user: User, event_id: uuid.UUID) -> Event:
    event = _require_event_lifecycle(db, user=user, event_id=event_id)
    if event.status != "published":
        raise HTTPException(status_code=400, detail="Only published events can be paused")
    event.status = "paused"
    write_audit_log(
        db,
        action="events.pause",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
    )
    return _commit_refresh_event(db, event.id)


def resume_event(db: Session, *, user: User, event_id: uuid.UUID) -> Event:
    """Restore a paused event to published (admin or host)."""
    event = _require_event_lifecycle(db, user=user, event_id=event_id)
    if event.status != "paused":
        raise HTTPException(status_code=400, detail="Only paused events can be resumed")
    event.status = "published"
    if event.published_at is None:
        event.published_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="events.resume",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
    )
    return _commit_refresh_event(db, event.id)


def postpone_event(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    start_datetime: datetime,
    end_datetime: datetime,
) -> Event:
    """Move start/end for a live listing without re-review or status change.

    Related door/check-in times shift by the same delta when set.
    """
    event = _require_event_lifecycle(db, user=user, event_id=event_id)
    if event.status not in {"published", "paused"}:
        raise HTTPException(
            status_code=400,
            detail="Only published or paused events can be postponed",
        )

    def _aware(dt: datetime) -> datetime:
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    start_datetime = _aware(start_datetime)
    end_datetime = _aware(end_datetime)
    if end_datetime <= start_datetime:
        raise HTTPException(
            status_code=400,
            detail="end_datetime must be after start_datetime",
        )

    old_start = _aware(event.start_datetime)
    old_end = _aware(event.end_datetime)
    delta = start_datetime - old_start

    if event.doors_open_datetime is not None:
        event.doors_open_datetime = _aware(event.doors_open_datetime) + delta
    if event.check_in_start_time is not None:
        event.check_in_start_time = _aware(event.check_in_start_time) + delta
    if event.check_in_end_time is not None:
        event.check_in_end_time = _aware(event.check_in_end_time) + delta

    event.start_datetime = start_datetime
    event.end_datetime = end_datetime

    write_audit_log(
        db,
        action="events.postpone",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={
            "old_start": old_start.isoformat(),
            "old_end": old_end.isoformat(),
            "new_start": start_datetime.isoformat(),
            "new_end": end_datetime.isoformat(),
            "status": event.status,
        },
    )
    return _commit_refresh_event(db, event.id)


def cancel_event(db: Session, *, user: User, event_id: uuid.UUID) -> Event:
    event = _require_event_lifecycle(
        db, user=user, event_id=event_id, permission="events.cancel"
    )
    if event.status in {"completed", "cancelled", "archived"}:
        raise HTTPException(status_code=400, detail="Event cannot be cancelled")
    locked = db.scalar(
        select(Event).where(Event.id == event.id).with_for_update()
    )
    if locked is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event = locked
    if event.status in {"completed", "cancelled", "archived"}:
        raise HTTPException(status_code=400, detail="Event cannot be cancelled")
    event.status = "cancelled"
    db.flush()
    # Commit cancellation before locking pending orders so payment finalization
    # cannot observe a published event while holding the order row lock.
    db.commit()
    event = get_event_by_id(db, event.id)
    assert event is not None

    from app.payments.reservations import invalidate_event_pending_reservations

    invalidate_event_pending_reservations(
        db, event_id=event.id, reason="event_cancelled", actor_user_id=user.id
    )
    write_audit_log(
        db,
        action="events.cancel",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"had_sales": _event_has_sales(event)},
    )
    _enqueue_event_cancelled_emails(db, event)
    return _commit_refresh_event(db, event.id)


def _enqueue_event_cancelled_emails(db: Session, event: Event) -> None:
    """Notify active ticket holders — public event title only, no private venue."""
    from app.email.service import enqueue_template
    from app.tickets.models import Ticket
    from app.users.models import User as UserModel

    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.event_id == event.id,
                Ticket.status.in_(("active", "checked_in")),
            )
        )
    )
    seen: set[uuid.UUID] = set()
    for ticket in tickets:
        if ticket.buyer_user_id in seen:
            continue
        seen.add(ticket.buyer_user_id)
        buyer = db.get(UserModel, ticket.buyer_user_id)
        if buyer is None:
            continue
        if buyer.email:
            enqueue_template(
                db,
                template="ticket_event_cancelled",
                to=buyer.email,
                recipient_user_id=buyer.id,
                dedupe_key=f"event:{event.id}:cancelled:user:{buyer.id}",
                context={"event_title": event.title},
            )
        from app.notifications.service import notify_user

        notify_user(
            db,
            user_id=buyer.id,
            kind="ticket.event_cancelled",
            title="Event cancelled on Pàdéyá",
            body=f"{event.title} was cancelled. Check your tickets for next steps.",
            link_path="/dashboard/tickets",
            dedupe_key=f"event:{event.id}:cancelled:notif:{buyer.id}",
        )


def archive_event(db: Session, *, user: User, event_id: uuid.UUID) -> Event:
    """Archive completed/cancelled events, or unused draft/rejected drafts.

    Never hard-delete paid events. Drafts with no sales may be soft-archived.
    """
    event = _require_event_lifecycle(
        db, user=user, event_id=event_id, permission="events.archive"
    )
    if event.status in {"draft", "rejected"}:
        if _event_has_sales(event):
            raise HTTPException(
                status_code=400,
                detail="Events with ticket sales cannot be archived as drafts — cancel instead",
            )
    elif event.status not in {"completed", "cancelled"}:
        raise HTTPException(
            status_code=400,
            detail="Only draft, rejected, completed, or cancelled events can be archived",
        )
    previous_status = event.status
    event.status = "archived"
    write_audit_log(
        db,
        action="events.archive",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"had_sales": _event_has_sales(event), "from_status": previous_status},
    )
    return _commit_refresh_event(db, event.id)


def discard_event(db: Session, *, user: User, event_id: uuid.UUID) -> None:
    """Hard-delete draft/rejected events with no ticket sales only."""
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(db, user, event)
    if event.status not in {"draft", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Only draft or rejected events can be discarded",
        )
    if _event_has_sales(event):
        raise HTTPException(
            status_code=400,
            detail="Events with ticket sales cannot be discarded — cancel instead",
        )
    event_id_str = str(event.id)
    write_audit_log(
        db,
        action="events.discard",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=event_id_str,
        details={"title": event.title, "slug": event.slug},
    )
    db.delete(event)
    db.commit()


def restore_archived_event(db: Session, *, user: User, event_id: uuid.UUID) -> Event:
    """Restore an archived event to draft (unused) or cancelled (had lifecycle end)."""
    event = _require_event_lifecycle(
        db, user=user, event_id=event_id, permission="events.archive"
    )
    if event.status != "archived":
        raise HTTPException(status_code=400, detail="Only archived events can be restored")

    # Prefer draft for unused archives; otherwise cancelled so hosts can re-open ops carefully.
    next_status = "draft" if not _event_has_sales(event) else "cancelled"
    previous = event.status
    event.status = next_status
    write_audit_log(
        db,
        action="events.restore_archive",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"from_status": previous, "to_status": next_status},
    )
    return _commit_refresh_event(db, event.id)


def delete_event_media(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    media_id: uuid.UUID,
) -> Event:
    """Remove one media row from an event (gallery/banner/etc.)."""
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(db, user, event)

    media = db.scalar(
        select(EventMedia).where(
            EventMedia.id == media_id,
            EventMedia.event_id == event_id,
        )
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")

    media_type = media.media_type
    media_url = media.url
    if event.banner_url == media_url:
        event.banner_url = None
    if getattr(event, "mobile_banner_url", None) == media_url:
        event.mobile_banner_url = None
    if getattr(event, "social_share_image_url", None) == media_url:
        event.social_share_image_url = None

    write_audit_log(
        db,
        action="events.media_delete",
        actor_user_id=user.id,
        resource_type="event_media",
        resource_id=str(media.id),
        details={"event_id": str(event_id), "media_type": media_type, "url": media_url},
    )
    db.delete(media)
    return _commit_refresh_event(db, event_id)


def deactivate_ticket_type(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
) -> TicketType:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(db, user, event)
    ticket = db.scalar(
        select(TicketType).where(
            TicketType.id == ticket_type_id,
            TicketType.event_id == event_id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket type not found")
    ticket.status = "inactive"
    write_audit_log(
        db,
        action="events.ticket_type_deactivate",
        actor_user_id=user.id,
        resource_type="ticket_type",
        resource_id=str(ticket.id),
    )
    db.commit()
    db.refresh(ticket)
    _invalidate_public_event_cache(event)
    return ticket


def delete_ticket_type(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
) -> None:
    """Hard-delete unused ticket types only (no sales/reservations)."""
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(db, user, event)
    ticket = db.scalar(
        select(TicketType).where(
            TicketType.id == ticket_type_id,
            TicketType.event_id == event_id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket type not found")
    if (ticket.quantity_sold or 0) > 0 or (ticket.quantity_reserved or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Ticket type has sales or holds — deactivate instead",
        )
    write_audit_log(
        db,
        action="events.ticket_type_delete",
        actor_user_id=user.id,
        resource_type="ticket_type",
        resource_id=str(ticket.id),
        details={"name": ticket.name, "type": ticket.type},
    )
    db.delete(ticket)
    db.commit()
    _invalidate_public_event_cache(event)


def submit_event_for_review(db: Session, *, user: User, event_id: uuid.UUID) -> Event:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(
        db, user, event, permission=("events.publish", "events.edit")
    )

    if event.status not in {"draft", "rejected", "paused"}:
        raise HTTPException(
            status_code=400,
            detail="Only draft, rejected, or paused events can be submitted",
        )
    event.rejection_reason = None
    if get_settings().events_auto_publish_on_submit:
        event.status = "published"
        event.published_at = datetime.now(UTC)
        event.admin_flagged_at = datetime.now(UTC)
        event.admin_flag_reason = AUTO_PUBLISH_REVIEW_FLAG_REASON
        event.admin_flagged_by_user_id = None
        write_audit_log(
            db,
            action="events.auto_publish",
            actor_user_id=user.id,
            resource_type="event",
            resource_id=str(event.id),
        )
        refreshed = _commit_refresh_event(db, event.id)
        _notify_admin_event_lifecycle(db, refreshed, published=True)
        return refreshed

    event.status = "pending_review"
    write_audit_log(
        db,
        action="events.submit_review",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
    )
    return _commit_refresh_event(db, event.id)


def approve_event(db: Session, *, user: User, event_id: uuid.UUID) -> Event:
    if not (
        user_has_permission(user, "events.approve")
        or user_has_role(user, "super_admin")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status == "published":
        if event.admin_flagged_at is not None:
            event.admin_flagged_at = None
            event.admin_flag_reason = None
            event.admin_flagged_by_user_id = None
            write_audit_log(
                db,
                action="events.review_cleared",
                actor_user_id=user.id,
                resource_type="event",
                resource_id=str(event.id),
            )
            return _commit_refresh_event(db, event.id)
        return event
    if event.status != "pending_review":
        raise HTTPException(status_code=400, detail="Event is not pending review")
    event.status = "published"
    event.published_at = datetime.now(UTC)
    event.rejection_reason = None
    write_audit_log(
        db,
        action="events.approve",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
    )
    refreshed = _commit_refresh_event(db, event.id)
    _notify_admin_event_lifecycle(db, refreshed, published=True)
    return refreshed


def reject_event(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    payload: EventRejectRequest,
) -> Event:
    if not (
        user_has_permission(user, "events.approve")
        or user_has_role(user, "super_admin")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status == "pending_review":
        event.status = "rejected"
        event.rejection_reason = payload.reason
        event.published_at = None
    elif event.status == "published" and event.admin_flagged_at is not None:
        event.status = "rejected"
        event.rejection_reason = payload.reason
        event.published_at = None
        event.admin_flagged_at = None
        event.admin_flag_reason = None
        event.admin_flagged_by_user_id = None
    else:
        raise HTTPException(
            status_code=400,
            detail="Event is not pending review or flagged for post-publish review",
        )
    write_audit_log(
        db,
        action="events.reject",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"reason": payload.reason},
    )
    return _commit_refresh_event(db, event.id)


def flag_event(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    reason: str,
) -> Event:
    """Mark an event for admin attention without changing publish status."""
    if not _is_event_admin(user):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    cleaned = reason.strip()
    if len(cleaned) < 3:
        raise HTTPException(status_code=400, detail="Flag reason is required")
    event.admin_flagged_at = datetime.now(UTC)
    event.admin_flag_reason = cleaned[:2000]
    event.admin_flagged_by_user_id = user.id
    write_audit_log(
        db,
        action="events.flag",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"reason": cleaned[:500]},
    )
    return _commit_refresh_event(db, event.id)


def clear_event_flag(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    reason: str | None = None,
) -> Event:
    if not _is_event_admin(user):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.admin_flagged_at is None:
        return event
    event.admin_flagged_at = None
    event.admin_flag_reason = None
    event.admin_flagged_by_user_id = None
    write_audit_log(
        db,
        action="events.clear_flag",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"reason": (reason or "").strip()[:500] or None},
    )
    return _commit_refresh_event(db, event.id)


def upload_host_media_file(
    db: Session,
    *,
    user: User,
    data: bytes,
    filename: str,
    content_type: str,
    media_type: str = "gallery",
) -> dict[str, Any]:
    """Stage a public image upload.

    Profile photos (avatar/logo, or legacy `other` when the user has no host)
    use account storage so fans can upload without host onboarding. All other
    media types still require a host profile.
    """
    kind = (media_type or "gallery").strip().lower()
    from app.hosts.service import get_host_by_user_id

    host = get_host_by_user_id(db, user.id)
    is_profile_kind = kind in {"avatar", "logo"}
    # Older passport UI uploaded with media_type=other — allow fans through.
    fan_profile_upload = host is None and kind in {"avatar", "logo", "other"}

    if is_profile_kind or fan_profile_upload:
        from app.users.avatar_upload import upload_and_apply_account_avatar

        return upload_and_apply_account_avatar(
            db,
            user=user,
            data=data,
            filename=filename,
            content_type=content_type,
        )

    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission=("events.create", "events.edit")
    )
    if kind not in {
        "banner",
        "mobile_banner",
        "gallery",
        "teaser",
        "sponsor",
        "social_share",
        "other",
    }:
        raise HTTPException(status_code=400, detail="Invalid media_type")
    storage = get_public_media_storage()
    try:
        stored = storage.store_bytes(
            data=data,
            filename=filename,
            content_type=content_type,
            folder=host_public_folder(host.id, kind),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "url": stored.url,
        "key": stored.key,
        "media_type": kind,
        "event_id": None,
    }


def upload_event_media_file(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    data: bytes,
    filename: str,
    content_type: str,
    media_type: str = "gallery",
    alt_text: str | None = None,
    set_as_banner: bool = False,
) -> Event:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(db, user, event)

    if media_type not in {
        "banner",
        "mobile_banner",
        "gallery",
        "teaser",
        "sponsor",
        "social_share",
        "other",
    }:
        raise HTTPException(status_code=400, detail="Invalid media_type")

    storage = get_public_media_storage()
    try:
        stored = storage.store_bytes(
            data=data,
            filename=filename,
            content_type=content_type,
            folder=event_public_folder(event.id, media_type),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media = EventMedia(
        event_id=event.id,
        url=stored.url,
        media_type=media_type,
        alt_text=alt_text,
        sort_order=len(event.media or []),
    )
    db.add(media)
    if set_as_banner or media_type == "banner":
        event.banner_url = stored.url
    if media_type == "mobile_banner":
        event.mobile_banner_url = stored.url
    if media_type == "social_share":
        event.social_share_image_url = stored.url
    return _commit_refresh_event(db, event.id)


def add_event_media(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    payload: EventMediaCreate,
) -> Event:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(db, user, event)

    storage = get_public_media_storage()
    folder = event_public_folder(event.id, payload.media_type)
    if payload.url:
        stored = storage.store_remote_url(url=payload.url, folder=folder)
    elif payload.filename:
        stored = storage.build_placeholder_url(
            filename=payload.filename, folder=folder
        )
    else:
        raise HTTPException(status_code=400, detail="Provide url or filename")

    media = EventMedia(
        event_id=event.id,
        url=stored.url,
        media_type=payload.media_type,
        alt_text=payload.alt_text,
        sort_order=payload.sort_order,
    )
    db.add(media)
    if payload.set_as_banner or payload.media_type == "banner":
        event.banner_url = stored.url
    if payload.media_type == "mobile_banner":
        event.mobile_banner_url = stored.url
    if payload.media_type == "social_share":
        event.social_share_image_url = stored.url
    return _commit_refresh_event(db, event.id)


def create_ticket_type(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    payload: TicketTypeCreate,
) -> TicketType:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(
        db,
        user,
        event,
        permission=(
            "tickets.manage_pricing",
            "tickets.manage_capacity",
            "events.edit",
        ),
    )

    ticket = TicketType(event_id=event.id, **payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    _invalidate_public_event_cache(event)
    return ticket


def update_ticket_type(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    payload: TicketTypeUpdate,
) -> TicketType:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = assert_can_manage_event(
        db,
        user,
        event,
        permission=(
            "tickets.manage_pricing",
            "tickets.manage_capacity",
            "events.edit",
        ),
    )

    ticket = db.scalar(
        select(TicketType).where(
            TicketType.id == ticket_type_id,
            TicketType.event_id == event_id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket type not found")

    data = payload.model_dump(exclude_unset=True)
    # After sales, block structural changes that would corrupt existing orders.
    # Impersonation with host_events scope may override (audited below).
    from app.admin.impersonation_scopes import SCOPE_HOST_EVENTS
    from app.auth.impersonation_context import get_impersonation_context

    ctx = get_impersonation_context()
    structural_override = bool(
        ctx is not None and ctx.has_scope(SCOPE_HOST_EVENTS)
    )
    if (
        not structural_override
        and ((ticket.quantity_sold or 0) > 0 or (ticket.quantity_reserved or 0) > 0)
    ):
        protected = {
            "price",
            "type",
            "name",
            "quantity",
            "seats_per_unit",
            "min_per_order",
            "max_per_order",
        }
        blocked = sorted(set(data) & protected)
        if blocked:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot change "
                    + ", ".join(blocked)
                    + " after sales — deactivate the ticket type instead"
                ),
            )

    for key, value in data.items():
        setattr(ticket, key, value)
    write_audit_log(
        db,
        action="events.ticket_type_update",
        actor_user_id=user.id,
        resource_type="ticket_type",
        resource_id=str(ticket.id),
        details={
            "fields": list(data.keys()),
            **(
                {
                    "impersonation_id": str(ctx.impersonation_id),
                    "actor_admin_id": str(ctx.actor_admin_id),
                    "structural_override": True,
                }
                if structural_override
                and (
                    (ticket.quantity_sold or 0) > 0
                    or (ticket.quantity_reserved or 0) > 0
                )
                else {}
            ),
        },
    )
    db.commit()
    db.refresh(ticket)
    _invalidate_public_event_cache(event)
    return ticket


def list_ticket_types(db: Session, *, user: User, event_id: uuid.UUID) -> list[TicketType]:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = get_host_for_user_optional(db, user)
    if event.status == "published" and (host is None or host.id != event.host_id):
        return [tt for tt in event.ticket_types if tt.visibility == "public"]
    if host is None or host.id != event.host_id:
        if not user_has_role(user, "super_admin"):
            raise HTTPException(status_code=403, detail="Not allowed")
    return list(event.ticket_types)


def get_host_for_user_optional(db: Session, user: User) -> Host | None:
    from app.hosts.service import get_host_by_user_id

    return get_host_by_user_id(db, user.id)


def public_event_detail(db: Session, slug: str) -> Event:
    from app.core.http_errors import raise_not_found

    event = get_event_by_slug(db, slug)
    # Completed events stay publicly reachable for Past Event + Memories UX.
    if event is None or event.status not in {"published", "completed"}:
        # Privacy-safe: do not distinguish missing vs unpublished/deleted.
        raise_not_found()
    return event
