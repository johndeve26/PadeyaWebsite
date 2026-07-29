"""Guest checkout: pending order without login, webhook issuance, claim token."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token
from app.email.models import EmailEvent
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order
from app.payments.paystack import sign_body_for_tests
from app.tickets.models import Ticket, TicketQrToken
from app.users.models import User
from app.users.service import get_role_by_name


def _seed_event(db_session: Session, *, price: str = "3000.00", slug: str = "guest-night") -> tuple[Event, TicketType, Host]:
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
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title="Guest Night",
        slug=slug,
        description="Guest checkout coverage with enough detail for validation rules.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Hall",
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
        name="GA",
        type="regular",
        description="General",
        price=Decimal(price),
        quantity=30,
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
    return event, ticket_type, host


def test_guest_order_create_and_checkout_init(client: TestClient, db_session: Session):
    event, ticket_type, _host = _seed_event(db_session, slug="guest-init")

    response = client.post(
        "/api/v1/orders",
        json={
            "event_id": str(event.id),
            "guest_buyer_name": "Guest Buyer",
            "guest_buyer_email": "guest.buyer@example.com",
            "guest_buyer_phone": "+2348011112222",
            "purchase_mode": "self",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_guest_checkout"] is True
    assert body["guest_buyer_email"] == "guest.buyer@example.com"
    assert body["buyer_email"] == "guest.buyer@example.com"
    assert body["status"] == "pending"
    assert body.get("buyer_user_id") in (None, "") or "buyer_user_id" not in body

    order = db_session.get(Order, UUID(body["id"]))
    assert order is not None
    assert order.buyer_user_id is None
    assert order.is_guest_checkout is True

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/guest",
            "access_code": "GACCESS",
            "reference": body["reference"],
        },
    ):
        checkout = client.post(f"/api/v1/payments/checkout/{body['id']}")
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["authorization_url"]
    assert checkout.json()["free_checkout"] is False


def test_guest_buy_for_other_and_webhook(client: TestClient, db_session: Session):
    event, ticket_type, _host = _seed_event(db_session, slug="guest-gift")

    order = client.post(
        "/api/v1/orders",
        json={
            "event_id": str(event.id),
            "guest_buyer_name": "Gift Guest",
            "guest_buyer_email": "gift.guest@example.com",
            "purchase_mode": "other",
            "recipient_name": "Ada Recipient",
            "recipient_email": "ada.guest@example.com",
            "send_ticket_to_recipient": True,
            "keep_buyer_copy": True,
            "gift_message": "Enjoy!",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    assert client.get(f"/api/v1/tickets/mine").status_code in (401, 403)
    assert (
        db_session.scalar(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
        is None
    )

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/guest",
            "access_code": "GACCESS",
            "reference": order["reference"],
        },
    ):
        assert (
            client.post(f"/api/v1/payments/checkout/{order['id']}").status_code == 200
        )

    payload = {
        "event": "charge.success",
        "data": {
            "reference": order["reference"],
            "amount": int(Decimal(order["total_amount"]) * 100),
            "currency": "NGN",
            "id": 777001,
            "status": "success",
        },
    }
    body = json.dumps(payload).encode()
    wh = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={
            "x-paystack-signature": sign_body_for_tests(body),
            "content-type": "application/json",
        },
    )
    assert wh.status_code == 200, wh.text

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1
    assert tickets[0].holder_email == "ada.guest@example.com"
    assert tickets[0].buyer_user_id is None
    assert db_session.scalar(
        select(TicketQrToken).where(TicketQrToken.ticket_id == tickets[0].id)
    )

    paid = db_session.get(Order, UUID(order["id"]))
    assert paid is not None
    assert paid.status == "paid"
    assert paid.claim_token_hash is not None

    emails = list(
        db_session.scalars(
            select(EmailEvent).where(
                EmailEvent.template.in_(
                    ("ticket_confirmed", "ticket_gift_received", "ticket_claim_link")
                )
            )
        )
    )
    templates = {e.template for e in emails}
    assert "ticket_confirmed" in templates
    assert "ticket_gift_received" in templates
    assert "ticket_claim_link" in templates

    # Idempotent webhook
    wh2 = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={
            "x-paystack-signature": sign_body_for_tests(body),
            "content-type": "application/json",
        },
    )
    assert wh2.status_code == 200
    assert (
        len(
            list(
                db_session.scalars(
                    select(Ticket).where(Ticket.order_id == UUID(order["id"]))
                )
            )
        )
        == 1
    )


def test_guest_claim_after_login(client: TestClient, db_session: Session):
    event, ticket_type, _host = _seed_event(db_session, slug="guest-claim", price="0.00")

    order = client.post(
        "/api/v1/orders",
        json={
            "event_id": str(event.id),
            "guest_buyer_name": "Claim Guest",
            "guest_buyer_email": "claim.guest@example.com",
            "purchase_mode": "self",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    checkout = client.post(f"/api/v1/payments/checkout/{order['id']}")
    assert checkout.status_code == 200
    assert checkout.json()["free_checkout"] is True

    paid = db_session.get(Order, UUID(order["id"]))
    assert paid is not None and paid.status == "paid"
    assert paid.claim_token_hash is not None

    # Recover raw token by re-issuing via start endpoint path is opaque;
    # set a known token for the claim API test.
    raw = "guest-claim-token-test-value-32chars!!"
    paid.claim_token_hash = hash_token(raw)
    db_session.commit()

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "claim.guest@example.com",
            "password": "securepass1",
            "full_name": "Claim Guest",
        "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "claim.guest@example.com", "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    from tests.helpers.email_verification import mark_user_email_verified

    mark_user_email_verified(db_session, email="claim.guest@example.com")

    claim = client.post(
        "/api/v1/orders/claim",
        headers=headers,
        json={"token": raw},
    )
    assert claim.status_code == 200, claim.text
    assert claim.json()["claimed"] is True

    db_session.refresh(paid)
    assert paid.buyer_user_id is not None
    assert paid.claimed_at is not None

    mine = client.get("/api/v1/tickets/mine", headers=headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1


def test_guest_claim_start_validates_reference_and_email(
    client: TestClient, db_session: Session
):
    event, ticket_type, _host = _seed_event(db_session, slug="guest-resend", price="0.00")
    order = client.post(
        "/api/v1/orders",
        json={
            "event_id": str(event.id),
            "guest_buyer_name": "Resend Guest",
            "guest_buyer_email": "resend.guest@example.com",
            "purchase_mode": "self",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()
    assert client.post(f"/api/v1/payments/checkout/{order['id']}").status_code == 200

    missing = client.post(
        "/api/v1/orders/claim/start",
        json={"order_reference": "PDY-DOESNOTEXIST", "email": "resend.guest@example.com"},
    )
    assert missing.status_code == 404
    assert "No order found" in missing.json()["detail"]

    wrong_email = client.post(
        "/api/v1/orders/claim/start",
        json={
            "order_reference": order["reference"].lower(),
            "email": "other@example.com",
        },
    )
    assert wrong_email.status_code == 400
    assert "doesn't match" in wrong_email.json()["detail"]

    ok = client.post(
        "/api/v1/orders/claim/start",
        json={
            "order_reference": f"  {order['reference']}  ",
            "email": "resend.guest@example.com",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "sent"
    assert "Claim link sent" in ok.json()["detail"]


def test_guest_claim_start_account_checkout_returns_on_account(
    client: TestClient, db_session: Session
):
    event, ticket_type, _host = _seed_event(db_session, slug="account-resend", price="0.00")
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "account.buyer@example.com",
            "password": "securepass1",
            "full_name": "Account Buyer",
        "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "account.buyer@example.com", "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()
    assert order["is_guest_checkout"] is False
    assert client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers).status_code == 200

    resp = client.post(
        "/api/v1/orders/claim/start",
        json={
            "order_reference": order["reference"],
            "email": "account.buyer@example.com",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "on_account"
    assert body["order_id"] == order["id"]


def test_guest_cannot_bypass_own_host_via_email(
    client: TestClient, db_session: Session
):
    event, ticket_type, host = _seed_event(db_session, slug="guest-own-host")
    owner = db_session.get(User, host.user_id)
    assert owner is not None
    owner.email = "owner-guest-bypass@example.com"
    owner.password_hash = hash_password("securepass1")
    db_session.commit()

    response = client.post(
        "/api/v1/orders",
        json={
            "event_id": str(event.id),
            "guest_buyer_name": "Owner Trying Guest",
            "guest_buyer_email": "owner-guest-bypass@example.com",
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert response.status_code == 403, response.text
