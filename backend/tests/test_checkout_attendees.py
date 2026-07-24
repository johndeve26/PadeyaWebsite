"""Checkout purchase modes: self, gift/other, group attendees, delivery safety."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.models import EmailEvent
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order
from app.payments.paystack import sign_body_for_tests
from app.tickets.models import Ticket, TicketQrToken
from app.users.models import User
from app.users.service import get_role_by_name


def _register_and_login(client: TestClient, email: str, name: str = "Buyer User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_event(db_session: Session, *, price: str = "5000.00", slug: str = "gift-night") -> tuple[Event, TicketType]:
    host_user = User(
        email=f"host-{slug}@example.com",
        password_hash="x",
        full_name="Event Host",
        is_active=True,
    )
    role = get_role_by_name(db_session, "host")
    assert role is not None
    host_user.roles.append(role)
    db_session.add(host_user)
    db_session.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Event Host",
        slug=f"host-{slug}",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Gift Night",
        slug=slug,
        description="Checkout attendee tests with enough detail for validation.",
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
        quantity=20,
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


def _pay_via_webhook(client: TestClient, order: dict) -> None:
    payload = {
        "event": "charge.success",
        "data": {
            "reference": order["reference"],
            "amount": int(Decimal(order["total_amount"]) * 100),
            "currency": "NGN",
            "id": 999001,
            "status": "success",
        },
    }
    body = json.dumps(payload).encode()
    sig = sign_body_for_tests(body)
    with patch("app.payments.webhook.send_ticket_email"):
        # Allow real send in some tests; default patch only when needed
        pass
    response = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "content-type": "application/json"},
    )
    assert response.status_code == 200, response.text


def test_buy_for_self_saves_attendee_from_buyer(client: TestClient, db_session: Session):
    event, ticket_type = _seed_event(db_session, slug="self-mode")
    headers = _register_and_login(client, "self-buyer@example.com", "Self Buyer")

    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "self",
            "attendee_name": "Self Buyer",
            "attendee_email": "self-buyer@example.com",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["purchase_mode"] == "self"
    assert body["is_gift"] is False
    assert len(body["attendees"]) == 1
    assert body["attendees"][0]["attendee_name"] == "Self Buyer"
    assert body["attendees"][0]["attendee_email"] == "self-buyer@example.com"


def test_buy_for_someone_else_fields_saved(client: TestClient, db_session: Session):
    event, ticket_type = _seed_event(db_session, slug="other-mode")
    headers = _register_and_login(client, "gifter@example.com", "Gifter")

    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "other",
            "recipient_name": "Ada Friend",
            "recipient_email": "ada.friend@example.com",
            "recipient_phone": "+2348012345678",
            "gift_message": "See you there!",
            "send_ticket_to_recipient": True,
            "keep_buyer_copy": True,
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 2}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["purchase_mode"] == "other"
    assert body["is_gift"] is True
    assert body["purchased_for_someone_else"] is True
    assert body["recipient_email"] == "ada.friend@example.com"
    assert body["gift_message"] == "See you there!"
    assert body["send_ticket_to_recipient"] is True
    assert body["keep_buyer_copy"] is True
    assert body["recipient_user_id"] is None if "recipient_user_id" in body else True
    assert len(body["attendees"]) == 2
    assert all(a["attendee_email"] == "ada.friend@example.com" for a in body["attendees"])

    order = db_session.get(Order, UUID(body["id"]))
    assert order is not None
    assert order.recipient_user_id is None  # never claim by email alone


def test_group_multi_attendees_saved(client: TestClient, db_session: Session):
    event, ticket_type = _seed_event(db_session, slug="group-mode")
    headers = _register_and_login(client, "group-buyer@example.com")

    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "group",
            "send_ticket_to_recipient": True,
            "keep_buyer_copy": True,
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 2}],
            "attendees": [
                {
                    "ticket_type_id": str(ticket_type.id),
                    "unit_index": 0,
                    "attendee_name": "Person One",
                    "attendee_email": "one@example.com",
                },
                {
                    "ticket_type_id": str(ticket_type.id),
                    "unit_index": 1,
                    "attendee_name": "Person Two",
                    "attendee_email": "two@example.com",
                    "attendee_phone": "+2348099990000",
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["purchase_mode"] == "group"
    assert len(body["attendees"]) == 2
    emails = {a["attendee_email"] for a in body["attendees"]}
    assert emails == {"one@example.com", "two@example.com"}


def test_no_qr_before_payment_confirmation(client: TestClient, db_session: Session):
    event, ticket_type = _seed_event(db_session, slug="pre-confirm", price="0.00")
    headers = _register_and_login(client, "pending@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "other",
            "recipient_name": "Pending Friend",
            "recipient_email": "pending.friend@example.com",
            "send_ticket_to_recipient": True,
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    order_id = UUID(order["id"])
    tickets = list(db_session.scalars(select(Ticket).where(Ticket.order_id == order_id)))
    assert tickets == []
    assert db_session.scalar(select(Ticket).where(Ticket.order_id == order_id)) is None


def test_gift_webhook_assigns_holder_and_emails(
    client: TestClient, db_session: Session
):
    event, ticket_type = _seed_event(db_session, slug="gift-webhook")
    headers = _register_and_login(client, "webhook-gifter@example.com", "Webhook Gifter")

    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "other",
            "recipient_name": "Gift Recipient",
            "recipient_email": "gift.recipient@example.com",
            "gift_message": "Enjoy!",
            "send_ticket_to_recipient": True,
            "keep_buyer_copy": True,
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
        checkout = client.post(
            f"/api/v1/payments/checkout/{order['id']}",
            headers=headers,
        )
    assert checkout.status_code == 200, checkout.text

    payload = {
        "event": "charge.success",
        "data": {
            "reference": order["reference"],
            "amount": int(Decimal(order["total_amount"]) * 100),
            "currency": "NGN",
            "id": 424242,
            "status": "success",
        },
    }
    body = json.dumps(payload).encode()
    sig = sign_body_for_tests(body)
    wh = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "content-type": "application/json"},
    )
    assert wh.status_code == 200, wh.text

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1
    assert tickets[0].holder_name == "Gift Recipient"
    assert tickets[0].holder_email == "gift.recipient@example.com"
    assert tickets[0].is_gift is True
    assert tickets[0].buyer_user_id is not None
    assert tickets[0].recipient_user_id is None
    assert tickets[0].qr_token is not None or db_session.scalar(
        select(TicketQrToken).where(TicketQrToken.ticket_id == tickets[0].id)
    )

    emails = list(
        db_session.scalars(
            select(EmailEvent).where(
                EmailEvent.template.in_(("ticket_confirmed", "ticket_gift_received"))
            )
        )
    )
    templates = {e.template for e in emails}
    assert "ticket_confirmed" in templates
    assert "ticket_gift_received" in templates
    gift_mail = next(e for e in emails if e.template == "ticket_gift_received")
    assert gift_mail.recipient_email == "gift.recipient@example.com"
    assert gift_mail.recipient_user_id is None


def test_free_order_confirm_issues_gift_tickets(
    client: TestClient, db_session: Session
):
    event, ticket_type = _seed_event(db_session, slug="free-gift", price="0.00")
    headers = _register_and_login(client, "free-gifter@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "other",
            "recipient_name": "Free Friend",
            "recipient_email": "free.friend@example.com",
            "send_ticket_to_recipient": True,
            "keep_buyer_copy": False,
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()
    assert order["total_amount"] == "0.00"

    checkout = client.post(
        f"/api/v1/payments/checkout/{order['id']}",
        headers=headers,
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["free_checkout"] is True

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1
    assert tickets[0].holder_email == "free.friend@example.com"


def test_own_host_still_blocked_with_gift_mode(
    client: TestClient, db_session: Session
):
    event, ticket_type = _seed_event(db_session, slug="own-host-gift")
    host = db_session.get(Host, event.host_id)
    assert host is not None
    owner = db_session.get(User, host.user_id)
    assert owner is not None
    # Give owner a password login path via register-like token is hard; use API as owner
    # by setting password through login after forcing known password is awkward —
    # reuse host-as-fan pattern: login as host email after registering fails.
    # Instead patch assert won't be needed — register a new buyer who owns the host:
    # The host user was created without auth password. Create order as that user via
    # direct service is out of scope; use existing test_host_as_fan for owner block.
    # Here verify gift payload does not bypass for a random user buying own... skip
    # if we can't auth as host. Create login by updating password_hash.
    from app.core.security import hash_password

    owner.password_hash = hash_password("securepass1")
    owner.email = "own-host-buyer@example.com"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "own-host-buyer@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "other",
            "recipient_name": "Someone Else",
            "recipient_email": "someone@example.com",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert response.status_code == 403, response.text


def test_invalid_recipient_email_rejected(client: TestClient, db_session: Session):
    event, ticket_type = _seed_event(db_session, slug="bad-email")
    headers = _register_and_login(client, "bad-email-buyer@example.com")

    response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "purchase_mode": "other",
            "recipient_name": "No Email",
            "recipient_email": "not-an-email",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert response.status_code == 400, response.text
