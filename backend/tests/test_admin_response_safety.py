"""Admin user API response safety — never leak secrets."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.users.admin_response_safety import (
    FORBIDDEN_ADMIN_USER_KEYS,
    assert_admin_user_payload_safe,
    find_forbidden_admin_user_keys,
    mask_email,
    scrub_admin_user_payload,
)


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


def test_scrub_drops_forbidden_keys_keeps_safe_fields():
    dirty = {
        "id": "u1",
        "email_masked": "ab•••@example.com",
        "password": "secret",
        "password_hash": "hash",
        "hashed_password": "hash2",
        "access_token": "tok",
        "refresh_token": "rtok",
        "reset_token": "reset",
        "email_verification_token": "ev",
        "session_token": "st",
        "oauth_token": "oauth",
        "2fa_secret": "otp",
        "qr_payload": "qr",
        "qr_secret": "qrs",
        "ticket_qr_secret": "tqr",
        "merch_pickup_token": "pickup",
        "paystack_raw_payload": {"x": 1},
        "payment_provider_secret": "sk",
        "private_message_body": "hi",
        "message_body": "msg",
        "account": {
            "phone_masked": "•••1234",
            "phone_available": True,
            "two_factor_status": "not_implemented",
            "totp_secret": "should-drop",
        },
        "activity": {"tickets_count": 3, "orders_count": 1},
        "status": "active",
        "configured": True,
        "last_four": "4242",
        "created_at": "2026-07-20T00:00:00Z",
        "moderation": {
            "internal_notes": [{"body": "admin-only note is allowed", "note_type": "support"}]
        },
    }
    clean = scrub_admin_user_payload(dirty)
    assert_admin_user_payload_safe(clean)
    assert "password" not in clean
    assert "password_hash" not in clean
    assert "access_token" not in clean
    assert "totp_secret" not in clean["account"]
    assert clean["email_masked"] == "ab•••@example.com"
    assert clean["account"]["phone_masked"] == "•••1234"
    assert clean["activity"]["tickets_count"] == 3
    assert clean["moderation"]["internal_notes"][0]["body"] == "admin-only note is allowed"
    assert find_forbidden_admin_user_keys(clean) == []
    assert "password" in FORBIDDEN_ADMIN_USER_KEYS
    assert mask_email("buyer@example.com").startswith("bu•••@")


def test_admin_user_endpoints_never_leak_secrets(client: TestClient, assign_role):
    target_h = _auth(client, "safe-target@example.com", "Safe Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    admin_email = "safe-admin@example.com"
    _auth(client, admin_email, "Safe Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    client.post(
        f"/api/v1/admin/users/{user_id}/notes",
        headers=admin,
        json={"note_type": "support", "body": "Safe internal note text"},
    )
    client.post(
        f"/api/v1/admin/users/{user_id}/flags",
        headers=admin,
        json={
            "flag_type": "spam",
            "severity": "low",
            "reason": "Noise only",
        },
    )

    for path in (
        "/api/v1/admin/users",
        f"/api/v1/admin/users/{user_id}",
        f"/api/v1/admin/users/{user_id}/activity",
        f"/api/v1/admin/users/{user_id}/audit",
        f"/api/v1/admin/users/{user_id}/notes",
    ):
        res = client.get(path, headers=admin)
        assert res.status_code == 200, path
        assert_admin_user_payload_safe(res.json())

    detail = client.get(f"/api/v1/admin/users/{user_id}", headers=admin).json()
    assert "email_masked" in detail
    assert "•••@" in detail["email_masked"]
    assert detail["account"]["phone_available"] is False
    assert detail["account"]["phone_masked"] is None
    assert "tickets_count" in detail["activity"]
    assert detail["account"]["two_factor_status"] == "not_implemented"

    # Sensitive action responses also stay scrubbed
    logout = client.post(
        f"/api/v1/admin/users/{user_id}/force-logout",
        headers=admin,
        json={"reason": "Safety check logout"},
    )
    assert logout.status_code == 200
    assert_admin_user_payload_safe(logout.json())
    assert "token" not in logout.json()

    reset = client.post(
        f"/api/v1/admin/users/{user_id}/force-password-reset",
        headers=admin,
        json={"reason": "Safety check reset"},
    )
    assert reset.status_code == 200
    assert_admin_user_payload_safe(reset.json())
    assert "reset_token" not in reset.json()
    assert "access_token" not in reset.json()
