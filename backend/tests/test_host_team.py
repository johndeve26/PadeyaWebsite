"""Host team invites, hybrid scan auth, permissions, and audit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checkins.models import EventStaffAssignment
from app.checkins.permissions import can_scan_event
from app.core.audit import AuditLog
from app.email.models import EmailEvent
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile, HostTeamInvite, HostTeamMember
from app.hosts.team_permissions import permissions_for_role
from app.merch.service import can_fulfill_event_merch
from app.users.models import User
from app.users.service import get_role_by_name, user_has_role


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
            "bio": "Team host",
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
        title="Team Scan Night",
        slug=f"team-scan-{uuid4().hex[:8]}",
        description="Event for host team scan permission tests with enough text.",
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


def test_invite_unknown_email_pending_and_email_outbox(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "invite-host@example.com", "Invite Host")
    _onboard(client, host_h, "Invite Host Co")

    created = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "new-staff@example.com", "role": "scanner"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["user_id"] is None
    assert body["invited_email"] == "new-staff@example.com"
    assert body["permissions"]["tickets.scan_qr"] is False
    assert body["permissions"]["merch.scan_pickup_qr"] is False
    assert "invite_token_hash" not in body

    email_row = db_session.scalar(
        select(EmailEvent).where(EmailEvent.template == "team_invite")
    )
    assert email_row is not None
    assert email_row.recipient_email == "new-staff@example.com"
    assert "invite_path" in (email_row.context_json or {})
    path = (email_row.context_json or {}).get("invite_path", "")
    raw_token = path.rsplit("/", 1)[-1]
    assert raw_token and len(raw_token) >= 16
    invite_row = db_session.scalar(
        select(HostTeamInvite).where(HostTeamInvite.email == "new-staff@example.com")
    )
    assert invite_row is not None
    assert invite_row.token_hash
    assert invite_row.token_hash != raw_token
    import hashlib

    assert invite_row.token_hash == hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()


def test_invite_existing_user_accept_grants_host_staff(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "accept-host@example.com", "Accept Host")
    _onboard(client, host_h, "Accept Host Co")
    member_h = _auth(client, "accept-member@example.com", "Accept Member")

    invited = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "accept-member@example.com", "role": "ops"},
    )
    assert invited.status_code == 201, invited.text
    assert invited.json()["status"] == "pending"

    row = db_session.scalar(
        select(HostTeamInvite).where(
            HostTeamInvite.email == "accept-member@example.com"
        )
    )
    assert row is not None
    assert row.status == "pending"
    # Recover raw token from email context
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "team_invite",
            EmailEvent.recipient_email == "accept-member@example.com",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    path = (email_row.context_json or {}).get("invite_path", "")
    token = path.rsplit("/", 1)[-1]
    assert token

    preview = client.get(f"/api/v1/hosts/team-invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["host_display_name"]
    assert "***" in preview.json()["invited_email_hint"]
    assert "accept-member@example.com" not in preview.json()["invited_email_hint"]

    wrong = _auth(client, "wrong-accept@example.com", "Wrong")
    denied = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept",
        headers=wrong,
    )
    assert denied.status_code == 403
    assert "invited email" in denied.json()["detail"].lower()

    accepted = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"
    assert accepted.json()["role"] == "event_manager"

    db_session.expire_all()
    member = db_session.scalar(
        select(User).where(User.email == "accept-member@example.com")
    )
    assert member is not None
    assert user_has_role(member, "host_staff")

    audits = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.action == "hosts.team_accept")
        )
    )
    assert audits


def test_hybrid_scan_host_wide_and_event_staff(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "scan-host@example.com", "Scan Host")
    host_body = _onboard(client, host_h, "Scan Host Co")
    host = db_session.get(Host, UUID(host_body["id"]))
    assert host is not None
    event = _seed_event(db_session, host)

    # Member with host-wide scan — no event assignment
    member_h = _auth(client, "scan-member@example.com", "Scan Member")
    invite = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={
            "email": "scan-member@example.com",
            "role": "scanner",
            "scope": "host_wide",
            "permissions": {
                "tickets.scan_qr": True,
                "tickets.check_in": True,
                "merch.scan_pickup_qr": True,
                "merch.mark_picked_up": True,
            },
        },
    )
    assert invite.status_code == 201
    assert invite.json()["permissions"]["tickets.scan_qr"] is True
    assert invite.json()["scope"] == "host_wide"
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "scan-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    accepted = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept", headers=member_h
    )
    assert accepted.status_code == 200

    member = db_session.scalar(
        select(User).where(User.email == "scan-member@example.com")
    )
    assert member is not None
    assert can_scan_event(db_session, member, event.id) is True
    assert can_fulfill_event_merch(db_session, member, event.id) is True

    # Suspend blocks host-wide
    mid = accepted.json()["id"]
    assert (
        client.post(f"/api/v1/hosts/me/team/{mid}/suspend", headers=host_h).status_code
        == 200
    )
    db_session.expire_all()
    member = db_session.scalar(
        select(User).where(User.email == "scan-member@example.com")
    )
    assert can_scan_event(db_session, member, event.id) is False

    # Event staff alone still works (regression)
    staff_h = _auth(client, "event-only@example.com", "Event Only")
    staff_user = db_session.scalar(
        select(User).where(User.email == "event-only@example.com")
    )
    assert staff_user is not None
    role = get_role_by_name(db_session, "host_staff")
    if role and role not in staff_user.roles:
        staff_user.roles.append(role)
    db_session.add(
        EventStaffAssignment(
            event_id=event.id,
            user_id=staff_user.id,
            assigned_by_user_id=host.user_id,
            role_label="scanner",
        )
    )
    db_session.commit()
    db_session.refresh(staff_user)
    assert can_scan_event(db_session, staff_user, event.id) is True


def test_permission_toggle_blocks_scan(client: TestClient, db_session: Session):
    host_h = _auth(client, "perm-host@example.com", "Perm Host")
    host_body = _onboard(client, host_h, "Perm Host Co")
    host = db_session.get(Host, UUID(host_body["id"]))
    assert host is not None
    event = _seed_event(db_session, host)
    member_h = _auth(client, "perm-member@example.com", "Perm Member")

    invite = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "perm-member@example.com", "role": "scanner"},
    )
    assert invite.status_code == 201
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "perm-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    accepted = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept", headers=member_h
    )
    assert accepted.status_code == 200
    mid = accepted.json()["id"]

    updated = client.patch(
        f"/api/v1/hosts/me/team/{mid}/permissions",
        headers=host_h,
        json={
            "role": "scanner",
            "permissions": {
                "tickets.scan_qr": False,
                "tickets.check_in": False,
                "merch.scan_pickup_qr": False,
                "merch.mark_picked_up": False,
            },
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["permissions"]["tickets.scan_qr"] is False

    member = db_session.scalar(
        select(User).where(User.email == "perm-member@example.com")
    )
    db_session.expire_all()
    member = db_session.scalar(
        select(User).where(User.email == "perm-member@example.com")
    )
    assert can_scan_event(db_session, member, event.id) is False


def test_non_host_cannot_manage_team(client: TestClient):
    host_h = _auth(client, "owner-only@example.com", "Owner")
    _onboard(client, host_h, "Owner Co")
    stranger = _auth(client, "stranger-team@example.com", "Stranger")
    assert (
        client.get("/api/v1/hosts/me/team", headers=stranger).status_code == 404
    )
    assert (
        client.post(
            "/api/v1/hosts/me/team/invite",
            headers=stranger,
            json={"email": "x@example.com", "role": "scanner"},
        ).status_code
        == 404
    )


def test_role_defaults():
    from app.hosts.team_permissions import (
        PERMISSION_KEYS,
        default_scope_for_role,
        normalize_role,
    )

    scanner = permissions_for_role("scanner")
    assert scanner["tickets.scan_qr"] is False
    assert scanner["merch.scan_pickup_qr"] is False
    assert scanner["events.view"] is True
    assert len(PERMISSION_KEYS) >= 40
    assert default_scope_for_role("scanner") == "selected_events"
    assert default_scope_for_role("merch_staff") == "selected_events"
    assert default_scope_for_role("admin") == "host_wide"
    assert default_scope_for_role("sponsor_manager") == "host_wide"
    assert default_scope_for_role("viewer") == "selected_events"
    assert default_scope_for_role("event_manager") == "host_wide"
    assert default_scope_for_role("ambassador_manager") == "host_wide"
    assert default_scope_for_role("finance_manager") == "host_wide"
    assert default_scope_for_role("support_staff") == "host_wide"

    assert normalize_role("ops") == "event_manager"
    assert normalize_role("manager") == "admin"
    assert normalize_role("ambassador") == "ambassador_manager"
    assert normalize_role("finance") == "finance_manager"
    assert permissions_for_role("event_manager")["events.create"] is True
    assert permissions_for_role("event_manager")["tickets.scan_qr"] is False
    assert permissions_for_role("event_manager")["ambassadors.view"] is True
    assert permissions_for_role("event_manager")["ambassadors.view_conversions"] is True
    assert permissions_for_role("event_manager")["ambassadors.create_campaigns"] is False

    admin = permissions_for_role("admin")
    assert admin["team.invite"] is True
    assert admin["team.edit_permissions"] is True
    assert admin["finance.manage_payout_settings"] is False
    assert admin["finance.view_payouts"] is False
    assert admin["finance.manage_payouts"] is False
    assert admin["events.publish"] is True
    assert admin["tickets.scan_qr"] is False
    assert admin["ambassadors.approve_rewards"] is True
    assert admin["ambassadors.reverse_rewards"] is True
    assert admin["ambassadors.mark_rewards_paid"] is False
    assert admin["ambassadors.export"] is False

    amb_mgr = permissions_for_role("ambassador_manager")
    assert amb_mgr["ambassadors.create_campaigns"] is True
    assert amb_mgr["ambassadors.approve_rewards"] is True
    assert amb_mgr["ambassadors.mark_rewards_paid"] is False
    assert amb_mgr["events.create"] is False

    fin_mgr = permissions_for_role("finance_manager")
    assert fin_mgr["finance.manage_payouts"] is True
    assert fin_mgr["ambassadors.mark_rewards_paid"] is True
    assert fin_mgr["ambassadors.approve_rewards"] is False

    assert permissions_for_role("merch_staff")["merch.scan_pickup_qr"] is False
    assert permissions_for_role("support_staff")["messages.reply"] is True
    assert permissions_for_role("sponsor_manager")["sponsors.manage_slots"] is True
    assert permissions_for_role("viewer")["events.view"] is True
    assert permissions_for_role("viewer")["events.edit"] is False
    assert permissions_for_role("viewer")["ambassadors.view"] is False


def test_cannot_invite_host_owner(client: TestClient):
    host_h = _auth(client, "self-invite-host@example.com", "Self Host")
    _onboard(client, host_h, "Self Host Co")
    blocked = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "self-invite-host@example.com", "role": "admin"},
    )
    assert blocked.status_code == 400, blocked.text


def test_admin_with_manage_team_can_invite_on_host_route(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "admin-owner@example.com", "Admin Owner")
    host_body = _onboard(client, host_h, "Admin Owner Co")
    host_id = host_body["id"]
    admin_h = _auth(client, "admin-member@example.com", "Admin Member")

    invite = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "admin-member@example.com", "role": "admin"},
    )
    assert invite.status_code == 201
    assert invite.json()["permissions"]["team.invite"] is True
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "admin-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    accepted = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept", headers=admin_h
    )
    assert accepted.status_code == 200
    mid = accepted.json()["id"]

    # Admin can list/invite via host-scoped route
    listed = client.get(f"/api/v1/hosts/{host_id}/team", headers=admin_h)
    assert listed.status_code == 200, listed.text

    # Non-owner cannot grant finance.manage_payout_settings
    patched = client.patch(
        f"/api/v1/hosts/{host_id}/team/{mid}/permissions",
        headers=admin_h,
        json={
            "role": "admin",
            "permissions": {
                **invite.json()["permissions"],
                "finance.manage_payout_settings": True,
                "finance.view_payouts": True,
            },
        },
    )
    assert patched.status_code == 200
    assert patched.json()["permissions"]["finance.manage_payout_settings"] is False
    # view_payouts is not owner-only — admin may grant it
    assert patched.json()["permissions"]["finance.view_payouts"] is True

    # Scanner without team.* cannot access team routes
    scan_h = _auth(client, "no-team-perm@example.com", "No Team")
    inv2 = client.post(
        f"/api/v1/hosts/{host_id}/team/invite",
        headers=host_h,
        json={"email": "no-team-perm@example.com", "role": "scanner"},
    )
    assert inv2.status_code == 201
    email2 = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "no-team-perm@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    token2 = (email2.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    client.post(f"/api/v1/hosts/team-invites/{token2}/accept", headers=scan_h)
    denied = client.get(f"/api/v1/hosts/{host_id}/team", headers=scan_h)
    assert denied.status_code == 403


def test_workspaces_for_owner_and_team_member(client: TestClient, db_session: Session):
    host_h = _auth(client, "ws-host@example.com", "WS Host")
    host_body = _onboard(client, host_h, "WS Host Co")
    member_h = _auth(client, "ws-member@example.com", "WS Member")

    owner_ws = client.get("/api/v1/hosts/workspaces", headers=host_h)
    assert owner_ws.status_code == 200
    assert any(
        w["host_id"] == host_body["id"] and w["is_owner"] for w in owner_ws.json()
    )

    invite = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "ws-member@example.com", "role": "scanner"},
    )
    assert invite.status_code == 201
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "ws-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    assert (
        client.post(
            f"/api/v1/hosts/team-invites/{token}/accept", headers=member_h
        ).status_code
        == 200
    )

    member_ws = client.get("/api/v1/hosts/workspaces", headers=member_h)
    assert member_ws.status_code == 200
    rows = member_ws.json()
    match = next(w for w in rows if w["host_id"] == host_body["id"])
    assert match["is_owner"] is False
    assert match["kind"] == "team_member"
    assert match["permissions"]["finance.manage_payout_settings"] is False
    assert match["permissions"]["tickets.scan_qr"] is False


def test_selected_events_scope_syncs_staff_and_limits_host_wide_scan(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "scope-host@example.com", "Scope Host")
    host_body = _onboard(client, host_h, "Scope Host Co")
    host = db_session.get(Host, UUID(host_body["id"]))
    assert host is not None
    event_a = _seed_event(db_session, host)
    event_b = _seed_event(db_session, host)

    member_h = _auth(client, "scope-member@example.com", "Scope Member")
    invite = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={
            "email": "scope-member@example.com",
            "role": "scanner",
            "scope": "selected_events",
            "scoped_event_ids": [str(event_a.id)],
            "permissions": {
                "tickets.scan_qr": True,
                "tickets.check_in": True,
            },
        },
    )
    assert invite.status_code == 201, invite.text
    assert invite.json()["scope"] == "selected_events"
    assert str(event_a.id) in [str(x) for x in invite.json()["scoped_event_ids"]]

    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "scope-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    assert (
        client.post(
            f"/api/v1/hosts/team-invites/{token}/accept", headers=member_h
        ).status_code
        == 200
    )

    member = db_session.scalar(
        select(User).where(User.email == "scope-member@example.com")
    )
    assert member is not None
    assert can_scan_event(db_session, member, event_a.id) is True
    assert can_scan_event(db_session, member, event_b.id) is False
    staff = db_session.scalar(
        select(EventStaffAssignment).where(
            EventStaffAssignment.event_id == event_a.id,
            EventStaffAssignment.user_id == member.id,
        )
    )
    assert staff is not None


def test_scanner_default_needs_event_assignment(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "desk-host@example.com", "Desk Host")
    host_body = _onboard(client, host_h, "Desk Host Co")
    host = db_session.get(Host, UUID(host_body["id"]))
    assert host is not None
    event = _seed_event(db_session, host)
    member_h = _auth(client, "desk-member@example.com", "Desk Member")

    invite = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "desk-member@example.com", "role": "scanner"},
    )
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "desk-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    client.post(f"/api/v1/hosts/team-invites/{token}/accept", headers=member_h)

    member = db_session.scalar(
        select(User).where(User.email == "desk-member@example.com")
    )
    assert member is not None
    assert can_scan_event(db_session, member, event.id) is False

    db_session.add(
        EventStaffAssignment(
            event_id=event.id,
            user_id=member.id,
            assigned_by_user_id=host.user_id,
            role_label="scanner",
        )
    )
    db_session.commit()
    db_session.refresh(member)
    assert can_scan_event(db_session, member, event.id) is True


def test_legacy_create_becomes_pending_invite(client: TestClient, db_session: Session):
    host_h = _auth(client, "legacy-host@example.com", "Legacy Host")
    _onboard(client, host_h, "Legacy Host Co")
    member_h = _auth(client, "legacy-member@example.com", "Legacy Member")
    member_id = client.get("/api/v1/users/me", headers=member_h).json()["id"]

    created = client.post(
        "/api/v1/hosts/me/team",
        headers=host_h,
        json={"user_id": member_id, "role_label": "ops"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending"

    audits = db_session.scalars(
        select(AuditLog).where(AuditLog.resource_type == "host_team_member")
    ).all()
    assert any(a.action in {"hosts.team_invite", "hosts.team_create"} for a in audits)


def test_invite_expires_in_seven_days_and_marks_accepted(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "ttl-host@example.com", "TTL Host")
    _onboard(client, host_h, "TTL Host Co")
    member_h = _auth(client, "ttl-member@example.com", "TTL Member")

    invited = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "ttl-member@example.com", "role": "scanner"},
    )
    assert invited.status_code == 201
    raw_expires = invited.json()["invite_expires_at"]
    expires = datetime.fromisoformat(raw_expires.replace("Z", "+00:00"))
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    delta = expires - datetime.now(UTC)
    assert timedelta(days=6, hours=20) < delta < timedelta(days=7, hours=4)

    invite_row = db_session.scalar(
        select(HostTeamInvite).where(HostTeamInvite.email == "ttl-member@example.com")
    )
    assert invite_row is not None
    assert invite_row.token_hash
    assert "invite_token" not in invited.json()
    assert "token_hash" not in invited.json()

    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "ttl-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    accepted = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept", headers=member_h
    )
    assert accepted.status_code == 200
    assert accepted.json()["id"] != str(invite_row.id)

    db_session.expire_all()
    invite_row = db_session.get(HostTeamInvite, invite_row.id)
    assert invite_row is not None
    assert invite_row.status == "accepted"
    assert invite_row.accepted_at is not None

    member_row = db_session.get(HostTeamMember, UUID(accepted.json()["id"]))
    assert member_row is not None
    assert member_row.status == "active"

    host_mail = db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.template == "team_invite_accepted",
            EmailEvent.recipient_email == "ttl-host@example.com",
        )
    )
    assert host_mail is not None


def test_revoke_and_expired_invites_cannot_be_accepted(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "revoke-host@example.com", "Revoke Host")
    _onboard(client, host_h, "Revoke Host Co")
    member_h = _auth(client, "revoke-member@example.com", "Revoke Member")

    invited = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "revoke-member@example.com", "role": "scanner"},
    )
    invite_id = invited.json()["id"]
    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "revoke-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]

    revoked = client.post(
        f"/api/v1/hosts/me/team/{invite_id}/revoke", headers=host_h
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] in {"revoked", "declined"}
    blocked = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept", headers=member_h
    )
    assert blocked.status_code in {400, 404}

    # Fresh invite then force-expire (reuses revoked row with new token)
    invited2 = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "revoke-member@example.com", "role": "viewer"},
    )
    assert invited2.status_code == 201
    invite2_id = UUID(invited2.json()["id"])
    db_session.expire_all()
    row2 = db_session.get(HostTeamInvite, invite2_id)
    assert row2 is not None
    assert row2.status == "pending"
    assert row2.token_hash

    email2 = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "revoke-member@example.com",
            EmailEvent.template == "team_invite",
            EmailEvent.dedupe_key == f"team_invite:{row2.id}:{row2.token_hash}",
        )
    )
    assert email2 is not None
    token2 = (email2.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    assert token2
    assert client.get(f"/api/v1/hosts/team-invites/{token2}").status_code == 200

    row2.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.commit()

    expired = client.post(
        f"/api/v1/hosts/team-invites/{token2}/accept", headers=member_h
    )
    assert expired.status_code == 400, expired.text


def test_duplicate_pending_invite_is_replaced(client: TestClient, db_session: Session):
    host_h = _auth(client, "dup-host@example.com", "Dup Host")
    _onboard(client, host_h, "Dup Host Co")

    first = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "dup-member@example.com", "role": "scanner"},
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "dup-member@example.com", "role": "admin"},
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id
    assert second.json()["role"] == "admin"

    pending = list(
        db_session.scalars(
            select(HostTeamInvite).where(
                HostTeamInvite.email == "dup-member@example.com",
                HostTeamInvite.status == "pending",
            )
        )
    )
    assert len(pending) == 1


def test_invite_by_padeya_username_with_and_without_at(
    client: TestClient, db_session: Session
):
    from app.passport.service import ensure_passport

    host_h = _auth(client, "uname-host@example.com", "Uname Host")
    _onboard(client, host_h, "Uname Host Co")
    member_h = _auth(client, "gatekeeper@example.com", "Gate Keeper")
    member = db_session.scalar(
        select(User).where(User.email == "gatekeeper@example.com")
    )
    assert member is not None
    passport = ensure_passport(db_session, member)
    passport.username = "gatekeeper"
    db_session.commit()

    import hashlib

    bare = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "gatekeeper", "role": "scanner"},
    )
    assert bare.status_code == 201, bare.text
    assert bare.json()["status"] == "pending"
    assert bare.json()["invited_email"] is None
    assert bare.json()["invited_username"] == "@gatekeeper"
    assert bare.json()["user_id"] == str(member.id)

    # Re-invite with @ prefix replaces pending row and rotates token
    invited = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "@gatekeeper", "role": "scanner"},
    )
    assert invited.status_code == 201, invited.text
    assert invited.json()["invited_email"] is None
    assert invited.json()["invited_username"] == "@gatekeeper"
    assert invited.json()["id"] == bare.json()["id"]

    db_session.expire_all()
    invite_row = db_session.get(HostTeamInvite, UUID(invited.json()["id"]))
    assert invite_row is not None and invite_row.status == "pending"
    email_rows = list(
        db_session.scalars(
            select(EmailEvent)
            .where(
                EmailEvent.template == "team_invite",
                EmailEvent.recipient_email == "gatekeeper@example.com",
            )
            .order_by(EmailEvent.created_at.desc())
        )
    )
    assert email_rows
    token = None
    for row in email_rows:
        candidate = (row.context_json or {}).get("invite_path", "").rsplit("/", 1)[-1]
        if (
            candidate
            and hashlib.sha256(candidate.encode("utf-8")).hexdigest()
            == invite_row.token_hash
        ):
            token = candidate
            break
    assert token, "expected invite email matching current token_hash"

    accepted = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"


def test_invite_unknown_username_returns_404(client: TestClient, db_session: Session):
    host_h = _auth(client, "missing-uname-host@example.com", "Missing Uname Host")
    _onboard(client, host_h, "Missing Uname Host Co")
    missing = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "@no_such_padeya_user", "role": "viewer"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "No Pàdéyá user found with that username."
    # Never create unknown-username pending invites
    assert (
        db_session.scalar(
            select(HostTeamInvite).where(
                HostTeamInvite.email.ilike("%no_such_padeya_user%")
            )
        )
        is None
    )


def test_username_invite_notifies_and_accept_requires_user_id(
    client: TestClient, db_session: Session
):
    from app.messaging.models import InAppNotification
    from app.passport.privacy import VISIBILITY_PUBLIC
    from app.passport.service import ensure_passport

    host_h = _auth(client, "uname-flow-host@example.com", "Uname Flow Host")
    _onboard(client, host_h, "Uname Flow Host Co")
    member_h = _auth(client, "uname-flow-member@example.com", "Uname Flow Member")
    member = db_session.scalar(
        select(User).where(User.email == "uname-flow-member@example.com")
    )
    assert member is not None
    passport = ensure_passport(db_session, member)
    passport.username = "uname_flow_member"
    passport.display_name = "Flow Member"
    passport.avatar_url = "https://cdn.example.com/uname-flow.png"
    passport.visibility = VISIBILITY_PUBLIC
    db_session.commit()

    invited = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={
            "invite_identifier": "@uname_flow_member",
            "role": "scanner",
            "permissions_json": {"tickets.scan_qr": True},
            "scope_json": {"type": "selected_events", "event_ids": []},
        },
    )
    assert invited.status_code == 201, invited.text
    body = invited.json()
    assert body["invite_id"]
    assert body["invite_method"] == "username"
    assert body["status"] == "pending"
    assert body["username"] == "@uname_flow_member"
    assert body["display_name"] == "Flow Member"
    assert body["avatar_url"] == "https://cdn.example.com/uname-flow.png"
    assert body.get("masked_email") is None
    assert "uname-flow-member@example.com" not in invited.text
    assert "invited_email" not in body
    # Delivery email still stored internally
    invite_row = db_session.get(HostTeamInvite, UUID(body["invite_id"]))
    assert invite_row is not None
    assert invite_row.email == "uname-flow-member@example.com"
    assert invite_row.invited_user_id == member.id

    note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == member.id,
            InAppNotification.kind == "team.invite",
        )
    )
    assert note is not None
    assert (
        "Uname Flow Host Co invited your Pàdéyá account @uname_flow_member"
        in (note.body or "")
    )

    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "team_invite",
            EmailEvent.recipient_email == "uname-flow-member@example.com",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]

    wrong = _auth(client, "uname-flow-wrong@example.com", "Wrong")
    denied = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=wrong,
    )
    assert denied.status_code == 403
    assert (
        denied.json()["detail"]
        == "This invite was sent to another Pàdéyá account."
    )

    accepted = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"
    assert accepted.json()["user_id"] == str(member.id)

    from app.core.audit import AuditLog

    audits = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.resource_type == "host_team_member")
        )
    )
    assert any(a.action == "hosts.team_invite" for a in audits)
    assert any(a.action == "hosts.team_accept" for a in audits)


def test_invite_resolve_helpers_distinguish_email_and_username():
    from app.hosts.team_invite_resolve import (
        looks_like_email,
        looks_like_username,
        normalize_invitee_input,
    )

    assert looks_like_email("staff@example.com")
    assert looks_like_email("  name@example.com  ")
    assert not looks_like_email("@gatekeeper")
    assert not looks_like_email("gatekeeper")
    assert looks_like_username("@gatekeeper")
    assert looks_like_username("gatekeeper")
    assert normalize_invitee_input("  Staff@Example.com  ") == "staff@example.com"
    assert normalize_invitee_input("@GateKeeper") == "@gatekeeper"
    assert normalize_invitee_input("GateKeeper") == "@gatekeeper"
    assert normalize_invitee_input("  @User_Name  ") == "@user_name"
