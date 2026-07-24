"""Safe admin user actions — notes, flags, sessions, review, password reset."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.auth.models import PasswordResetToken
from app.core.security import generate_password_reset_code, hash_token
from app.users.models import UserAdminNote


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


def test_admin_safe_actions_notes_flags_sessions_review(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "actions-target@example.com", "Target User")
    me = client.get("/api/v1/users/me", headers=target_h).json()
    user_id = me["id"]

    admin_email = "actions-admin@example.com"
    _auth(client, admin_email, "Actions Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    note = client.post(
        f"/api/v1/users/admin/{user_id}/notes",
        headers=admin,
        json={"note_type": "support", "body": "Called support — waiting on ID check"},
    )
    assert note.status_code == 200, note.text
    assert note.json()["note_type"] == "support"
    assert note.json()["created_by_admin_id"]
    assert note.json()["updated_at"] is None
    assert "password" not in note.text.lower()
    assert db_session.scalar(select(UserAdminNote).limit(1)) is not None

    flag = client.post(
        f"/api/v1/users/admin/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "refund_abuse",
            "severity": "high",
            "reason": "Multiple refund attempts",
            "internal_note": "Check last three orders",
        },
    )
    assert flag.status_code == 200, flag.text
    body = flag.json()
    flag_id = body["id"]
    assert body["status"] == "active"
    assert body["flag_type"] == "refund_abuse"
    assert body["severity"] == "high"
    assert body["internal_note"] == "Check last three orders"
    assert body["created_by_admin_id"]
    assert "created_by_user_id" not in body
    assert "code" not in body

    resolved = client.post(
        f"/api/v1/users/admin/{user_id}/flags/{flag_id}/resolve",
        headers=admin,
        json={"resolution_note": "Verified legitimate"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    review = client.post(
        f"/api/v1/users/admin/{user_id}/under-review",
        headers=admin,
        json={"reason": "Pending identity verification"},
    )
    assert review.status_code == 200
    assert review.json()["under_review"] is True

    detail = client.get(f"/api/v1/users/admin/{user_id}", headers=admin)
    assert detail.status_code == 200
    body = detail.json()
    assert body["under_review"] is True
    assert len(body["moderation"]["internal_notes"]) >= 1
    assert any(f["id"] == flag_id for f in body["moderation"]["admin_flags"])
    assert "password_hash" not in body
    assert "access_token" not in str(body)

    # Ensure a refresh session exists, then force logout
    login2 = client.post(
        "/api/v1/auth/login",
        json={"email": "actions-target@example.com", "password": "securepass1"},
    )
    assert login2.status_code == 200
    refresh = login2.json()["refresh_token"]

    revoked = client.post(
        f"/api/v1/users/admin/{user_id}/sessions/revoke-all",
        headers=admin,
        json={"reason": "Force logout after review"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked_count"] >= 1
    assert "token" not in revoked.json()

    refresh_fail = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh}
    )
    assert refresh_fail.status_code in {401, 403}

    clear = client.post(
        f"/api/v1/users/admin/{user_id}/clear-under-review",
        headers=admin,
        json={"reason": "Cleared after verification"},
    )
    assert clear.status_code == 200
    assert clear.json()["under_review"] is False
    assert clear.json()["account_status"] == "active"


def test_admin_force_password_reset_and_confirm(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "reset-target@example.com", "Reset Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "reset-admin@example.com"
    _auth(client, admin_email, "Reset Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    forced = client.post(
        f"/api/v1/users/admin/{user_id}/password-reset",
        headers=admin,
        json={"reason": "User requested reset via support"},
    )
    assert forced.status_code == 200, forced.text
    assert forced.json()["email_sent"] is True
    assert "token" not in forced.json()

    row = db_session.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.user_id == UUID(user_id))
        .order_by(PasswordResetToken.created_at.desc())
    )
    assert row is not None
    raw = generate_password_reset_code()
    row.token_hash = hash_token(raw)
    row.used_at = None
    from datetime import UTC, datetime, timedelta

    row.expires_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.commit()

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "reset-target@example.com",
            "code": raw,
            "new_password": "newsecurepass9",
        },
    )
    assert confirm.status_code == 200, confirm.text

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-target@example.com", "password": "securepass1"},
    )
    assert old_login.status_code in {401, 403}

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-target@example.com", "password": "newsecurepass9"},
    )
    assert new_login.status_code == 200


def test_admin_suspend_revokes_sessions(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "suspend-target@example.com", "Suspend Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]
    refresh = client.post(
        "/api/v1/auth/login",
        json={"email": "suspend-target@example.com", "password": "securepass1"},
    ).json()["refresh_token"]

    admin_email = "suspend-admin@example.com"
    _auth(client, admin_email, "Suspend Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    suspended = client.post(
        f"/api/v1/users/admin/{user_id}/suspend",
        headers=admin,
        json={"reason": "Abuse confirmed"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["is_active"] is False

    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code
        in {401, 403}
    )

    restored = client.post(
        f"/api/v1/users/admin/{user_id}/unsuspend",
        headers=admin,
        json={"reason": "Appeal accepted"},
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True
