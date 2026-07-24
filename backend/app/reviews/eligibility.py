"""Verified review eligibility rules."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def evaluate_review_eligibility(
    db: Session,
    *,
    user_id: UUID,
    ticket_id: UUID | None = None,
    event_id: UUID | None = None,
) -> tuple[bool, str | None, Ticket | None, Event | None]:
    """
    Eligible when the user holds a checked-in ticket for an ended event
    and has not already reviewed that ticket/event.
    """
    ticket: Ticket | None = None
    if ticket_id is not None:
        ticket = db.get(Ticket, ticket_id)
    elif event_id is not None:
        ticket = db.scalar(
            select(Ticket)
            .where(
                Ticket.event_id == event_id,
                Ticket.buyer_user_id == user_id,
                Ticket.status == "checked_in",
            )
            .order_by(Ticket.checked_in_at.desc())
        )
        if ticket is None:
            ticket = db.scalar(
                select(Ticket)
                .where(Ticket.event_id == event_id, Ticket.buyer_user_id == user_id)
                .order_by(Ticket.created_at.desc())
            )

    if ticket is None:
        return False, "No ticket found for this event", None, None

    if ticket.buyer_user_id != user_id:
        return False, "You can only review tickets you own", ticket, None

    if ticket.status in {"refunded", "cancelled", "expired", "invalid", "transferred"}:
        return False, f"Ticket is {ticket.status} and cannot be reviewed", ticket, None

    if ticket.status != "checked_in" or ticket.checked_in_at is None:
        return False, "Only checked-in attendees can leave a verified review", ticket, None

    event = db.get(Event, ticket.event_id)
    if event is None:
        return False, "Event not found", ticket, None

    from app.hosts.fan_self_abuse import (
        REVIEW_OWN_HOST_DETAIL,
        is_user_owner_of_host,
    )

    if is_user_owner_of_host(
        db, user_id=user_id, host_profile_id=event.host_id
    ):
        return False, REVIEW_OWN_HOST_DETAIL, ticket, event

    now = datetime.now(UTC)
    if _aware(event.end_datetime) > now:
        return False, "Reviews open after the event ends", ticket, event

    existing = db.scalar(
        select(VerifiedReview.id).where(
            (VerifiedReview.ticket_id == ticket.id)
            | (
                (VerifiedReview.event_id == event.id)
                & (VerifiedReview.reviewer_user_id == user_id)
            )
        )
    )
    if existing is not None:
        return False, "You have already reviewed this event", ticket, event

    return True, None, ticket, event
