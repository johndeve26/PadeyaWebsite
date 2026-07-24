"""Offline scanner sync foundation with conflict detection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.checkins.permissions import can_scan_event
from app.checkins.service import (
    INVALID_STATUSES,
    _log_checkin,
    _resolve_ticket_from_code,
    _resolve_ticket_from_qr,
    _ticket_info,
)
from app.core.audit import write_audit_log
from app.tickets.advanced_models import OfflineScanBatch, OfflineScanItem
from app.tickets.models import Ticket
from app.users.models import User


def sync_offline_scans(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    client_batch_id: str,
    device_label: str | None,
    scans: list[dict],
) -> dict:
    if not can_scan_event(db, user, event_id):
        raise HTTPException(status_code=403, detail="Not authorized to sync scans for this event")
    if not client_batch_id.strip():
        raise HTTPException(status_code=400, detail="client_batch_id required")
    if not scans:
        raise HTTPException(status_code=400, detail="scans required")

    existing = db.scalar(
        select(OfflineScanBatch).where(
            OfflineScanBatch.event_id == event_id,
            OfflineScanBatch.client_batch_id == client_batch_id.strip(),
        )
    )
    if existing is not None:
        return _serialize_batch(db, existing)

    batch = OfflineScanBatch(
        event_id=event_id,
        uploaded_by_user_id=user.id,
        client_batch_id=client_batch_id.strip(),
        device_label=device_label,
        status="synced",
        accepted_count=0,
        conflict_count=0,
        invalid_count=0,
        synced_at=datetime.now(UTC),
    )
    db.add(batch)
    db.flush()

    results: list[dict] = []
    for raw in scans:
        client_scan_id = str(raw.get("client_scan_id") or "").strip()
        if not client_scan_id:
            raise HTTPException(status_code=400, detail="Each scan needs client_scan_id")
        scanned_at = raw.get("scanned_at")
        if isinstance(scanned_at, str):
            scanned_at_dt = datetime.fromisoformat(scanned_at.replace("Z", "+00:00"))
        elif isinstance(scanned_at, datetime):
            scanned_at_dt = scanned_at
        else:
            scanned_at_dt = datetime.now(UTC)

        ticket: Ticket | None = None
        resolve_message = "ok"
        qr_payload = raw.get("qr_payload")
        public_code = raw.get("public_code")
        if qr_payload:
            ticket, resolve_message = _resolve_ticket_from_qr(
                db, event_id=event_id, qr_payload=str(qr_payload)
            )
        elif public_code:
            ticket = _resolve_ticket_from_code(
                db, event_id=event_id, public_code=str(public_code)
            )
            if ticket is None:
                resolve_message = "Ticket not found"
        else:
            resolve_message = "Provide qr_payload or public_code"

        sync_status = "invalid"
        conflict_reason: str | None = None
        check_in_id: uuid.UUID | None = None

        if ticket is None or resolve_message != "ok":
            sync_status = "invalid"
            conflict_reason = resolve_message
            batch.invalid_count += 1
            _log_checkin(
                db,
                event_id=event_id,
                user=user,
                outcome="invalid",
                method="offline",
                ticket=ticket,
                detail=resolve_message,
            )
        elif ticket.status in INVALID_STATUSES:
            sync_status = "invalid"
            conflict_reason = f"Ticket is {ticket.status}"
            batch.invalid_count += 1
            _log_checkin(
                db,
                event_id=event_id,
                user=user,
                outcome="invalid",
                method="offline",
                ticket=ticket,
                detail=conflict_reason,
            )
        elif ticket.status == "checked_in":
            # Conflict: already checked in online (or earlier sync)
            sync_status = "conflict"
            conflict_reason = (
                f"Ticket already checked in at {ticket.checked_in_at.isoformat() if ticket.checked_in_at else 'unknown'}"
            )
            batch.conflict_count += 1
            entry = _log_checkin(
                db,
                event_id=event_id,
                user=user,
                outcome="duplicate",
                method="offline",
                ticket=ticket,
                detail=conflict_reason,
            )
            check_in_id = entry.id
        elif ticket.status != "active":
            sync_status = "invalid"
            conflict_reason = f"Unexpected status {ticket.status}"
            batch.invalid_count += 1
        else:
            now = datetime.now(UTC)
            ticket.status = "checked_in"
            ticket.checked_in_at = scanned_at_dt if scanned_at_dt.tzinfo else scanned_at_dt.replace(
                tzinfo=UTC
            )
            entry = _log_checkin(
                db,
                event_id=event_id,
                user=user,
                outcome="success",
                method="offline",
                ticket=ticket,
                detail="Offline sync check-in",
            )
            check_in_id = entry.id
            sync_status = "accepted"
            batch.accepted_count += 1
            from app.checkins.notify import notify_attendee_checked_in

            notify_attendee_checked_in(db, ticket=ticket, event_id=event_id)
            _ = now

        item = OfflineScanItem(
            batch_id=batch.id,
            client_scan_id=client_scan_id,
            ticket_id=ticket.id if ticket else None,
            public_code=ticket.public_code if ticket else (str(public_code) if public_code else None),
            scanned_at_client=scanned_at_dt if isinstance(scanned_at_dt, datetime) else datetime.now(UTC),
            sync_status=sync_status,
            conflict_reason=conflict_reason,
            check_in_id=check_in_id,
        )
        db.add(item)
        results.append(
            {
                "client_scan_id": client_scan_id,
                "sync_status": sync_status,
                "conflict_reason": conflict_reason,
                "ticket": _ticket_info(ticket),
                "check_in_id": check_in_id,
            }
        )

    if batch.conflict_count > 0:
        batch.status = "conflicts"
    write_audit_log(
        db,
        action="checkins.offline_sync",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event_id),
        details={
            "batch_id": str(batch.id),
            "accepted": batch.accepted_count,
            "conflicts": batch.conflict_count,
            "invalid": batch.invalid_count,
        },
    )
    db.commit()
    db.refresh(batch)
    return {
        "batch_id": batch.id,
        "client_batch_id": batch.client_batch_id,
        "status": batch.status,
        "accepted_count": batch.accepted_count,
        "conflict_count": batch.conflict_count,
        "invalid_count": batch.invalid_count,
        "results": results,
    }


def _serialize_batch(db: Session, batch: OfflineScanBatch) -> dict:
    items = list(
        db.scalars(select(OfflineScanItem).where(OfflineScanItem.batch_id == batch.id))
    )
    results = []
    for item in items:
        ticket = db.get(Ticket, item.ticket_id) if item.ticket_id else None
        results.append(
            {
                "client_scan_id": item.client_scan_id,
                "sync_status": item.sync_status,
                "conflict_reason": item.conflict_reason,
                "ticket": _ticket_info(ticket),
                "check_in_id": item.check_in_id,
            }
        )
    return {
        "batch_id": batch.id,
        "client_batch_id": batch.client_batch_id,
        "status": batch.status,
        "accepted_count": batch.accepted_count,
        "conflict_count": batch.conflict_count,
        "invalid_count": batch.invalid_count,
        "results": results,
    }


def list_offline_batches(db: Session, *, user: User, event_id: uuid.UUID) -> list[OfflineScanBatch]:
    if not can_scan_event(db, user, event_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return list(
        db.scalars(
            select(OfflineScanBatch)
            .where(OfflineScanBatch.event_id == event_id)
            .options(selectinload(OfflineScanBatch.items))
            .order_by(OfflineScanBatch.created_at.desc())
        )
    )
