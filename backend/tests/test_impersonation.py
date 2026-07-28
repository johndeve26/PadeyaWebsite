"""Admin user impersonation tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.core.security import decode_access_token
from tests.helpers.auth import register_json


def _register(
    client: TestClient,
    *,
    email: str,
    password: str = "securepass1",
    full_name: str = "Test User",
):
    return client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, password=password, full_name=full_name),
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _start(
    client: TestClient,
    *,
    admin_token: str,
    user_id: str,
    reason: str = "support ticket",
    support_ticket_id: str | None = None,
    duration_minutes: int = 30,
):
    body: dict = {"reason": reason, "duration_minutes": duration_minutes}
    if support_ticket_id is not None:
        body["support_ticket_id"] = support_ticket_id
    return client.post(
        f"/api/v1/admin/users/{user_id}/impersonation/start",
        headers=_auth_header(admin_token),
        json=body,
    )


def _user_id(client: TestClient, access_token: str) -> str:
    return client.get(
        "/api/v1/auth/me",
        headers=_auth_header(access_token),
    ).json()["id"]


def test_impersonation_start_end_and_me(
    client: TestClient, assign_role, db_session: Session
):
    admin_tokens = _register(
        client, email="admin-imp@example.com", full_name="Admin Imp"
    ).json()
    target = _register(
        client, email="target-imp@example.com", full_name="Target Imp"
    ).json()
    assign_role("admin-imp@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    denied = _start(
        client,
        admin_token=target["access_token"],
        user_id=target_id,
        reason="support ticket",
    )
    assert denied.status_code == 403

    started = _start(
        client,
        admin_token=admin_tokens["access_token"],
        user_id=target_id,
        reason="QA ticket #42",
    )
    assert started.status_code == 200
    body = started.json()
    assert body["access_token"]
    assert body["impersonation_id"]
    assert body["target_user_id"] == target_id
    assert body["expires_at"]
    assert body["redirect_to"] == "/dashboard"
    assert "refresh_token" not in body
    assert body["scopes"] == ["view", "host_events", "credentials"]
    assert body["pack"] == "full"

    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == target_id
    assert payload["actual_user_id"] == target_id
    assert payload["is_impersonating"] is True
    assert payload["actor_admin_id"]
    assert payload["impersonation_id"] == body["impersonation_id"]
    assert payload["started_at"]
    assert payload["expires_at"]
    assert payload["reason"] == "QA ticket #42"
    assert payload["impersonation_scopes"] == [
        "view",
        "host_events",
        "credentials",
    ]
    assert payload["impersonation_pack"] == "full"
    assert "buyer" in payload["roles"]
    assert "admin.full_access" not in payload["permissions"]
    assert "admin.users.impersonate" not in payload["permissions"]

    me = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(body["access_token"]),
    )
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == "target-imp@example.com"
    assert me_body["impersonation"]["active"] is True
    assert me_body["impersonation"]["is_impersonating"] is True
    assert me_body["impersonation"]["actual_user_id"] == target_id
    assert me_body["impersonation"]["impersonator_email"] == "admin-imp@example.com"
    assert me_body["impersonation"]["scopes"] == [
        "view",
        "host_events",
        "credentials",
    ]
    assert me_body["impersonation"]["pack"] == "full"
    assert "admin.full_access" not in me_body["permissions"]

    status = client.get(
        "/api/v1/me/impersonation",
        headers=_auth_header(body["access_token"]),
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["is_impersonating"] is True
    assert status_body["target_user_id"] == target_id
    assert status_body["impersonation_id"] == body["impersonation_id"]
    assert status_body["scopes"] == ["view", "host_events", "credentials"]
    assert status_body["pack"] == "full"

    idle = client.get(
        "/api/v1/me/impersonation",
        headers=_auth_header(admin_tokens["access_token"]),
    )
    assert idle.status_code == 200
    assert idle.json()["is_impersonating"] is False

    # Admin APIs must not accept the impersonation token (target perms only).
    admin_denied = client.get(
        "/api/v1/admin/audit-logs",
        headers=_auth_header(body["access_token"]),
    )
    assert admin_denied.status_code == 403

    # Target's real session still works (not hijacked).
    still_target = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(target["access_token"]),
    )
    assert still_target.status_code == 200
    assert still_target.json()["impersonation"] is None

    ended = client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(body["access_token"]),
    )
    assert ended.status_code == 200
    end_body = ended.json()
    assert end_body["ended"] is True
    assert end_body["return_to"] == f"/admin/users/{target_id}"

    actions = {
        row.action
        for row in db_session.scalars(
            select(AuditLog).where(
                AuditLog.action.in_(
                    [
                        "admin_impersonation_started",
                        "admin_impersonation_ended",
                    ]
                )
            )
        )
    }
    assert "admin_impersonation_started" in actions
    assert "admin_impersonation_ended" in actions

    from uuid import UUID

    from app.admin.impersonation_models import (
        IMPERSONATION_STATUS_ENDED,
        AdminImpersonationAuditLog,
        AdminImpersonationSession,
    )

    session_row = db_session.get(AdminImpersonationSession, UUID(body["impersonation_id"]))
    assert session_row is not None
    assert session_row.status == IMPERSONATION_STATUS_ENDED
    assert session_row.ended_at is not None
    assert str(session_row.target_user_id) == target_id

    audit_actions = {
        row.action
        for row in db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id
                == UUID(body["impersonation_id"])
            )
        )
    }
    assert "admin_impersonation_started" in audit_actions
    assert "admin_impersonation_ended" in audit_actions
    assert "admin_impersonation_request_made" in audit_actions


def test_cannot_impersonate_super_admin(client: TestClient, assign_role):
    admin_a = _register(client, email="admin-a@example.com").json()
    admin_b = _register(client, email="admin-b@example.com").json()
    assign_role("admin-a@example.com", "super_admin")
    assign_role("admin-b@example.com", "super_admin")
    other_id = _user_id(client, admin_b["access_token"])

    response = _start(
        client,
        admin_token=admin_a["access_token"],
        user_id=other_id,
        reason="should fail",
    )
    assert response.status_code == 403


def test_cannot_impersonate_self(client: TestClient, assign_role):
    admin = _register(client, email="admin-self@example.com").json()
    assign_role("admin-self@example.com", "super_admin")
    admin_id = _user_id(client, admin["access_token"])

    response = _start(
        client,
        admin_token=admin["access_token"],
        user_id=admin_id,
        reason="self check",
    )
    assert response.status_code == 400


def test_impersonation_requires_reason(client: TestClient, assign_role):
    admin = _register(client, email="admin-reason@example.com").json()
    target = _register(client, email="target-reason@example.com").json()
    assign_role("admin-reason@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    response = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="ab",
    )
    assert response.status_code == 422


def test_end_without_impersonation(client: TestClient, assign_role):
    admin = _register(client, email="admin-stop@example.com").json()
    assign_role("admin-stop@example.com", "super_admin")
    response = client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(admin["access_token"]),
    )
    assert response.status_code == 400


def test_impersonation_audit_stamps_actor(
    client: TestClient, assign_role, db_session: Session
):
    admin = _register(client, email="admin-audit@example.com").json()
    target = _register(
        client, email="target-audit@example.com", full_name="Target Audit"
    ).json()
    assign_role("admin-audit@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    admin_id = _user_id(client, admin["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="audit stamp check",
    ).json()

    updated = client.patch(
        "/api/v1/users/me",
        headers=_auth_header(started["access_token"]),
        json={"full_name": "Impersonated Name"},
    )
    assert updated.status_code == 403
    assert (
        updated.json()["detail"]
        == "This action is disabled during admin impersonation."
    )

    row = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "users.profile_update")
    )
    assert row is None


def test_impersonation_duration_and_ticket(
    client: TestClient, assign_role, db_session: Session
):
    admin = _register(client, email="admin-dur@example.com").json()
    target = _register(client, email="target-dur@example.com").json()
    assign_role("admin-dur@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="Duration check",
        support_ticket_id="SUP-99",
        duration_minutes=15,
    )
    assert started.status_code == 200
    body = started.json()
    assert body["target_user_id"] == target_id
    assert body["redirect_to"] == "/dashboard"

    payload = decode_access_token(body["access_token"])
    assert payload["support_ticket_id"] == "SUP-99"

    row = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "admin_impersonation_started")
    )
    assert row is not None
    assert row.details is not None
    assert row.details.get("support_ticket_id") == "SUP-99"
    assert row.details.get("duration_minutes") == 15


def test_impersonation_rejects_invalid_duration(client: TestClient, assign_role):
    admin = _register(client, email="admin-baddur@example.com").json()
    target = _register(client, email="target-baddur@example.com").json()
    assign_role("admin-baddur@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    response = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="bad duration",
        duration_minutes=45,
    )
    assert response.status_code == 422


def test_finance_admin_cannot_impersonate_by_default(client: TestClient, assign_role):
    finance = _register(client, email="finance-deny@example.com").json()
    target = _register(client, email="target-finance-deny@example.com").json()
    assign_role("finance-deny@example.com", "finance_admin")
    target_id = _user_id(client, target["access_token"])

    response = _start(
        client,
        admin_token=finance["access_token"],
        user_id=target_id,
        reason="finance attempt",
    )
    assert response.status_code == 403


def test_support_agent_cannot_impersonate_without_grant(client: TestClient, assign_role):
    support = _register(client, email="support-deny@example.com").json()
    target = _register(client, email="target-support-deny@example.com").json()
    assign_role("support-deny@example.com", "support_agent")
    target_id = _user_id(client, target["access_token"])

    response = _start(
        client,
        admin_token=support["access_token"],
        user_id=target_id,
        reason="support attempt",
    )
    assert response.status_code == 403


def test_support_with_explicit_impersonate_permission(
    client: TestClient, assign_role, db_session: Session
):
    from app.users.service import get_permission_by_code, get_role_by_name

    support = _register(client, email="support-allow@example.com").json()
    target = _register(client, email="target-support-allow@example.com").json()
    assign_role("support-allow@example.com", "support_agent")

    role = get_role_by_name(db_session, "support_agent")
    perm = get_permission_by_code(db_session, "admin.users.impersonate")
    assert role is not None and perm is not None
    if perm not in role.permissions:
        role.permissions.append(perm)
        db_session.commit()

    target_id = _user_id(client, target["access_token"])
    response = _start(
        client,
        admin_token=support["access_token"],
        user_id=target_id,
        reason="trusted support grant",
    )
    assert response.status_code == 200


def test_cannot_impersonate_finance_or_support_targets(client: TestClient, assign_role):
    admin = _register(client, email="admin-prot@example.com").json()
    finance = _register(client, email="finance-target@example.com").json()
    support = _register(client, email="support-target@example.com").json()
    assign_role("admin-prot@example.com", "super_admin")
    assign_role("finance-target@example.com", "finance_admin")
    assign_role("support-target@example.com", "support_agent")

    finance_id = _user_id(client, finance["access_token"])
    support_id = _user_id(client, support["access_token"])

    assert (
        _start(
            client,
            admin_token=admin["access_token"],
            user_id=finance_id,
            reason="block finance",
        ).status_code
        == 403
    )
    assert (
        _start(
            client,
            admin_token=admin["access_token"],
            user_id=support_id,
            reason="block support",
        ).status_code
        == 403
    )


def test_suspended_user_only_super_admin(
    client: TestClient, assign_role, db_session: Session
):
    from datetime import UTC, datetime
    from uuid import UUID

    from app.users.models import User
    from app.users.service import get_permission_by_code, get_role_by_name

    admin = _register(client, email="admin-sus@example.com").json()
    support = _register(client, email="support-sus@example.com").json()
    target = _register(client, email="target-sus@example.com").json()
    assign_role("admin-sus@example.com", "super_admin")
    assign_role("support-sus@example.com", "support_agent")

    role = get_role_by_name(db_session, "support_agent")
    perm = get_permission_by_code(db_session, "admin.users.impersonate")
    assert role is not None and perm is not None
    if perm not in role.permissions:
        role.permissions.append(perm)
        db_session.commit()

    target_id = _user_id(client, target["access_token"])
    row = db_session.get(User, UUID(target_id))
    assert row is not None
    row.is_active = False
    row.deactivated_at = datetime.now(UTC)
    db_session.commit()

    denied = _start(
        client,
        admin_token=support["access_token"],
        user_id=target_id,
        reason="support suspended",
    )
    assert denied.status_code == 403

    allowed = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="super admin suspended debug",
    )
    assert allowed.status_code == 200


def test_scrub_impersonation_metadata_drops_secrets():
    from app.admin.impersonation_audit import scrub_impersonation_metadata

    cleaned = scrub_impersonation_metadata(
        {
            "reason": "ok",
            "password": "secret",
            "access_token": "tok",
            "paystack_ref": "x",
            "nested": {"qr_payload": "bad", "event_id": "e1"},
            "body": {"anything": True},
            "request_body": {"email": "x"},
            "payment_payload": {"amount": 1},
            "message_body": "private chat",
        }
    )
    assert cleaned is not None
    assert cleaned["reason"] == "ok"
    assert "password" not in cleaned
    assert "access_token" not in cleaned
    assert "paystack_ref" not in cleaned
    assert "body" not in cleaned
    assert "request_body" not in cleaned
    assert "payment_payload" not in cleaned
    assert "message_body" not in cleaned
    assert cleaned["nested"] == {"event_id": "e1"}


def test_sensitive_action_blocked_while_impersonating(
    client: TestClient, assign_role, db_session: Session
):
    from uuid import UUID

    from app.admin.impersonation_models import AdminImpersonationAuditLog

    admin = _register(client, email="admin-block@example.com").json()
    target = _register(client, email="target-block@example.com").json()
    assign_role("admin-block@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="block nested start",
    ).json()

    # Nested start while impersonating must be blocked and audited.
    nested = _start(
        client,
        admin_token=started["access_token"],
        user_id=target_id,
        reason="should be blocked",
    )
    assert nested.status_code == 403
    assert (
        nested.json()["detail"]
        == "This action is disabled during admin impersonation."
    )

    blocked = list(
        db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id
                == UUID(started["impersonation_id"]),
                AdminImpersonationAuditLog.action
                == "admin_impersonation_sensitive_action_blocked",
            )
        )
    )
    assert len(blocked) >= 1
    assert blocked[0].path and "impersonation/start" in blocked[0].path


def test_cannot_impersonate_security_locked(
    client: TestClient, assign_role, db_session: Session
):
    from datetime import UTC, datetime
    from uuid import UUID

    from app.users.models import User

    admin = _register(client, email="admin-lock@example.com").json()
    target = _register(client, email="target-lock@example.com").json()
    assign_role("admin-lock@example.com", "super_admin")

    target_id = _user_id(client, target["access_token"])
    row = db_session.get(User, UUID(target_id))
    assert row is not None
    row.security_locked_at = datetime.now(UTC)
    row.security_lock_reason = "fraud review"
    db_session.commit()

    response = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="should block lock",
    )
    assert response.status_code == 403
    assert "security lock" in response.json()["detail"].lower()


def test_impersonation_history_endpoint(client: TestClient, assign_role):
    admin = _register(
        client, email="admin-hist@example.com", full_name="Hist Admin"
    ).json()
    target = _register(client, email="target-hist@example.com").json()
    assign_role("admin-hist@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="history check reason",
        support_ticket_id="SUP-99",
    )
    assert started.status_code == 200
    body = started.json()

    client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(body["access_token"]),
    )

    history = client.get(
        f"/api/v1/admin/users/{target_id}/impersonation/history",
        headers=_auth_header(admin["access_token"]),
    )
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) >= 1
    row = next(r for r in rows if r["id"] == body["impersonation_id"])
    assert row["started_by"] == "Admin Hist"
    assert row["reason"] == "history check reason"
    assert row["support_ticket_id"] == "SUP-99"
    assert row["started_at"]
    assert row["ended_at"]
    assert row["status"] == "ended"


def test_impersonation_internal_audit_fields(
    client: TestClient, assign_role, db_session: Session
):
    """Internal audit includes admin/target/reason/ticket/times/routes/blocked actions."""
    from uuid import UUID

    from sqlalchemy import select

    from app.admin.impersonation_models import (
        AdminImpersonationAuditLog,
        AdminImpersonationSession,
    )

    admin = _register(client, email="admin-audfields@example.com").json()
    target = _register(client, email="target-audfields@example.com").json()
    assign_role("admin-audfields@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    admin_id = _user_id(client, admin["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="QA checkout reproduction",
        support_ticket_id="SUP-AUDIT-9",
    )
    assert started.status_code == 200
    body = started.json()
    impersonation_id = UUID(body["impersonation_id"])
    headers = _auth_header(body["access_token"])

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    blocked = client.patch(
        "/api/v1/passport/me/settings",
        headers=headers,
        json={"visibility": "private"},
    )
    assert blocked.status_code == 403

    ended = client.post("/api/v1/admin/impersonation/end", headers=headers)
    assert ended.status_code == 200

    session = db_session.get(AdminImpersonationSession, impersonation_id)
    assert session is not None
    assert str(session.actor_admin_id) == admin_id
    assert str(session.target_user_id) == target_id
    assert session.reason == "QA checkout reproduction"
    assert session.support_ticket_id == "SUP-AUDIT-9"
    assert session.started_at is not None
    assert session.expires_at is not None
    assert session.ended_at is not None

    start_row = db_session.scalar(
        select(AdminImpersonationAuditLog).where(
            AdminImpersonationAuditLog.impersonation_id == impersonation_id,
            AdminImpersonationAuditLog.action == "admin_impersonation_started",
        )
    )
    assert start_row is not None
    assert str(start_row.actor_admin_id) == admin_id
    assert str(start_row.target_user_id) == target_id
    assert start_row.metadata_json is not None
    assert start_row.metadata_json.get("reason") == "QA checkout reproduction"
    assert start_row.metadata_json.get("support_ticket_id") == "SUP-AUDIT-9"
    assert start_row.metadata_json.get("started_at")
    assert start_row.metadata_json.get("expires_at")

    end_row = db_session.scalar(
        select(AdminImpersonationAuditLog).where(
            AdminImpersonationAuditLog.impersonation_id == impersonation_id,
            AdminImpersonationAuditLog.action == "admin_impersonation_ended",
        )
    )
    assert end_row is not None
    assert end_row.metadata_json is not None
    assert end_row.metadata_json.get("ended_at")
    assert end_row.metadata_json.get("expires_at")
    assert end_row.metadata_json.get("support_ticket_id") == "SUP-AUDIT-9"

    request_rows = list(
        db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id == impersonation_id,
                AdminImpersonationAuditLog.action == "admin_impersonation_request_made",
            )
        )
    )
    assert any(r.path and "/auth/me" in r.path for r in request_rows)

    blocked_rows = list(
        db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id == impersonation_id,
                AdminImpersonationAuditLog.action
                == "admin_impersonation_sensitive_action_blocked",
            )
        )
    )
    assert len(blocked_rows) >= 1
    assert any(r.path and "passport" in (r.path or "") for r in blocked_rows)

    # 11B field matrix on every stamped event.
    for row in (start_row, end_row, *request_rows, *blocked_rows):
        assert row.impersonation_id == impersonation_id
        assert str(row.actor_admin_id) == admin_id
        assert str(row.target_user_id) == target_id
        assert row.action in {
            "admin_impersonation_started",
            "admin_impersonation_ended",
            "admin_impersonation_request_made",
            "admin_impersonation_sensitive_action_blocked",
        }
        assert row.created_at is not None
        meta = row.metadata_json or {}
        assert meta.get("reason") == "QA checkout reproduction"
        assert meta.get("support_ticket_id") == "SUP-AUDIT-9"
        # Never audit request/message bodies or secrets.
        assert "body" not in meta
        assert "password" not in meta
        assert "access_token" not in meta
        assert "payment_payload" not in meta
        assert "message_body" not in meta


def test_impersonation_audit_written_for_demo_seed_target(
    client: TestClient, assign_role, db_session: Session
):
    """Demo seed targets stay fully audited."""
    from uuid import UUID

    from sqlalchemy import select

    from app.admin.impersonation_models import AdminImpersonationAuditLog

    admin = _register(client, email="admin-demo-skip@example.com").json()
    target = _register(client, email="fan99@demo.padeye.test").json()
    assign_role("admin-demo-skip@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="demo audit check",
    )
    assert started.status_code == 200
    impersonation_id = UUID(started.json()["impersonation_id"])

    started_row = db_session.scalar(
        select(AdminImpersonationAuditLog).where(
            AdminImpersonationAuditLog.impersonation_id == impersonation_id,
            AdminImpersonationAuditLog.action == "admin_impersonation_started",
        )
    )
    assert started_row is not None
    assert started_row.metadata_json is not None
    assert started_row.metadata_json.get("demo_seed_target") is True

    global_actions = {
        row.action
        for row in db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_impersonation_started",
                AuditLog.resource_id == str(impersonation_id),
            )
        )
    }
    assert "admin_impersonation_started" in global_actions


def test_admin_lookup_user_by_email(client: TestClient, assign_role):
    admin = _register(client, email="admin-lookup@example.com").json()
    target = _register(
        client, email="buyer-lookup@demo.padeye.test", full_name="Lookup Buyer"
    ).json()
    assign_role("admin-lookup@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    found = client.get(
        "/api/v1/users/admin/lookup",
        params={"email": "buyer-lookup@demo.padeye.test"},
        headers=_auth_header(admin["access_token"]),
    )
    assert found.status_code == 200
    body = found.json()
    assert body["id"] == target_id
    assert body["email"] == "buyer-lookup@demo.padeye.test"

    missing = client.get(
        "/api/v1/users/admin/lookup",
        params={"email": "missing@demo.padeye.test"},
        headers=_auth_header(admin["access_token"]),
    )
    assert missing.status_code == 404


def test_session_identity_while_impersonating(client: TestClient, assign_role):
    admin = _register(client, email="admin-sess@example.com").json()
    target = _register(client, email="target-sess@example.com").json()
    assign_role("admin-sess@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    admin_id = _user_id(client, admin["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="session identity check",
    ).json()

    session = client.get(
        "/api/v1/me/session",
        headers=_auth_header(started["access_token"]),
    )
    assert session.status_code == 200
    body = session.json()
    assert body["current_user_id"] == target_id
    assert body["actor_admin_id"] == admin_id
    assert body["impersonation_id"] == started["impersonation_id"]
    assert body["is_impersonating"] is True

    normal = client.get(
        "/api/v1/me/session",
        headers=_auth_header(target["access_token"]),
    )
    assert normal.status_code == 200
    normal_body = normal.json()
    assert normal_body["current_user_id"] == target_id
    assert normal_body["actor_admin_id"] is None
    assert normal_body["impersonation_id"] is None
    assert normal_body["is_impersonating"] is False


def test_impersonation_session_mismatch_rejected(
    client: TestClient, assign_role, db_session: Session
):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID, uuid4

    from app.admin.impersonation_models import AdminImpersonationSession
    from app.core.security import create_impersonation_access_token

    admin = _register(client, email="admin-mismatch@example.com").json()
    target = _register(client, email="target-mismatch@example.com").json()
    other = _register(client, email="other-mismatch@example.com").json()
    assign_role("admin-mismatch@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    other_id = _user_id(client, other["access_token"])
    admin_id = _user_id(client, admin["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="mismatch check",
    ).json()

    # Forge a token that points at a different target than the DB session row.
    started_at = datetime.now(UTC)
    expires_at = started_at + timedelta(minutes=30)
    forged = create_impersonation_access_token(
        actual_user_id=UUID(other_id),
        actor_admin_id=UUID(admin_id),
        impersonation_id=UUID(started["impersonation_id"]),
        roles=["buyer"],
        permissions=[],
        started_at=started_at,
        expires_at=expires_at,
        reason="forged",
    )
    session_row = db_session.get(
        AdminImpersonationSession, UUID(started["impersonation_id"])
    )
    assert session_row is not None
    assert str(session_row.target_user_id) == target_id

    denied = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(forged),
    )
    assert denied.status_code == 401
    assert "mismatch" in denied.json()["detail"].lower()


def test_should_block_impersonation_action_matrix():
    from app.admin.impersonation_guards import should_block_impersonation_action

    view = ["view"]
    host = ["view", "host_events"]
    full = ["view", "host_events", "credentials"]

    # Allowed: view dashboard / tickets / orders / merch / refunds / Passport / Vault / exit
    assert not should_block_impersonation_action("GET", "/api/v1/auth/me", view)
    assert not should_block_impersonation_action("GET", "/api/v1/tickets/mine", view)
    assert not should_block_impersonation_action("GET", "/api/v1/orders/mine", view)
    assert not should_block_impersonation_action("GET", "/api/v1/passport/me", view)
    assert not should_block_impersonation_action("GET", "/api/v1/vault/items", view)
    assert not should_block_impersonation_action(
        "GET", "/api/v1/finance/host/balance", view
    )
    assert not should_block_impersonation_action(
        "GET", "/api/v1/finance/refunds/mine", view
    )
    assert not should_block_impersonation_action("GET", "/api/v1/support/cases", view)
    assert not should_block_impersonation_action(
        "POST", "/api/v1/admin/impersonation/end", view
    )

    # Blocked: admin routes (any method)
    assert should_block_impersonation_action(
        "POST", "/api/v1/admin/users/x/impersonation/start", full
    )
    assert should_block_impersonation_action("GET", "/api/v1/admin/audit-logs", full)
    assert should_block_impersonation_action("GET", "/api/v1/admin/users", full)

    # Credentials only with credentials scope
    assert should_block_impersonation_action(
        "POST", "/api/v1/auth/change-password", view
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/auth/change-password", host
    )
    assert not should_block_impersonation_action(
        "POST", "/api/v1/auth/change-password", full
    )
    assert not should_block_impersonation_action(
        "POST", "/api/v1/auth/change-email", full
    )
    assert not should_block_impersonation_action(
        "PATCH", "/api/v1/users/me/email", full
    )
    assert not should_block_impersonation_action(
        "PATCH", "/api/v1/users/me/phone", full
    )
    # Host event media + unused ticket-type delete — host_events pack
    assert should_block_impersonation_action(
        "POST", "/api/v1/events/media/upload", view
    )
    assert not should_block_impersonation_action(
        "POST", "/api/v1/events/media/upload", host
    )
    assert not should_block_impersonation_action(
        "POST", "/api/v1/events/by-id/abc/media/upload", host
    )
    assert not should_block_impersonation_action(
        "DELETE", "/api/v1/events/by-id/abc/ticket-types/def", host
    )
    assert not should_block_impersonation_action(
        "DELETE", "/api/v1/events/by-id/abc/media/def", host
    )
    assert should_block_impersonation_action(
        "DELETE", "/api/v1/events/by-id/abc/ticket-types/def", view
    )
    # Legacy studio — host_events pack
    assert should_block_impersonation_action(
        "PATCH", "/api/v1/host/legacy", view
    )
    assert not should_block_impersonation_action(
        "PATCH", "/api/v1/host/legacy", host
    )
    assert not should_block_impersonation_action(
        "PATCH", "/api/v1/legacy/me", host
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/host/legacy/content-blocks", view
    )
    assert not should_block_impersonation_action(
        "POST", "/api/v1/host/legacy/content-blocks/reorder", host
    )
    # Blocked: 2FA / account delete
    assert should_block_impersonation_action("POST", "/api/v1/users/me/2fa/enable")
    assert should_block_impersonation_action("POST", "/api/v1/users/me/2fa/disable")
    assert should_block_impersonation_action("POST", "/api/v1/delete-account")
    assert should_block_impersonation_action("DELETE", "/api/v1/users/me")

    # Blocked: bank / payouts / finance mutations
    assert should_block_impersonation_action(
        "POST", "/api/v1/hosts/me/bank-accounts"
    )
    assert should_block_impersonation_action("POST", "/api/v1/finance/host/payouts")
    assert should_block_impersonation_action(
        "POST", "/api/v1/finance/refunds/requests"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/finance/admin/payouts/x/review"
    )

    # Blocked: checkout / paid purchase / cart
    assert should_block_impersonation_action("POST", "/api/v1/orders")
    assert should_block_impersonation_action(
        "POST", "/api/v1/payments/checkout/abc"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/dashboard/cart/items"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/merch/discounts/validate"
    )

    # Blocked: ticket transfer + content delete
    assert should_block_impersonation_action(
        "POST", "/api/v1/tickets/abc/transfer"
    )
    assert should_block_impersonation_action("DELETE", "/api/v1/reviews/abc")
    assert should_block_impersonation_action(
        "POST", "/api/v1/messages/abc/delete"
    )

    # Blocked: Passport privacy + social / Fan Connect
    assert should_block_impersonation_action(
        "PATCH", "/api/v1/passport/me/settings"
    )
    assert should_block_impersonation_action(
        "PATCH", "/api/v1/dashboard/passport/settings"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/oauth/google/connect"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/fan-connect/requests"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/fan-connect/connections/x/disconnect"
    )
    assert should_block_impersonation_action(
        "PATCH", "/api/v1/fan-connect/settings"
    )

    # Blocked: provider / API keys + support queue actions
    assert should_block_impersonation_action(
        "PUT", "/api/v1/admin/settings/runtime/email/smtp_host"
    )
    assert should_block_impersonation_action(
        "PUT", "/api/v1/host/merchandise/print-on-demand/integrations"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/support/cases/abc/assign"
    )
    assert should_block_impersonation_action(
        "POST", "/api/v1/support/cases/abc/resolve"
    )


def test_sensitive_actions_blocked_while_impersonating(
    client: TestClient, assign_role
):
    detail = "This action is disabled during admin impersonation."
    admin = _register(client, email="admin-sens@example.com").json()
    target = _register(client, email="target-sens@example.com").json()
    assign_role("admin-sens@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="sensitive action audit",
    ).json()
    headers = _auth_header(started["access_token"])

    # Safe reads still work.
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    tickets = client.get("/api/v1/tickets/mine", headers=headers)
    assert tickets.status_code == 200
    orders = client.get("/api/v1/orders/mine", headers=headers)
    assert orders.status_code == 200

    # Dangerous / admin / money / transfer / privacy mutations blocked.
    blocked_calls = [
        client.post(
            "/api/v1/orders",
            headers=headers,
            json={"items": []},
        ),
        client.post(
            f"/api/v1/payments/checkout/{target_id}",
            headers=headers,
        ),
        client.post(
            f"/api/v1/tickets/{target_id}/transfer",
            headers=headers,
            json={"to_email": "other@example.com", "to_name": "Other User"},
        ),
        client.patch(
            "/api/v1/passport/me/settings",
            headers=headers,
            json={"visibility": "private"},
        ),
        client.post(
            "/api/v1/fan-connect/requests",
            headers=headers,
            json={"to_user_id": str(target_id)},
        ),
        client.post(
            "/api/v1/hosts/me/bank-accounts",
            headers=headers,
            json={
                "bank_name": "Test",
                "account_name": "Test",
                "account_number": "0123456789",
            },
        ),
        client.post(
            "/api/v1/finance/host/payouts",
            headers=headers,
            json={"amount_kobo": 1000},
        ),
        client.post(
            "/api/v1/support/cases",
            headers=headers,
            json={"subject": "x", "body": "y"},
        ),
        client.get("/api/v1/admin/audit-logs", headers=headers),
    ]
    for response in blocked_calls:
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == detail

    # Exit still works.
    ended = client.post("/api/v1/admin/impersonation/end", headers=headers)
    assert ended.status_code == 200
    assert ended.json()["ended"] is True


def test_one_active_impersonation_per_admin(client: TestClient, assign_role):
    admin = _register(client, email="admin-one@example.com").json()
    t1 = _register(client, email="target-one-a@example.com").json()
    t2 = _register(client, email="target-one-b@example.com").json()
    assign_role("admin-one@example.com", "super_admin")
    id1 = _user_id(client, t1["access_token"])
    id2 = _user_id(client, t2["access_token"])

    first = _start(
        client,
        admin_token=admin["access_token"],
        user_id=id1,
        reason="first session",
    )
    assert first.status_code == 200

    second = _start(
        client,
        admin_token=admin["access_token"],
        user_id=id2,
        reason="second session blocked",
    )
    assert second.status_code == 400
    assert "end your current impersonation" in second.json()["detail"].lower()

    client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(first.json()["access_token"]),
    )
    after_end = _start(
        client,
        admin_token=admin["access_token"],
        user_id=id2,
        reason="after explicit end",
    )
    assert after_end.status_code == 200


def test_stale_expired_session_does_not_block_new_start(
    client: TestClient, assign_role, db_session: Session
):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from app.admin.impersonation_models import (
        IMPERSONATION_STATUS_ACTIVE,
        AdminImpersonationSession,
    )

    admin = _register(client, email="admin-stale@example.com").json()
    t1 = _register(client, email="target-stale-a@example.com").json()
    t2 = _register(client, email="target-stale-b@example.com").json()
    assign_role("admin-stale@example.com", "super_admin")
    id1 = _user_id(client, t1["access_token"])
    id2 = _user_id(client, t2["access_token"])

    first = _start(
        client,
        admin_token=admin["access_token"],
        user_id=id1,
        reason="will go stale",
    ).json()
    row = db_session.get(AdminImpersonationSession, UUID(first["impersonation_id"]))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    row.status = IMPERSONATION_STATUS_ACTIVE
    db_session.commit()

    second = _start(
        client,
        admin_token=admin["access_token"],
        user_id=id2,
        reason="after stale expire",
    )
    assert second.status_code == 200


def test_impersonation_ends_when_target_disabled_mid_session(
    client: TestClient, assign_role, db_session: Session
):
    from datetime import UTC, datetime
    from uuid import UUID

    from app.admin.impersonation_models import AdminImpersonationSession
    from app.users.models import User

    admin = _register(client, email="admin-dis-tgt@example.com").json()
    target = _register(client, email="target-dis-tgt@example.com").json()
    assign_role("admin-dis-tgt@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="disable target mid session",
    ).json()

    ok = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started["access_token"]),
    )
    assert ok.status_code == 200

    row = db_session.get(User, UUID(target_id))
    assert row is not None
    row.is_active = False
    row.deactivated_at = datetime.now(UTC)
    db_session.commit()

    denied = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started["access_token"]),
    )
    assert denied.status_code == 401
    assert "target account is disabled" in denied.json()["detail"].lower()

    session = db_session.get(
        AdminImpersonationSession, UUID(started["impersonation_id"])
    )
    assert session is not None
    assert session.status == "revoked"


def test_impersonation_ends_when_admin_disabled_mid_session(
    client: TestClient, assign_role, db_session: Session
):
    from datetime import UTC, datetime
    from uuid import UUID

    from app.users.models import User

    admin = _register(client, email="admin-dis-adm@example.com").json()
    target = _register(client, email="target-dis-adm@example.com").json()
    assign_role("admin-dis-adm@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    admin_id = _user_id(client, admin["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="disable admin mid session",
    ).json()

    row = db_session.get(User, UUID(admin_id))
    assert row is not None
    row.is_active = False
    row.deactivated_at = datetime.now(UTC)
    db_session.commit()

    denied = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started["access_token"]),
    )
    assert denied.status_code == 401
    assert "admin account is disabled" in denied.json()["detail"].lower()


def test_exit_ends_impersonation_session(
    client: TestClient, assign_role, db_session: Session
):
    from uuid import UUID

    from app.admin.impersonation_models import AdminImpersonationSession

    admin = _register(client, email="admin-exit@example.com").json()
    target = _register(client, email="target-exit@example.com").json()
    assign_role("admin-exit@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="exit ends session",
    ).json()
    ended = client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(started["access_token"]),
    )
    assert ended.status_code == 200

    row = db_session.get(
        AdminImpersonationSession, UUID(started["impersonation_id"])
    )
    assert row is not None
    assert row.status == "ended"
    assert row.ended_at is not None

    denied = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started["access_token"]),
    )
    assert denied.status_code == 401


def test_suspended_start_still_usable_until_mid_session_disable(
    client: TestClient, assign_role, db_session: Session
):
    """Super-admin may start on already-suspended users; session remains usable."""
    from datetime import UTC, datetime
    from uuid import UUID

    from app.users.models import User

    admin = _register(client, email="admin-sus-ok@example.com").json()
    target = _register(client, email="target-sus-ok@example.com").json()
    assign_role("admin-sus-ok@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    row = db_session.get(User, UUID(target_id))
    assert row is not None
    row.is_active = False
    row.deactivated_at = datetime.now(UTC) - __import__("datetime").timedelta(days=1)
    db_session.commit()

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="super admin suspended debug continue",
    )
    assert started.status_code == 200
    me = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started.json()["access_token"]),
    )
    assert me.status_code == 200
    assert me.json()["email"] == "target-sus-ok@example.com"


# --- §14 checklist: named coverage for core contracts ---


def test_super_admin_can_start_impersonation_with_reason(client: TestClient, assign_role):
    admin = _register(client, email="sa-start@example.com").json()
    target = _register(client, email="sa-target@example.com").json()
    assign_role("sa-start@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="support reproduction",
    )
    assert started.status_code == 200
    assert started.json()["target_user_id"] == target_id
    payload = decode_access_token(started.json()["access_token"])
    assert payload["reason"] == "support reproduction"
    assert payload["is_impersonating"] is True


def test_admin_without_permission_gets_403(client: TestClient, assign_role):
    finance = _register(client, email="fin-noperm@example.com").json()
    target = _register(client, email="fin-target@example.com").json()
    assign_role("fin-noperm@example.com", "finance_admin")
    target_id = _user_id(client, target["access_token"])

    response = _start(
        client,
        admin_token=finance["access_token"],
        user_id=target_id,
        reason="should be denied",
    )
    assert response.status_code == 403


def test_normal_user_gets_403_on_impersonation_start(client: TestClient):
    buyer = _register(client, email="buyer-noperm@example.com").json()
    other = _register(client, email="other-noperm@example.com").json()
    other_id = _user_id(client, other["access_token"])

    response = _start(
        client,
        admin_token=buyer["access_token"],
        user_id=other_id,
        reason="buyer cannot impersonate",
    )
    assert response.status_code == 403


def test_host_owner_cannot_impersonate_even_with_grant(
    client: TestClient, assign_role, db_session: Session
):
    from app.users.service import get_permission_by_code, get_role_by_name

    host = _register(client, email="host-imp-deny@example.com").json()
    target = _register(client, email="target-host-imp@example.com").json()
    assign_role("host-imp-deny@example.com", "host")

    role = get_role_by_name(db_session, "host")
    perm = get_permission_by_code(db_session, "admin.users.impersonate")
    assert role is not None and perm is not None
    if perm not in role.permissions:
        role.permissions.append(perm)
        db_session.commit()

    target_id = _user_id(client, target["access_token"])
    response = _start(
        client,
        admin_token=host["access_token"],
        user_id=target_id,
        reason="host should never impersonate",
    )
    assert response.status_code == 403


def test_host_staff_cannot_impersonate_even_with_grant(
    client: TestClient, assign_role, db_session: Session
):
    from app.users.service import get_permission_by_code, get_role_by_name

    staff = _register(client, email="staff-imp-deny@example.com").json()
    target = _register(client, email="target-staff-imp@example.com").json()
    assign_role("staff-imp-deny@example.com", "host_staff")

    role = get_role_by_name(db_session, "host_staff")
    perm = get_permission_by_code(db_session, "admin.users.impersonate")
    assert role is not None and perm is not None
    if perm not in role.permissions:
        role.permissions.append(perm)
        db_session.commit()

    target_id = _user_id(client, target["access_token"])
    response = _start(
        client,
        admin_token=staff["access_token"],
        user_id=target_id,
        reason="staff should never impersonate",
    )
    assert response.status_code == 403


def test_cannot_impersonate_account_status_deleted(
    client: TestClient, assign_role, db_session: Session
):
    from uuid import UUID

    from app.users.account_status_constants import ACCOUNT_STATUS_DELETED
    from app.users.models import User

    admin = _register(client, email="admin-status-del@example.com").json()
    target = _register(client, email="target-status-del@example.com").json()
    assign_role("admin-status-del@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    row = db_session.get(User, UUID(target_id))
    assert row is not None
    row.account_status = ACCOUNT_STATUS_DELETED
    db_session.commit()

    response = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="deleted account status",
    )
    assert response.status_code == 404


def test_can_start_impersonation_matrix():
    from app.admin.impersonation_service import can_start_impersonation

    class _Perm:
        def __init__(self, code: str) -> None:
            self.code = code

    class _Role:
        def __init__(self, name: str, perms: list[str]) -> None:
            self.name = name
            self.permissions = [_Perm(c) for c in perms]

    class _User:
        def __init__(self, roles: list[_Role]) -> None:
            self.roles = roles

    assert can_start_impersonation(
        _User([_Role("super_admin", ["admin.full_access"])])  # type: ignore[arg-type]
    )
    assert can_start_impersonation(
        _User(
            [
                _Role(
                    "support_agent",
                    ["admin.users.view", "admin.users.impersonate"],
                )
            ]
        )  # type: ignore[arg-type]
    )
    assert not can_start_impersonation(
        _User([_Role("support_agent", ["admin.users.view"])])  # type: ignore[arg-type]
    )
    assert not can_start_impersonation(
        _User([_Role("finance_admin", ["payments.view"])])  # type: ignore[arg-type]
    )
    assert not can_start_impersonation(
        _User([_Role("host", ["admin.users.impersonate"])])  # type: ignore[arg-type]
    )
    assert not can_start_impersonation(
        _User([_Role("host_staff", ["admin.users.impersonate"])])  # type: ignore[arg-type]
    )
    assert not can_start_impersonation(
        _User([_Role("buyer", [])])  # type: ignore[arg-type]
    )


def test_resolve_impersonation_scopes_matrix():
    from app.admin.impersonation_scopes import (
        pack_label,
        resolve_impersonation_scopes,
    )

    class _Perm:
        def __init__(self, code: str) -> None:
            self.code = code

    class _Role:
        def __init__(self, name: str, perms: list[str]) -> None:
            self.name = name
            self.permissions = [_Perm(c) for c in perms]

    class _User:
        def __init__(self, roles: list[_Role]) -> None:
            self.roles = roles

    full = resolve_impersonation_scopes(
        _User([_Role("super_admin", ["admin.full_access"])])  # type: ignore[arg-type]
    )
    assert full == ["view", "host_events", "credentials"]
    assert pack_label(full) == "full"

    support = resolve_impersonation_scopes(
        _User(
            [
                _Role(
                    "support_agent",
                    ["admin.users.impersonate"],
                )
            ]
        )  # type: ignore[arg-type]
    )
    assert support == ["view"]
    assert pack_label(support) == "view"

    ops = resolve_impersonation_scopes(
        _User(
            [
                _Role(
                    "operations",
                    [
                        "admin.users.impersonate",
                        "admin.users.impersonate.host_events",
                    ],
                )
            ]
        )  # type: ignore[arg-type]
    )
    assert ops == ["view", "host_events"]
    assert pack_label(ops) == "host_events"

    assert (
        resolve_impersonation_scopes(
            _User([_Role("buyer", [])])  # type: ignore[arg-type]
        )
        == []
    )


def test_cannot_impersonate_deleted_user(client: TestClient, assign_role):
    from uuid import uuid4

    admin = _register(client, email="admin-deleted@example.com").json()
    assign_role("admin-deleted@example.com", "super_admin")

    response = _start(
        client,
        admin_token=admin["access_token"],
        user_id=str(uuid4()),
        reason="missing user",
    )
    assert response.status_code == 404
    assert "deleted" in response.json()["detail"].lower() or "not found" in response.json()[
        "detail"
    ].lower()


def test_impersonation_session_expires(
    client: TestClient, assign_role, db_session: Session
):
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from app.admin.impersonation_models import (
        IMPERSONATION_STATUS_EXPIRED,
        AdminImpersonationAuditLog,
        AdminImpersonationSession,
    )

    admin = _register(client, email="admin-exp@example.com").json()
    target = _register(client, email="target-exp@example.com").json()
    assign_role("admin-exp@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="will expire",
        support_ticket_id="SUP-EXP-1",
    ).json()
    impersonation_id = UUID(started["impersonation_id"])

    row = db_session.get(AdminImpersonationSession, impersonation_id)
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(seconds=5)
    db_session.commit()

    denied = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started["access_token"]),
    )
    assert denied.status_code == 401
    assert "expired" in denied.json()["detail"].lower()

    db_session.refresh(row)
    assert row.status == IMPERSONATION_STATUS_EXPIRED

    expired_audit = list(
        db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id == impersonation_id,
                AdminImpersonationAuditLog.action == "admin_impersonation_expired",
            )
        )
    )
    assert len(expired_audit) >= 1
    exp = expired_audit[0]
    assert exp.actor_admin_id == row.actor_admin_id
    assert exp.target_user_id == row.target_user_id
    assert exp.created_at is not None
    assert (exp.metadata_json or {}).get("reason") == "will expire"
    assert (exp.metadata_json or {}).get("support_ticket_id") == "SUP-EXP-1"
    assert (exp.metadata_json or {}).get("expires_at")


def test_end_impersonation_works(client: TestClient, assign_role):
    admin = _register(client, email="admin-endok@example.com").json()
    target = _register(client, email="target-endok@example.com").json()
    assign_role("admin-endok@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="end check",
    ).json()
    ended = client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(started["access_token"]),
    )
    assert ended.status_code == 200
    assert ended.json()["ended"] is True
    assert ended.json()["return_to"] == f"/admin/users/{target_id}"

    after = client.get(
        "/api/v1/me/impersonation",
        headers=_auth_header(started["access_token"]),
    )
    assert after.status_code in {200, 401}


def test_current_user_becomes_target_user(client: TestClient, assign_role):
    admin = _register(client, email="admin-cur@example.com").json()
    target = _register(
        client, email="target-cur@example.com", full_name="Target Current"
    ).json()
    assign_role("admin-cur@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    admin_id = _user_id(client, admin["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="identity swap",
    ).json()
    me = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started["access_token"]),
    ).json()
    assert me["id"] == target_id
    assert me["email"] == "target-cur@example.com"
    assert me["id"] != admin_id


def test_actor_admin_id_remains_admin(client: TestClient, assign_role):
    admin = _register(client, email="admin-actor@example.com").json()
    target = _register(client, email="target-actor@example.com").json()
    assign_role("admin-actor@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    admin_id = _user_id(client, admin["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="actor stamp",
    ).json()
    payload = decode_access_token(started["access_token"])
    assert payload["actor_admin_id"] == admin_id
    assert payload["actual_user_id"] == target_id
    assert payload["sub"] == target_id

    session = client.get(
        "/api/v1/me/session",
        headers=_auth_header(started["access_token"]),
    ).json()
    assert session["current_user_id"] == target_id
    assert session["actor_admin_id"] == admin_id


def test_admin_permissions_do_not_leak_into_impersonated_session(
    client: TestClient, assign_role
):
    admin = _register(client, email="admin-noleak@example.com").json()
    target = _register(client, email="target-noleak@example.com").json()
    assign_role("admin-noleak@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="no leak",
    ).json()
    payload = decode_access_token(started["access_token"])
    assert "admin.full_access" not in payload.get("permissions", [])
    assert "admin.users.impersonate" not in payload.get("permissions", [])

    me = client.get(
        "/api/v1/auth/me",
        headers=_auth_header(started["access_token"]),
    ).json()
    assert "admin.full_access" not in me.get("permissions", [])
    assert "super_admin" not in me.get("roles", [])

    denied = client.get(
        "/api/v1/admin/audit-logs",
        headers=_auth_header(started["access_token"]),
    )
    assert denied.status_code == 403


def test_audit_log_created_on_start_and_end(
    client: TestClient, assign_role, db_session: Session
):
    from uuid import UUID

    from app.admin.impersonation_models import AdminImpersonationAuditLog

    admin = _register(client, email="admin-aud2@example.com").json()
    target = _register(client, email="target-aud2@example.com").json()
    assign_role("admin-aud2@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="audit start end",
    ).json()
    impersonation_id = UUID(started["impersonation_id"])

    start_rows = list(
        db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id == impersonation_id,
                AdminImpersonationAuditLog.action == "admin_impersonation_started",
            )
        )
    )
    assert len(start_rows) == 1

    ended = client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(started["access_token"]),
    )
    assert ended.status_code == 200

    end_rows = list(
        db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id == impersonation_id,
                AdminImpersonationAuditLog.action == "admin_impersonation_ended",
            )
        )
    )
    assert len(end_rows) == 1

    global_actions = {
        row.action
        for row in db_session.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == str(impersonation_id),
                AuditLog.action.in_(
                    ["admin_impersonation_started", "admin_impersonation_ended"]
                ),
            )
        )
    }
    assert "admin_impersonation_started" in global_actions
    assert "admin_impersonation_ended" in global_actions


def test_impersonation_session_rules_10d(
    client: TestClient, assign_role, db_session: Session
):
    """10D — claims, identity separation, duration, expiry, logout, no nested."""
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from app.admin.impersonation_models import (
        IMPERSONATION_STATUS_ACTIVE,
        IMPERSONATION_STATUS_ENDED,
        AdminImpersonationSession,
    )
    from app.admin.impersonation_service import (
        DEFAULT_DURATION_MINUTES,
        MAX_DURATION_MINUTES,
    )

    assert DEFAULT_DURATION_MINUTES == 30
    assert MAX_DURATION_MINUTES == 60

    admin = _register(client, email="admin-10d@example.com").json()
    target = _register(client, email="target-10d@example.com").json()
    assign_role("admin-10d@example.com", "super_admin")
    admin_id = _user_id(client, admin["access_token"])
    target_id = _user_id(client, target["access_token"])

    # Default duration when omitted → 30 minutes.
    started = client.post(
        f"/api/v1/admin/users/{target_id}/impersonation/start",
        headers=_auth_header(admin["access_token"]),
        json={"reason": "10D session contract"},
    )
    assert started.status_code == 200, started.text
    body = started.json()
    payload = decode_access_token(body["access_token"])

    required_claims = (
        "actual_user_id",
        "actor_admin_id",
        "impersonation_id",
        "is_impersonating",
        "started_at",
        "expires_at",
        "reason",
    )
    for claim in required_claims:
        assert claim in payload, claim
    assert payload["actual_user_id"] == target_id
    assert payload["sub"] == target_id
    assert payload["actor_admin_id"] == admin_id
    assert payload["impersonation_id"] == body["impersonation_id"]
    assert payload["is_impersonating"] is True
    assert payload["reason"] == "10D session contract"
    assert "admin.full_access" not in payload.get("permissions", [])
    assert "super_admin" not in payload.get("roles", [])

    started_at = datetime.fromisoformat(payload["started_at"])
    expires_at = datetime.fromisoformat(payload["expires_at"])
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    delta = expires_at - started_at
    assert timedelta(minutes=29) <= delta <= timedelta(minutes=31)

    # Current user = target; actor admin stored separately.
    me = client.get(
        "/api/v1/auth/me", headers=_auth_header(body["access_token"])
    ).json()
    assert me["id"] == target_id
    assert me["impersonation"]["actor_admin_id"] == admin_id
    assert me["impersonation"]["actual_user_id"] == target_id

    session = client.get(
        "/api/v1/me/session", headers=_auth_header(body["access_token"])
    ).json()
    assert session["current_user_id"] == target_id
    assert session["actor_admin_id"] == admin_id
    assert session["is_impersonating"] is True
    assert session["impersonation_id"] == body["impersonation_id"]

    # /admin blocked while impersonating.
    assert (
        client.get(
            "/api/v1/admin/audit-logs",
            headers=_auth_header(body["access_token"]),
        ).status_code
        == 403
    )

    # No nested impersonation.
    nested = _start(
        client,
        admin_token=body["access_token"],
        user_id=target_id,
        reason="nested should fail",
    )
    assert nested.status_code == 403

    # Max duration 60; >60 rejected.
    assert (
        _start(
            client,
            admin_token=admin["access_token"],
            user_id=target_id,
            reason="too long",
            duration_minutes=90,
        ).status_code
        in {400, 422}
    )

    # Exit ends the session.
    ended = client.post(
        "/api/v1/admin/impersonation/end",
        headers=_auth_header(body["access_token"]),
    )
    assert ended.status_code == 200
    row = db_session.get(AdminImpersonationSession, UUID(body["impersonation_id"]))
    assert row is not None
    assert row.status == IMPERSONATION_STATUS_ENDED

    # Logout ends an active impersonation session.
    started2 = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="logout should end",
        duration_minutes=60,
    ).json()
    logout = client.post(
        "/api/v1/auth/logout",
        headers=_auth_header(started2["access_token"]),
        json={},
    )
    assert logout.status_code == 200
    row2 = db_session.get(
        AdminImpersonationSession, UUID(started2["impersonation_id"])
    )
    assert row2 is not None
    assert row2.status != IMPERSONATION_STATUS_ACTIVE


def test_audit_log_created_on_blocked_sensitive_action(
    client: TestClient, assign_role, db_session: Session
):
    from uuid import UUID

    from app.admin.impersonation_models import AdminImpersonationAuditLog

    admin = _register(client, email="admin-blok2@example.com").json()
    target = _register(client, email="target-blok2@example.com").json()
    assign_role("admin-blok2@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="block audit",
    ).json()
    impersonation_id = UUID(started["impersonation_id"])

    blocked = client.patch(
        "/api/v1/passport/me/settings",
        headers=_auth_header(started["access_token"]),
        json={"visibility": "private"},
    )
    assert blocked.status_code == 403
    assert (
        blocked.json()["detail"]
        == "This action is disabled during admin impersonation."
    )

    rows = list(
        db_session.scalars(
            select(AdminImpersonationAuditLog).where(
                AdminImpersonationAuditLog.impersonation_id == impersonation_id,
                AdminImpersonationAuditLog.action
                == "admin_impersonation_sensitive_action_blocked",
            )
        )
    )
    assert len(rows) >= 1


def test_target_user_is_not_notified(
    client: TestClient, assign_role, db_session: Session
):
    """Impersonation must never email or in-app notify the target (14B)."""
    from uuid import UUID

    from app.email.models import EmailEvent
    from app.messaging.models import InAppNotification

    admin = _register(client, email="admin-nonotify@example.com").json()
    target = _register(client, email="target-nonotify@example.com").json()
    assign_role("admin-nonotify@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])
    target_uuid = UUID(str(target_id))
    target_email = "target-nonotify@example.com"

    before_email_ids = {
        row.id
        for row in db_session.scalars(
            select(EmailEvent).where(EmailEvent.recipient_email == target_email)
        ).all()
    }
    before_notif_ids = {
        row.id
        for row in db_session.scalars(
            select(InAppNotification).where(InAppNotification.user_id == target_uuid)
        ).all()
    }

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="internal QA — target must not be notified",
    )
    assert started.status_code == 200

    headers = _auth_header(started.json()["access_token"])
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    ended = client.post("/api/v1/admin/impersonation/end", headers=headers)
    assert ended.status_code == 200

    db_session.expire_all()

    new_emails = [
        row
        for row in db_session.scalars(
            select(EmailEvent).where(EmailEvent.recipient_email == target_email)
        ).all()
        if row.id not in before_email_ids
    ]
    assert new_emails == [], "No new emails may be queued for the impersonation target"

    new_notifs = [
        row
        for row in db_session.scalars(
            select(InAppNotification).where(InAppNotification.user_id == target_uuid)
        ).all()
        if row.id not in before_notif_ids
    ]
    assert new_notifs == [], "No in-app notifications may be created for the target"
