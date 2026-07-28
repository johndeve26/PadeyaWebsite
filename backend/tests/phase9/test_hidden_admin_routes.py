"""Phase 9 — hidden admin routes auth + secret redaction."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.phase9.helpers import (
    HIDDEN_EMAIL_SETTINGS,
    HIDDEN_EMAIL_TEST_CONNECTION,
    HIDDEN_EMAIL_TEST_SEND,
    HIDDEN_GO_LIVE,
    HIDDEN_NOTIFICATION_SETTINGS,
    persona_with_role,
)

SECRET_MARKERS = (
    "smtp_password",
    "password",
    "secret_key",
    "api_key",
    "access_key",
    "webhook_secret",
    "database_url",
)


def _assert_no_usable_secrets(payload: object) -> None:
    text = str(payload).lower()
    # Masked hints like smtp_password_configured / last4 are OK; raw field keys in JSON bodies are not.
    if isinstance(payload, dict):
        assert "smtp_password" not in payload
        assert "smtp_password_encrypted" not in payload
        for key in ("r2_secret_access_key", "paystack_secret_key", "secret_key"):
            assert key not in payload
        for v in payload.values():
            if isinstance(v, (dict, list)):
                _assert_no_usable_secrets(v)
        return
    if isinstance(payload, list):
        for item in payload:
            _assert_no_usable_secrets(item)
        return
    for marker in ("sk_live_", "sk_test_", "whsec_"):
        assert marker not in text


def test_hidden_admin_routes_anonymous_rejected(client: TestClient):
    for method, path in [
        ("GET", HIDDEN_EMAIL_SETTINGS),
        ("PATCH", HIDDEN_EMAIL_SETTINGS),
        ("POST", HIDDEN_EMAIL_TEST_CONNECTION),
        ("POST", HIDDEN_EMAIL_TEST_SEND),
        ("GET", HIDDEN_NOTIFICATION_SETTINGS),
        ("PATCH", HIDDEN_NOTIFICATION_SETTINGS),
        ("GET", HIDDEN_GO_LIVE),
    ]:
        res = client.request(method, path, json={} if method in {"PATCH", "POST"} else None)
        assert res.status_code in {401, 403}, (method, path, res.status_code, res.text)


def test_hidden_email_settings_require_full_access_not_lower_admins(
    client: TestClient, assign_role
):
    fan = persona_with_role(
        client, assign_role, email=f"fan-{uuid4().hex[:8]}@example.com", role="buyer"
    )
    host = persona_with_role(
        client, assign_role, email=f"host-{uuid4().hex[:8]}@example.com", role="host"
    )
    support = persona_with_role(
        client,
        assign_role,
        email=f"support-{uuid4().hex[:8]}@example.com",
        role="support_agent",
    )
    finance = persona_with_role(
        client,
        assign_role,
        email=f"finance-{uuid4().hex[:8]}@example.com",
        role="finance_admin",
    )
    marketing = persona_with_role(
        client,
        assign_role,
        email=f"mkt-{uuid4().hex[:8]}@example.com",
        role="marketing",
    )
    operations = persona_with_role(
        client,
        assign_role,
        email=f"ops-{uuid4().hex[:8]}@example.com",
        role="operations",
    )
    super_admin = persona_with_role(
        client,
        assign_role,
        email=f"sa-{uuid4().hex[:8]}@example.com",
        role="super_admin",
    )

    for persona in (fan, host, support, finance, marketing, operations):
        res = client.get(HIDDEN_EMAIL_SETTINGS, headers=persona.headers)
        assert res.status_code == 403, (persona.email, res.status_code, res.text)
        res = client.patch(
            HIDDEN_EMAIL_SETTINGS,
            headers=persona.headers,
            json={"email_enabled": True},
        )
        assert res.status_code == 403, (persona.email, res.status_code)

    ok = client.get(HIDDEN_EMAIL_SETTINGS, headers=super_admin.headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    _assert_no_usable_secrets(body)
    assert body.get("smtp_password_configured") in {True, False}
    assert "smtp_password" not in body


def test_hidden_email_test_routes_require_full_access(client: TestClient, assign_role):
    support = persona_with_role(
        client,
        assign_role,
        email=f"support-test-{uuid4().hex[:8]}@example.com",
        role="support_agent",
    )
    finance = persona_with_role(
        client,
        assign_role,
        email=f"finance-test-{uuid4().hex[:8]}@example.com",
        role="finance_admin",
    )
    super_admin = persona_with_role(
        client,
        assign_role,
        email=f"sa-test-{uuid4().hex[:8]}@example.com",
        role="super_admin",
    )

    for persona in (support, finance):
        assert (
            client.post(HIDDEN_EMAIL_TEST_CONNECTION, headers=persona.headers).status_code
            == 403
        )
        assert (
            client.post(
                HIDDEN_EMAIL_TEST_SEND,
                headers=persona.headers,
                json={"test_recipient_email": "probe@example.com"},
            ).status_code
            == 403
        )

    # Connection probe allowed for super_admin (provider may be log/dev in tests).
    conn = client.post(HIDDEN_EMAIL_TEST_CONNECTION, headers=super_admin.headers)
    assert conn.status_code in {200, 400}, conn.text
    _assert_no_usable_secrets(conn.json())

    send = client.post(
        HIDDEN_EMAIL_TEST_SEND,
        headers=super_admin.headers,
        json={"test_recipient_email": "probe@example.com"},
    )
    assert send.status_code in {200, 400}, send.text
    _assert_no_usable_secrets(send.json())
    assert "smtp_password" not in send.json()


def test_hidden_notification_settings_require_manage_settings(
    client: TestClient, assign_role
):
    support = persona_with_role(
        client,
        assign_role,
        email=f"support-notif-{uuid4().hex[:8]}@example.com",
        role="support_agent",
    )
    finance = persona_with_role(
        client,
        assign_role,
        email=f"finance-notif-{uuid4().hex[:8]}@example.com",
        role="finance_admin",
    )
    marketing = persona_with_role(
        client,
        assign_role,
        email=f"mkt-notif-{uuid4().hex[:8]}@example.com",
        role="marketing",
    )
    # marketing may or may not have manage_settings — assert finance/support denied;
    # admin role has manage_settings.
    admin = persona_with_role(
        client,
        assign_role,
        email=f"admin-notif-{uuid4().hex[:8]}@example.com",
        role="admin",
    )

    for persona in (support, finance):
        assert (
            client.get(HIDDEN_NOTIFICATION_SETTINGS, headers=persona.headers).status_code
            == 403
        )

    # marketing typically has notification send but not necessarily manage_settings
    mkt = client.get(HIDDEN_NOTIFICATION_SETTINGS, headers=marketing.headers)
    assert mkt.status_code in {200, 403}, mkt.text

    ok = client.get(HIDDEN_NOTIFICATION_SETTINGS, headers=admin.headers)
    assert ok.status_code == 200, ok.text
    _assert_no_usable_secrets(ok.json())


def test_hidden_go_live_requires_view_readiness(client: TestClient, assign_role):
    fan = persona_with_role(
        client, assign_role, email=f"fan-gl-{uuid4().hex[:8]}@example.com", role="buyer"
    )
    support = persona_with_role(
        client,
        assign_role,
        email=f"support-gl-{uuid4().hex[:8]}@example.com",
        role="support_agent",
    )
    finance = persona_with_role(
        client,
        assign_role,
        email=f"finance-gl-{uuid4().hex[:8]}@example.com",
        role="finance_admin",
    )
    super_admin = persona_with_role(
        client,
        assign_role,
        email=f"sa-gl-{uuid4().hex[:8]}@example.com",
        role="super_admin",
    )

    for persona in (fan, support, finance):
        res = client.get(HIDDEN_GO_LIVE, headers=persona.headers)
        assert res.status_code == 403, (persona.email, res.status_code, res.text)

    ok = client.get(HIDDEN_GO_LIVE, headers=super_admin.headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    _assert_no_usable_secrets(body)
    blob = str(body).lower()
    assert "postgresql://" not in blob
    assert "sk_live_" not in blob
