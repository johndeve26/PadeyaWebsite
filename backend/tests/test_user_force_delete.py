"""Admin force-delete (soft EOL) — requires prior suspension."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.users.models import User


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass1",
            "full_name": name,
            "gender": "prefer_not_to_say",
        },
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


def test_force_delete_requires_suspended(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "fd-target@example.com", "FD Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "fd-admin@example.com"
    _auth(client, admin_email, "FD Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    # Active user cannot be force-deleted
    denied = client.post(
        f"/api/v1/admin/users/{user_id}/force-delete",
        headers=admin,
        json={"reason": "Cleanup test account"},
    )
    assert denied.status_code == 400, denied.text
    assert "suspended" in denied.json()["detail"].lower()

    # Status endpoint still rejects deleted
    via_status = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin,
        json={"status": "deleted", "reason": "Should not work"},
    )
    assert via_status.status_code == 400

    suspend = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin,
        json={"status": "suspended", "reason": "Prep for force delete"},
    )
    assert suspend.status_code == 200
    assert suspend.json()["account_status"] == "suspended"

    # Reason required
    short = client.post(
        f"/api/v1/admin/users/{user_id}/force-delete",
        headers=admin,
        json={"reason": "ab"},
    )
    assert short.status_code in {400, 422}

    ok = client.post(
        f"/api/v1/admin/users/{user_id}/force-delete",
        headers=admin,
        json={"reason": "Cleanup test account"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["account_status"] == "deleted"
    assert ok.json()["is_active"] is False

    row = db_session.get(User, UUID(user_id))
    assert row is not None
    assert row.account_status == "deleted"
    assert row.is_active is False

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_status_changed",
                AuditLog.resource_id == str(user_id),
            )
        ).all()
    )
    force_audits = [
        a
        for a in audits
        if (a.details or {}).get("after_json", {}).get("account_status") == "deleted"
    ]
    assert force_audits
    assert force_audits[-1].details.get("force_delete") is True
    assert force_audits[-1].details.get("reason")

    # Hidden from default list; visible with status=deleted
    listed = client.get("/api/v1/admin/users", headers=admin)
    assert listed.status_code == 200
    assert all(row["id"] != user_id for row in listed.json()["items"])

    deleted_list = client.get(
        "/api/v1/admin/users",
        headers=admin,
        params={"status": "deleted"},
    )
    assert deleted_list.status_code == 200
    assert any(row["id"] == user_id for row in deleted_list.json()["items"])

    # Idempotent reject
    again = client.post(
        f"/api/v1/admin/users/{user_id}/force-delete",
        headers=admin,
        json={"reason": "Already gone"},
    )
    assert again.status_code == 400


def test_force_delete_permission_and_self(client: TestClient, assign_role):
    target_h = _auth(client, "fd-perm-target@example.com", "Perm Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "fd-perm-admin@example.com"
    _auth(client, admin_email, "Perm Admin")
    assign_role(admin_email, "admin")  # has suspend, not force_delete
    admin = _relogin(client, admin_email)

    suspend = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin,
        json={"status": "suspended", "reason": "Prep for denied force delete"},
    )
    assert suspend.status_code == 200

    denied = client.post(
        f"/api/v1/admin/users/{user_id}/force-delete",
        headers=admin,
        json={"reason": "Should be forbidden"},
    )
    assert denied.status_code == 403

    super_email = "fd-perm-super@example.com"
    _auth(client, super_email, "Super")
    assign_role(super_email, "super_admin")
    super_h = _relogin(client, super_email)
    me = client.get("/api/v1/users/me", headers=super_h).json()["id"]

    self_del = client.post(
        f"/api/v1/admin/users/{me}/force-delete",
        headers=super_h,
        json={"reason": "Cannot delete myself"},
    )
    assert self_del.status_code == 400
    assert "own" in self_del.json()["detail"].lower()
