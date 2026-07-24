"""Host table reservation and seat assignment (placeholder)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checkins.permissions import can_scan_event, get_event_or_none
from app.core.audit import write_audit_log
from app.hosts.models import Host
from app.tickets.advanced_models import TableReservation
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import user_has_permission


def _require_host_event(db: Session, user: User, event_id: uuid.UUID) -> None:
    event = get_event_or_none(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if user_has_permission(user, "admin.full_access"):
        return
    host = db.scalar(select(Host).where(Host.user_id == user.id))
    if host is None or host.id != event.host_id:
        if not can_scan_event(db, user, event_id):
            raise HTTPException(status_code=403, detail="Not authorized for this event")


def list_table_reservations(db: Session, *, user: User, event_id: uuid.UUID) -> list[TableReservation]:
    _require_host_event(db, user, event_id)
    return list(
        db.scalars(
            select(TableReservation)
            .where(TableReservation.event_id == event_id)
            .order_by(TableReservation.table_label.asc())
        )
    )


def create_table_reservation(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    table_label: str,
    capacity: int = 1,
    seat_label: str | None = None,
    assignment_note: str | None = None,
) -> TableReservation:
    _require_host_event(db, user, event_id)
    if capacity < 1:
        raise HTTPException(status_code=400, detail="capacity must be >= 1")
    row = TableReservation(
        event_id=event_id,
        table_label=table_label.strip(),
        seat_label=seat_label,
        capacity=capacity,
        status="open",
        assignment_note=assignment_note,
    )
    db.add(row)
    write_audit_log(
        db,
        action="tickets.table_create",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event_id),
        details={"table_label": table_label, "capacity": capacity},
    )
    db.commit()
    db.refresh(row)
    return row


def assign_table_seat(
    db: Session,
    *,
    user: User,
    reservation_id: uuid.UUID,
    ticket_id: uuid.UUID | None,
    seat_label: str | None = None,
) -> TableReservation:
    reservation = db.get(TableReservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Table reservation not found")
    _require_host_event(db, user, reservation.event_id)

    if ticket_id is not None:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None or ticket.event_id != reservation.event_id:
            raise HTTPException(status_code=400, detail="Ticket not valid for this event")
        if ticket.status not in {"active", "checked_in"}:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot assign ticket with status {ticket.status}",
            )
        reservation.primary_ticket_id = ticket.id
        reservation.status = "assigned"
        if seat_label:
            reservation.seat_label = seat_label
            ticket.seat_label = seat_label
        ticket.table_label = reservation.table_label
    else:
        reservation.primary_ticket_id = None
        reservation.status = "open"
        if seat_label is not None:
            reservation.seat_label = seat_label

    write_audit_log(
        db,
        action="tickets.table_assign",
        actor_user_id=user.id,
        resource_type="table_reservation",
        resource_id=str(reservation.id),
        details={
            "ticket_id": str(ticket_id) if ticket_id else None,
            "seat_label": seat_label,
        },
    )
    db.commit()
    db.refresh(reservation)
    return reservation


def cancel_table_reservation(
    db: Session, *, user: User, reservation_id: uuid.UUID
) -> TableReservation:
    reservation = db.get(TableReservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Table reservation not found")
    _require_host_event(db, user, reservation.event_id)
    if reservation.status == "cancelled":
        return reservation
    reservation.status = "cancelled"
    reservation.primary_ticket_id = None
    write_audit_log(
        db,
        action="tickets.table_cancel",
        actor_user_id=user.id,
        resource_type="table_reservation",
        resource_id=str(reservation.id),
    )
    db.commit()
    db.refresh(reservation)
    return reservation
