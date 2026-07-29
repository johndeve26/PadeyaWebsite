"""Shared helpers for Phase 4 payment-integrity tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.users.models import User
from app.users.service import get_role_by_name


def register_and_login(client: TestClient, email: str) -> dict[str, str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Buyer User", "gender": "prefer_not_to_say"},
    )
    assert reg.status_code in {200, 201, 409}, reg.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    token = login.json().get("access_token")
    assert token, login.text
    return {"Authorization": f"Bearer {token}"}


def seed_published_event(
    db_session: Session,
    *,
    price: str = "5000.00",
    qty: int = 10,
    slug: str | None = None,
    host_email: str | None = None,
) -> tuple[Event, TicketType]:
    suffix = uuid4().hex[:8]
    host_user = User(
        email=host_email or f"eventhost-{suffix}@example.com",
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
        slug=f"event-host-{suffix}",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Paid Night",
        slug=slug or f"paid-night-{suffix}",
        description="A published event for Phase 4 payment integrity tests with enough detail.",
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


def create_pending_order(
    client: TestClient,
    headers: dict[str, str],
    *,
    event_id: str,
    ticket_type_id: str,
    quantity: int = 1,
) -> dict[str, Any]:
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": event_id,
            "items": [{"ticket_type_id": ticket_type_id, "quantity": quantity}],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    from unittest.mock import patch

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": body["reference"],
        },
    ):
        checkout = client.post(f"/api/v1/payments/checkout/{body['id']}", headers=headers)
    assert checkout.status_code == 200, checkout.text
    return body


def charge_success_payload(
    *,
    reference: str,
    amount_kobo: int,
    event_id: int = 424242,
    currency: str = "NGN",
    status: str = "success",
    include_amount: bool = True,
    include_currency: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": event_id,
        "reference": reference,
        "status": status,
    }
    if include_amount:
        data["amount"] = amount_kobo
    if include_currency:
        data["currency"] = currency
    return {"event": "charge.success", "data": data}


def post_signed_webhook(
    client: TestClient,
    payload: dict[str, Any],
    *,
    signature: str | None = None,
    secret: str | None = None,
) -> Any:
    body = json.dumps(payload).encode("utf-8")
    sig = signature if signature is not None else sign_body_for_tests(body, secret=secret)
    headers = {"content-type": "application/json"}
    if sig is not None:
        headers["x-paystack-signature"] = sig
    return client.post("/api/v1/payments/webhooks/paystack", content=body, headers=headers)


def expected_kobo(total_amount: Decimal | str | float | int) -> int:
    return int(Decimal(str(total_amount)) * 100)
