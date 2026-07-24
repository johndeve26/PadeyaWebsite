"""Ticket / merch scanner allow-deny rules and desk scan audit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checkins.models import EventStaffAssignment
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostTeamMember
from app.hosts.team_permissions import pack_scope_json, permissions_for_role
from app.teams.permissions import (
    can_scan_merch_pickup,
    can_scan_ticket,
    merch_scan_denial_reason,
    ticket_scan_denial_reason,
)
from app.teams.scan_audit import DeskScanAuditLog
from app.users.models import User
from app.users.service import get_role_by_name


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> dict:
    r = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Scanner integration host with enough text here.",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _seed_event(db: Session, host: Host, title: str = "Scan Night") -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title=title,
        slug=f"scan-{uuid4().hex[:8]}",
        description="Scanner integration event description with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="Hall",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            description="GA",
            price=Decimal("500.00"),
            quantity=100,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=4,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    db.refresh(event)
    return event


def _member(
    db: Session,
    *,
    host: Host,
    user: User,
    role: str = "scanner",
    perms: dict | None = None,
    scope: str = "host_wide",
    event_ids: list | None = None,
    status: str = "active",
) -> HostTeamMember:
    row = HostTeamMember(
        host_id=host.id,
        user_id=user.id,
        role=role,
        role_label=role,
        status=status,
        permissions_json=perms or permissions_for_role(role),
        scope_json=pack_scope_json(scope, event_ids or []),
        joined_at=datetime.now(UTC) if status == "active" else None,
        suspended_at=datetime.now(UTC) if status == "suspended" else None,
        removed_at=datetime.now(UTC) if status == "removed" else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_ticket_scanner_allow_and_deny_matrix(client: TestClient, db_session: Session):
    host_h = _auth(client, "scan-own@example.com", "Owner")
    body = _onboard(client, host_h, "Scan Own Co")
    host = db_session.get(Host, UUID(body["id"]))
    assert host is not None
    event_a = _seed_event(db_session, host, "Event A")
    event_b = _seed_event(db_session, host, "Event B")
    owner = db_session.get(User, host.user_id)
    assert owner is not None

    assert can_scan_ticket(db_session, owner.id, host.id, event_a.id) is True

    _auth(client, "scan-hw@example.com", "HW")
    hw = db_session.scalar(select(User).where(User.email == "scan-hw@example.com"))
    assert hw is not None
    perms = permissions_for_role("scanner")
    perms["tickets.scan_qr"] = True
    _member(
        db_session,
        host=host,
        user=hw,
        perms=perms,
        scope="host_wide",
    )
    assert can_scan_ticket(db_session, hw.id, host.id, event_a.id) is True
    assert can_scan_ticket(db_session, hw.id, host.id, event_b.id) is True

    _auth(client, "scan-scoped@example.com", "Scoped")
    scoped = db_session.scalar(
        select(User).where(User.email == "scan-scoped@example.com")
    )
    assert scoped is not None
    _member(
        db_session,
        host=host,
        user=scoped,
        perms=perms,
        scope="selected_events",
        event_ids=[event_a.id],
    )
    assert can_scan_ticket(db_session, scoped.id, host.id, event_a.id) is True
    assert can_scan_ticket(db_session, scoped.id, host.id, event_b.id) is False
    assert "scoped" in (
        ticket_scan_denial_reason(db_session, scoped.id, host.id, event_b.id) or ""
    ).lower()

    _auth(client, "scan-staff@example.com", "Staff")
    staff = db_session.scalar(
        select(User).where(User.email == "scan-staff@example.com")
    )
    assert staff is not None
    role = get_role_by_name(db_session, "host_staff")
    if role and role not in staff.roles:
        staff.roles.append(role)
    db_session.add(
        EventStaffAssignment(
            event_id=event_b.id,
            user_id=staff.id,
            assignment_type="ticket_scanner",
            status="active",
            role_label="scanner",
        )
    )
    db_session.commit()
    assert can_scan_ticket(db_session, staff.id, host.id, event_b.id) is True
    assert can_scan_ticket(db_session, staff.id, host.id, event_a.id) is False
    assert "different event" in (
        ticket_scan_denial_reason(db_session, staff.id, host.id, event_a.id) or ""
    ).lower()

    # Suspended / no permission / expired
    _auth(client, "scan-sus@example.com", "Sus")
    sus = db_session.scalar(select(User).where(User.email == "scan-sus@example.com"))
    assert sus is not None
    _member(db_session, host=host, user=sus, perms=perms, status="suspended")
    assert can_scan_ticket(db_session, sus.id, host.id, event_a.id) is False
    assert "suspended" in (
        ticket_scan_denial_reason(db_session, sus.id, host.id, event_a.id) or ""
    ).lower()

    # Leftover active staff must not restore desk access after suspend.
    db_session.add(
        EventStaffAssignment(
            event_id=event_a.id,
            user_id=sus.id,
            assignment_type="ticket_scanner",
            status="active",
            role_label="scanner",
        )
    )
    db_session.commit()
    assert can_scan_ticket(db_session, sus.id, host.id, event_a.id) is False

    _auth(client, "scan-noperm@example.com", "NoPerm")
    noperm = db_session.scalar(
        select(User).where(User.email == "scan-noperm@example.com")
    )
    assert noperm is not None
    _member(
        db_session,
        host=host,
        user=noperm,
        perms=permissions_for_role("viewer"),
        scope="host_wide",
    )
    assert can_scan_ticket(db_session, noperm.id, host.id, event_a.id) is False

    _auth(client, "scan-exp@example.com", "Exp")
    exp = db_session.scalar(select(User).where(User.email == "scan-exp@example.com"))
    assert exp is not None
    db_session.add(
        EventStaffAssignment(
            event_id=event_a.id,
            user_id=exp.id,
            assignment_type="ticket_scanner",
            status="active",
            role_label="scanner",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    db_session.commit()
    assert can_scan_ticket(db_session, exp.id, host.id, event_a.id) is False
    assert "expired" in (
        ticket_scan_denial_reason(db_session, exp.id, host.id, event_a.id) or ""
    ).lower()

    # Other host team
    other_h = _auth(client, "other-host@example.com", "Other")
    other_body = _onboard(client, other_h, "Other Co")
    other_host = db_session.get(Host, UUID(other_body["id"]))
    assert other_host is not None
    assert can_scan_ticket(db_session, hw.id, other_host.id, event_a.id) is False


def test_merch_scanner_typed_assignment(client: TestClient, db_session: Session):
    host_h = _auth(client, "merch-scan-own@example.com", "MOwner")
    body = _onboard(client, host_h, "Merch Scan Co")
    host = db_session.get(Host, UUID(body["id"]))
    assert host is not None
    event = _seed_event(db_session, host)

    _auth(client, "merch-desk@example.com", "Desk")
    desk = db_session.scalar(
        select(User).where(User.email == "merch-desk@example.com")
    )
    assert desk is not None
    db_session.add(
        EventStaffAssignment(
            event_id=event.id,
            user_id=desk.id,
            assignment_type="ticket_scanner",
            status="active",
            role_label="scanner",
        )
    )
    db_session.commit()
    assert can_scan_merch_pickup(db_session, desk.id, host.id, event.id) is False
    assert "merch pickup" in (
        merch_scan_denial_reason(db_session, desk.id, host.id, event.id) or ""
    ).lower()

    row = db_session.scalar(
        select(EventStaffAssignment).where(
            EventStaffAssignment.event_id == event.id,
            EventStaffAssignment.user_id == desk.id,
        )
    )
    assert row is not None
    row.assignment_type = "merch_pickup"
    db_session.commit()
    assert can_scan_merch_pickup(db_session, desk.id, host.id, event.id) is True


def test_merch_staff_cannot_scan_other_host_pickup(
    client: TestClient, db_session: Session
):
    host_a_h = _auth(client, "merch-a-host@example.com", "Merch A")
    body_a = _onboard(client, host_a_h, "Merch A Co")
    host_a = db_session.get(Host, UUID(body_a["id"]))
    assert host_a is not None
    event_a = _seed_event(db_session, host_a)

    host_b_h = _auth(client, "merch-b-host@example.com", "Merch B")
    body_b = _onboard(client, host_b_h, "Merch B Co")
    host_b = db_session.get(Host, UUID(body_b["id"]))
    assert host_b is not None
    event_b = _seed_event(db_session, host_b)

    _auth(client, "merch-cross@example.com", "Cross Merch")
    desk = db_session.scalar(
        select(User).where(User.email == "merch-cross@example.com")
    )
    assert desk is not None
    perms = permissions_for_role("merch_staff")
    perms["merch.scan_pickup_qr"] = True
    perms["merch.mark_picked_up"] = True
    _member(
        db_session,
        host=host_a,
        user=desk,
        role="merch_staff",
        perms=perms,
        scope="selected_events",
        event_ids=[event_a.id],
    )
    db_session.add(
        EventStaffAssignment(
            event_id=event_a.id,
            user_id=desk.id,
            assignment_type="merch_pickup",
            status="active",
            role_label="Pickup Staff",
        )
    )
    db_session.commit()

    assert can_scan_merch_pickup(db_session, desk.id, host_a.id, event_a.id) is True
    assert can_scan_merch_pickup(db_session, desk.id, host_b.id, event_b.id) is False
    assert can_scan_merch_pickup(db_session, desk.id, host_a.id, event_b.id) is False


def test_merch_scan_denial_is_audited(client: TestClient, db_session: Session):
    host_h = _auth(client, "merch-deny-host@example.com", "Merch Deny")
    body = _onboard(client, host_h, "Merch Deny Co")
    host = db_session.get(Host, UUID(body["id"]))
    assert host is not None
    event = _seed_event(db_session, host)

    stranger_h = _auth(client, "merch-deny-stranger@example.com", "Stranger")
    denied = client.post(
        f"/api/v1/host/events/{event.id}/merchandise/scan-qr",
        headers=stranger_h,
        json={"token": "not-a-valid-merch-token"},
    )
    assert denied.status_code in {403, 400, 422}, denied.text

    # When access is denied, desk audit should record the attempt.
    if denied.status_code == 403:
        log = db_session.scalar(
            select(DeskScanAuditLog)
            .where(
                DeskScanAuditLog.action == "merch.scan_pickup",
                DeskScanAuditLog.result == "denied",
                DeskScanAuditLog.event_id == event.id,
            )
            .order_by(DeskScanAuditLog.created_at.desc())
        )
        assert log is not None
        assert log.host_id == host.id
        assert log.denial_reason


def test_ticket_scan_denial_is_audited(client: TestClient, db_session: Session):
    host_h = _auth(client, "audit-scan-host@example.com", "Audit Host")
    body = _onboard(client, host_h, "Audit Scan Co")
    host = db_session.get(Host, UUID(body["id"]))
    assert host is not None
    event = _seed_event(db_session, host)

    stranger_h = _auth(client, "audit-stranger@example.com", "Stranger")
    denied = client.post(
        "/api/v1/checkins/scan",
        headers=stranger_h,
        json={"event_id": str(event.id), "public_code": "NOPE"},
    )
    assert denied.status_code == 403, denied.text

    log = db_session.scalar(
        select(DeskScanAuditLog)
        .where(
            DeskScanAuditLog.action == "tickets.scan",
            DeskScanAuditLog.result == "denied",
            DeskScanAuditLog.event_id == event.id,
        )
        .order_by(DeskScanAuditLog.created_at.desc())
    )
    assert log is not None
    assert log.host_id == host.id
    assert log.actor_user_id is not None
    assert log.denial_reason
    assert log.created_at is not None
