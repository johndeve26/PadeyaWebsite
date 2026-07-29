"""Admin team management — invites, roles, permissions, audit."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.impersonation_service import can_start_impersonation
from app.admin_team.models import AdminAuditLog, AdminInvite
from app.admin_team.service import ensure_system_admin_roles
from app.email.models import EmailEvent
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_user_by_email, user_has_permission


def _register(
    client: TestClient, *, prefix: str, name: str = "User"
) -> tuple[dict, str]:
    email = f"{prefix}-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": name},
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}, email


def test_super_admin_invite_support(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    db_session.commit()

    admin_headers, admin_email = _register(client, prefix="sa", name="Super Admin")
    assign_role(admin_email, "super_admin")

    _, target_email = _register(client, prefix="support-target", name="Support Target")

    invited = client.post(
        "/api/v1/admin/team/invite",
        headers=admin_headers,
        json={"email": target_email, "system_key": "support"},
    )
    assert invited.status_code == 201, invited.text
    body = invited.json()
    assert body["status"] == "provisioned"
    assert body["member"]["status"] == "active"
    assert body["member"]["role"]["system_key"] == "support"
    assert "invite_token" not in body

    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "admin_team_invite",
            EmailEvent.recipient_email == target_email,
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    assert (email_row.context_json or {}).get("provisioned") is True

    target = get_user_by_email(db_session, target_email)
    assert target is not None
    db_session.refresh(target)
    assert user_has_permission(target, "support.reply")
    assert not user_has_permission(target, "payments.view")
    assert not user_has_permission(target, "refunds.approve")

    audits = (
        db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.action == "admin_team.invite")
        .all()
    )
    assert len(audits) >= 1
    assert all(
        "token" not in str(a.details or {}).lower()
        and "password" not in str(a.details or {}).lower()
        for a in audits
    )


def test_pending_admin_invite_emails_and_accept(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    db_session.commit()

    admin_headers, admin_email = _register(client, prefix="sa-pend", name="Super Admin")
    assign_role(admin_email, "super_admin")

    pending_email = f"pending-{uuid4().hex[:8]}@example.com"
    invited = client.post(
        "/api/v1/admin/team/invite",
        headers=admin_headers,
        json={"email": pending_email, "system_key": "support"},
    )
    assert invited.status_code == 201, invited.text
    body = invited.json()
    assert body["status"] == "pending"
    assert body["invite_id"]
    assert "invite_token" not in body

    email_row = db_session.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.template == "admin_team_invite",
            EmailEvent.recipient_email == pending_email,
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    path = (email_row.context_json or {}).get("invite_path", "")
    assert path.startswith("/admin/team/invites/")
    token = path.rsplit("/", 1)[-1]
    assert token and len(token) >= 16

    invite_row = db_session.scalar(
        select(AdminInvite).where(AdminInvite.email == pending_email)
    )
    assert invite_row is not None
    assert invite_row.token_hash != token

    preview = client.get(f"/api/v1/admin/team/invites/{token}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["status"] == "pending"
    assert "***" in preview.json()["email_hint"]
    assert pending_email not in preview.json()["email_hint"]

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": pending_email,
            "password": "Password123!",
            "full_name": "Invitee",
        },
    )
    assert reg.status_code == 201, reg.text
    invitee_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    wrong_headers, _ = _register(client, prefix="wrong-admin", name="Wrong")
    denied = client.post(
        f"/api/v1/admin/team/invites/{token}/accept",
        headers=wrong_headers,
    )
    assert denied.status_code == 403

    accepted = client.post(
        f"/api/v1/admin/team/invites/{token}/accept",
        headers=invitee_headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"
    assert accepted.json()["role"]["system_key"] == "support"

    target = get_user_by_email(db_session, pending_email)
    assert target is not None
    db_session.refresh(target)
    assert user_has_permission(target, "support.reply")



def test_admin_without_permission_cannot_invite(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    headers, email = _register(client, prefix="no-team", name="Support Only")
    assign_role(email, "support_agent")

    res = client.post(
        "/api/v1/admin/team/invite",
        headers=headers,
        json={"email": "someone@example.com", "system_key": "support"},
    )
    assert res.status_code == 403


def test_custom_role_can_be_created(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    db_session.commit()

    headers, email = _register(client, prefix="role-admin", name="Role Admin")
    assign_role(email, "super_admin")

    created = client.post(
        "/api/v1/admin/team/roles",
        headers=headers,
        json={
            "name": "Event Support",
            "description": "Tickets and appeals only",
            "permission_codes": [
                "admin.users.view",
                "events.review",
                "support.reply",
                "admin.appeals.review",
            ],
        },
    )
    assert created.status_code == 201, created.text
    role = created.json()
    assert role["name"] == "Event Support"
    assert "support.reply" in role["permission_codes"]
    assert "payments.view" not in role["permission_codes"]
    assert role["is_system"] is False


def test_custom_role_permissions_can_be_toggled_and_archived(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    db_session.commit()

    headers, email = _register(client, prefix="role-edit", name="Role Editor")
    assign_role(email, "super_admin")

    created = client.post(
        "/api/v1/admin/team/roles",
        headers=headers,
        json={
            "name": "Toggle Desk",
            "permission_codes": ["admin.users.view", "support.reply"],
        },
    )
    assert created.status_code == 201, created.text
    role_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/admin/team/roles/{role_id}",
        headers=headers,
        json={
            "permission_codes": [
                "admin.users.view",
                "support.reply",
                "events.review",
            ],
        },
    )
    assert updated.status_code == 200, updated.text
    codes = updated.json()["permission_codes"]
    assert "events.review" in codes
    assert "payments.view" not in codes

    # Untick support.reply
    trimmed = client.patch(
        f"/api/v1/admin/team/roles/{role_id}",
        headers=headers,
        json={"permission_codes": ["admin.users.view", "events.review"]},
    )
    assert trimmed.status_code == 200, trimmed.text
    assert "support.reply" not in trimmed.json()["permission_codes"]

    # System roles cannot be edited
    roles = client.get("/api/v1/admin/team/roles", headers=headers)
    support = next(r for r in roles.json()["roles"] if r["system_key"] == "support")
    blocked = client.patch(
        f"/api/v1/admin/team/roles/{support['id']}",
        headers=headers,
        json={"permission_codes": ["admin.users.view"]},
    )
    assert blocked.status_code == 403

    archived = client.post(
        f"/api/v1/admin/team/roles/{role_id}/archive",
        headers=headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived_at"] is not None

    listed = client.get("/api/v1/admin/team/roles", headers=headers)
    assert listed.status_code == 200
    assert all(r["id"] != role_id for r in listed.json()["roles"])


def test_permissions_enforced_and_support_cannot_access_finance(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    db_session.commit()

    _headers, email = _register(client, prefix="fin-gate", name="Support")
    assign_role(email, "support_agent")
    user = get_user_by_email(db_session, email)
    assert user is not None
    assert not user_has_permission(user, "payments.view")
    assert not user_has_permission(user, "refunds.approve")
    assert not user_has_permission(user, "payouts.approve")


def test_finance_cannot_impersonate_by_default(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    _headers, email = _register(client, prefix="fin", name="Finance")
    assign_role(email, "finance_admin")
    user = get_user_by_email(db_session, email)
    assert user is not None
    assert not user_has_permission(user, "admin.users.impersonate")
    assert can_start_impersonation(user) is False


def test_disabled_team_member_cannot_access_admin(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    db_session.commit()

    sa_headers, sa_email = _register(client, prefix="sa2", name="Super")
    assign_role(sa_email, "super_admin")

    _, member_email = _register(client, prefix="to-disable", name="Soon Disabled")
    invite = client.post(
        "/api/v1/admin/team/invite",
        headers=sa_headers,
        json={"email": member_email, "system_key": "support"},
    )
    assert invite.status_code == 201, invite.text
    member_id = invite.json()["member"]["id"]

    disabled = client.post(
        f"/api/v1/admin/team/members/{member_id}/disable",
        headers=sa_headers,
        json={"reason": "offboarding"},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["status"] == "disabled"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": member_email, "password": "Password123!"},
    )
    assert login.status_code == 200, login.text
    fresh = {"Authorization": f"Bearer {login.json()['access_token']}"}

    blocked = client.get("/api/v1/admin/team", headers=fresh)
    assert blocked.status_code == 403

    user = get_user_by_email(db_session, member_email)
    assert user is not None
    db_session.refresh(user)
    assert "support_agent" not in {r.name for r in user.roles}


def test_audit_logs_created_on_role_change(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    db_session.commit()

    sa_headers, sa_email = _register(client, prefix="audit-sa", name="Super")
    assign_role(sa_email, "super_admin")
    _, target_email = _register(client, prefix="audit-target", name="Target")

    invite = client.post(
        "/api/v1/admin/team/invite",
        headers=sa_headers,
        json={"email": target_email, "system_key": "operations"},
    )
    assert invite.status_code == 201, invite.text
    member_id = invite.json()["member"]["id"]

    roles = client.get("/api/v1/admin/team/roles", headers=sa_headers)
    assert roles.status_code == 200, roles.text
    marketing = next(
        r for r in roles.json()["roles"] if r["system_key"] == "marketing"
    )

    patched = client.patch(
        f"/api/v1/admin/team/members/{member_id}",
        headers=sa_headers,
        json={"admin_role_id": marketing["id"]},
    )
    assert patched.status_code == 200, patched.text

    audits = (
        db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.action == "admin_team.member_update")
        .all()
    )
    assert len(audits) >= 1
