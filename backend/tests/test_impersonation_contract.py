"""Contract checks for impersonation API shapes (8B)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth(client: TestClient, email: str, name: str = "User") -> dict:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return login.json()


def test_impersonation_endpoint_contract(client: TestClient, assign_role):
    target = _auth(client, "imp-contract-target@example.com", "Target")
    target_id = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {target['access_token']}"},
    ).json()["id"]

    admin = _auth(client, "imp-contract-admin@example.com", "Admin")
    assign_role("imp-contract-admin@example.com", "super_admin")
    admin_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "imp-contract-admin@example.com",
            "password": "securepass1",
        },
    ).json()
    admin_h = {"Authorization": f"Bearer {admin_login['access_token']}"}

    idle = client.get("/api/v1/me/impersonation", headers=admin_h)
    assert idle.status_code == 200
    assert idle.json()["is_impersonating"] is False

    started = client.post(
        f"/api/v1/admin/users/{target_id}/impersonation/start",
        headers=admin_h,
        json={
            "reason": "Support QA for checkout screen",
            "support_ticket_id": "SUP-42",
            "duration_minutes": 30,
        },
    )
    assert started.status_code == 200, started.text
    body = started.json()
    # Product contract fields
    assert set(body.keys()) >= {
        "impersonation_id",
        "target_user_id",
        "expires_at",
        "redirect_to",
    }
    assert body["target_user_id"] == target_id
    assert body["redirect_to"] == "/dashboard"
    # Client session token (separate audited impersonation JWT — not the user's password)
    assert body["access_token"]
    assert "refresh_token" not in body
    assert "password" not in body

    imp_h = {"Authorization": f"Bearer {body['access_token']}"}
    status = client.get("/api/v1/me/impersonation", headers=imp_h)
    assert status.status_code == 200
    assert status.json()["is_impersonating"] is True
    assert status.json()["impersonation_id"] == body["impersonation_id"]
    assert status.json()["target_user_id"] == target_id

    ended = client.post("/api/v1/admin/impersonation/end", headers=imp_h)
    assert ended.status_code == 200, ended.text
    end_body = ended.json()
    assert end_body == {
        "ended": True,
        "return_to": f"/admin/users/{target_id}",
    }
