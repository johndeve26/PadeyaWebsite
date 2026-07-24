"""Phase 13 — Ambassadors must never see buyer/payment/venue/team secrets."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ambassadors.privacy import (
    FORBIDDEN_AMBASSADOR_KEYS,
    assert_ambassador_payload_safe,
    collect_forbidden_keys,
    sale_row_for_ambassador,
)
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _register(client: TestClient, email: str, name: str = "Buyer") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    return _login(client, email)


def _seed_open_event(db: Session) -> tuple[Host, Event, TicketType]:
    host_user = User(
        email=f"priv-amb-host-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Priv Amb Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Priv Amb Host",
        slug=f"priv-amb-host-{uuid4().hex[:8]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Privacy Amb Night",
        slug=f"privacy-amb-night-{uuid4().hex[:8]}",
        description="Event used for ambassador privacy tests.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        address="12 Hidden Street",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        open_ambassadors_enabled=True,
        open_ambassador_commission_percent=Decimal("8.00"),
    )
    db.add(event)
    db.flush()

    ga = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("5000.00"),
        quantity=100,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(ga)
    db.commit()
    return host, event, ga


def _pay_order(
    client: TestClient, order_id: str, reference: str, amount: str, buyer_email: str
):
    with patch("app.payments.service.initialize_transaction") as mock_init:
        mock_init.return_value = {
            "authorization_url": "https://paystack.test/pay",
            "access_code": "ACCESS",
            "reference": reference,
        }
        checkout = client.post(
            f"/api/v1/payments/checkout/{order_id}",
            headers=_login(client, buyer_email),
        )
        assert checkout.status_code == 200, checkout.text

    amount_kobo = int(Decimal(amount) * 100)
    body = json.dumps(
        {
            "event": "charge.success",
            "data": {
                "id": 991133,
                "reference": reference,
                "amount": amount_kobo,
                "status": "success",
            },
        }
    ).encode()
    response = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sign_body_for_tests(body)},
    )
    assert response.status_code == 200, response.text


def test_privacy_helpers_block_forbidden_keys():
    dirty = {
        "clicks": 3,
        "sales": [
            {
                "event_title": "X",
                "order_id": "should-not",
                "buyer_email": "x@y.com",
                "shipping_address": "12 Hidden",
            }
        ],
    }
    hits = collect_forbidden_keys(dirty)
    assert any("order_id" in h for h in hits)
    assert any("buyer_email" in h for h in hits)
    with pytest.raises(AssertionError):
        assert_ambassador_payload_safe(dirty)

    row = sale_row_for_ambassador(
        sale_id=uuid4(),
        ambassador_id=uuid4(),
        tickets_sold=1,
        merch_units_sold=0,
        revenue_amount=Decimal("100"),
        commission_owed=Decimal("10"),
        commission_type="percentage",
        hold_until=None,
        status="confirmed",
        created_at=datetime.now(UTC),
        event_title="Night",
    )
    assert_ambassador_payload_safe(row)
    assert "order_id" not in row
    assert FORBIDDEN_AMBASSADOR_KEYS.isdisjoint(row.keys())


def test_ambassador_self_apis_omit_forbidden_fields(
    client: TestClient, db_session: Session
):
    host, event, ga = _seed_open_event(db_session)
    amb_headers = _register(client, "amb-privacy@example.com", "Amb Privacy")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb_headers,
        json={"accept_terms": True},
    )
    assert joined.status_code == 201, joined.text
    code = joined.json()["referral_code"]
    ambassador_id = joined.json()["id"]

    buyer = _register(client, "buyer-privacy@example.com", "Buyer Privacy")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "referral_code": code,
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    _pay_order(
        client,
        body["id"],
        body["reference"],
        body["total_amount"],
        "buyer-privacy@example.com",
    )

    enrollments = client.get(
        "/api/v1/promos/ambassador/enrollments", headers=amb_headers
    )
    assert enrollments.status_code == 200, enrollments.text
    payload = enrollments.json()
    assert_ambassador_payload_safe(payload)

    sales = payload["enrollments"][0]["sales"]
    assert len(sales) >= 1
    sale = sales[0]
    assert "order_id" not in sale
    assert "order_reference" not in sale
    assert "event_id" not in sale
    assert "buyer_email" not in sale
    assert "address" not in sale
    assert "shipping_address" not in sale
    assert sale["event_title"] == "Privacy Amb Night"
    assert sale["tickets_sold"] == 1
    assert Decimal(str(sale["revenue_amount"])) == Decimal("5000.00")
    assert sale.get("status")
    assert sale.get("created_at")

    # Allowed aggregates on enrollment shell
    enrollment = payload["enrollments"][0]
    assert enrollment["clicks"] >= 0
    assert enrollment["tickets_sold"] >= 1
    assert "commission_owed" in enrollment

    me = client.get("/api/v1/promos/ambassador/me", headers=amb_headers)
    assert me.status_code == 200
    assert_ambassador_payload_safe(me.json())
    for s in me.json()["sales"]:
        assert "order_id" not in s
        assert "order_reference" not in s
        assert "payment_reference" not in s

    summary = client.get(
        "/api/v1/promos/ambassador/earnings-summary", headers=amb_headers
    )
    assert summary.status_code == 200
    assert_ambassador_payload_safe(summary.json())
    assert summary.json()["confirmed_sales"] >= 1
    assert "estimated_earnings" in summary.json()

    # Host detail may include order_reference for ops (not buyer PII).
    host_user = db_session.get(User, host.user_id)
    assert host_user is not None
    host_headers = _login(client, host_user.email)
    detail = client.get(
        f"/api/v1/promos/ambassadors/{ambassador_id}",
        headers=host_headers,
    )
    assert detail.status_code == 200, detail.text
    host_sale = detail.json()["sales"][0]
    assert host_sale.get("order_reference") == body["reference"]
    assert host_sale.get("order_id") == body["id"]
    assert "buyer_email" not in host_sale
    assert "shipping_address" not in host_sale


def test_domain_earnings_has_no_forbidden_keys(
    client: TestClient, db_session: Session
):
    _seed_open_event(db_session)
    headers = _register(client, "amb-domain-priv@example.com")
    resp = client.get("/api/v1/ambassadors/me/earnings", headers=headers)
    if resp.status_code == 200:
        assert_ambassador_payload_safe(resp.json())
        for key in FORBIDDEN_AMBASSADOR_KEYS:
            assert key not in resp.json()
    else:
        assert resp.status_code in {404, 403}
