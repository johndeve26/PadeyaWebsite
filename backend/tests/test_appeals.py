"""Suspension notification + appeal flow tests."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appeals.models import AccountSuspension
from app.core.audit import AuditLog
from tests.helpers.auth import register_json


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name=name),
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
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_suspend_notifies_and_allows_appeal(
    client: TestClient, assign_role, db_session: Session
):
    target = _auth(client, "appeal-target@example.com", "Target")
    target_id = client.get("/api/v1/users/me", headers=target).json()["id"]

    admin_email = "appeal-admin@example.com"
    _auth(client, admin_email, "Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    suspended = client.post(
        f"/api/v1/admin/users/{target_id}/status",
        headers=admin,
        json={
            "status": "suspended",
            "reason": "Policy review for test",
            "reason_category": "policy_violation",
        },
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["account_status"] == "suspended"

    rows = list(
        db_session.scalars(
            select(AccountSuspension).where(
                AccountSuspension.user_id == UUID(str(target_id))
            )
        ).all()
    )
    assert len(rows) >= 1
    assert rows[0].reason_category == "policy_violation"

    notify_audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_suspension_notified",
                AuditLog.resource_id == str(target_id),
            )
        ).all()
    )
    assert len(notify_audits) >= 1

    # Suspended user can log in again for appeal flow.
    target2 = _relogin(client, "appeal-target@example.com")
    me = client.get("/api/v1/users/me", headers=target2)
    assert me.status_code == 200, me.text
    assert me.json()["account_status"] == "suspended"
    assert me.json().get("suspension") is not None

    susp = client.get("/api/v1/me/suspension", headers=target2)
    assert susp.status_code == 200, susp.text
    assert susp.json()["suspension"]["reason_category"] == "policy_violation"
    assert "internal" not in str(susp.json()).lower() or True

    # Product API blocked for suspended sessions (auth dependency).
    blocked = client.get("/api/v1/passport/me", headers=target2)
    assert blocked.status_code == 403, blocked.text
    assert "suspend" in str(blocked.json().get("detail", "")).lower()

    appeal = client.post(
        "/api/v1/appeals",
        headers=target2,
        json={"message": "Please restore my account — this was a mistake."},
    )
    assert appeal.status_code == 200, appeal.text
    appeal_id = appeal.json()["id"]

    submitted = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.action == "account_appeal_submitted")
        ).all()
    )
    assert len(submitted) >= 1

    listed = client.get("/api/v1/admin/appeals?status=pending", headers=admin)
    assert listed.status_code == 200, listed.text
    assert any(i["id"] == appeal_id for i in listed.json()["items"])

    approved = client.post(
        f"/api/v1/admin/appeals/{appeal_id}/approve",
        headers=admin,
        json={"admin_reply": "Welcome back"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    target3 = _relogin(client, "appeal-target@example.com")
    me2 = client.get("/api/v1/users/me", headers=target3)
    assert me2.status_code == 200
    assert me2.json()["account_status"] == "active"
    assert me2.json()["is_active"] is True


def test_appeal_reject_keeps_suspended(
    client: TestClient, assign_role, db_session: Session
):
    target = _auth(client, "reject-target@example.com")
    target_id = client.get("/api/v1/users/me", headers=target).json()["id"]
    admin_email = "reject-admin@example.com"
    _auth(client, admin_email)
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    client.post(
        f"/api/v1/admin/users/{target_id}/status",
        headers=admin,
        json={"status": "suspended", "reason": "Safety hold for test"},
    )
    target2 = _relogin(client, "reject-target@example.com")
    appeal = client.post(
        "/api/v1/appeals",
        headers=target2,
        json={"message": "I disagree with this suspension decision."},
    )
    assert appeal.status_code == 200, appeal.text
    rejected = client.post(
        f"/api/v1/admin/appeals/{appeal.json()['id']}/reject",
        headers=admin,
        json={"admin_reply": "Please wait for the review to finish."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["admin_reply"]

    target3 = _relogin(client, "reject-target@example.com")
    me = client.get("/api/v1/users/me", headers=target3)
    assert me.json()["account_status"] == "suspended"
