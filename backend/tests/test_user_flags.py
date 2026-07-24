"""Admin user flags MVP — catalog types, severity, audit."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.users.flag_constants import FLAG_TYPES
from app.users.models import UserAdminFlag


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


def test_user_flags_mvp_create_resolve_dismiss_audited(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "flags-target@example.com", "Flags Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "flags-admin@example.com"
    _auth(client, admin_email, "Flags Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    bad = client.post(
        f"/api/v1/users/admin/{user_id}/flags",
        headers=admin,
        json={"flag_type": "not_a_real_flag", "reason": "Should fail"},
    )
    assert bad.status_code == 400

    bad_sev = client.post(
        f"/api/v1/users/admin/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "spam",
            "severity": "ultra",
            "reason": "Should fail severity",
        },
    )
    assert bad_sev.status_code == 400

    created = client.post(
        f"/api/v1/users/admin/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "chargeback_risk",
            "severity": "critical",
            "reason": "Disputed payment pattern",
            "internal_note": "Ops review queue",
        },
    )
    assert created.status_code == 200, created.text
    flag = created.json()
    assert flag["flag_type"] == "chargeback_risk"
    assert flag["severity"] == "critical"
    assert flag["status"] == "active"
    assert flag["reason"] == "Disputed payment pattern"
    assert flag["internal_note"] == "Ops review queue"
    assert flag["created_by_admin_id"]
    assert flag["resolved_by_admin_id"] is None
    assert flag["resolved_at"] is None
    flag_id = flag["id"]

    row = db_session.get(UserAdminFlag, UUID(flag_id))
    assert row is not None
    assert row.flag_type == "chargeback_risk"

    audits = list(
        db_session.scalars(
            select(AuditLog)
            .where(
                AuditLog.action == "admin_user_flag_created",
                AuditLog.resource_id == user_id,
            )
            .order_by(AuditLog.created_at.desc())
        ).all()
    )
    assert audits
    assert audits[0].details["after_json"]["flag_type"] == "chargeback_risk"
    assert audits[0].details["after_json"]["severity"] == "critical"

    listed = client.get(
        f"/api/v1/users/admin/{user_id}/flags",
        headers=admin,
    )
    assert listed.status_code == 200
    assert any(item["id"] == flag_id for item in listed.json())

    detail = client.get(f"/api/v1/users/admin/{user_id}", headers=admin)
    assert detail.status_code == 200
    assert detail.json()["risk_level"] == "high"
    assert "flag:chargeback_risk" in detail.json()["moderation"]["flags"]

    resolved = client.post(
        f"/api/v1/users/admin/{user_id}/flags/{flag_id}/resolve",
        headers=admin,
        json={"resolution_note": "Bank confirmed ok"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_by_admin_id"]
    assert resolved.json()["resolved_at"]

    resolve_audits = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.action == "admin_user_flag_updated")
        ).all()
    )
    assert resolve_audits

    second = client.post(
        f"/api/v1/users/admin/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "trusted_user",
            "severity": "low",
            "reason": "Long-standing good history",
        },
    )
    assert second.status_code == 200
    second_id = second.json()["id"]

    dismissed = client.post(
        f"/api/v1/users/admin/{user_id}/flags/{second_id}/dismiss",
        headers=admin,
        json={},
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"

    dismiss_audits = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.action == "admin_user_flag_updated")
        ).all()
    )
    assert dismiss_audits

    # Catalog completeness guard
    assert len(FLAG_TYPES) == 15
