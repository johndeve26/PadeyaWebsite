"""Admin User Management MVP — list/search and safe field exposure."""

from __future__ import annotations

from fastapi.testclient import TestClient


from app.users.admin_response_safety import (
    FORBIDDEN_ADMIN_USER_KEYS,
    assert_admin_user_payload_safe,
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


SENSITIVE_KEYS = set(FORBIDDEN_ADMIN_USER_KEYS)


def _assert_no_sensitive_keys(payload: object) -> None:
    assert_admin_user_payload_safe(payload)


def test_admin_list_users_requires_permission(client: TestClient):
    buyer = _auth(client, "list-buyer@example.com", "Buyer")
    denied = client.get("/api/v1/users/admin", headers=buyer)
    assert denied.status_code == 403


def test_admin_list_users_search_filter_and_safe_fields(
    client: TestClient, assign_role
):
    _auth(client, "alpha.user@example.com", "Alpha User")
    _auth(client, "beta.host@example.com", "Beta Host")
    assign_role("beta.host@example.com", "host")

    admin_email = "users-list-admin@example.com"
    _auth(client, admin_email, "List Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    listed = client.get("/api/v1/users/admin", headers=admin)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert "items" in body
    assert body["total"] >= 3
    assert body["page"] == 1
    _assert_no_sensitive_keys(body)

    for row in body["items"]:
        assert "email" in row
        assert "full_name" in row
        assert "roles" in row
        assert "is_active" in row
        assert "permissions" not in row
        assert "password_hash" not in row

    search = client.get(
        "/api/v1/users/admin",
        headers=admin,
        params={"q": "alpha.user"},
    )
    assert search.status_code == 200
    search_body = search.json()
    assert search_body["total"] >= 1
    assert any("alpha.user" in row["email"] for row in search_body["items"])

    by_role = client.get(
        "/api/v1/users/admin",
        headers=admin,
        params={"role": "host"},
    )
    assert by_role.status_code == 200
    role_body = by_role.json()
    assert role_body["total"] >= 1
    assert all("host" in row["roles"] for row in role_body["items"])

    detail_id = search_body["items"][0]["id"]
    detail = client.get(f"/api/v1/users/admin/{detail_id}", headers=admin)
    assert detail.status_code == 200
    detail_body = detail.json()
    _assert_no_sensitive_keys(detail_body)
    assert "password_hash" not in detail_body
    assert "email_masked" in detail_body
    assert "•••@" in detail_body["email_masked"]
    assert detail_body["risk_level"] in {"low", "medium", "high"}
    assert "profile" in detail_body
    assert "account" in detail_body
    assert "activity" in detail_body
    assert "moderation" in detail_body
    assert "recent_audit" in detail_body
    assert "tickets_count" in detail_body["activity"]
    assert detail_body["account"]["auth_provider"] == "password"
    assert detail_body["account"]["two_factor_status"] == "not_implemented"
    assert detail_body["account"]["phone_available"] is False


def test_admin_deactivate_with_reason_and_status_filter(
    client: TestClient, assign_role
):
    user = _auth(client, "deactivate-me@example.com", "Deactivate Me")
    me = client.get("/api/v1/users/me", headers=user)
    user_id = me.json()["id"]

    admin_email = "users-deactivate-admin@example.com"
    _auth(client, admin_email, "Deactivate Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    deactivated = client.post(
        f"/api/v1/users/admin/{user_id}/deactivate",
        headers=admin,
        json={"reason": "Abuse report confirmed"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert deactivated.json()["deactivated_at"] is not None
    _assert_no_sensitive_keys(deactivated.json())

    inactive = client.get(
        "/api/v1/users/admin",
        headers=admin,
        params={"status": "inactive", "q": "deactivate-me"},
    )
    assert inactive.status_code == 200
    assert inactive.json()["total"] >= 1
    assert all(not row["is_active"] for row in inactive.json()["items"])

    restored = client.post(
        f"/api/v1/users/admin/{user_id}/restore",
        headers=admin,
        json={"reason": "False positive"},
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True
    assert restored.json()["deactivated_at"] is None


def test_admin_list_users_active_before_inactive(client: TestClient, assign_role):
    """Deactivated/inactive accounts sink below active ones (then created desc)."""
    active_h = _auth(client, "sort-active@example.com", "Sort Active")
    inactive_h = _auth(client, "sort-inactive@example.com", "Sort Inactive")
    active_id = client.get("/api/v1/users/me", headers=active_h).json()["id"]
    inactive_id = client.get("/api/v1/users/me", headers=inactive_h).json()["id"]

    admin_email = "users-sort-admin@example.com"
    _auth(client, admin_email, "Sort Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    deactivated = client.post(
        f"/api/v1/users/admin/{inactive_id}/deactivate",
        headers=admin,
        json={"reason": "Park inactive for sort test"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    listed = client.get(
        "/api/v1/admin/users",
        headers=admin,
        params={"q": "sort-", "limit": 40},
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    ids = [row["id"] for row in items]
    assert active_id in ids
    assert inactive_id in ids

    # Within this filtered page, every active row must appear before any inactive.
    seen_inactive = False
    for row in items:
        if not row["is_active"]:
            seen_inactive = True
        elif seen_inactive:
            raise AssertionError("Active user appeared after an inactive user")

    assert ids.index(active_id) < ids.index(inactive_id)
