"""Admin user management audit events (phase 11)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.users.admin_user_audit import (
    ADMIN_USER_FLAG_CREATED,
    ADMIN_USER_FLAG_UPDATED,
    ADMIN_USER_FORCE_LOGOUT,
    ADMIN_USER_FORCE_PASSWORD_RESET,
    ADMIN_USER_NOTE_CREATED,
    ADMIN_USER_PRIVATE_CONTACT_VIEWED,
    ADMIN_USER_STATUS_CHANGED,
    ADMIN_USER_VIEWED,
    scrub_admin_user_audit_metadata,
)


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


def test_scrub_admin_user_audit_metadata_drops_secrets():
    cleaned = scrub_admin_user_audit_metadata(
        {
            "admin_user_id": "a1",
            "target_user_id": "t1",
            "reason": "ops review",
            "password": "secret",
            "access_token": "tok",
            "after_json": {
                "note_id": "n1",
                "body": "should drop",
                "internal_note": "drop me",
                "body_length": 12,
                "reset_token": "bad",
            },
            "before_json": {"account_status": "active"},
        }
    )
    assert cleaned is not None
    assert cleaned["admin_user_id"] == "a1"
    assert cleaned["reason"] == "ops review"
    assert "password" not in cleaned
    assert "access_token" not in cleaned
    assert cleaned["after_json"]["note_id"] == "n1"
    assert cleaned["after_json"]["body_length"] == 12
    assert "body" not in cleaned["after_json"]
    assert "internal_note" not in cleaned["after_json"]
    assert "reset_token" not in cleaned["after_json"]
    assert cleaned["before_json"]["account_status"] == "active"


def test_admin_user_actions_write_canonical_audit_events(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "audit-target@example.com", "Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "audit-admin@example.com"
    _auth(client, admin_email, "Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    detail = client.get(f"/api/v1/admin/users/{user_id}", headers=admin)
    assert detail.status_code == 200

    note = client.post(
        f"/api/v1/admin/users/{user_id}/notes",
        headers=admin,
        json={"note_type": "support", "body": "Audited note body"},
    )
    assert note.status_code == 200

    flag = client.post(
        f"/api/v1/admin/users/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "manual_watchlist",
            "severity": "low",
            "reason": "Watch for QA",
            "internal_note": "secret context must not be audited",
        },
    )
    assert flag.status_code == 200
    flag_id = flag.json()["id"]

    patched = client.patch(
        f"/api/v1/admin/users/{user_id}/flags/{flag_id}",
        headers=admin,
        json={"status": "resolved", "reason": "Cleared after review"},
    )
    assert patched.status_code == 200

    status = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin,
        json={"status": "under_review", "reason": "Ops hold"},
    )
    assert status.status_code == 200

    logout = client.post(
        f"/api/v1/admin/users/{user_id}/force-logout",
        headers=admin,
        json={"reason": "Force logout for support"},
    )
    assert logout.status_code == 200

    reset = client.post(
        f"/api/v1/admin/users/{user_id}/force-password-reset",
        headers=admin,
        json={"reason": "User requested reset"},
    )
    assert reset.status_code == 200

    rows = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.resource_id == user_id)
        ).all()
    )
    actions = {row.action for row in rows}
    for expected in (
        ADMIN_USER_VIEWED,
        ADMIN_USER_PRIVATE_CONTACT_VIEWED,
        ADMIN_USER_NOTE_CREATED,
        ADMIN_USER_FLAG_CREATED,
        ADMIN_USER_FLAG_UPDATED,
        ADMIN_USER_STATUS_CHANGED,
        ADMIN_USER_FORCE_LOGOUT,
        ADMIN_USER_FORCE_PASSWORD_RESET,
    ):
        assert expected in actions, expected

    # Structured fields + scrubbing
    note_row = next(r for r in rows if r.action == ADMIN_USER_NOTE_CREATED)
    assert note_row.actor_user_id is not None
    assert note_row.details is not None
    assert note_row.details["admin_user_id"] == str(note_row.actor_user_id)
    assert note_row.details["target_user_id"] == user_id
    assert "body" not in (note_row.details.get("after_json") or {})
    assert "Audited note body" not in str(note_row.details)

    flag_row = next(r for r in rows if r.action == ADMIN_USER_FLAG_CREATED)
    assert "secret context" not in str(flag_row.details)
    assert flag_row.details.get("reason") == "Watch for QA"

    status_row = next(r for r in rows if r.action == ADMIN_USER_STATUS_CHANGED)
    assert status_row.details["before_json"]["account_status"] == "active"
    assert status_row.details["after_json"]["account_status"] == "under_review"
    assert status_row.details.get("reason") == "Ops hold"
