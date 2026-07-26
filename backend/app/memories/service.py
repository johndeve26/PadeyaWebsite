"""Event Memories business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host
from app.hosts.service import require_user_host
from app.legacy.service import get_host_by_slug
from app.memories.albums import album_is_seo_indexable, memory_counts
from app.memories.constants import (
    ATTENDED_TICKET_STATUSES,
    OWNED_TICKET_STATUSES,
    TOP_REVIEWS_LIMIT,
)
from app.memories.eligibility import fan_eligibility
from app.memories.image_processing import validate_external_gallery_url
from app.memories.models import EventMemory, EventMemoryMedia
from app.memories.schemas import EventMemoryUpdate, MemoryModerateRequest
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PUBLIC
from app.reviews.models import VerifiedReview
from app.reviews.service import serialize_review
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import user_has_permission


def ensure_event_memory(db: Session, event: Event) -> EventMemory:
    """Create a published memory row for a completed (or live) event if missing."""
    existing = db.scalar(
        select(EventMemory).where(EventMemory.event_id == event.id)
    )
    if existing is not None:
        return existing

    now = datetime.now(UTC)
    memory = EventMemory(
        event_id=event.id,
        host_id=event.host_id,
        status="published",
        published_at=now,
        moderation_status="none",
    )
    db.add(memory)
    db.flush()
    return memory


def get_memory_by_event_id(db: Session, event_id: UUID) -> EventMemory | None:
    return db.scalar(select(EventMemory).where(EventMemory.event_id == event_id))


def invalidate_memory_caches(event: Event | None) -> None:
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
        pass
    try:
        from app.core.frontend_revalidate import notify_memories_frontend_revalidate

        notify_memories_frontend_revalidate(slug=event.slug)
    except Exception:
        pass


def _require_host_owns_event(db: Session, user: User, event: Event) -> Host:
    host = require_user_host(db, user)
    if host.id != event.host_id and not user_has_permission(user, "admin.full_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to edit this event memory",
        )
    return host


def _is_publicly_visible(memory: EventMemory, event: Event) -> bool:
    # Public album pages are post-event only (completed).
    if event.status != "completed":
        return False
    if memory.status != "published":
        return False
    if memory.moderation_status == "removed":
        return False
    return True


def _attendance_stats(db: Session, event_id: UUID) -> dict:
    tickets_sold = int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.event_id == event_id,
                Ticket.status.in_(OWNED_TICKET_STATUSES),
            )
        )
        or 0
    )
    checked_in = int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.event_id == event_id,
                Ticket.status.in_(ATTENDED_TICKET_STATUSES),
            )
        )
        or 0
    )
    rate: Decimal | None = None
    if tickets_sold > 0:
        rate = (Decimal(checked_in) / Decimal(tickets_sold) * Decimal("100")).quantize(
            Decimal("0.1")
        )
    return {
        "tickets_sold": tickets_sold,
        "checked_in": checked_in,
        "check_in_rate": rate,
    }


def _event_verified_rating(db: Session, event_id: UUID) -> tuple[Decimal | None, int]:
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    event = db.get(Event, event_id)
    rows = list(
        db.scalars(
            select(VerifiedReview).where(
                VerifiedReview.event_id == event_id,
                VerifiedReview.status == "visible",
            )
        )
    )
    if event is not None:
        rows = [
            r
            for r in rows
            if not is_user_owner_of_host(
                db, user_id=r.reviewer_user_id, host_profile_id=event.host_id
            )
        ]
    count = len(rows)
    if not rows:
        return None, count
    avg = sum(int(r.rating) for r in rows) / count
    return Decimal(str(avg)).quantize(Decimal("0.1")), count


def _top_event_reviews(db: Session, event_id: UUID) -> list[dict]:
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    event = db.get(Event, event_id)
    reviews = list(
        db.scalars(
            select(VerifiedReview)
            .where(
                VerifiedReview.event_id == event_id,
                VerifiedReview.status == "visible",
            )
            .order_by(VerifiedReview.rating.desc(), VerifiedReview.created_at.desc())
        )
    )
    if event is not None:
        reviews = [
            r
            for r in reviews
            if not is_user_owner_of_host(
                db, user_id=r.reviewer_user_id, host_profile_id=event.host_id
            )
        ]
    return [serialize_review(db, r) for r in reviews[:TOP_REVIEWS_LIMIT]]


def _upcoming_host_events(db: Session, host_id: UUID, *, exclude_event_id: UUID) -> list[dict]:
    now = datetime.now(UTC)
    events = db.scalars(
        select(Event)
        .where(
            Event.host_id == host_id,
            Event.status == "published",
            Event.id != exclude_event_id,
            Event.end_datetime >= now,
        )
        .order_by(Event.start_datetime.asc())
        .limit(3)
    ).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "slug": e.slug,
            "start_datetime": e.start_datetime,
            "city": e.city,
            "banner_url": e.banner_url,
        }
        for e in events
    ]


def _photo_attribution_from_map(
    media: EventMemoryMedia,
    *,
    passport_by_user: dict,
) -> tuple[str | None, bool]:
    if media.uploader_role != "fan":
        return None, False
    if media.uploader_user_id is None:
        return None, True
    passport = passport_by_user.get(media.uploader_user_id)
    if passport is not None and passport.visibility == VISIBILITY_PUBLIC:
        name = (passport.display_name or "").strip()
        if name:
            return name, True
    return None, True


def _photo_attribution(db: Session, media: EventMemoryMedia) -> tuple[str | None, bool]:
    if media.uploader_role != "fan":
        return None, False
    if media.uploader_user_id is None:
        return None, True
    passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == media.uploader_user_id)
    )
    return _photo_attribution_from_map(
        media, passport_by_user={media.uploader_user_id: passport} if passport else {}
    )


def _serialize_photo(
    db: Session,
    media: EventMemoryMedia,
    *,
    include_private: bool = False,
    passport_by_user: dict | None = None,
) -> dict:
    if passport_by_user is not None:
        attribution, verified = _photo_attribution_from_map(
            media, passport_by_user=passport_by_user
        )
    else:
        attribution, verified = _photo_attribution(db, media)
    return {
        "id": media.id,
        "media_type": media.media_type,
        "url": media.url,
        "thumbnail_url": media.thumbnail_url or media.url,
        "storage_key": media.storage_key if include_private else None,
        "label": media.label,
        "caption": media.caption,
        "sort_order": media.sort_order,
        "uploader_role": media.uploader_role or "host",
        "is_cover": bool(getattr(media, "is_cover", False)),
        "status": getattr(media, "status", None) or "active",
        "width": getattr(media, "width", None),
        "height": getattr(media, "height", None),
        "mime_type": getattr(media, "mime_type", None),
        "size_bytes": media.size_bytes if include_private else None,
        "attribution": attribution,
        "verified_attendee": verified and media.uploader_role == "fan",
        "created_at": media.created_at,
    }


def serialize_memory(
    db: Session,
    memory: EventMemory,
    *,
    include_private: bool = False,
) -> dict:
    event = db.get(Event, memory.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = db.get(Host, memory.host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")

    rating, review_count = _event_verified_rating(db, event.id)
    media_rows = sorted(memory.media, key=lambda x: (x.sort_order, x.created_at))
    if not include_private:
        media_rows = [m for m in media_rows if (m.status or "active") == "active"]
    else:
        media_rows = [m for m in media_rows if (m.status or "active") != "removed"]

    fan_ids = {
        m.uploader_user_id
        for m in media_rows
        if m.uploader_role == "fan" and m.uploader_user_id is not None
    }
    passport_by_user: dict = {}
    if fan_ids:
        for passport in db.scalars(
            select(FanPassport).where(FanPassport.user_id.in_(fan_ids))
        ).all():
            passport_by_user[passport.user_id] = passport

    media = [
        _serialize_photo(
            db,
            m,
            include_private=include_private,
            passport_by_user=passport_by_user,
        )
        for m in media_rows
    ]
    host_media = [m for m in media if m["uploader_role"] == "host"]
    community_media = [m for m in media if m["uploader_role"] == "fan"]
    counts = memory_counts(db, memory.id)

    return {
        "id": memory.id,
        "event_id": memory.event_id,
        "host_id": memory.host_id,
        "status": memory.status,
        "host_recap_note": memory.host_recap_note,
        "external_gallery_url": memory.external_gallery_url,
        "external_gallery_label": memory.external_gallery_label,
        "moderation_status": memory.moderation_status,
        "event_title": event.title,
        "event_slug": event.slug,
        "start_datetime": event.start_datetime,
        "end_datetime": event.end_datetime,
        "venue_name": event.venue_name,
        "city": event.city,
        "banner_url": event.banner_url,
        "host_display_name": host.display_name,
        "host_username": host.slug,
        "attendance": _attendance_stats(db, event.id),
        "verified_rating": rating,
        "review_count": review_count,
        "top_reviews": _top_event_reviews(db, event.id),
        "media": media,
        "host_media": host_media,
        "community_media": community_media,
        "counts": counts,
        "upcoming_events": _upcoming_host_events(db, host.id, exclude_event_id=event.id),
        "share_path": f"/@{host.slug}/memories/{event.slug}",
        "memories_path": f"/events/{event.slug}/memories",
        "published_at": memory.published_at,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
        "seo_indexable": album_is_seo_indexable(db, memory, event),
    }


def get_public_memory(db: Session, *, username: str, event_slug: str) -> dict:
    host = get_host_by_slug(db, username)
    if host is None or host.status != "active":
        raise HTTPException(status_code=404, detail="Memory not found")

    event = db.scalar(
        select(Event).where(Event.host_id == host.id, Event.slug == event_slug)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    memory = get_memory_by_event_id(db, event.id)
    if memory is None or not _is_publicly_visible(memory, event):
        raise HTTPException(status_code=404, detail="Memory not found")

    return serialize_memory(db, memory)


def get_public_memory_by_slug(db: Session, *, event_slug: str) -> dict:
    event = db.scalar(select(Event).where(Event.slug == event_slug))
    if event is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    if event.status != "completed":
        raise HTTPException(status_code=404, detail="Memory not found")
    memory = get_memory_by_event_id(db, event.id)
    if memory is None:
        memory = ensure_event_memory(db, event)
        db.commit()
        db.refresh(memory)
    if not _is_publicly_visible(memory, event):
        raise HTTPException(status_code=404, detail="Memory not found")
    return serialize_memory(db, memory)


def get_host_memory(db: Session, *, user: User, event_id: UUID) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)

    if event.status not in {"published", "paused", "completed"}:
        raise HTTPException(
            status_code=400,
            detail="Memory is available after the event is published",
        )

    memory = ensure_event_memory(db, event)
    db.commit()
    db.refresh(memory)
    return serialize_memory(db, memory, include_private=True)


def update_host_memory(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    payload: EventMemoryUpdate,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)

    if event.status not in {"published", "paused", "completed"}:
        raise HTTPException(
            status_code=400,
            detail="Only published, paused, or completed events can have editable memories",
        )

    memory = ensure_event_memory(db, event)
    if memory.status == "hidden" and not user_has_permission(user, "admin.full_access"):
        raise HTTPException(
            status_code=403,
            detail="This memory was hidden by moderation",
        )

    data = payload.model_dump(exclude_unset=True)
    if "host_recap_note" in data:
        note = data["host_recap_note"]
        memory.host_recap_note = (note.strip() if isinstance(note, str) else None) or None
    if "external_gallery_url" in data:
        try:
            memory.external_gallery_url = validate_external_gallery_url(
                data["external_gallery_url"]
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "external_gallery_label" in data:
        memory.external_gallery_label = data["external_gallery_label"]

    write_audit_log(
        db,
        action="memories.host.update",
        actor_user_id=user.id,
        resource_type="event_memory",
        resource_id=str(memory.id),
    )
    db.commit()
    db.refresh(memory)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=True)


def delete_memory_media(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    media_id: UUID,
) -> dict:
    from app.memories.photos import delete_own_or_host_photo

    return delete_own_or_host_photo(
        db, user=user, event_id=event_id, media_id=media_id
    )


def list_public_host_memories(db: Session, host_id: UUID) -> list[dict]:
    rows = db.scalars(
        select(EventMemory)
        .where(
            EventMemory.host_id == host_id,
            EventMemory.status == "published",
            EventMemory.moderation_status != "removed",
        )
        .order_by(EventMemory.published_at.desc())
    ).all()

    cards: list[dict] = []
    for memory in rows:
        event = db.get(Event, memory.event_id)
        if event is None or event.status != "completed":
            continue
        if memory.moderation_status == "removed":
            continue
        host = db.get(Host, memory.host_id)
        if host is None:
            continue
        rating, _ = _event_verified_rating(db, event.id)
        cards.append(
            {
                "id": memory.id,
                "event_id": event.id,
                "event_title": event.title,
                "event_slug": event.slug,
                "start_datetime": event.start_datetime,
                "city": event.city,
                "banner_url": event.banner_url,
                "share_path": f"/@{host.slug}/memories/{event.slug}",
                "verified_rating": rating,
            }
        )
    return cards


def list_admin_memories(db: Session, user: User) -> list[dict]:
    if not user_has_permission(user, "memories.moderate") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")

    rows = db.scalars(
        select(EventMemory).order_by(EventMemory.created_at.desc()).limit(100)
    ).all()
    return [serialize_memory(db, m, include_private=True) for m in rows]


def list_admin_photos(db: Session, user: User, *, limit: int = 100) -> list[dict]:
    if not user_has_permission(user, "memories.moderate") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")

    lim = max(1, min(int(limit or 100), 200))
    rows = list(
        db.execute(
            select(EventMemoryMedia, EventMemory, Event)
            .join(EventMemory, EventMemory.id == EventMemoryMedia.memory_id)
            .join(Event, Event.id == EventMemory.event_id)
            .order_by(EventMemoryMedia.created_at.desc())
            .limit(lim)
        ).all()
    )
    out: list[dict] = []
    for media, memory, event in rows:
        out.append(
            {
                "id": media.id,
                "memory_id": memory.id,
                "event_id": event.id,
                "event_title": event.title,
                "event_slug": event.slug,
                "uploader_role": media.uploader_role,
                "uploader_user_id": media.uploader_user_id,
                "status": media.status,
                "url": media.url,
                "thumbnail_url": media.thumbnail_url or media.url,
                "caption": media.caption,
                "created_at": media.created_at,
                "hidden_by": media.hidden_by,
            }
        )
    return out


def moderate_memory(
    db: Session,
    *,
    user: User,
    memory_id: UUID,
    payload: MemoryModerateRequest,
) -> dict:
    if not user_has_permission(user, "memories.moderate") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")

    memory = db.get(EventMemory, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    now = datetime.now(UTC)
    if payload.action == "hide":
        memory.status = "hidden"
        memory.moderation_status = "removed"
    elif payload.action == "unhide":
        memory.status = "published"
        memory.moderation_status = "approved"
        if memory.published_at is None:
            memory.published_at = now
    elif payload.action == "flag":
        memory.moderation_status = "flagged"
    elif payload.action == "approve":
        memory.moderation_status = "approved"
        if memory.status == "hidden":
            memory.status = "published"
    else:
        raise HTTPException(status_code=400, detail="Unsupported moderation action")

    memory.moderation_note = payload.note
    memory.moderated_by_user_id = user.id
    memory.moderated_at = now

    write_audit_log(
        db,
        action=f"memories.moderate.{payload.action}",
        actor_user_id=user.id,
        resource_type="event_memory",
        resource_id=str(memory.id),
        details={"note": payload.note},
    )
    db.commit()
    db.refresh(memory)
    event = db.get(Event, memory.event_id)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=True)


def get_eligibility_for_slug(db: Session, *, user: User | None, event_slug: str) -> dict:
    event = db.scalar(select(Event).where(Event.slug == event_slug))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    memory = get_memory_by_event_id(db, event.id)
    if user is None:
        return {
            "authenticated": False,
            "ticket_verified": False,
            "event_started": False,
            "can_upload": False,
            "role": None,
            "used": 0,
            "limit": 0,
            "remaining": 0,
            "host_limit": 10,
        }
    # Hosts get host eligibility
    try:
        host = require_user_host(db, user)
        if host.id == event.host_id:
            from app.memories.constants import HOST_MEMORY_PHOTO_LIMIT
            from app.memories.eligibility import count_active_photos

            mem = memory or ensure_event_memory(db, event)
            used = count_active_photos(db, memory_id=mem.id, uploader_role="host")
            remaining = max(0, HOST_MEMORY_PHOTO_LIMIT - used)
            return {
                "authenticated": True,
                "ticket_verified": True,
                "event_started": True,
                "can_upload": remaining > 0 and event.status in {"published", "paused", "completed"},
                "role": "host",
                "used": used,
                "limit": HOST_MEMORY_PHOTO_LIMIT,
                "remaining": remaining,
                "host_limit": HOST_MEMORY_PHOTO_LIMIT,
            }
    except HTTPException:
        pass
    return fan_eligibility(db, user=user, event=event, memory=memory)

