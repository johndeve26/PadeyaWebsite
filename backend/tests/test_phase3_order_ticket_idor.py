"""Phase 3 — order and ticket ownership / IDOR."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.users.models import User
from tests.helpers.phase3_personas import (
    login_existing,
    register_persona,
    seed_host_with_event,
    seed_paid_order_with_ticket,
)


def _two_buyers_one_order(client: TestClient, db: Session):
    fan_a = register_persona(client, email="p3-ord-a@example.com", full_name="Fan A")
    fan_b = register_persona(client, email="p3-ord-b@example.com", full_name="Fan B")
    _, host, event, tt = seed_host_with_event(
        db, email="p3-ord-host@example.com", slug_suffix="ordh"
    )
    host_b_user, host_b, event_b, tt_b = seed_host_with_event(
        db, email="p3-ord-host-b@example.com", slug_suffix="ordhb", title="Other Night"
    )
    buyer_a = db.query(User).filter_by(email=fan_a.email).one()
    order, ticket = seed_paid_order_with_ticket(
        db, buyer=buyer_a, event=event, ticket_type=tt
    )
    return fan_a, fan_b, order, ticket, host, event, host_b, event_b


def test_fan_a_reads_own_order_and_ticket(client: TestClient, db_session: Session):
    fan_a, _, order, ticket, *_ = _two_buyers_one_order(client, db_session)
    o = client.get(f"/api/v1/orders/{order.id}", headers=fan_a.headers)
    assert o.status_code == 200, o.text
    assert o.json()["id"] == str(order.id)

    t = client.get(f"/api/v1/tickets/{ticket.id}", headers=fan_a.headers)
    assert t.status_code == 200, t.text
    assert t.json()["id"] == str(ticket.id)


def test_fan_b_cannot_read_or_mutate_fan_a_order(client: TestClient, db_session: Session):
    fan_a, fan_b, order, ticket, *_ = _two_buyers_one_order(client, db_session)

    # Anti-enumeration: foreign order is concealed as 404.
    assert (
        client.get(f"/api/v1/orders/{order.id}", headers=fan_b.headers).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/orders/{order.id}/archive", headers=fan_b.headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/orders/{order.id}/resend-ticket-emails",
            headers=fan_b.headers,
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/tickets/{ticket.id}", headers=fan_b.headers).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/tickets/{ticket.id}/transfer",
            headers=fan_b.headers,
            json={"recipient_email": fan_b.email},
        ).status_code
        in {403, 404, 422}
    )


def test_random_uuid_order_and_ticket_do_not_leak(client: TestClient, db_session: Session):
    fan = register_persona(client, email="p3-ord-rand@example.com", full_name="Rand Fan")
    missing = uuid4()
    assert client.get(f"/api/v1/orders/{missing}", headers=fan.headers).status_code == 404
    assert client.get(f"/api/v1/tickets/{missing}", headers=fan.headers).status_code == 404
    assert client.get(f"/api/v1/orders/{missing}").status_code in {401, 403}


def test_unrelated_host_cannot_access_buyer_order(client: TestClient, db_session: Session):
    fan_a, _, order, ticket, *_rest = _two_buyers_one_order(client, db_session)
    host_b_headers = login_existing(client, "p3-ord-host-b@example.com")
    assert (
        client.get(f"/api/v1/orders/{order.id}", headers=host_b_headers).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/tickets/{ticket.id}", headers=host_b_headers).status_code
        == 404
    )


def test_anonymous_cannot_access_order_or_ticket(client: TestClient, db_session: Session):
    fan_a, _, order, ticket, *_ = _two_buyers_one_order(client, db_session)
    assert client.get(f"/api/v1/orders/{order.id}").status_code in {401, 403}
    assert client.get(f"/api/v1/tickets/{ticket.id}").status_code in {401, 403}
