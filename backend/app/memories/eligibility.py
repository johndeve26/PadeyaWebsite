"""Ticket eligibility for fan memory contributions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.memories.constants import (
    ELIGIBLE_EVENT_STATUSES,
    ELIGIBLE_TICKET_STATUSES,
    FAN_MEMORY_PHOTO_LIMIT,
    HOST_MEMORY_PHOTO_LIMIT,
)
from app.memories.models import EventMemory, EventMemoryMedia
from app.tickets.models import Ticket
from app.users.models import User


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def user_holds_event_memory_ticket(
    db: Session, *, event_id: UUID, user_id: UUID
) -> bool:
    """True if user bought or claimed a valid ticket for this event."""
    row = db.scalar(
        select(Ticket.id)
        .where(
            Ticket.event_id == event_id,
            Ticket.status.in_(ELIGIBLE_TICKET_STATUSES),
            or_(
                Ticket.buyer_user_id == user_id,
                Ticket.claimed_by_user_id == user_id,
            ),
        )
        .limit(1)
    )
    return row is not None


def event_memory_upload_window_open(event: Event, *, now: datetime | None = None) -> bool:
    """Fans may upload once the event has started (or later when completed)."""
    current = now or datetime.now(UTC)
    if event.status not in ELIGIBLE_EVENT_STATUSES:
        return False
    return _aware(event.start_datetime) <= current


def count_active_photos(
    db: Session,
    *,
    memory_id: UUID,
    uploader_role: str | None = None,
    uploader_user_id: UUID | None = None,
) -> int:
    q = (
        select(func.count())
        .select_from(EventMemoryMedia)
        .where(
            EventMemoryMedia.memory_id == memory_id,
            EventMemoryMedia.status == "active",
        )
    )
    if uploader_role is not None:
        q = q.where(EventMemoryMedia.uploader_role == uploader_role)
    if uploader_user_id is not None:
        q = q.where(EventMemoryMedia.uploader_user_id == uploader_user_id)
    return int(db.scalar(q) or 0)


def fan_eligibility(
    db: Session, *, user: User, event: Event, memory: EventMemory | None
) -> dict:
    """Public-safe eligibility payload (no ticket/order IDs)."""
    holds = user_holds_event_memory_ticket(db, event_id=event.id, user_id=user.id)
    window = event_memory_upload_window_open(event)
    used = 0
    if memory is not None:
        used = count_active_photos(
            db,
            memory_id=memory.id,
            uploader_role="fan",
            uploader_user_id=user.id,
        )
    remaining = max(0, FAN_MEMORY_PHOTO_LIMIT - used) if holds and window else 0
    can_upload = holds and window and remaining > 0 and event.status != "cancelled"
    return {
        "authenticated": True,
        "ticket_verified": holds,
        "event_started": window,
        "can_upload": can_upload,
        "role": "fan",
        "used": used,
        "limit": FAN_MEMORY_PHOTO_LIMIT,
        "remaining": remaining,
        "host_limit": HOST_MEMORY_PHOTO_LIMIT,
    }
