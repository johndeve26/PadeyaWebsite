"""Merch discount codes — validation, paid usage, refund safety."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.merch.discounts import (
    clamp_order_total,
    create_discount,
    validate_merch_discount,
)
from app.merch.models import EventMerchProduct, MerchDiscountCode, MerchDiscountRedemption
from app.payments.models import Order
from app.payments.paystack import sign_body_for_tests
from app.users.models import User
from app.users.service import get_role_by_name
from app.core.security import hash_password


def _login(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session) -> tuple[User, Host, Event, TicketType]:
    host_user = User(
        email="discounthost@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Discount Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Discount Host",
        slug="discount-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(
        HostProfile(
            host_id=host.id,
            city="Lagos",
            merch_storefront_enabled=True,
            merch_storefront_visibility="public",
        )
    )
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title="Discount Fest",
        slug="discount-fest",
        description="Published event for merch discount tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Yard",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        allow_merch_only_checkout=True,
    )
    db.add(event)
    db.flush()
    ticket_type = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="Entry",
        price=Decimal("3000.00"),
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(event)
    db.refresh(ticket_type)
    db.refresh(host_user)
    return host_user, host, event, ticket_type


def _register_buyer(client: TestClient, email: str) -> dict[str, str]:
    # full_name (and therefore the derived username) must be unique per buyer —
    # the register endpoint slugifies full_name into a username and 409s on
    # collision, which would silently block registration + the login below.
    local_part = email.split("@")[0]
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass1",
            "full_name": f"Buyer {local_part}",
            "gender": "prefer_not_to_say",
        },
    )
    assert res.status_code == 201, res.text
    return _login(client, email)


def _create_product(
    client: TestClient, host_headers: dict[str, str], event_id: UUID, *, inventory: int = 10
) -> dict:
    response = client.post(
        f"/api/v1/merch/events/{event_id}/products",
        headers=host_headers,
        json={
            "name": "Discount Tee",
            "description": "Soft cotton tee",
            "base_price": "5000.00",
            "status": "active",
            "pickup_instructions": "Merch stand",
            "variants": [
                {"label": "M / Black", "inventory_count": inventory, "status": "active"}
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _pay_order(client: TestClient, headers: dict[str, str], order: dict) -> None:
    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)

    event_id = int(UUID(order["id"]).int % 10**9) + 2000
    payload = {
        "event": "charge.success",
        "data": {
            "id": event_id,
            "reference": order["reference"],
            "amount": int(Decimal(order["total_amount"]) * 100),
            "status": "success",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    ok = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={
            "x-paystack-signature": sign_body_for_tests(body),
            "content-type": "application/json",
        },
    )
    assert ok.status_code == 200, ok.text


def test_clamp_order_total_never_below_zero():
    assert clamp_order_total(
        subtotal=Decimal("100"),
        ticket_discount=Decimal("80"),
        merch_discount=Decimal("50"),
        shipping_amount=Decimal("0"),
    ) == Decimal("0.00")


def test_invalid_window_rejected(client: TestClient, db_session: Session):
    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]

    create_discount(
        db_session,
        host_id=host.id,
        code="FUTURE",
        discount_type="percent",
        discount_value=Decimal("10"),
        starts_at=datetime.now(UTC) + timedelta(days=2),
    )
    create_discount(
        db_session,
        host_id=host.id,
        code="PAST",
        discount_type="percent",
        discount_value=Decimal("10"),
        ends_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.commit()

    buyer = _register_buyer(client, "windowbuyer@example.com")
    for code in ("FUTURE", "PAST"):
        resp = client.post(
            "/api/v1/orders",
            headers=buyer,
            json={
                "event_id": str(event.id),
                "merch_discount_code": code,
                "items": [
                    {
                        "item_kind": "merch",
                        "merch_variant_id": variant_id,
                        "quantity": 1,
                    }
                ],
            },
        )
        assert resp.status_code == 400, resp.text


def test_usage_limit_and_unpaid_does_not_increment(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    create_discount(
        db_session,
        host_id=host.id,
        code="ONCE",
        discount_type="fixed_amount",
        discount_value=Decimal("500"),
        usage_limit=1,
    )
    db_session.commit()

    buyer = _register_buyer(client, "limitbuyer@example.com")
    pending = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "ONCE",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert pending.status_code == 201, pending.text
    from sqlalchemy import select

    code_row = db_session.scalar(
        select(MerchDiscountCode).where(MerchDiscountCode.code == "ONCE")
    )
    assert code_row is not None
    assert code_row.usage_count_paid == 0

    _pay_order(client, buyer, pending.json())
    db_session.refresh(code_row)
    assert code_row.usage_count_paid == 1

    buyer2 = _register_buyer(client, "limitbuyer2@example.com")
    blocked = client.post(
        "/api/v1/orders",
        headers=buyer2,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "ONCE",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert blocked.status_code == 400
    assert "usage limit" in blocked.json()["detail"].lower()


def test_per_buyer_limit(client: TestClient, db_session: Session):
    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id, inventory=20)
    variant_id = product["variants"][0]["id"]
    create_discount(
        db_session,
        host_id=host.id,
        code="BUYER1",
        discount_type="percent",
        discount_value=Decimal("10"),
        per_buyer_limit=1,
    )
    db_session.commit()

    buyer = _register_buyer(client, "perbuyer@example.com")
    first = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "BUYER1",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert first.status_code == 201, first.text
    _pay_order(client, buyer, first.json())

    second = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "BUYER1",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert second.status_code == 400
    assert "already used" in second.json()["detail"].lower()


def test_min_order_amount(client: TestClient, db_session: Session):
    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    create_discount(
        db_session,
        host_id=host.id,
        code="MIN10K",
        discount_type="percent",
        discount_value=Decimal("10"),
        min_order_amount=Decimal("10000.00"),
    )
    db_session.commit()

    buyer = _register_buyer(client, "minbuyer@example.com")
    resp = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "MIN10K",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert resp.status_code == 400
    assert "minimum" in resp.json()["detail"].lower()


def test_fixed_amount_clamped_to_eligible(client: TestClient, db_session: Session):
    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    create_discount(
        db_session,
        host_id=host.id,
        code="HUGE",
        discount_type="fixed_amount",
        discount_value=Decimal("999999.00"),
    )
    db_session.commit()

    buyer = _register_buyer(client, "clampbuyer@example.com")
    resp = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "HUGE",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert Decimal(body["merch_discount_amount"]) == Decimal("5000.00")
    assert Decimal(body["total_amount"]) == Decimal("0.00")


def test_free_shipping_requires_shipping(client: TestClient, db_session: Session):
    from app.merch.shipping import upsert_zone

    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    prod = db_session.get(EventMerchProduct, UUID(product["id"]))
    assert prod is not None
    prod.shipping_enabled = True
    upsert_zone(
        db_session,
        host_id=host.id,
        name="Lagos",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        flat_fee=Decimal("2000.00"),
        event_id=event.id,
    )
    create_discount(
        db_session,
        host_id=host.id,
        code="FREESHIP",
        discount_type="free_shipping",
        discount_value=Decimal("0"),
    )
    db_session.commit()

    buyer = _register_buyer(client, "shipbuyer@example.com")
    pickup = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "pickup",
            "merch_discount_code": "FREESHIP",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert pickup.status_code == 400

    shipped = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "shipping",
            "merch_discount_code": "FREESHIP",
            "shipping_address": {
                "recipient_name": "Ada Buyer",
                "phone": "+2348012345678",
                "line1": "12 Street",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert shipped.status_code == 201, shipped.text
    body = shipped.json()
    assert Decimal(body["shipping_amount"]) == Decimal("0.00")
    assert Decimal(body["total_amount"]) == Decimal("5000.00")


def test_refund_reverses_usage(client: TestClient, db_session: Session):
    from sqlalchemy import select

    from app.merch.fulfillment import cancel_fulfillments_for_refunded_order

    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    create_discount(
        db_session,
        host_id=host.id,
        code="REFUNDSAFE",
        discount_type="percent",
        discount_value=Decimal("15"),
        usage_limit=1,
        per_buyer_limit=1,
    )
    db_session.commit()

    buyer = _register_buyer(client, "refundbuyer@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "REFUNDSAFE",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    _pay_order(client, buyer, body)

    code_row = db_session.scalar(
        select(MerchDiscountCode).where(MerchDiscountCode.code == "REFUNDSAFE")
    )
    assert code_row is not None
    db_session.refresh(code_row)
    assert code_row.usage_count_paid == 1

    order_row = db_session.get(Order, UUID(body["id"]))
    assert order_row is not None
    cancel_fulfillments_for_refunded_order(db_session, order=order_row)
    db_session.commit()
    db_session.refresh(code_row)
    assert code_row.usage_count_paid == 0

    red = db_session.scalar(
        select(MerchDiscountRedemption).where(
            MerchDiscountRedemption.order_id == order_row.id
        )
    )
    assert red is not None
    assert red.status == "reversed"

    # Buyer can use again after refund reverse
    again = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "merch_discount_code": "REFUNDSAFE",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert again.status_code == 201, again.text


def test_host_discount_crud_and_validate(client: TestClient, db_session: Session):
    _, _, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]

    created = client.post(
        "/api/v1/host/merchandise/discounts",
        headers=host_headers,
        json={
            "code": "HOST15",
            "description": "Host merch deal",
            "discount_type": "percent",
            "discount_value": "15",
            "currency": "NGN",
            "applies_to": "merch_only",
            "usage_limit": 50,
            "per_buyer_limit": 2,
        },
    )
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["code"] == "HOST15"
    assert data["description"] == "Host merch deal"
    assert data["currency"] == "NGN"
    assert data["usage_count"] == 0

    listed = client.get("/api/v1/host/merchandise/discounts", headers=host_headers)
    assert listed.status_code == 200
    assert any(r["code"] == "HOST15" for r in listed.json())

    paused = client.patch(
        f"/api/v1/host/merchandise/discounts/{data['id']}",
        headers=host_headers,
        json={"status": "paused"},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    buyer = _register_buyer(client, "validatebuyer@example.com")
    preview = client.post(
        "/api/v1/merch/discounts/validate",
        headers=buyer,
        json={
            "code": "HOST15",
            "event_id": str(event.id),
            "items": [{"merch_variant_id": variant_id, "quantity": 1}],
        },
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is False

    client.patch(
        f"/api/v1/host/merchandise/discounts/{data['id']}",
        headers=host_headers,
        json={"status": "active"},
    )
    preview_ok = client.post(
        "/api/v1/merch/discounts/validate",
        headers=buyer,
        json={
            "code": "HOST15",
            "event_id": str(event.id),
            "items": [{"merch_variant_id": variant_id, "quantity": 1}],
        },
    )
    assert preview_ok.status_code == 200
    body = preview_ok.json()
    assert body["valid"] is True
    assert Decimal(body["discount_amount"]) > 0


def test_specific_products_and_event_merch_modes(
    client: TestClient, db_session: Session
):
    from fastapi import HTTPException
    import pytest

    _, host, event, _ = _seed(db_session)
    host_headers = _login(client, "discounthost@example.com")
    product = _create_product(client, host_headers, event.id)
    prod = db_session.get(EventMerchProduct, UUID(product["id"]))
    assert prod is not None
    buyer_user = User(
        email="unitbuyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Unit",
        is_active=True,
    )
    db_session.add(buyer_user)
    db_session.flush()

    with pytest.raises(HTTPException):
        create_discount(
            db_session,
            host_id=host.id,
            code="NOPRODS",
            discount_type="percent",
            discount_value=Decimal("10"),
            applies_to="specific_products",
        )

    with pytest.raises(HTTPException):
        create_discount(
            db_session,
            host_id=host.id,
            code="NOEVENT",
            discount_type="percent",
            discount_value=Decimal("10"),
            applies_to="specific_event_merch",
        )

    code = create_discount(
        db_session,
        host_id=host.id,
        code="PRODONLY",
        discount_type="percent",
        discount_value=Decimal("20"),
        applies_to="specific_products",
        product_ids=[str(prod.id)],
    )
    db_session.commit()

    _, discount, _ = validate_merch_discount(
        db_session,
        code_str="PRODONLY",
        host_id=host.id,
        buyer=buyer_user,
        merch_lines=[(prod, Decimal("5000.00"), False)],
    )
    assert discount == Decimal("1000.00")
    assert code.id is not None
