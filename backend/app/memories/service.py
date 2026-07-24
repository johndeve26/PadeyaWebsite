"""Event Memories business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.media import get_media_storage
from app.events.models import Event
from app.hosts.models import Host
from app.hosts.service import require_user_host
from app.legacy.service import get_host_by_slug
from app.memories.constants import (
    ATTENDED_TICKET_STATUSES,
    OWNED_TICKET_STATUSES,
    TOP_REVIEWS_LIMIT,
)
from app.memories.models import EventMemory, EventMemoryMedia
from app.memories.schemas import EventMemoryUpdate, MemoryMediaCreate, MemoryModerateRequest
from app.reviews.models import VerifiedReview
from app.reviews.service import serialize_review
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import user_has_permission


def ensure_event_memory(db: Session, event: Event) -> EventMemory:
    """Create a published memory row for a completed event if missing."""
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


def _require_host_owns_event(db: Session, user: User, event: Event) -> Host:
    host = require_user_host(db, user)
    if host.id != event.host_id and not user_has_permission(user, "admin.full_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to edit this event memory",
        )
    return host


def _is_publicly_visible(memory: EventMemory, event: Event) -> bool:
    if event.status != "completed":
        return False
    if memory.status != "published":
        return False
    if memory.moderation_status in {"removed", "flagged"}:
        # flagged still visible? Spec: admin can hide. Use hidden status for hide.
        # removed = hard hide; flagged can stay visible until hide
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
    media = [
        {
            "id": m.id,
            "media_type": m.media_type,
            "url": m.url,
            "storage_key": m.storage_key if include_private else None,
            "label": m.label,
            "sort_order": m.sort_order,
            "created_at": m.created_at,
        }
        for m in sorted(memory.media, key=lambda x: x.sort_order)
    ]

    return {
        "id": memory.id,
        "event_id": memory.event_id,
        "host_id": memory.host_id,
        "status": memory.status,
        "host_recap_note": memory.host_recap_note,
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
        "upcoming_events": _upcoming_host_events(db, host.id, exclude_event_id=event.id),
        "share_path": f"/@{host.slug}/memories/{event.slug}",
        "published_at": memory.published_at,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
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


def get_host_memory(db: Session, *, user: User, event_id: UUID) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)

    if event.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Memory is available after the event is marked completed",
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

    if event.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Only completed events can have editable memories",
        )

    memory = ensure_event_memory(db, event)
    if memory.status == "hidden" and not user_has_permission(user, "admin.full_access"):
        raise HTTPException(
            status_code=403,
            detail="This memory was hidden by moderation",
        )

    if payload.host_recap_note is not None:
        memory.host_recap_note = payload.host_recap_note.strip() or None

    write_audit_log(
        db,
        action="memories.host.update",
        actor_user_id=user.id,
        resource_type="event_memory",
        resource_id=str(memory.id),
    )
    db.commit()
    db.refresh(memory)
    return serialize_memory(db, memory, include_private=True)


def add_memory_media(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    payload: MemoryMediaCreate,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)

    if event.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Only completed events can have memory media",
        )

    memory = ensure_event_memory(db, event)
    if memory.status == "hidden":
        raise HTTPException(
            status_code=403,
            detail="This memory was hidden by moderation",
        )

    try:
        stored = get_media_storage().store_remote_url(
            url=payload.url, folder="memories"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sort_order = payload.sort_order
    if sort_order is None:
        max_order = db.scalar(
            select(func.max(EventMemoryMedia.sort_order)).where(
                EventMemoryMedia.memory_id == memory.id
            )
        )
        sort_order = int(max_order or 0) + 1

    media = EventMemoryMedia(
        memory_id=memory.id,
        media_type=payload.media_type.strip().lower(),
        url=stored.url,
        storage_key=stored.key,
        label=payload.label,
        sort_order=sort_order,
    )
    db.add(media)
    write_audit_log(
        db,
        action="memories.host.media_add",
        actor_user_id=user.id,
        resource_type="event_memory",
        resource_id=str(memory.id),
        details={"media_id": str(media.id)},
    )
    db.commit()
    db.refresh(memory)
    return serialize_memory(db, memory, include_private=True)


def delete_memory_media(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    media_id: UUID,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)

    memory = get_memory_by_event_id(db, event.id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    media = db.get(EventMemoryMedia, media_id)
    if media is None or media.memory_id != memory.id:
        raise HTTPException(status_code=404, detail="Media not found")

    db.delete(media)
    write_audit_log(
        db,
        action="memories.host.media_delete",
        actor_user_id=user.id,
        resource_type="event_memory",
        resource_id=str(memory.id),
        details={"media_id": str(media_id)},
    )
    db.commit()
    db.refresh(memory)
    return serialize_memory(db, memory, include_private=True)


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
    return serialize_memory(db, memory, include_private=True)
