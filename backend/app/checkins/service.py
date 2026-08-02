"""Check-in validation, scanning, sessions, and stats."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import jwt
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.checkins.models import CheckIn, EventStaffAssignment, ScannerSession
from app.checkins.permissions import (
    can_manage_event_staff,
    can_override_checkin,
    can_scan_event,
    get_event_or_none,
)
from app.checkins.schemas import (
    CheckInRequest,
    ManualOverrideRequest,
    StartSessionRequest,
    ValidateQrRequest,
)
from app.core.audit import write_audit_log
from app.tickets.models import Ticket
from app.tickets.qr import decode_signed_qr_payload, hash_jti
from app.users.models import User
from app.users.service import get_role_by_name, get_user_by_email

INVALID_STATUSES = {"refunded", "cancelled", "expired", "invalid", "transferred"}
# Event statuses that must not admit attendees at the gate.
NON_ADMITTING_EVENT_STATUSES = frozenset(
    {"draft", "rejected", "cancelled", "archived"}
)


def _require_scan_access(db: Session, user: User, event_id: uuid.UUID) -> None:
    from app.events.models import Event
    from app.teams.permissions import ticket_scan_denial_reason
    from app.teams.scan_audit import write_desk_scan_audit
    from app.users.restrictions import assert_can_scan_tickets

    assert_can_scan_tickets(db, user)

    event = db.get(Event, event_id)
    host_id = event.host_id if event is not None else None
    if can_scan_event(db, user, event_id):
        return
    reason = (
        ticket_scan_denial_reason(db, user.id, host_id, event_id)
        if host_id is not None
        else "Event not found"
    )
    write_desk_scan_audit(
        db,
        actor_user_id=user.id,
        host_profile_id=host_id,
        event_id=event_id,
        action="tickets.scan",
        result="denied",
        denial_reason=reason or "Not authorized to scan tickets for this event",
    )
    db.commit()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=reason or "Not authorized to scan tickets for this event",
    )


def _audit_ticket_scan(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    result: str,
    ticket_id: uuid.UUID | None = None,
    denial_reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    from app.events.models import Event
    from app.teams.scan_audit import write_desk_scan_audit

    event = db.get(Event, event_id)
    write_desk_scan_audit(
        db,
        actor_user_id=user.id,
        host_profile_id=event.host_id if event is not None else None,
        event_id=event_id,
        action="tickets.scan",
        result=result,
        ticket_id=ticket_id,
        denial_reason=denial_reason,
        metadata=metadata,
    )


def _get_session(db: Session, session_id: uuid.UUID | None, event_id: uuid.UUID) -> ScannerSession | None:
    if session_id is None:
        return None
    session = db.get(ScannerSession, session_id)
    if session is None or session.event_id != event_id:
        raise HTTPException(status_code=400, detail="Invalid scanner session")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Scanner session is not active")
    return session


def start_scanner_session(
    db: Session,
    *,
    user: User,
    payload: StartSessionRequest,
    ip_address: str | None = None,
) -> ScannerSession:
    _require_scan_access(db, user, payload.event_id)
    if get_event_or_none(db, payload.event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    session = ScannerSession(
        event_id=payload.event_id,
        user_id=user.id,
        status="active",
        device_label=payload.device_label,
        ip_address=ip_address,
    )
    db.add(session)
    write_audit_log(
        db,
        action="checkins.session_start",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(payload.event_id),
        details={"device_label": payload.device_label},
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(session)
    return session


def end_scanner_session(db: Session, *, user: User, session_id: uuid.UUID) -> ScannerSession:
    session = db.get(ScannerSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _require_scan_access(db, user, session.event_id)
    if session.user_id != user.id and not can_override_checkin(user):
        raise HTTPException(status_code=403, detail="Cannot end another scanner's session")
    session.status = "ended"
    session.ended_at = datetime.now(UTC)
    db.commit()
    db.refresh(session)
    return session


def _ticket_info(ticket: Ticket | None) -> dict:
    """Minimal desk scan payload — no buyer email/phone or payment refs."""
    if ticket is None:
        return {
            "ticket_id": None,
            "public_code": None,
            "status": None,
            "holder_name": None,
            "holder_email": None,
            "ticket_type_name": None,
            "checked_in_at": None,
        }
    return {
        "ticket_id": ticket.id,
        "public_code": ticket.public_code,
        "status": ticket.status,
        "holder_name": ticket.holder_name,
        # Privacy: scanner staff never receive holder email/phone.
        "holder_email": None,
        "ticket_type_name": ticket.ticket_type_name,
        "checked_in_at": ticket.checked_in_at,
    }


def _resolve_ticket_from_qr(db: Session, *, event_id: uuid.UUID, qr_payload: str) -> tuple[Ticket | None, str]:
    try:
        payload = decode_signed_qr_payload(qr_payload)
    except jwt.PyJWTError:
        return None, "QR signature is invalid or expired"

    if str(payload.get("eid")) != str(event_id):
        return None, "Ticket is not valid for this event"

    public_code = payload.get("code")
    jti = payload.get("jti")
    if not public_code or not jti:
        return None, "QR payload is incomplete"

    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.public_code == public_code, Ticket.event_id == event_id)
        .options(selectinload(Ticket.qr_token))
    )
    if ticket is None:
        return None, "Ticket not found"

    token = ticket.qr_token
    if token is None or token.revoked_at is not None:
        return ticket, "QR token has been revoked"
    if token.jti_hash != hash_jti(str(jti)):
        return ticket, "QR token does not match issued ticket"
    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        return ticket, "QR token has expired"

    return ticket, "ok"


def _resolve_ticket_from_code(
    db: Session, *, event_id: uuid.UUID, public_code: str
) -> Ticket | None:
    return db.scalar(
        select(Ticket).where(
            Ticket.event_id == event_id,
            Ticket.public_code == public_code.strip().upper(),
        )
    ) or db.scalar(
        select(Ticket).where(
            Ticket.event_id == event_id,
            Ticket.public_code == public_code.strip(),
        )
    )


def _lock_ticket_for_admission(db: Session, ticket_id: uuid.UUID) -> Ticket | None:
    """Serialize concurrent check-ins / offline sync on the same ticket (CC-002)."""
    return db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _pending_transfer_blocks_admission(db: Session, ticket_id: uuid.UUID) -> bool:
    from app.tickets.advanced_models import TicketTransfer

    pending = db.scalar(
        select(TicketTransfer.id).where(
            TicketTransfer.ticket_id == ticket_id,
            TicketTransfer.status == "pending",
        )
    )
    return pending is not None


def _event_admission_block_reason(db: Session, event_id: uuid.UUID) -> str | None:
    from app.events.models import Event

    event = db.get(Event, event_id)
    if event is None:
        return "Event not found"
    if event.status in NON_ADMITTING_EVENT_STATUSES:
        return f"Event is {event.status} and cannot admit attendees"
    return None


def can_admit_ticket(
    db: Session,
    *,
    ticket: Ticket,
    event_id: uuid.UUID,
) -> tuple[bool, str, str | None]:
    """Authoritative eligibility for gate admission.

    Returns (ok, outcome, message). Outcome is success|duplicate|invalid when not ok
    for duplicate/invalid paths; when ok, outcome is ``active``.
    """
    block = _event_admission_block_reason(db, event_id)
    if block:
        return False, "invalid", block
    if ticket.event_id != event_id:
        return False, "invalid", "Ticket is not valid for this event"
    if ticket.status in INVALID_STATUSES:
        return False, "invalid", f"Ticket is {ticket.status} and cannot be checked in"
    if ticket.status == "checked_in":
        return False, "duplicate", "Ticket already checked in"
    if ticket.status != "active":
        return False, "invalid", f"Ticket status '{ticket.status}' cannot be checked in"
    if _pending_transfer_blocks_admission(db, ticket.id):
        return False, "invalid", "Ticket has a pending transfer and cannot be checked in"
    return True, "active", None


def _log_checkin(
    db: Session,
    *,
    event_id: uuid.UUID,
    user: User,
    outcome: str,
    method: str,
    ticket: Ticket | None = None,
    session: ScannerSession | None = None,
    detail: str | None = None,
    override_reason: str | None = None,
) -> CheckIn:
    entry = CheckIn(
        event_id=event_id,
        ticket_id=ticket.id if ticket else None,
        ticket_public_code=ticket.public_code if ticket else None,
        scanner_session_id=session.id if session else None,
        scanned_by_user_id=user.id,
        outcome=outcome,
        method=method,
        detail=detail,
        override_reason=override_reason,
        holder_name=ticket.holder_name if ticket else None,
        ticket_type_name=ticket.ticket_type_name if ticket else None,
    )
    db.add(entry)
    db.flush()
    return entry


def validate_qr(
    db: Session,
    *,
    user: User,
    payload: ValidateQrRequest,
) -> dict:
    _require_scan_access(db, user, payload.event_id)
    session = _get_session(db, payload.session_id, payload.event_id)
    ticket, message = _resolve_ticket_from_qr(
        db, event_id=payload.event_id, qr_payload=payload.qr_payload
    )
    if ticket is None or message != "ok":
        return {
            "outcome": "invalid",
            "message": message,
            "ticket": _ticket_info(ticket),
            "check_in_id": None,
            "checked_in_at": None,
            "scanner_name": user.full_name,
        }

    ok, outcome, admit_message = can_admit_ticket(
        db, ticket=ticket, event_id=payload.event_id
    )
    if not ok:
        return {
            "outcome": outcome,
            "message": admit_message
            or (
                "Ticket already checked in"
                if outcome == "duplicate"
                else "Ticket cannot be checked in"
            ),
            "ticket": _ticket_info(ticket),
            "check_in_id": None,
            "checked_in_at": ticket.checked_in_at,
            "scanner_name": user.full_name,
        }
    _ = session
    return {
        "outcome": "valid",
        "message": "Ticket is valid for check-in",
        "ticket": _ticket_info(ticket),
        "check_in_id": None,
        "checked_in_at": None,
        "scanner_name": user.full_name,
    }


def check_in_ticket(
    db: Session,
    *,
    user: User,
    payload: CheckInRequest,
) -> dict:
    _require_scan_access(db, user, payload.event_id)
    session = _get_session(db, payload.session_id, payload.event_id)

    ticket: Ticket | None = None
    method = "manual"
    resolve_message = "ok"

    if payload.qr_payload:
        method = "qr"
        ticket, resolve_message = _resolve_ticket_from_qr(
            db, event_id=payload.event_id, qr_payload=payload.qr_payload
        )
    elif payload.public_code:
        ticket = _resolve_ticket_from_code(
            db, event_id=payload.event_id, public_code=payload.public_code
        )
        if ticket is None:
            resolve_message = "Ticket not found"
    else:
        raise HTTPException(status_code=400, detail="Provide qr_payload or public_code")

    if ticket is None or resolve_message != "ok":
        entry = _log_checkin(
            db,
            event_id=payload.event_id,
            user=user,
            outcome="invalid",
            method=method,
            ticket=ticket,
            session=session,
            detail=resolve_message if ticket is None else resolve_message,
        )
        _audit_ticket_scan(
            db,
            user=user,
            event_id=payload.event_id,
            result="invalid",
            ticket_id=ticket.id if ticket else None,
            denial_reason=resolve_message,
            metadata={"method": method},
        )
        db.commit()
        return {
            "outcome": "invalid",
            "message": resolve_message if ticket is None else resolve_message,
            "ticket": _ticket_info(ticket),
            "check_in_id": entry.id,
            "checked_in_at": None,
            "scanner_name": user.full_name,
        }

    # CC-002: lock ticket row before status transition so concurrent scans serialize.
    locked = _lock_ticket_for_admission(db, ticket.id)
    if locked is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = locked

    ok, outcome, admit_message = can_admit_ticket(
        db, ticket=ticket, event_id=payload.event_id
    )
    if not ok:
        detail = admit_message or (
            "Duplicate scan"
            if outcome == "duplicate"
            else "Ticket cannot be checked in"
        )
        entry = _log_checkin(
            db,
            event_id=payload.event_id,
            user=user,
            outcome=outcome,
            method=method,
            ticket=ticket,
            session=session,
            detail=detail,
        )
        _audit_ticket_scan(
            db,
            user=user,
            event_id=payload.event_id,
            result=outcome,
            ticket_id=ticket.id,
            denial_reason=detail,
            metadata={"method": method},
        )
        db.commit()
        message = (
            "Duplicate scan — this ticket was already checked in"
            if outcome == "duplicate"
            else (admit_message or "Ticket cannot be checked in")
        )
        return {
            "outcome": outcome,
            "message": message,
            "ticket": _ticket_info(ticket),
            "check_in_id": entry.id,
            "checked_in_at": ticket.checked_in_at,
            "scanner_name": user.full_name,
        }

    now = datetime.now(UTC)
    ticket.status = "checked_in"
    ticket.checked_in_at = now
    entry = _log_checkin(
        db,
        event_id=payload.event_id,
        user=user,
        outcome="success",
        method=method,
        ticket=ticket,
        session=session,
        detail="Checked in",
    )
    _audit_ticket_scan(
        db,
        user=user,
        event_id=payload.event_id,
        result="success",
        ticket_id=ticket.id,
        metadata={"method": method},
    )
    write_audit_log(
        db,
        action="checkins.success",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"event_id": str(payload.event_id), "method": method},
    )

    from app.analytics.trusted import emit_checkin_success
    from app.events.models import Event as EventModel

    event_row = db.get(EventModel, payload.event_id)
    if event_row is not None:
        emit_checkin_success(
            db,
            event_id=payload.event_id,
            host_id=event_row.host_id,
            user_id=ticket.buyer_user_id or user.id,
            ticket_id=ticket.id,
        )

    from app.checkins.notify import notify_attendee_checked_in

    notify_attendee_checked_in(db, ticket=ticket, event_id=payload.event_id)

    db.commit()
    return {
        "outcome": "success",
        "message": "Check-in successful",
        "ticket": _ticket_info(ticket),
        "check_in_id": entry.id,
        "checked_in_at": now,
        "scanner_name": user.full_name,
    }


def override_check_in(
    db: Session,
    *,
    user: User,
    payload: ManualOverrideRequest,
) -> dict:
    if not can_override_checkin(user):
        raise HTTPException(status_code=403, detail="Admin permission required for override")
    _require_scan_access(db, user, payload.event_id)
    session = _get_session(db, payload.session_id, payload.event_id)

    ticket = db.scalar(
        select(Ticket).where(
            Ticket.id == payload.ticket_id,
            Ticket.event_id == payload.event_id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    was_already_checked = (
        ticket.status == "checked_in" and ticket.checked_in_at is not None
    )

    now = datetime.now(UTC)
    ticket.status = "checked_in"
    ticket.checked_in_at = now
    entry = _log_checkin(
        db,
        event_id=payload.event_id,
        user=user,
        outcome="success",
        method="override",
        ticket=ticket,
        session=session,
        detail="Admin override check-in",
        override_reason=payload.reason,
    )
    write_audit_log(
        db,
        action="checkins.override",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={
            "event_id": str(payload.event_id),
            "reason": payload.reason,
        },
    )
    if not was_already_checked:
        from app.checkins.notify import notify_attendee_checked_in

        notify_attendee_checked_in(db, ticket=ticket, event_id=payload.event_id)
    db.commit()
    return {
        "outcome": "success",
        "message": "Override check-in successful",
        "ticket": _ticket_info(ticket),
        "check_in_id": entry.id,
        "checked_in_at": now,
        "scanner_name": user.full_name,
    }


def search_attendees(db: Session, *, user: User, event_id: uuid.UUID, query: str) -> list[Ticket]:
    """Desk attendee lookup by public code or holder name (not email)."""
    _require_scan_access(db, user, event_id)
    q = query.strip()
    if len(q) < 2:
        return []
    pattern = f"%{q}%"
    return list(
        db.scalars(
            select(Ticket)
            .where(
                Ticket.event_id == event_id,
                or_(
                    Ticket.public_code.ilike(pattern),
                    Ticket.holder_name.ilike(pattern),
                ),
            )
            .order_by(Ticket.holder_name.asc())
            .limit(25)
        )
    )


def serialize_desk_attendee(ticket: Ticket) -> dict:
    """Minimal attendee row for scanner search — no email/phone."""
    return {
        "id": ticket.id,
        "public_code": ticket.public_code,
        "ticket_type_name": ticket.ticket_type_name,
        "status": ticket.status,
        "holder_name": ticket.holder_name,
        "checked_in_at": ticket.checked_in_at,
    }


def list_checkins(db: Session, *, user: User, event_id: uuid.UUID) -> list[CheckIn]:
    _require_scan_access(db, user, event_id)
    return list(
        db.scalars(
            select(CheckIn)
            .where(CheckIn.event_id == event_id)
            .order_by(CheckIn.created_at.desc())
            .limit(200)
        )
    )


def event_checkin_stats(db: Session, *, user: User, event_id: uuid.UUID) -> dict:
    _require_scan_access(db, user, event_id)
    total = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.event_id == event_id)
    ) or 0
    checked_in = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.event_id == event_id, Ticket.status == "checked_in")
    ) or 0

    def count_outcome(outcome: str) -> int:
        return (
            db.scalar(
                select(func.count())
                .select_from(CheckIn)
                .where(CheckIn.event_id == event_id, CheckIn.outcome == outcome)
            )
            or 0
        )

    overrides = (
        db.scalar(
            select(func.count())
            .select_from(CheckIn)
            .where(CheckIn.event_id == event_id, CheckIn.method == "override")
        )
        or 0
    )

    return {
        "event_id": event_id,
        "total_tickets": total,
        "checked_in": checked_in,
        "remaining": max(0, total - checked_in),
        "successful_scans": count_outcome("success"),
        "duplicate_scans": count_outcome("duplicate"),
        "invalid_scans": count_outcome("invalid"),
        "override_scans": overrides,
    }


def assign_event_staff(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    email: str,
) -> EventStaffAssignment:
    if not can_manage_event_staff(db, user, event_id):
        raise HTTPException(status_code=403, detail="Only the event host can assign staff")
    if get_event_or_none(db, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    staff_user = get_user_by_email(db, email.lower().strip())
    if staff_user is None:
        raise HTTPException(status_code=404, detail="User not found — they must register first")

    staff_role = get_role_by_name(db, "host_staff")
    if staff_role and staff_role not in staff_user.roles:
        staff_user.roles.append(staff_role)

    existing = db.scalar(
        select(EventStaffAssignment).where(
            EventStaffAssignment.event_id == event_id,
            EventStaffAssignment.user_id == staff_user.id,
        )
    )
    if existing:
        return existing

    assignment = EventStaffAssignment(
        event_id=event_id,
        user_id=staff_user.id,
        assigned_by_user_id=user.id,
        role_label="scanner",
    )
    db.add(assignment)
    write_audit_log(
        db,
        action="checkins.staff_assign",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event_id),
        details={"staff_user_id": str(staff_user.id), "email": staff_user.email},
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def unassign_event_staff(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    assignment_id: uuid.UUID,
) -> None:
    if not can_manage_event_staff(db, user, event_id):
        raise HTTPException(status_code=403, detail="Only the event host can unassign staff")
    row = db.scalar(
        select(EventStaffAssignment).where(
            EventStaffAssignment.id == assignment_id,
            EventStaffAssignment.event_id == event_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Staff assignment not found")
    write_audit_log(
        db,
        action="checkins.staff_unassign",
        actor_user_id=user.id,
        resource_type="event_staff",
        resource_id=str(row.id),
        details={"staff_user_id": str(row.user_id)},
    )
    db.delete(row)
    db.commit()


def list_event_staff(db: Session, *, user: User, event_id: uuid.UUID) -> list[EventStaffAssignment]:
    if not (can_manage_event_staff(db, user, event_id) or can_scan_event(db, user, event_id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    return list(
        db.scalars(
            select(EventStaffAssignment).where(EventStaffAssignment.event_id == event_id)
        )
    )


def serialize_checkin(db: Session, entry: CheckIn) -> dict:
    scanner = db.get(User, entry.scanned_by_user_id)
    return {
        "id": entry.id,
        "event_id": entry.event_id,
        "ticket_id": entry.ticket_id,
        "ticket_public_code": entry.ticket_public_code,
        "scanned_by_user_id": entry.scanned_by_user_id,
        "outcome": entry.outcome,
        "method": entry.method,
        "detail": entry.detail,
        "override_reason": entry.override_reason,
        "holder_name": entry.holder_name,
        "ticket_type_name": entry.ticket_type_name,
        "created_at": entry.created_at,
        "scanner_name": scanner.full_name if scanner else None,
    }


def serialize_session(db: Session, session: ScannerSession) -> dict:
    scanner = db.get(User, session.user_id)
    return {
        "id": session.id,
        "event_id": session.event_id,
        "user_id": session.user_id,
        "status": session.status,
        "device_label": session.device_label,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "scanner_name": scanner.full_name if scanner else None,
    }


def serialize_staff(db: Session, assignment: EventStaffAssignment) -> dict:
    staff = db.get(User, assignment.user_id)
    return {
        "id": assignment.id,
        "event_id": assignment.event_id,
        "user_id": assignment.user_id,
        "role_label": assignment.role_label,
        "created_at": assignment.created_at,
        "user_email": staff.email if staff else None,
        "user_name": staff.full_name if staff else None,
    }
