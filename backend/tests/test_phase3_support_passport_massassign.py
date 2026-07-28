"""Phase 3 — support case IDOR, passport privacy, mass-assignment probes."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers.phase3_personas import register_persona


def test_support_case_owner_only(client: TestClient, assign_role):
    fan_a = register_persona(client, email="p3-sup-a@example.com", full_name="Sup A")
    fan_b = register_persona(client, email="p3-sup-b@example.com", full_name="Sup B")

    created = client.post(
        "/api/v1/support/cases",
        headers=fan_a.headers,
        json={
            "subject": "Phase3 case",
            "body": "Need help with my ticket order please.",
            "category": "tickets",
        },
    )
    # Some deployments may require slightly different payload keys.
    if created.status_code not in {200, 201}:
        created = client.post(
            "/api/v1/support/cases",
            headers=fan_a.headers,
            json={
                "subject": "Phase3 case",
                "message": "Need help with my ticket order please.",
                "category": "general",
            },
        )
    assert created.status_code in {200, 201}, created.text
    case_id = created.json()["id"]

    own = client.get(f"/api/v1/support/cases/{case_id}", headers=fan_a.headers)
    assert own.status_code == 200, own.text

    foreign = client.get(f"/api/v1/support/cases/{case_id}", headers=fan_b.headers)
    assert foreign.status_code in {403, 404}, foreign.text

    reply = client.post(
        f"/api/v1/support/cases/{case_id}/messages",
        headers=fan_b.headers,
        json={"body": "hijack"},
    )
    assert reply.status_code in {403, 404}, reply.text

    missing = client.get(f"/api/v1/support/cases/{uuid4()}", headers=fan_a.headers)
    assert missing.status_code == 404


def test_passport_private_not_visible_to_others(client: TestClient):
    owner = register_persona(
        client, email="p3-pass-owner@example.com", full_name="Pass Owner"
    )
    other = register_persona(
        client, email="p3-pass-other@example.com", full_name="Pass Other"
    )

    settings = client.patch(
        "/api/v1/passport/me/settings",
        headers=owner.headers,
        json={"visibility": "private"},
    )
    if settings.status_code == 404:
        client.post("/api/v1/passport/me", headers=owner.headers, json={})
        settings = client.patch(
            "/api/v1/passport/me/settings",
            headers=owner.headers,
            json={"visibility": "private"},
        )
    assert settings.status_code in {200, 201}, settings.text

    me = client.get("/api/v1/auth/me", headers=owner.headers).json()
    username = me.get("username") or me.get("passport_username")
    if not username:
        passport = client.get("/api/v1/passport/me", headers=owner.headers)
        assert passport.status_code == 200, passport.text
        username = passport.json().get("username") or passport.json().get("slug")
    assert username, me

    public = client.get(f"/api/v1/passport/public/{username}")
    assert public.status_code in {403, 404}, public.text

    other_view = client.get(
        f"/api/v1/passport/public/{username}", headers=other.headers
    )
    assert other_view.status_code in {403, 404}, other_view.text


def test_mass_assignment_ignores_role_and_owner_fields(client: TestClient, assign_role):
    fan = register_persona(client, email="p3-mass@example.com", full_name="Mass Fan")
    # Profile update must not accept privilege escalation fields.
    resp = client.patch(
        "/api/v1/users/me",
        headers=fan.headers,
        json={
            "full_name": "Mass Fan Updated",
            "role": "super_admin",
            "roles": ["super_admin"],
            "is_admin": True,
            "permissions": ["admin.full_access"],
            "user_id": str(uuid4()),
        },
    )
    # Either 200 ignoring extras, or 422 rejecting unknown fields — never escalate.
    assert resp.status_code in {200, 422}, resp.text
    me = client.get("/api/v1/auth/me", headers=fan.headers)
    assert me.status_code == 200
    body = me.json()
    roles = body.get("roles") or []
    perms = body.get("permissions") or []
    assert "super_admin" not in roles
    assert "admin.full_access" not in perms
