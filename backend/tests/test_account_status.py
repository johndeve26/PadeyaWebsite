"""Account status / restrictions MVP — transitions, reason, audit."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.users.account_status_constants import ACCOUNT_STATUSES
from app.users.models import User


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


def test_account_status_mvp_transitions(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "status-target@example.com", "Status Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "status-admin@example.com"
    _auth(client, admin_email, "Status Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    # Reason required
    no_reason = client.post(
        f"/api/v1/users/admin/{user_id}/account-status",
        headers=admin,
        json={"status": "under_review", "reason": "ab"},
    )
    assert no_reason.status_code in {400, 422}

    # Banned is writable (global); deleted remains soft EOL / not casual
    banned = client.post(
        f"/api/v1/users/admin/{user_id}/account-status",
        headers=admin,
        json={"status": "banned", "reason": "Permanent ban for abuse"},
    )
    assert banned.status_code == 200, banned.text
    assert banned.json()["account_status"] == "banned"

    # Restore then continue under_review flow
    restore_ban = client.post(
        f"/api/v1/users/admin/{user_id}/account-status",
        headers=admin,
        json={"status": "active", "reason": "Reset for under_review test"},
    )
    assert restore_ban.status_code == 200

    review = client.post(
        f"/api/v1/users/admin/{user_id}/account-status",
        headers=admin,
        json={
            "status": "under_review",
            "reason": "Pending ID verification",
            "restrictions": ["cannot_join_ambassador_campaigns"],
        },
    )
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["account_status"] == "under_review"
    assert body["under_review"] is True
    assert body["is_active"] is True
    assert "cannot_join_ambassador_campaigns" in body["account_restrictions"]
    assert body["ambassadors_blocked"] is True

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_status_changed",
                AuditLog.resource_id == user_id,
            )
        ).all()
    )
    assert audits
    assert audits[-1].details["before_json"]["account_status"] == "active"
    assert audits[-1].details["after_json"]["account_status"] == "under_review"
    assert audits[-1].details["reason"]

    suspend = client.post(
        f"/api/v1/users/admin/{user_id}/suspend",
        headers=admin,
        json={"reason": "Confirmed abuse pattern"},
    )
    assert suspend.status_code == 200, suspend.text
    assert suspend.json()["account_status"] == "suspended"
    assert suspend.json()["is_active"] is False

    # Suspended cannot go to under_review
    bad = client.post(
        f"/api/v1/users/admin/{user_id}/account-status",
        headers=admin,
        json={"status": "under_review", "reason": "Should fail"},
    )
    assert bad.status_code == 400

    restore = client.post(
        f"/api/v1/users/admin/{user_id}/unsuspend",
        headers=admin,
        json={"reason": "Appeal accepted"},
    )
    assert restore.status_code == 200
    assert restore.json()["account_status"] == "active"
    assert restore.json()["is_active"] is True

    detail = client.get(f"/api/v1/users/admin/{user_id}", headers=admin)
    assert detail.status_code == 200
    assert detail.json()["account_status"] == "active"
    assert "cannot_join_ambassador_campaigns" in detail.json()["account_restrictions"]

    row = db_session.get(User, UUID(user_id))
    assert row is not None
    assert row.account_status == "active"

    assert len(ACCOUNT_STATUSES) == 6
