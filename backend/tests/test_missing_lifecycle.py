"""Coverage for previously missing resource lifecycles."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.hosts.models import HostVerification


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


def _relogin(client: TestClient, email: str) -> dict[str, str]:
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
            "bio": "Lifecycle",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_host_team_lifecycle_and_ownership(client: TestClient, db_session: Session):
    from app.email.models import EmailEvent

    host_h = _auth(client, "team-host@example.com", "Team Host")
    _onboard(client, host_h, "Team Host Co")
    member_h = _auth(client, "team-member@example.com", "Member")

    created = client.post(
        "/api/v1/hosts/me/team/invite",
        headers=host_h,
        json={"email": "team-member@example.com", "role": "ops"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending"

    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == "team-member@example.com",
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    token = (email_row.context_json or {})["invite_path"].rsplit("/", 1)[-1]
    accepted = client.post(
        f"/api/v1/hosts/team-invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"
    tid = accepted.json()["id"]

    listed = client.get("/api/v1/hosts/me/team", headers=host_h)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/v1/hosts/me/team/{tid}",
        headers=host_h,
        json={"role": "manager", "role_label": "Admin"},
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "admin"

    other = _auth(client, "other-host@example.com", "Other")
    _onboard(client, other, "Other Host")
    assert (
        client.get(f"/api/v1/hosts/me/team/{tid}", headers=other).status_code == 404
    )

    assert client.delete(f"/api/v1/hosts/me/team/{tid}", headers=host_h).status_code == 405

    archived = client.post(f"/api/v1/hosts/me/team/{tid}/archive", headers=host_h)
    assert archived.status_code == 200
    assert archived.json()["status"] == "removed"
    assert archived.json()["archived_at"] is not None

    restored = client.post(f"/api/v1/hosts/me/team/{tid}/restore", headers=host_h)
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"
    assert restored.json()["archived_at"] is None

    audits = db_session.scalars(
        select(AuditLog).where(AuditLog.resource_type == "host_team_member")
    ).all()
    assert any(a.action == "hosts.team_invite" for a in audits)
    # Soft-remove via /archive (alias of remove) writes hosts.team_remove
    assert any(
        a.action in ("hosts.team_remove", "hosts.team_archive") for a in audits
    )


def test_host_bank_account_masks_number_and_blocks_hard_delete(client: TestClient):
    headers = _auth(client, "bank-host@example.com", "Bank Host")
    _onboard(client, headers, "Bank Host Co")
    created = client.post(
        "/api/v1/hosts/me/bank-accounts",
        headers=headers,
        json={
            "label": "Primary",
            "bank_name": "GTBank",
            "account_name": "Bank Host",
            "account_number": "0123456789",
            "is_default": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["account_number_last4"] == "6789"
    assert "account_number" not in body
    assert "account_number_encrypted" not in body
    aid = body["id"]

    assert client.delete(f"/api/v1/hosts/me/bank-accounts/{aid}", headers=headers).status_code == 405
    archived = client.post(f"/api/v1/hosts/me/bank-accounts/{aid}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    restored = client.post(f"/api/v1/hosts/me/bank-accounts/{aid}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_host_verification_approve_reject_roles(
    client: TestClient, assign_role, db_session: Session
):
    host_h = _auth(client, "verify-host@example.com", "Verify Host")
    host = _onboard(client, host_h, "Verify Host Co")
    verification = db_session.scalar(
        select(HostVerification).where(HostVerification.host_id == UUID(host["id"]))
    )
    assert verification is not None
    vid = str(verification.id)

    buyer = _auth(client, "verify-buyer@example.com", "Buyer")
    assert (
        client.post(
            f"/api/v1/hosts/admin/verifications/{vid}/approve", headers=buyer
        ).status_code
        == 403
    )

    admin_email = "verify-admin@example.com"
    _auth(client, admin_email, "Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    approved = client.post(
        f"/api/v1/hosts/admin/verifications/{vid}/approve", headers=admin
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["host_display_name"] == "Verify Host Co"
    assert approved.json()["owner_email"] == "verify-host@example.com"

    listed = client.get("/api/v1/hosts/admin/verifications", headers=admin)
    assert listed.status_code == 200
    match = next(r for r in listed.json() if r["id"] == vid)
    assert match["host_display_name"] == "Verify Host Co"
    assert match["host_slug"]
    assert match["owner_user_id"]
    assert "password" not in listed.text.lower()

    host2_h = _auth(client, "verify-host2@example.com", "Host Two")
    host2 = _onboard(client, host2_h, "Host Two Co")
    v2 = db_session.scalar(
        select(HostVerification).where(HostVerification.host_id == UUID(host2["id"]))
    )
    assert v2 is not None
    rejected = client.post(
        f"/api/v1/hosts/admin/verifications/{v2.id}/reject",
        headers=admin,
        json={"notes": "Incomplete documents"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_event_templates_archive_restore(client: TestClient):
    headers = _auth(client, "tmpl-host@example.com", "Tmpl Host")
    _onboard(client, headers, "Tmpl Host Co")
    created = client.post(
        "/api/v1/events/templates",
        headers=headers,
        json={"name": "Club Night", "payload": {"venue_name": "Hall"}},
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    listed = client.get("/api/v1/events/templates", headers=headers)
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/v1/events/templates/{tid}",
        headers=headers,
        json={"name": "Club Night v2"},
    )
    assert patched.json()["name"] == "Club Night v2"

    assert client.delete(f"/api/v1/events/templates/{tid}", headers=headers).status_code == 405
    assert (
        client.post(f"/api/v1/events/templates/{tid}/archive", headers=headers).json()[
            "status"
        ]
        == "archived"
    )
    assert (
        client.post(f"/api/v1/events/templates/{tid}/restore", headers=headers).json()[
            "status"
        ]
        == "active"
    )


def test_vault_subscription_cancel_archive(client: TestClient):
    host_h = _auth(client, "sub-host@example.com", "Sub Host")
    host = _onboard(client, host_h, "Sub Host Co")
    buyer = _auth(client, "sub-buyer@example.com", "Buyer")

    created = client.post(
        "/api/v1/vault/subscriptions",
        headers=buyer,
        json={"host_id": host["id"], "plan_label": "standard", "price": "5000"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["id"]

    mine = client.get("/api/v1/vault/subscriptions/mine", headers=buyer)
    assert len(mine.json()) == 1

    host_list = client.get("/api/v1/vault/host/subscriptions", headers=host_h)
    assert len(host_list.json()) == 1

    assert client.delete(f"/api/v1/vault/subscriptions/{sid}", headers=buyer).status_code == 405
    cancelled = client.post(f"/api/v1/vault/subscriptions/{sid}/cancel", headers=buyer)
    assert cancelled.json()["status"] == "cancelled"
    archived = client.post(f"/api/v1/vault/subscriptions/{sid}/archive", headers=buyer)
    assert archived.json()["archived_at"] is not None
    restored = client.post(f"/api/v1/vault/subscriptions/{sid}/restore", headers=buyer)
    assert restored.json()["archived_at"] is None


def test_cms_blog_publish_and_public_read(client: TestClient, assign_role):
    admin_email = "cms-admin@example.com"
    _auth(client, admin_email, "CMS Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    created = client.post(
        "/api/v1/cms/admin/blog",
        headers=admin,
        json={"title": "Hello Pàdéyá", "body": "Welcome to the platform."},
    )
    assert created.status_code == 201, created.text
    post_id = created.json()["id"]
    slug = created.json()["slug"]
    assert created.json()["status"] == "draft"

    assert client.get(f"/api/v1/cms/blog/{slug}").status_code == 404
    published = client.post(f"/api/v1/cms/admin/blog/{post_id}/publish", headers=admin)
    assert published.json()["status"] == "published"
    public = client.get(f"/api/v1/cms/blog/{slug}")
    assert public.status_code == 200
    assert public.json()["title"] == "Hello Pàdéyá"

    assert client.delete(f"/api/v1/cms/admin/blog/{post_id}", headers=admin).status_code == 405
    archived = client.post(f"/api/v1/cms/admin/blog/{post_id}/archive", headers=admin)
    assert archived.json()["status"] == "archived"
    assert client.get(f"/api/v1/cms/blog/{slug}").status_code == 404


def test_user_profile_deactivate_restore(client: TestClient, assign_role):
    user_h = _auth(client, "profile-user@example.com", "Profile User")
    patched = client.patch(
        "/api/v1/users/me",
        headers=user_h,
        json={"full_name": "Updated Name"},
    )
    assert patched.status_code == 200
    assert patched.json()["full_name"] == "Updated Name"
    user_id = patched.json()["id"]

    admin_email = "user-admin@example.com"
    _auth(client, admin_email, "Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    assert client.delete(f"/api/v1/users/admin/{user_id}", headers=admin).status_code == 405
    deactivated = client.post(
        f"/api/v1/users/admin/{user_id}/deactivate",
        headers=admin,
        json={"reason": "Profile lifecycle test deactivate"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert deactivated.json().get("account_status") == "suspended"

    # Suspended users may sign in to view status and submit an appeal.
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "profile-user@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200

    restored = client.post(
        f"/api/v1/users/admin/{user_id}/restore",
        headers=admin,
        json={"reason": "Profile lifecycle test restore"},
    )
    assert restored.json()["is_active"] is True


def test_audit_log_admin_list(client: TestClient, assign_role):
    host_h = _auth(client, "audit-host@example.com", "Audit Host")
    _onboard(client, host_h, "Audit Host Co")

    buyer = _auth(client, "audit-buyer@example.com", "Buyer")
    assert client.get("/api/v1/admin/audit-logs", headers=buyer).status_code == 403

    admin_email = "audit-admin@example.com"
    _auth(client, admin_email, "Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    logs = client.get(
        "/api/v1/admin/audit-logs",
        headers=admin,
        params={"action": "hosts.onboard"},
    )
    assert logs.status_code == 200
    assert len(logs.json()) >= 1
    assert logs.json()[0]["action"] == "hosts.onboard"


def test_featured_and_category_admin(client: TestClient, assign_role):
    host_h = _auth(client, "feat-host@example.com", "Feat Host")
    _onboard(client, host_h, "Feat Host Co")
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    event = client.post(
        "/api/v1/events",
        headers=host_h,
        json={
            "title": "Featured Night",
            "description": "A night out for featured testing coverage.",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "venue_name": "Hall",
            "city": "Lagos",
            "state": "Lagos",
            "venue": {
                "name": "Hall",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
        },
    )
    assert event.status_code == 201, event.text
    eid = event.json()["id"]

    admin_email = "feat-admin@example.com"
    _auth(client, admin_email, "Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    featured = client.post(f"/api/v1/events/admin/{eid}/feature", headers=admin)
    assert featured.status_code == 200
    assert featured.json()["featured"] is True
    unfeatured = client.post(f"/api/v1/events/admin/{eid}/unfeature", headers=admin)
    assert unfeatured.json()["featured"] is False

    cat = client.post(
        "/api/v1/events/admin/categories",
        headers=admin,
        json={"name": "Afrobeats", "slug": "afrobeats-test"},
    )
    assert cat.status_code == 201, cat.text
    cid = cat.json()["id"]
    deact = client.post(f"/api/v1/events/admin/categories/{cid}/deactivate", headers=admin)
    assert deact.json()["is_active"] is False
    rest = client.post(f"/api/v1/events/admin/categories/{cid}/restore", headers=admin)
    assert rest.json()["is_active"] is True


def test_table_reservation_cancel(client: TestClient):
    host_h = _auth(client, "table-host@example.com", "Table Host")
    _onboard(client, host_h, "Table Host Co")
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    event = client.post(
        "/api/v1/events",
        headers=host_h,
        json={
            "title": "Table Night",
            "description": "Table reservation cancel coverage event.",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "venue_name": "Hall",
            "city": "Lagos",
            "state": "Lagos",
            "venue": {
                "name": "Hall",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
        },
    ).json()
    table = client.post(
        f"/api/v1/tickets/events/{event['id']}/tables",
        headers=host_h,
        json={"table_label": "VIP-1", "capacity": 4},
    )
    assert table.status_code == 200 or table.status_code == 201, table.text
    rid = table.json()["id"]
    cancelled = client.post(f"/api/v1/tickets/tables/{rid}/cancel", headers=host_h)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
