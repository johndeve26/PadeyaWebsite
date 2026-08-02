"""Admin host workspace soft lifecycle — suspend / restore / force-delete."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.hosts.models import Host
from tests.helpers.auth import register_json


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, password="securepass1", full_name=name),
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
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Lifecycle test host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_host_suspend_restore_and_force_delete(
    client: TestClient, assign_role, db_session: Session
):
    host_h = _auth(client, "host-life@example.com", "Host Life")
    host = _onboard(client, host_h, "Life Events")
    host_id = host["id"]

    admin_email = "host-life-admin@example.com"
    _auth(client, admin_email, "Life Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    # Active host cannot be force-deleted
    denied = client.post(
        f"/api/v1/hosts/admin/{host_id}/force-delete",
        headers=admin,
        json={"reason": "Cleanup test workspace"},
    )
    assert denied.status_code == 400, denied.text
    assert "suspended" in denied.json()["detail"].lower()

    # Suspend requires reason
    short = client.post(
        f"/api/v1/hosts/admin/{host_id}/suspend",
        headers=admin,
        json={"reason": "ab"},
    )
    assert short.status_code == 400

    suspend = client.post(
        f"/api/v1/hosts/admin/{host_id}/suspend",
        headers=admin,
        json={"reason": "Policy violation review"},
    )
    assert suspend.status_code == 200, suspend.text
    assert suspend.json()["status"] == "suspended"

    row = db_session.get(Host, UUID(host_id))
    assert row is not None
    assert row.status == "suspended"

    # Owner can still read workspace status, but manage mutations are blocked
    status_me = client.get("/api/v1/hosts/me", headers=host_h)
    assert status_me.status_code == 200
    assert status_me.json()["status"] == "suspended"

    blocked = client.patch(
        "/api/v1/hosts/me",
        headers=host_h,
        json={"bio": "Should not update while suspended"},
    )
    assert blocked.status_code == 403, blocked.text
    assert "suspended" in blocked.json()["detail"].lower()

    workspaces = client.get("/api/v1/me/team-workspaces", headers=host_h)
    assert workspaces.status_code == 200
    assert all(w["host_id"] != host_id for w in workspaces.json())

    # Owner user account remains usable
    me = client.get("/api/v1/users/me", headers=host_h)
    assert me.status_code == 200
    assert me.json()["email"] == "host-life@example.com"

    restore = client.post(
        f"/api/v1/hosts/admin/{host_id}/restore",
        headers=admin,
        json={"reason": "Cleared after review"},
    )
    assert restore.status_code == 200, restore.text
    assert restore.json()["status"] == "active"

    ok_me = client.get("/api/v1/hosts/me", headers=host_h)
    assert ok_me.status_code == 200
    assert ok_me.json()["id"] == host_id

    # Suspend again then force-delete
    assert (
        client.post(
            f"/api/v1/hosts/admin/{host_id}/suspend",
            headers=admin,
            json={"reason": "Prep for soft EOL"},
        ).status_code
        == 200
    )

    force = client.post(
        f"/api/v1/hosts/admin/{host_id}/force-delete",
        headers=admin,
        json={"reason": "Cleanup test workspace"},
    )
    assert force.status_code == 200, force.text
    assert force.json()["status"] == "deleted"

    db_session.expire_all()
    row = db_session.get(Host, UUID(host_id))
    assert row is not None
    assert row.status == "deleted"

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.resource_type == "host",
                AuditLog.resource_id == str(host_id),
            )
        ).all()
    )
    actions = {a.action for a in audits}
    assert "hosts.suspend" in actions
    assert "hosts.restore" in actions
    assert "hosts.force_delete" in actions
    force_audits = [a for a in audits if a.action == "hosts.force_delete"]
    assert force_audits[-1].details.get("force_delete") is True

    again = client.post(
        f"/api/v1/hosts/admin/{host_id}/force-delete",
        headers=admin,
        json={"reason": "Already gone"},
    )
    assert again.status_code == 400

    # Deleted cannot be restored
    no_restore = client.post(
        f"/api/v1/hosts/admin/{host_id}/restore",
        headers=admin,
        json={"reason": "Should fail"},
    )
    assert no_restore.status_code == 400


def test_host_lifecycle_permissions(client: TestClient, assign_role):
    host_h = _auth(client, "host-perm@example.com", "Host Perm")
    host = _onboard(client, host_h, "Perm Events")
    host_id = host["id"]

    # Support has verify, not suspend
    support_email = "host-perm-support@example.com"
    _auth(client, support_email, "Support")
    assign_role(support_email, "support_agent")
    support = _relogin(client, support_email)

    denied_suspend = client.post(
        f"/api/v1/hosts/admin/{host_id}/suspend",
        headers=support,
        json={"reason": "Should be forbidden"},
    )
    assert denied_suspend.status_code == 403

    # Admin has suspend, not force_delete
    admin_email = "host-perm-admin@example.com"
    _auth(client, admin_email, "Admin")
    assign_role(admin_email, "admin")
    admin = _relogin(client, admin_email)

    suspend = client.post(
        f"/api/v1/hosts/admin/{host_id}/suspend",
        headers=admin,
        json={"reason": "Admin can suspend workspaces"},
    )
    assert suspend.status_code == 200, suspend.text

    denied_force = client.post(
        f"/api/v1/hosts/admin/{host_id}/force-delete",
        headers=admin,
        json={"reason": "Should be forbidden"},
    )
    assert denied_force.status_code == 403

    super_email = "host-perm-super@example.com"
    _auth(client, super_email, "Super")
    assign_role(super_email, "super_admin")
    super_h = _relogin(client, super_email)

    force = client.post(
        f"/api/v1/hosts/admin/{host_id}/force-delete",
        headers=super_h,
        json={"reason": "Super can force-delete"},
    )
    assert force.status_code == 200, force.text
    assert force.json()["status"] == "deleted"
