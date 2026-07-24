"""Host team audit: safe metadata, required actions, feed shape."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.models import EmailEvent
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostTeamAuditLog
from app.teams.scan_audit import DeskScanAuditLog, write_desk_scan_audit
from app.teams.team_audit import (
    finance_keys_granted,
    list_host_audit_feed,
    sanitize_audit_metadata,
)


def test_sanitize_audit_metadata_strips_secrets_and_payment_refs():
    raw = {
        "role": "admin",
        "token": "should-not-appear",
        "invite_token": "abc",
        "paystack_reference": "PSK_123",
        "payment_reference": "pay_ref_1",
        "account_number": "0123456789",
        "nested": {
            "ok": True,
            "webhook_secret": "whsec_xxx",
            "scope": "host_wide",
        },
        "long_opaque": "A" * 48,
        "permission": "finance.view_payouts",
    }
    safe = sanitize_audit_metadata(raw)
    assert safe is not None
    assert safe["role"] == "admin"
    assert safe["permission"] == "finance.view_payouts"
    assert "token" not in safe
    assert "invite_token" not in safe
    assert "paystack_reference" not in safe
    assert "payment_reference" not in safe
    assert "account_number" not in safe
    assert "long_opaque" not in safe
    assert safe["nested"]["ok"] is True
    assert safe["nested"]["scope"] == "host_wide"
    assert "webhook_secret" not in safe["nested"]


def test_finance_keys_granted_detects_new_grants():
    before = {"finance.view_payouts": False, "finance.manage_payout_settings": False}
    after = {"finance.view_payouts": True, "finance.manage_payout_settings": False}
    assert finance_keys_granted(before, after) == ["finance.view_payouts"]


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
            "bio": "Audit host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _invite_token(db: Session, email: str) -> str:
    email_row = db.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == email,
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    path = (email_row.context_json or {})["invite_path"]
    return path.rsplit("/", 1)[-1]


def _seed_event(db: Session, host: Host) -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Audit Scope Night",
        slug=f"audit-scope-{uuid4().hex[:8]}",
        description="Event for host team audit scope tests with enough text.",
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


def test_audit_feed_shape_and_required_actions(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "audit-feed-host@example.com", "Audit Host")
    host = _onboard(client, host_h, "Audit Feed Co")
    host_id = UUID(host["id"])
    host_row = db_session.get(Host, host_id)
    assert host_row is not None
    event = _seed_event(db_session, host_row)

    invitee_email = "audit-feed-member@example.com"
    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"email": invitee_email, "role": "viewer", "role_label": "Viewer"},
    )
    assert created.status_code == 201, created.text
    invite_id = created.json()["invite_id"]

    member_h = _auth(client, invitee_email, "Audit Member")
    accepted = client.post(
        f"/api/v1/team/invites/{_invite_token(db_session, invitee_email)}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    member_id = accepted.json()["id"]
    member_user_id = accepted.json()["user_id"]

    finance_patch = client.patch(
        f"/api/v1/host/team/members/{member_id}?host_id={host['id']}",
        headers=host_h,
        json={"permissions": {"finance.view_payouts": True}},
    )
    assert finance_patch.status_code == 200, finance_patch.text
    assert finance_patch.json()["permissions"]["finance.view_payouts"] is True

    scope_patch = client.patch(
        f"/api/v1/host/team/members/{member_id}?host_id={host['id']}",
        headers=host_h,
        json={
            "scope": "selected_events",
            "scoped_event_ids": [str(event.id)],
        },
    )
    assert scope_patch.status_code == 200, scope_patch.text
    assert scope_patch.json()["scope"] == "selected_events"

    denied = client.post(
        f"/api/v1/host/team/invites?host_id={host['id']}",
        headers=member_h,
        json={"email": "should-fail@example.com", "role": "scanner"},
    )
    assert denied.status_code == 403

    write_desk_scan_audit(
        db_session,
        actor_user_id=UUID(member_user_id),
        host_profile_id=host_id,
        event_id=event.id,
        action="tickets.scan",
        result="success",
        metadata={
            "paystack_reference": "must-not-leak",
            "lane": "gate-a",
        },
    )
    db_session.commit()

    audit = client.get(
        f"/api/v1/host/team/audit-log?host_id={host['id']}&limit=100",
        headers=host_h,
    )
    assert audit.status_code == 200, audit.text
    rows = audit.json()
    assert len(rows) >= 1

    actions = {r["action"] for r in rows}
    assert "hosts.team_invite" in actions
    assert "hosts.team_accept" in actions
    assert "hosts.team_member_added" in actions
    assert "hosts.team_finance_permission_grant" in actions
    assert "hosts.team_scope_update" in actions
    assert "hosts.team_permission_denied" in actions
    assert "tickets.scan" in actions

    for row in rows:
        assert row.get("action")
        assert row.get("action_label")
        assert row.get("created_at")
        assert row.get("entity_type") or row.get("resource_type")
        details = row.get("details") or {}
        assert "token" not in details
        assert "paystack_reference" not in details
        assert "payment_reference" not in details
        blob = str(details).lower()
        assert "must-not-leak" not in blob

    invite_log = db_session.scalar(
        select(HostTeamAuditLog).where(
            HostTeamAuditLog.host_id == host_id,
            HostTeamAuditLog.action == "hosts.team_invite",
            HostTeamAuditLog.entity_id == invite_id,
        )
    )
    assert invite_log is not None
    meta = invite_log.metadata_json or {}
    assert "token" not in meta
    assert "permissions" not in meta

    feed = list_host_audit_feed(db_session, host_id=host_id, limit=50)
    assert any(r["source"] == "desk_scan" for r in feed)
    desk = next(r for r in feed if r["action"] == "tickets.scan")
    assert desk["action_label"] == "Ticket scanned"
    assert (desk.get("details") or {}).get("lane") == "gate-a"


def test_desk_scan_write_sanitizes_metadata(db_session: Session):
    row = write_desk_scan_audit(
        db_session,
        actor_user_id=None,
        host_profile_id=None,
        event_id=None,
        action="merch.scan_pickup",
        result="denied",
        denial_reason="missing_permission",
        metadata={
            "payment_ref": "secret-ref",
            "sku": "TEE-1",
        },
    )
    db_session.commit()
    stored = db_session.get(DeskScanAuditLog, row.id)
    assert stored is not None
    assert stored.metadata_json is not None
    assert "payment_ref" not in stored.metadata_json
    assert stored.metadata_json.get("sku") == "TEE-1"
