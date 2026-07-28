"""Phase 9 — high-risk admin / finance / tenancy helpers."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers.phase3_personas import PASSWORD, Persona, register_persona


HIDDEN_EMAIL_SETTINGS = "/api/v1/admin/emails/settings"
HIDDEN_EMAIL_TEST_CONNECTION = "/api/v1/admin/emails/settings/test-connection"
HIDDEN_EMAIL_TEST_SEND = "/api/v1/admin/emails/settings/test-send"
HIDDEN_NOTIFICATION_SETTINGS = "/api/v1/admin/emails/settings/notifications"
HIDDEN_GO_LIVE = "/api/v1/admin/platform/go-live"


def persona_with_role(
    client: TestClient,
    assign_role,
    *,
    email: str,
    role: str,
    full_name: str | None = None,
) -> Persona:
    return register_persona(
        client,
        email=email,
        full_name=full_name or email.split("@")[0],
        assign_role=assign_role,
        role=role,
    )


def login_headers(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
