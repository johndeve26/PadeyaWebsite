"""Event-level admission capacity (optional venue hard cap).

Product rule (Event Studio hint):
  \"Optional overall venue cap. Leave blank to limit stock per ticket tier only.\"

When ``event.capacity`` is set, checkout must keep:

  sum((quantity_sold + quantity_reserved) * seats_per_unit) + new_seats
  <= event.capacity

Ticket-type ``quantity`` remains the per-tier hard stock. Capacity is admission
seats (group/table ``seats_per_unit``), not merely ticket-type unit count.
Pending reservations count; paid sold counts. Merch does not consume capacity.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event, TicketType


def seats_for_units(tt: TicketType, units: int) -> int:
    seats = max(1, int(getattr(tt, "seats_per_unit", 1) or 1))
    return max(0, int(units)) * seats


def event_admission_committed(
    db: Session, *, event_id: uuid.UUID, lock_rows: bool = False
) -> int:
    """Seats already reserved or sold across all ticket types for the event."""
    q = select(TicketType).where(TicketType.event_id == event_id).order_by(TicketType.id)
    if lock_rows:
        q = q.with_for_update()
    rows = list(db.scalars(q))
    total = 0
    for tt in rows:
        units = int(tt.quantity_sold or 0) + int(tt.quantity_reserved or 0)
        total += seats_for_units(tt, units)
    return total


def lock_event_for_capacity(db: Session, event_id: uuid.UUID) -> Event:
    event = db.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def assert_event_capacity_allows(
    db: Session,
    *,
    event: Event,
    additional_seats: int,
) -> None:
    """Raise 409 if optional venue capacity would be exceeded.

    Caller must hold ``Event`` row lock when ``capacity`` is set so concurrent
    checkouts cannot interleave reads.
    """
    cap = getattr(event, "capacity", None)
    if cap is None:
        return
    try:
        limit = int(cap)
    except (TypeError, ValueError):
        return
    if limit < 1:
        return
    add = max(0, int(additional_seats))
    if add == 0:
        return
    committed = event_admission_committed(db, event_id=event.id, lock_rows=True)
    if committed + add > limit:
        raise HTTPException(
            status_code=409,
            detail=(
                "Not enough event capacity remaining "
                f"({max(0, limit - committed)} seat(s) left)"
            ),
        )
