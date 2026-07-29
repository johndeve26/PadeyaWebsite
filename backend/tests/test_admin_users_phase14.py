"""Phase 14 — Admin User Management acceptance matrix (canonical API)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.users.admin_response_safety import assert_admin_user_payload_safe
from app.users.admin_user_audit import scrub_admin_user_audit_metadata


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


def test_admin_with_permission_can_list_users(client: TestClient, assign_role):
    _auth(client, "phase14-listed@example.com", "Listed")
    admin_email = "phase14-lister@example.com"
    _auth(client, admin_email, "Lister")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    resp = client.get("/api/v1/admin/users", headers=admin)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert isinstance(body["items"], list)
    assert_admin_user_payload_safe(body)


def test_admin_without_permission_gets_403(client: TestClient, assign_role):
    email = "phase14-finance@example.com"
    _auth(client, email, "Finance")
    assign_role(email, "finance_admin")
    token = _relogin(client, email)

    resp = client.get("/api/v1/admin/users", headers=token)
    assert resp.status_code == 403


def test_normal_user_gets_403_on_admin_users(client: TestClient):
    buyer = _auth(client, "phase14-buyer@example.com", "Buyer")
    resp = client.get("/api/v1/admin/users", headers=buyer)
    assert resp.status_code == 403


def test_user_detail_never_returns_password_hash_or_token_fields(
    client: TestClient, assign_role
):
    target = _auth(client, "phase14-detail@example.com", "Detail Target")
    user_id = client.get("/api/v1/users/me", headers=target).json()["id"]

    admin_email = "phase14-detail-admin@example.com"
    _auth(client, admin_email, "Detail Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    detail = client.get(f"/api/v1/admin/users/{user_id}", headers=admin)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert_admin_user_payload_safe(body)
    blob = str(body).lower()
    for forbidden in (
        "password_hash",
        "hashed_password",
        "refresh_token",
        "access_token",
        "reset_token",
        "qr_payload",
        "payment_payload",
    ):
        assert forbidden not in blob
    assert "email_masked" in body
    assert "•••@" in body["email_masked"]


def test_admin_detail_returns_unmasked_email(
    client: TestClient, assign_role, db_session: Session
):
    """Admin directory detail always returns the real email (list parity)."""
    target = _auth(client, "phase14-contact@example.com", "Contact Target")
    user_id = client.get("/api/v1/users/me", headers=target).json()["id"]
    real_email = "phase14-contact@example.com"

    # Support has view but not view_private_contact by default — email still shown.
    support_email = "phase14-support-contact@example.com"
    _auth(client, support_email, "Support Contact")
    assign_role(support_email, "support_agent")
    support = _relogin(client, support_email)

    opened = client.get(f"/api/v1/admin/users/{user_id}", headers=support)
    assert opened.status_code == 200, opened.text
    body = opened.json()
    assert body["email"] == real_email
    assert "email_masked" in body
    assert "•••@" in body["email_masked"]

    # Private-contact audit fires because email is exposed on detail.
    rows = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_private_contact_viewed",
                AuditLog.resource_id == str(user_id),
            )
        ).all()
    )
    assert len(rows) >= 1


def test_add_flag_requires_reason(client: TestClient, assign_role):
    target = _auth(client, "phase14-flag-reason@example.com", "Flag Target")
    user_id = client.get("/api/v1/users/me", headers=target).json()["id"]

    admin_email = "phase14-flag-admin@example.com"
    _auth(client, admin_email, "Flag Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    missing = client.post(
        f"/api/v1/admin/users/{user_id}/flags",
        headers=admin,
        json={"flag_type": "manual_watchlist", "severity": "low"},
    )
    assert missing.status_code in {400, 422}

    short = client.post(
        f"/api/v1/admin/users/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "manual_watchlist",
            "severity": "low",
            "reason": "ab",
        },
    )
    assert short.status_code in {400, 422}


def test_add_note_works_and_writes_audit(
    client: TestClient, assign_role, db_session: Session
):
    target = _auth(client, "phase14-note@example.com", "Note Target")
    user_id = client.get("/api/v1/users/me", headers=target).json()["id"]

    admin_email = "phase14-note-admin@example.com"
    _auth(client, admin_email, "Note Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    note = client.post(
        f"/api/v1/admin/users/{user_id}/notes",
        headers=admin,
        json={"note_type": "support", "body": "Phase 14 acceptance note"},
    )
    assert note.status_code == 200, note.text
    assert note.json()["body"] == "Phase 14 acceptance note"
    assert_admin_user_payload_safe(note.json())

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_note_created",
                AuditLog.resource_id == user_id,
            )
        ).all()
    )
    assert audits
    assert "Phase 14 acceptance note" not in str(audits[0].details)
    assert "body" not in (audits[0].details.get("after_json") or {})


def test_add_flag_writes_audit_log(
    client: TestClient, assign_role, db_session: Session
):
    target = _auth(client, "phase14-flag-audit@example.com", "Flag Audit")
    user_id = client.get("/api/v1/users/me", headers=target).json()["id"]

    admin_email = "phase14-flag-audit-admin@example.com"
    _auth(client, admin_email, "Flag Audit Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    created = client.post(
        f"/api/v1/admin/users/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "manual_watchlist",
            "severity": "medium",
            "reason": "Phase 14 flag audit",
            "internal_note": "secret context must not land in audit",
        },
    )
    assert created.status_code == 200, created.text

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_flag_created",
                AuditLog.resource_id == user_id,
            )
        ).all()
    )
    assert audits
    assert audits[0].details.get("reason") == "Phase 14 flag audit"
    assert "secret context" not in str(audits[0].details)


def test_suspend_requires_permission_and_reason(
    client: TestClient, assign_role, db_session: Session
):
    target = _auth(client, "phase14-suspend@example.com", "Suspend Target")
    user_id = client.get("/api/v1/users/me", headers=target).json()["id"]

    support_email = "phase14-suspend-support@example.com"
    _auth(client, support_email, "Support")
    assign_role(support_email, "support_agent")
    support = _relogin(client, support_email)

    denied = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=support,
        json={"status": "suspended", "reason": "No suspend permission"},
    )
    assert denied.status_code == 403

    admin_email = "phase14-suspend-admin@example.com"
    _auth(client, admin_email, "Suspend Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    no_reason = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin,
        json={"status": "suspended", "reason": "ab"},
    )
    assert no_reason.status_code in {400, 422}

    suspended = client.post(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin,
        json={"status": "suspended", "reason": "Confirmed abuse for phase 14"},
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["account_status"] == "suspended"

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_status_changed",
                AuditLog.resource_id == user_id,
            )
        ).all()
    )
    assert audits
    assert audits[-1].details.get("reason") == "Confirmed abuse for phase 14"
    assert audits[-1].details["after_json"]["account_status"] == "suspended"


def test_sensitive_metadata_is_scrubbed_from_admin_user_audit():
    cleaned = scrub_admin_user_audit_metadata(
        {
            "admin_user_id": "a1",
            "target_user_id": "t1",
            "reason": "ops",
            "password": "secret",
            "access_token": "tok",
            "after_json": {
                "body": "drop me",
                "internal_note": "drop",
                "note_id": "n1",
                "reset_token": "bad",
            },
        }
    )
    assert cleaned is not None
    assert cleaned["reason"] == "ops"
    assert "password" not in cleaned
    assert "access_token" not in cleaned
    assert cleaned["after_json"]["note_id"] == "n1"
    assert "body" not in cleaned["after_json"]
    assert "internal_note" not in cleaned["after_json"]
    assert "reset_token" not in cleaned["after_json"]
