"""Central host-team permission checker (app.teams.permissions)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
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
    get_team_membership,
    has_event_permission,
    has_event_staff_assignment,
    has_host_permission,
    is_host_owner,
    require_event_permission,
    require_host_permission,
)
from app.users.models import User
from app.users.service import get_role_by_name


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
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
            "bio": "Permission host for tests with enough text.",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _seed_event(db: Session, host: Host) -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Perm Night",
        slug=f"perm-night-{uuid4().hex[:8]}",
        description="Event for permission checker tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Arena",
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
            price=Decimal("1000.00"),
            quantity=50,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    db.refresh(event)
    return event


def test_owner_and_membership_helpers(client: TestClient, db_session: Session):
    host_h = _auth(client, "perm-owner@example.com", "Owner")
    body = _onboard(client, host_h, "Owner Co")
    host = db_session.get(Host, UUID(body["id"]))
    assert host is not None
    owner = db_session.get(User, host.user_id)
    assert owner is not None

    assert is_host_owner(db_session, owner.id, host.id) is True
    assert has_host_permission(db_session, owner.id, host.id, "team.invite") is True
    assert has_host_permission(
        db_session, owner.id, host.id, "finance.manage_payout_settings"
    ) is True

    _auth(client, "perm-tm@example.com", "TM")
    member = db_session.scalar(select(User).where(User.email == "perm-tm@example.com"))
    assert member is not None
    assert is_host_owner(db_session, member.id, host.id) is False
    assert get_team_membership(db_session, member.id, host.id) is None

    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=member.id,
            role="admin",
            role_label="Admin",
            status="active",
            permissions_json=permissions_for_role("admin"),
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    row = get_team_membership(db_session, member.id, host.id)
    assert row is not None
    assert has_host_permission(db_session, member.id, host.id, "team.invite") is True
    assert has_host_permission(
        db_session, member.id, host.id, "finance.manage_payout_settings"
    ) is False
    require_host_permission(db_session, member.id, host.id, "team.view")
    with pytest.raises(HTTPException) as exc:
        require_host_permission(
            db_session, member.id, host.id, "finance.manage_payout_settings"
        )
    assert exc.value.status_code == 403


def test_event_permission_scope_and_staff(client: TestClient, db_session: Session):
    host_h = _auth(client, "scope-owner@example.com", "Scope Owner")
    body = _onboard(client, host_h, "Scope Owner Co")
    host = db_session.get(Host, UUID(body["id"]))
    assert host is not None
    event_a = _seed_event(db_session, host)
    event_b = _seed_event(db_session, host)

    _auth(client, "scope-tm@example.com", "Scope TM")
    member = db_session.scalar(select(User).where(User.email == "scope-tm@example.com"))
    assert member is not None
    role = get_role_by_name(db_session, "host_staff")
    if role and role not in member.roles:
        member.roles.append(role)

    perms = permissions_for_role("scanner")
    perms["tickets.scan_qr"] = True
    perms["tickets.check_in"] = True
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=member.id,
            role="scanner",
            role_label="Scanner",
            status="active",
            permissions_json=perms,
            scope_json=pack_scope_json("selected_events", [event_a.id]),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    assert (
        has_event_permission(
            db_session, member.id, host.id, event_a.id, "tickets.scan_qr"
        )
        is True
    )
    assert (
        has_event_permission(
            db_session, member.id, host.id, event_b.id, "tickets.scan_qr"
        )
        is False
    )
    assert can_scan_ticket(db_session, member.id, host.id, event_a.id) is True
    assert can_scan_ticket(db_session, member.id, host.id, event_b.id) is False

    db_session.add(
        EventStaffAssignment(
            event_id=event_b.id,
            user_id=member.id,
            assignment_type="ticket_scanner",
            role_label="scanner",
            status="active",
        )
    )
    db_session.commit()
    assert has_event_staff_assignment(
        db_session, member.id, event_b.id, "tickets.scan_qr"
    )
    assert can_scan_ticket(db_session, member.id, host.id, event_b.id) is True

    require_event_permission(
        db_session, member.id, host.id, event_a.id, "tickets.scan_qr"
    )
    with pytest.raises(HTTPException) as exc:
        require_event_permission(
            db_session, member.id, host.id, event_b.id, "merch.scan_pickup_qr"
        )
    assert exc.value.status_code == 403


def test_merch_desk_requires_merch_assignment_type(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "merch-owner@example.com", "Merch Owner")
    body = _onboard(client, host_h, "Merch Owner Co")
    host = db_session.get(Host, UUID(body["id"]))
    assert host is not None
    event = _seed_event(db_session, host)

    _auth(client, "merch-staff@example.com", "Merch Staff")
    staff = db_session.scalar(
        select(User).where(User.email == "merch-staff@example.com")
    )
    assert staff is not None
    role = get_role_by_name(db_session, "host_staff")
    if role and role not in staff.roles:
        staff.roles.append(role)

    row = EventStaffAssignment(
        event_id=event.id,
        user_id=staff.id,
        assignment_type="ticket_scanner",
        role_label="scanner",
        status="active",
    )
    db_session.add(row)
    db_session.commit()
    assert can_scan_ticket(db_session, staff.id, host.id, event.id) is True
    assert can_scan_merch_pickup(db_session, staff.id, host.id, event.id) is False

    row.assignment_type = "merch_pickup"
    db_session.commit()
    assert can_scan_merch_pickup(db_session, staff.id, host.id, event.id) is True
