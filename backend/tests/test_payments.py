"""Order, checkout, webhook, and ticket issuance tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event, EventCategory, EventCheckoutQuestion, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.payments.service import normalize_order_reference
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import get_role_by_name


def test_normalize_order_reference():
    assert normalize_order_reference("  pdy-abc123  ") == "PDY-ABC123"
    assert normalize_order_reference("PDY-A940B8FDCBEAC920") == "PDY-A940B8FDCBEAC920"


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Buyer User"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_published_event(db_session: Session, *, price: str = "5000.00", qty: int = 10) -> tuple[Event, TicketType]:
    host_user = User(
        email="eventhost@example.com",
        password_hash="x",
        full_name="Event Host",
        is_active=True,
    )
    role = get_role_by_name(db_session, "host")
    assert role is not None
    host_user.roles.append(role)
    db_session.add(host_user)
    db_session.flush()

    host = Host(user_id=host_user.id, display_name="Event Host", slug="event-host", status="active")
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Paid Night",
        slug="paid-night",
        description="A published event for checkout tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=5),
        venue_name="Arena",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()

    ticket_type = TicketType(
        event_id=event.id,
        name="Regular",
        type="regular",
        description="GA",
        price=Decimal(price),
        quantity=qty,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db_session.add(ticket_type)
    db_session.commit()
    db_session.refresh(event)
    db_session.refresh(ticket_type)
    return event, ticket_type


def test_order_creation(client: TestClient, db_session: Session):
    event, ticket_type = _seed_published_event(db_session)
    headers = _register_and_login(client, "buyer1@example.com")

    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 2}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["total_amount"] == "10000.00"
    assert len(body["items"]) == 1

    db_session.refresh(ticket_type)
    assert ticket_type.quantity_reserved == 2


def test_checkout_initialization(client: TestClient, db_session: Session):
    event, ticket_type = _seed_published_event(db_session)
    headers = _register_and_login(client, "buyer2@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        response = client.post(
            f"/api/v1/payments/checkout/{order['id']}",
            headers=headers,
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["authorization_url"] == "https://checkout.paystack.com/test"
    assert body["free_checkout"] is False
    assert body["reference"] == order["reference"]


def test_checkout_confirm_verifies_paystack_without_webhook(
    client: TestClient, db_session: Session
):
    event, ticket_type = _seed_published_event(db_session)
    headers = _register_and_login(client, "buyer-confirm@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)

    verify_data = {
        "id": 777003,
        "reference": order["reference"],
        "amount": 500000,
        "status": "success",
    }
    with patch(
        "app.payments.service.verify_transaction",
        return_value=verify_data,
    ):
        confirm = client.post(
            f"/api/v1/payments/checkout/{order['id']}/confirm",
            headers=headers,
        )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "paid"

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1

    with patch(
        "app.payments.service.verify_transaction",
        return_value=verify_data,
    ):
        again = client.post(
            f"/api/v1/payments/checkout/{order['id']}/confirm",
            headers=headers,
        )
    assert again.status_code == 200
    assert again.json()["status"] == "paid"
    tickets_after = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets_after) == 1


def test_webhook_verification_and_ticket_generation(client: TestClient, db_session: Session):
    event, ticket_type = _seed_published_event(db_session)
    headers = _register_and_login(client, "buyer3@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 2}],
        },
    ).json()

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)

    payload = {
        "event": "charge.success",
        "data": {
            "id": 999001,
            "reference": order["reference"],
            "amount": 1000000,
            "status": "success",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    signature = sign_body_for_tests(body)

    # Invalid signature rejected
    bad = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": "invalid", "content-type": "application/json"},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": signature, "content-type": "application/json"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "ok"

    tickets = list(
        db_session.scalars(
            select(Ticket)
            .where(Ticket.order_id == UUID(order["id"]))
            .options(selectinload(Ticket.qr_token))
        )
    )
    assert len(tickets) == 2
    assert all(t.status == "active" for t in tickets)
    assert all(t.qr_token is not None for t in tickets)
    assert "PDY-" in tickets[0].public_code

    # Buyer can fetch tickets with QR
    mine = client.get("/api/v1/tickets/mine", headers=headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 2
    card = mine.json()[0]
    assert card.get("event_title")
    assert card.get("event_starts_at")
    assert "location_label" in card
    assert "address" not in card
    assert card.get("qr_payload") in (None, "")
    detail = client.get(f"/api/v1/tickets/{tickets[0].id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["qr_payload"]


def test_idempotent_webhook_and_duplicate_protection(client: TestClient, db_session: Session):
    event, ticket_type = _seed_published_event(db_session, price="1000.00")
    headers = _register_and_login(client, "buyer4@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)

    payload = {
        "event": "charge.success",
        "data": {
            "id": 888002,
            "reference": order["reference"],
            "amount": 100000,
            "status": "success",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    signature = sign_body_for_tests(body)
    headers_wh = {"x-paystack-signature": signature, "content-type": "application/json"}

    first = client.post("/api/v1/payments/webhooks/paystack", content=body, headers=headers_wh)
    second = client.post("/api/v1/payments/webhooks/paystack", content=body, headers=headers_wh)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1

    db_session.refresh(ticket_type)
    assert ticket_type.quantity_sold == 1
    assert ticket_type.quantity_reserved == 0


def test_free_checkout_issues_tickets_server_side(client: TestClient, db_session: Session):
    event, ticket_type = _seed_published_event(db_session, price="0.00")
    headers = _register_and_login(client, "buyer5@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    response = client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["free_checkout"] is True

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1


def test_order_without_checkout_questions_unchanged(client: TestClient, db_session: Session):
    event, ticket_type = _seed_published_event(db_session)
    headers = _register_and_login(client, "buyer-no-q@example.com")
    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["checkout_answers"] == []


def test_required_checkout_answer_enforced_and_stored(
    client: TestClient, db_session: Session
):
    event, ticket_type = _seed_published_event(db_session)
    question = EventCheckoutQuestion(
        event_id=event.id,
        label="WhatsApp number",
        type="phone",
        required=True,
        help_text="Include country code",
        sort_order=0,
    )
    optional = EventCheckoutQuestion(
        event_id=event.id,
        label="Meal preference",
        type="dropdown",
        required=False,
        options=["Vegan", "Meat"],
        sort_order=1,
    )
    db_session.add_all([question, optional])
    db_session.commit()
    db_session.refresh(question)

    headers = _register_and_login(client, "buyer-q@example.com")
    missing = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert missing.status_code == 400
    assert "WhatsApp" in missing.json()["detail"]

    ok = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
            "checkout_answers": [
                {"question_id": str(question.id), "value": "+2348012345678"},
                {"question_id": str(optional.id), "value": "Vegan"},
            ],
        },
    )
    assert ok.status_code == 201, ok.text
    answers = ok.json()["checkout_answers"]
    assert len(answers) == 2
    by_label = {a["question_label"]: a["value"] for a in answers}
    assert by_label["WhatsApp number"] == "+2348012345678"
    assert by_label["Meal preference"] == "Vegan"
