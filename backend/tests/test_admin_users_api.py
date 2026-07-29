"""Canonical /api/v1/admin/users* endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog


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


def _relogin(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_users_canonical_endpoints(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "canon-target@example.com", "Canon Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "canon-admin@example.com"
    _auth(client, admin_email, "Canon Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    listed = client.get("/api/v1/admin/users", headers=admin)
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == user_id for row in listed.json()["items"])

    detail = client.get(f"/api/v1/admin/users/{user_id}", headers=admin)
    assert detail.status_code == 200
    assert detail.json()["id"] == user_id

    activity = client.get(f"/api/v1/admin/users/{user_id}/activity", headers=admin)
    assert activity.status_code == 200
    assert "orders_count" in activity.json()

    audit = client.get(f"/api/v1/admin/users/{user_id}/audit", headers=admin)
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)

    note = client.post(
        f"/api/v1/admin/users/{user_id}/notes",
        headers=admin,
        json={"note_type": "support", "body": "Canonical notes path works"},
    )
    assert note.status_code == 200, note.text

    notes = client.get(f"/api/v1/admin/users/{user_id}/notes", headers=admin)
    assert notes.status_code == 200
    assert any(n["id"] == note.json()["id"] for n in notes.json())

    flag = client.post(
        f"/api/v1/admin/users/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "spam",
            "severity": "medium",
            "reason": "Promo spam pattern",
        },
    )
    assert flag.status_code == 200, flag.text
    flag_id = flag.json()["id"]

    patched = client.patch(
        f"/api/v1/admin/users/{user_id}/flags/{flag_id}",
        headers=admin,
        json={"status": "resolved", "reason": "Cleared after review"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "resolved"

    status = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin,
        json={"status": "under_review", "reason": "Ops hold for QA"},
    )
    assert status.status_code == 200
    assert status.json()["account_status"] == "under_review"

    # Sensitive actions require reason
    no_reason = client.post(
        f"/api/v1/admin/users/{user_id}/force-logout",
        headers=admin,
        json={},
    )
    assert no_reason.status_code in {400, 422}

    logout = client.post(
        f"/api/v1/admin/users/{user_id}/force-logout",
        headers=admin,
        json={"reason": "Force logout for support"},
    )
    assert logout.status_code == 200
    assert "revoked_count" in logout.json()

    reset = client.post(
        f"/api/v1/admin/users/{user_id}/force-password-reset",
        headers=admin,
        json={"reason": "User requested reset via support"},
    )
    assert reset.status_code == 200
    assert reset.json()["email_sent"] is True
    assert "token" not in reset.text.lower() or "token_hash" not in reset.text.lower()

    actions = {
        row.action
        for row in db_session.scalars(
            select(AuditLog).where(AuditLog.resource_id == user_id)
        ).all()
    }
    assert "admin_user_note_created" in actions
    assert "admin_user_flag_created" in actions
    assert "admin_user_flag_updated" in actions
    assert "admin_user_status_changed" in actions
    assert "admin_user_force_logout" in actions
    assert "admin_user_force_password_reset" in actions
