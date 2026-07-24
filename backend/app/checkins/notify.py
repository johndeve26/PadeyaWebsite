"""Fan attendee notifications after successful check-in."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.events.models import Event
from app.hosts.models import Host
from app.notifications.triggers import notify_ticket_checked_in
from app.tickets.models import Ticket


def notify_attendee_checked_in(
    db: Session,
    *,
    ticket: Ticket,
    event_id: uuid.UUID,
) -> None:
    """Notify ticket buyer on first successful check-in (no guest-only tickets)."""
    if ticket.buyer_user_id is None:
        return
    event = db.get(Event, event_id)
    if event is None:
        return
    host_name: str | None = None
    if event.host_id is not None:
        host = db.get(Host, event.host_id)
        if host is not None:
            host_name = host.display_name
    label = (ticket.ticket_type_name or "").strip() or None
    notify_ticket_checked_in(
        db,
        attendee_user_id=ticket.buyer_user_id,
        ticket_id=ticket.id,
        event_title=event.title or "your event",
        event_slug=event.slug,
        host_display_name=host_name,
        ticket_label=label,
    )
