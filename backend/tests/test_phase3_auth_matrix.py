"""Phase 3 — authentication matrix for protected high-risk operations."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers.phase3_personas import (
    login_existing,
    register_persona,
    seed_host_with_event,
    seed_paid_order_with_ticket,
)


# Policy: 401 = missing/invalid auth; 403 = authenticated but forbidden; 404 = conceal.
DENY_UNAUTH = {401, 403}


def test_protected_endpoints_reject_anonymous(client: TestClient, db_session: Session, assign_role):
    fan = register_persona(client, email="p3-auth-fan@example.com", full_name="Auth Fan")
    _, host, event, tt = seed_host_with_event(
        db_session, email="p3-auth-host@example.com", slug_suffix="authh"
    )
    host_headers = login_existing(client, "p3-auth-host@example.com")
    from app.users.models import User

    buyer = db_session.query(User).filter_by(email=fan.email).one()
    order, ticket = seed_paid_order_with_ticket(
        db_session, buyer=buyer, event=event, ticket_type=tt
    )

    paths = [
        ("GET", f"/api/v1/orders/{order.id}"),
        ("GET", f"/api/v1/tickets/{ticket.id}"),
        ("GET", f"/api/v1/host/events/{event.id}/analytics/overview"),
        ("GET", "/api/v1/admin/audit-logs"),
        ("GET", "/api/v1/auth/me"),
        ("POST", f"/api/v1/orders/{order.id}/archive"),
    ]
    for method, path in paths:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code in DENY_UNAUTH, (path, resp.status_code, resp.text)


def test_malformed_and_invalid_bearer_rejected(client: TestClient, db_session: Session):
    _, _, event, _ = seed_host_with_event(
        db_session, email="p3-auth-bad@example.com", slug_suffix="authbad"
    )
    path = f"/api/v1/host/events/{event.id}/analytics/overview"
    for headers in (
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer not-a-jwt"},
        {"Authorization": "Token abc"},
        {"Authorization": f"Bearer {uuid4()}"},
    ):
        resp = client.get(path, headers=headers)
        assert resp.status_code in DENY_UNAUTH, (headers, resp.status_code, resp.text)


def test_disabled_account_cannot_use_token(client: TestClient, db_session: Session, assign_role):
    from app.users.models import User
    from uuid import UUID

    persona = register_persona(
        client, email="p3-disabled@example.com", full_name="Disabled User"
    )
    row = db_session.get(User, UUID(persona.user_id))
    assert row is not None
    row.is_active = False
    db_session.commit()

    me = client.get("/api/v1/auth/me", headers=persona.headers)
    assert me.status_code in {401, 403}, me.text


def test_valid_token_reaches_own_resources(client: TestClient, db_session: Session):
    fan = register_persona(client, email="p3-auth-ok@example.com", full_name="Ok Fan")
    me = client.get("/api/v1/auth/me", headers=fan.headers)
    assert me.status_code == 200
    assert me.json()["id"] == fan.user_id
