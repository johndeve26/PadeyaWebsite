"""Checkout fee integration tests — server is source of truth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.finance.fees.constants import (
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_TICKET_COMMISSION,
)
from app.finance.fees.models import OrderFeeSnapshot, PlatformFeeSetting
from app.finance.fees.money import major_to_minor
from app.finance.models import LedgerEntry
from app.finance.service import record_sale_credit_for_order
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, Payment
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_event(db: Session, *, price: Decimal = Decimal("10000.00")) -> tuple[Host, Event, TicketType, User]:
    host_user = User(
        email="checkout-fee-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Checkout Fee Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Checkout Fee Host",
        slug="checkout-fee-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Fees host"))

    buyer = User(
        email="checkout-fee-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Checkout Fee Buyer",
        is_active=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title="Checkout Fee Event",
        slug="checkout-fee-event",
        description="Event for checkout fee integration tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=price,
        quantity=100,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=10,
        sale_start=datetime.now(UTC) - timedelta(days=1),
        sale_end=start,
        status="active",
        visibility="public",
    )
    db.add(tt)
    db.commit()
    return host, event, tt, buyer


def _seed_fees(db: Session, *, host: Host) -> None:
    admin = User(
        email="checkout-fee-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Fee Admin",
        is_active=True,
    )
    role = get_role_by_name(db, "finance_admin")
    assert role is not None
    admin.roles.append(role)
    db.add(admin)
    db.flush()
    now = datetime.now(UTC) - timedelta(days=1)
    db.add(
        PlatformFeeSetting(
            fee_key=FEE_KEY_TICKET_COMMISSION,
            label="Ticket commission",
            category="ticket",
            fee_type="percentage",
            percentage_value=Decimal("5.00"),
            fixed_value=None,
            currency="NGN",
            payer="host",
            enabled=True,
            applies_to="all",
            effective_from=now,
            created_by_admin_id=admin.id,
            updated_by_admin_id=admin.id,
        )
    )
    db.add(
        PlatformFeeSetting(
            fee_key=FEE_KEY_BUYER_SERVICE,
            label="Buyer platform / service fee",
            category="general",
            fee_type="mixed",
            percentage_value=Decimal("2.00"),
            fixed_value=100_00,
            currency="NGN",
            payer="buyer",
            enabled=True,
            applies_to="all",
            effective_from=now,
            created_by_admin_id=admin.id,
            updated_by_admin_id=admin.id,
        )
    )
    db.commit()


def test_checkout_buyer_service_fee_not_host_commission(
    client: TestClient, db_session: Session
) -> None:
    host, event, tt, buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    headers = _login(client, buyer.email)

    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    # 2% of 10000 = 200 + ₦100 fixed = 300 buyer fee; host 5% not on buyer total
    assert Decimal(body["buyer_fee_total"]) == Decimal("300.00")
    assert Decimal(body["host_fee_total"]) == Decimal("500.00")
    assert Decimal(body["final_total"]) == Decimal("10300.00")
    assert Decimal(body["total_amount"]) == Decimal("10300.00")
    assert Decimal(body["host_net_estimate"]) == Decimal("9500.00")
    keys = {line["fee_key"] for line in body["fee_breakdown"]}
    assert FEE_KEY_BUYER_SERVICE in keys
    assert FEE_KEY_TICKET_COMMISSION not in keys  # host terms hidden from buyer


def test_paystack_amount_equals_server_final_total(
    client: TestClient, db_session: Session
) -> None:
    host, event, tt, buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    headers = _login(client, buyer.email)
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
        },
    )
    order_id = created.json()["id"]
    final_total = Decimal(created.json()["final_total"])

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://paystack.test/checkout",
            "access_code": "ACCESS",
        },
    ) as mock_init:
        checkout = client.post(
            f"/api/v1/payments/checkout/{order_id}",
            headers=headers,
        )
        assert checkout.status_code == 200, checkout.text
        assert Decimal(checkout.json()["amount"]) == final_total
        assert Decimal(checkout.json()["final_total"]) == final_total
        called_kobo = mock_init.call_args.kwargs["amount_kobo"]
        assert called_kobo == int(final_total * 100)


def test_fee_snapshot_stored_and_frozen(
    client: TestClient, db_session: Session
) -> None:
    host, event, tt, buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    headers = _login(client, buyer.email)
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
        },
    )
    order_id = UUID(created.json()["id"])
    snaps = (
        db_session.query(OrderFeeSnapshot)
        .filter(OrderFeeSnapshot.order_id == order_id)
        .all()
    )
    assert len(snaps) >= 2
    buyer_snap = next(s for s in snaps if s.fee_key == FEE_KEY_BUYER_SERVICE)
    assert buyer_snap.amount == major_to_minor(Decimal("300.00"))

    # Admin changes fee — snapshot stays
    setting = (
        db_session.query(PlatformFeeSetting)
        .filter_by(fee_key=FEE_KEY_BUYER_SERVICE)
        .one()
    )
    setting.percentage_value = Decimal("50.00")
    db_session.commit()

    db_session.refresh(buyer_snap)
    assert buyer_snap.amount == major_to_minor(Decimal("300.00"))


def test_free_order_waives_buyer_service_fee(
    client: TestClient, db_session: Session
) -> None:
    host, event, tt, buyer = _seed_event(db_session, price=Decimal("0.00"))
    _seed_fees(db_session, host=host)
    headers = _login(client, buyer.email)
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert Decimal(body["buyer_fee_total"]) == Decimal("0.00")
    assert Decimal(body["total_amount"]) == Decimal("0.00")

    checkout = client.post(
        f"/api/v1/payments/checkout/{body['id']}",
        headers=headers,
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["free_checkout"] is True


def test_host_credit_uses_host_net_not_buyer_total(
    client: TestClient, db_session: Session
) -> None:
    host, event, tt, buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    headers = _login(client, buyer.email)
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
        },
    )
    order = db_session.get(Order, UUID(created.json()["id"]))
    assert order is not None
    order.status = "paid"
    db_session.add(
        Payment(
            order_id=order.id,
            provider="paystack",
            reference=order.reference,
            amount=order.total_amount,
            currency="NGN",
            status="successful",
        )
    )
    db_session.commit()

    entry = record_sale_credit_for_order(db_session, order)
    db_session.commit()
    assert entry is not None
    assert Decimal(entry.amount) == Decimal("9500.00")
    assert Decimal(entry.amount) != Decimal(order.total_amount)


def test_guest_checkout_applies_fees(client: TestClient, db_session: Session) -> None:
    host, event, tt, _buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    created = client.post(
        "/api/v1/orders",
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
            "guest_buyer_name": "Guest Buyer",
            "guest_buyer_email": "guest-fee@example.com",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["is_guest_checkout"] is True
    assert Decimal(body["total_amount"]) == Decimal("10300.00")
    assert Decimal(body["buyer_fee_total"]) == Decimal("300.00")


def test_fee_quote_hides_host_commission(
    client: TestClient, db_session: Session
) -> None:
    host, _event, _tt, _buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    quote = client.post(
        "/api/v1/payments/fee-quote",
        json={
            "host_id": str(host.id),
            "ticket_subtotal": "10000.00",
            "ticket_discount": "0",
            "merch_subtotal": "0",
            "merch_discount": "0",
            "shipping_amount": "0",
        },
    )
    assert quote.status_code == 200, quote.text
    body = quote.json()
    assert Decimal(body["buyer_fee_total"]) == Decimal("300.00")
    assert Decimal(body["final_total"]) == Decimal("10300.00")
    assert all(line["payer"] == "buyer" for line in body["fee_breakdown"])
    assert FEE_KEY_TICKET_COMMISSION not in {
        line["fee_key"] for line in body["fee_breakdown"]
    }


def test_buy_for_someone_else_applies_fees(
    client: TestClient, db_session: Session
) -> None:
    host, event, tt, buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    headers = _login(client, buyer.email)
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
            "purchase_mode": "other",
            "recipient_name": "Gift Friend",
            "recipient_email": "gift-fee-friend@example.com",
            "send_ticket_to_recipient": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["purchase_mode"] == "other"
    assert Decimal(body["buyer_fee_total"]) == Decimal("300.00")
    assert Decimal(body["total_amount"]) == Decimal("10300.00")
    assert FEE_KEY_TICKET_COMMISSION not in {
        line["fee_key"] for line in body["fee_breakdown"]
    }


def test_promo_recalculates_buyer_fees_on_discounted_subtotal(
    client: TestClient, db_session: Session
) -> None:
    from app.promos.models import PromoCode

    host, event, tt, buyer = _seed_event(db_session)
    _seed_fees(db_session, host=host)
    db_session.add(
        PromoCode(
            host_id=host.id,
            code="FEE10",
            discount_type="percentage",
            discount_value=Decimal("10"),
            event_id=event.id,
            status="active",
            usage_limit=50,
            max_per_user=5,
        )
    )
    db_session.commit()
    headers = _login(client, buyer.email)
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
            "promo_code": "FEE10",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    # Subtotal 10000 − 10% = 9000; buyer fee = 2% of 9000 + 100 = 280
    assert Decimal(body["discount_amount"]) == Decimal("1000.00")
    assert Decimal(body["buyer_fee_total"]) == Decimal("280.00")
    assert Decimal(body["total_amount"]) == Decimal("9280.00")
    # Host commission on discounted ticket net: 5% of 9000 = 450
    assert Decimal(body["host_fee_total"]) == Decimal("450.00")
    assert Decimal(body["host_net_estimate"]) == Decimal("8550.00")
