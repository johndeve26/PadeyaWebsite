"""Abandoned merch cart recovery — no paid-state invention, no PII in notify bodies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.messaging.models import InAppNotification
from app.merch.cart import mark_cart_converted, recover_abandoned_carts
from app.merch.models import EventMerchVariant, MerchCart
from app.payments.models import Order
from app.users.models import User
from tests.test_merch import (
    _create_active_product,
    _login,
    _pay_order,
    _register_buyer,
    _seed_host_event,
)


def _buyer_id(db: Session, email: str) -> UUID:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user.id


def _add_cart_via_api(
    client: TestClient, headers: dict[str, str], variant_id: str, qty: int = 1
) -> dict:
    res = client.post(
        "/api/v1/dashboard/cart/items",
        headers=headers,
        json={"variant_id": variant_id, "quantity": qty},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_cart_abandons_after_idle_and_sends_reminder(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "cart-abandon@example.com")
    cart = _add_cart_via_api(client, buyer, variant_id)

    row = db_session.get(MerchCart, UUID(cart["id"]))
    assert row is not None
    row.last_activity_at = datetime.now(UTC) - timedelta(hours=25)
    db_session.commit()

    sent = recover_abandoned_carts(db_session, limit=50)
    assert sent == 1

    db_session.refresh(row)
    assert row.status == "abandoned"
    assert row.recovery_sent_at is not None

    buyer_id = _buyer_id(db_session, "cart-abandon@example.com")
    notes = list(
        db_session.scalars(
            select(InAppNotification).where(
                InAppNotification.user_id == buyer_id,
                InAppNotification.kind == "merch.cart_reminder",
            )
        )
    )
    assert len(notes) == 1
    assert "Still interested in your Pàdéyá merch?" == notes[0].title
    assert "still waiting" in notes[0].body.lower()
    assert notes[0].link_path == f"/events/{event.slug}/checkout"

    host_notes = list(
        db_session.scalars(
            select(InAppNotification).where(
                InAppNotification.user_id == host.user_id,
                InAppNotification.kind == "merch.host_cart_summary",
            )
        )
    )
    assert len(host_notes) == 1
    assert "shopper" in host_notes[0].body.lower()


def test_cart_converts_only_after_paid_webhook(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "cart-convert@example.com")
    cart = _add_cart_via_api(client, buyer, variant_id)
    cart_id = UUID(cart["id"])

    order_res = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order_res.status_code in {200, 201}, order_res.text
    order = order_res.json()
    assert order["status"] == "pending"

    row = db_session.get(MerchCart, cart_id)
    assert row is not None
    assert row.status == "active"
    assert row.order_id is None

    _pay_order(client, buyer, order)
    db_session.expire_all()
    row = db_session.get(MerchCart, cart_id)
    assert row is not None
    assert row.status == "converted"
    assert row.order_id == UUID(order["id"])


def test_recovery_skips_sold_out_lines(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=1)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "cart-soldout@example.com")
    cart = _add_cart_via_api(client, buyer, variant_id)

    variant = db_session.get(EventMerchVariant, UUID(variant_id))
    assert variant is not None
    variant.inventory_count = 0
    variant.quantity_sold = 0
    variant.quantity_reserved = 0
    variant.status = "sold_out"
    row = db_session.get(MerchCart, UUID(cart["id"]))
    assert row is not None
    row.last_activity_at = datetime.now(UTC) - timedelta(hours=30)
    db_session.commit()

    sent = recover_abandoned_carts(db_session, limit=50)
    assert sent == 0
    db_session.refresh(row)
    assert row.status == "expired"
    assert row.recovery_sent_at is None


def test_recovery_notify_body_has_no_buyer_pii(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=4)
    variant_id = product["variants"][0]["id"]
    email = "cart-pii-buyer@example.com"
    buyer = _register_buyer(client, email)
    cart = _add_cart_via_api(client, buyer, variant_id)
    row = db_session.get(MerchCart, UUID(cart["id"]))
    assert row is not None
    row.last_activity_at = datetime.now(UTC) - timedelta(hours=26)
    db_session.commit()

    recover_abandoned_carts(db_session, limit=50)
    buyer_id = _buyer_id(db_session, email)
    note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == buyer_id,
            InAppNotification.kind == "merch.cart_reminder",
        )
    )
    assert note is not None
    blob = f"{note.title}\n{note.body}".lower()
    assert email.lower() not in blob
    assert "merch buyer" not in blob  # full_name from register helper
    assert "+234" not in blob
    assert "street" not in blob
    assert "paystack" not in blob
    assert "card" not in blob


def test_recovery_rate_limited_one_per_cart_and_user_gap(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=8)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "cart-ratelimit@example.com")
    cart = _add_cart_via_api(client, buyer, variant_id)
    row = db_session.get(MerchCart, UUID(cart["id"]))
    assert row is not None
    row.last_activity_at = datetime.now(UTC) - timedelta(hours=30)
    db_session.commit()

    assert recover_abandoned_carts(db_session, limit=50) == 1
    db_session.refresh(row)
    first_sent = row.recovery_sent_at
    assert first_sent is not None

    # Second run: same cart already recovered
    assert recover_abandoned_carts(db_session, limit=50) == 0

    # New abandoned cart for same user within min gap → skip
    row.status = "converted"
    row.order_id = None
    db_session.commit()
    cart2 = _add_cart_via_api(client, buyer, variant_id)
    row2 = db_session.get(MerchCart, UUID(cart2["id"]))
    assert row2 is not None
    row2.last_activity_at = datetime.now(UTC) - timedelta(hours=30)
    db_session.commit()

    assert recover_abandoned_carts(db_session, limit=50) == 0
    db_session.refresh(row2)
    assert row2.recovery_sent_at is None
    assert row2.status == "abandoned"


def test_mark_cart_converted_helper_links_order(db_session: Session):
    _, host, event, _ = _seed_host_event(db_session)
    buyer = User(
        email="cart-helper@example.com",
        password_hash="x",
        full_name="Helper",
        is_active=True,
    )
    db_session.add(buyer)
    db_session.flush()
    cart = MerchCart(
        buyer_user_id=buyer.id,
        event_id=event.id,
        host_id=host.id,
        status="abandoned",
        last_activity_at=datetime.now(UTC) - timedelta(hours=40),
    )
    db_session.add(cart)
    db_session.flush()
    order = Order(
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        reference="cart-helper-ref",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("1000.00"),
        status="paid",
    )
    db_session.add(order)
    db_session.flush()
    mark_cart_converted(db_session, user_id=buyer.id, order_id=order.id)
    db_session.commit()
    db_session.refresh(cart)
    assert cart.status == "converted"
    assert cart.order_id == order.id


def test_adding_same_variant_increments_cart_quantity(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "cart-increment@example.com")
    first = _add_cart_via_api(client, buyer, variant_id, qty=1)
    assert first["items"][0]["quantity"] == 1
    second = _add_cart_via_api(client, buyer, variant_id, qty=2)
    assert len(second["items"]) == 1
    assert second["items"][0]["quantity"] == 3


def test_update_cart_item_quantity_sets_exact_value(
    client: TestClient, db_session: Session
):
    """PATCH sets an absolute quantity — unlike POST, it must not be additive.

    Checkout quantity steppers rely on this: bumping a line from 1 -> 2 must
    leave the cart at 2, not 1 + 2 = 3.
    """
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "cart-setqty@example.com")
    cart = _add_cart_via_api(client, buyer, variant_id, qty=1)
    item_id = cart["items"][0]["id"]

    updated = client.patch(
        f"/api/v1/dashboard/cart/items/{item_id}",
        headers=buyer,
        json={"quantity": 2},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2

    # Setting back down works too (not just increasing).
    lowered = client.patch(
        f"/api/v1/dashboard/cart/items/{item_id}",
        headers=buyer,
        json={"quantity": 1},
    )
    assert lowered.status_code == 200
    assert lowered.json()["items"][0]["quantity"] == 1

    # Over available stock (product inventory is 5) is rejected with 409.
    over = client.patch(
        f"/api/v1/dashboard/cart/items/{item_id}",
        headers=buyer,
        json={"quantity": 10},
    )
    assert over.status_code == 409

    other_buyer = _register_buyer(client, "cart-setqty-other@example.com")
    forbidden = client.patch(
        f"/api/v1/dashboard/cart/items/{item_id}",
        headers=other_buyer,
        json={"quantity": 1},
    )
    assert forbidden.status_code == 404


def test_dashboard_cart_resume_fields(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "cart-resume@example.com")
    _add_cart_via_api(client, buyer, variant_id)

    res = client.get("/api/v1/dashboard/cart", headers=buyer)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "active"
    assert body["event_slug"] == event.slug
    assert body["resume_path"] == f"/events/{event.slug}/checkout"
    assert "paid" not in body
    assert body.get("is_paid") is None
