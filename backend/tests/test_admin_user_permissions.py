"""Admin user management permission matrix (MVP)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.users.service import (
    get_permission_by_code,
    get_role_by_name,
    user_has_permission,
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


def test_support_agent_default_user_perms(db_session: Session):
    role = get_role_by_name(db_session, "support_agent")
    assert role is not None
    codes = {p.code for p in role.permissions}
    assert "admin.users.view" in codes
    assert "admin.users.add_note" in codes
    assert "admin.users.flag" not in codes
    assert "admin.users.suspend" not in codes
    assert "admin.users.force_logout" not in codes
    assert "users.read" not in codes


def test_finance_admin_no_user_management_by_default(db_session: Session):
    role = get_role_by_name(db_session, "finance_admin")
    assert role is not None
    codes = {p.code for p in role.permissions}
    assert not any(code.startswith("admin.users.") for code in codes)
    assert "users.read" not in codes


def test_admin_users_view_implies_activity_and_audit():
    class _Perm:
        def __init__(self, code: str) -> None:
            self.code = code

    class _Role:
        name = "support_agent"
        permissions = [_Perm("admin.users.view")]

    class _User:
        roles = [_Role()]

    user = _User()
    assert user_has_permission(user, "admin.users.view")  # type: ignore[arg-type]
    assert user_has_permission(user, "admin.users.view_activity")  # type: ignore[arg-type]
    assert user_has_permission(user, "admin.users.view_audit")  # type: ignore[arg-type]
    assert not user_has_permission(user, "admin.users.view_private_contact")  # type: ignore[arg-type]
    assert not user_has_permission(user, "admin.users.add_note")  # type: ignore[arg-type]


def test_support_can_view_and_note_but_not_flag(
    client: TestClient, assign_role
):
    target_h = _auth(client, "target-perm@example.com", "Target")
    target_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    support_email = "support-users@example.com"
    _auth(client, support_email, "Support")
    assign_role(support_email, "support_agent")
    token = _relogin(client, support_email)

    list_resp = client.get("/api/v1/admin/users", headers=token)
    assert list_resp.status_code == 200, list_resp.text

    note_resp = client.post(
        f"/api/v1/admin/users/{target_id}/notes",
        headers=token,
        json={"note_type": "general", "body": "Support follow-up note"},
    )
    assert note_resp.status_code == 200, note_resp.text

    flag_resp = client.post(
        f"/api/v1/admin/users/{target_id}/flags",
        headers=token,
        json={
            "flag_type": "manual_watchlist",
            "severity": "medium",
            "reason": "Should be forbidden for default support",
        },
    )
    assert flag_resp.status_code == 403

    suspend_resp = client.post(
        f"/api/v1/admin/users/{target_id}/status",
        headers=token,
        json={"status": "suspended", "reason": "Should be forbidden"},
    )
    assert suspend_resp.status_code == 403


def test_finance_cannot_access_user_directory(client: TestClient, assign_role):
    email = "finance-nousers@example.com"
    _auth(client, email, "Finance")
    assign_role(email, "finance_admin")
    token = _relogin(client, email)

    resp = client.get("/api/v1/admin/users", headers=token)
    assert resp.status_code == 403


def test_explicit_flag_grant_allows_support_flag(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "target-flag@example.com", "Target")
    target_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    support_email = "support-flag@example.com"
    _auth(client, support_email, "Support Flag")
    assign_role(support_email, "support_agent")
    role = get_role_by_name(db_session, "support_agent")
    assert role is not None
    perm = get_permission_by_code(db_session, "admin.users.flag")
    assert perm is not None
    if perm not in role.permissions:
        role.permissions.append(perm)
        db_session.commit()

    token = _relogin(client, support_email)
    flag_resp = client.post(
        f"/api/v1/admin/users/{target_id}/flags",
        headers=token,
        json={
            "flag_type": "manual_watchlist",
            "severity": "low",
            "reason": "Granted flag permission",
        },
    )
    assert flag_resp.status_code == 200, flag_resp.text
