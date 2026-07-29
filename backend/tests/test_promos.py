"""Promo codes and ambassador referral attribution tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.promos.models import Ambassador, AmbassadorSale, PromoCode, PromoRedemption
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
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    return _login(client, email)


def _seed_host_event(db: Session, *, vip: bool = True) -> tuple[Host, Event, TicketType, TicketType | None]:
    host_user = User(
        email="promo-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Promo Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Promo Host",
        slug="promo-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Mainland Vibes",
        slug="mainland-vibes",
        description="Event used for promo and ambassador checkout tests.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
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
    db.flush()

    vip_tt = None
    if vip:
        vip_tt = TicketType(
            event_id=event.id,
            name="VIP",
            type="vip",
            price=Decimal("10000.00"),
            quantity=50,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=3,
            visibility="public",
            status="active",
        )
        db.add(vip_tt)
        db.flush()

    db.commit()
    return host, event, ga, vip_tt


def _pay_order(client: TestClient, db: Session, order_id: str, reference: str, amount: str):
    with patch("app.payments.service.initialize_transaction") as mock_init:
        mock_init.return_value = {
            "authorization_url": "https://paystack.test/pay",
            "access_code": "ACCESS",
            "reference": reference,
        }
        checkout = client.post(
            f"/api/v1/payments/checkout/{order_id}",
            headers=_login(client, "promo-buyer@example.com"),
        )
        assert checkout.status_code == 200, checkout.text

    amount_kobo = int(Decimal(amount) * 100)
    body = json.dumps(
        {
            "event": "charge.success",
            "data": {
                "id": 991122,
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


def test_valid_promo_code(client: TestClient, db_session: Session):
    host, event, ga, _ = _seed_host_event(db_session)
    host_headers = _login(client, "promo-host@example.com")
    created = client.post(
        "/api/v1/promos/codes",
        headers=host_headers,
        json={
            "code": "SAVE10",
            "discount_type": "percentage",
            "discount_value": "10",
            "event_id": str(event.id),
            "usage_limit": 50,
        },
    )
    assert created.status_code == 201, created.text

    buyer = _register(client, "promo-buyer@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 2}],
            "promo_code": "save10",
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert body["subtotal_amount"] == "10000.00"
    assert body["discount_amount"] == "1000.00"
    assert body["total_amount"] == "9000.00"
    assert body["promo_code_snapshot"] == "SAVE10"

    _pay_order(client, db_session, body["id"], body["reference"], "9000.00")
    redemption = (
        db_session.query(PromoRedemption)
        .filter_by(order_id=UUID(body["id"]))
        .one()
    )
    assert redemption.status == "redeemed"


def test_expired_promo_code(client: TestClient, db_session: Session):
    _, event, ga, _ = _seed_host_event(db_session)
    host_headers = _login(client, "promo-host@example.com")
    client.post(
        "/api/v1/promos/codes",
        headers=host_headers,
        json={
            "code": "OLDCODE",
            "discount_type": "fixed",
            "discount_value": "500",
            "event_id": str(event.id),
            "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
    )
    buyer = _register(client, "promo-buyer@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "promo_code": "OLDCODE",
        },
    )
    assert order.status_code == 400
    assert "expired" in order.json()["detail"].lower()


def test_usage_limit_reached(client: TestClient, db_session: Session):
    host, event, ga, _ = _seed_host_event(db_session)
    host_headers = _login(client, "promo-host@example.com")
    promo = client.post(
        "/api/v1/promos/codes",
        headers=host_headers,
        json={
            "code": "ONCE",
            "discount_type": "fixed",
            "discount_value": "500",
            "event_id": str(event.id),
            "usage_limit": 1,
        },
    ).json()

    # Manually mark usage exhausted
    row = db_session.get(PromoCode, UUID(promo["id"]))
    assert row is not None
    row.usage_count = 1
    db_session.commit()

    buyer = _register(client, "promo-buyer@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "promo_code": "ONCE",
        },
    )
    assert order.status_code == 400
    assert "limit" in order.json()["detail"].lower()


def test_ticket_type_restricted_promo(client: TestClient, db_session: Session):
    _, event, ga, vip = _seed_host_event(db_session)
    assert vip is not None
    host_headers = _login(client, "promo-host@example.com")
    client.post(
        "/api/v1/promos/codes",
        headers=host_headers,
        json={
            "code": "VIPONLY",
            "discount_type": "percentage",
            "discount_value": "20",
            "event_id": str(event.id),
            "ticket_type_id": str(vip.id),
        },
    )
    buyer = _register(client, "promo-buyer@example.com")
    blocked = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "promo_code": "VIPONLY",
        },
    )
    assert blocked.status_code == 400
    assert "ticket type" in blocked.json()["detail"].lower()

    allowed = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(vip.id), "quantity": 1}],
            "promo_code": "VIPONLY",
        },
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["discount_amount"] == "2000.00"
    assert allowed.json()["total_amount"] == "8000.00"


def test_referral_attribution(client: TestClient, db_session: Session):
    host, event, ga, _ = _seed_host_event(db_session)
    host_headers = _login(client, "promo-host@example.com")

    amb_user = _register(client, "tola@example.com", "Tola Amb")
    created = client.post(
        "/api/v1/promos/ambassadors",
        headers=host_headers,
        json={
            "referral_code": "tola",
            "display_name": "Tola",
            "user_email": "tola@example.com",
            "commission_rate_percent": "10",
        },
    )
    assert created.status_code == 201, created.text

    click = client.post(
        "/api/v1/promos/referrals/click",
        json={
            "referral_code": "tola",
            "event_id": str(event.id),
            "landing_path": "/events/mainland-vibes?ref=tola",
        },
    )
    assert click.status_code == 201

    buyer = _register(client, "promo-buyer@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "referral_code": "tola",
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert body["referral_code"] == "tola"

    _pay_order(client, db_session, body["id"], body["reference"], body["total_amount"])

    db_session.expire_all()
    sales = db_session.query(AmbassadorSale).all()
    sale = next(s for s in sales if str(s.order_id) == body["id"])
    assert sale.tickets_sold == 1
    assert sale.revenue_amount == Decimal("5000.00")
    assert sale.commission_owed == Decimal("500.00")

    dash = client.get("/api/v1/promos/ambassador/me", headers=amb_user)
    assert dash.status_code == 200
    assert dash.json()["tickets_sold"] == 1
    assert dash.json()["clicks"] >= 1


def test_curated_ambassador_event_scoped_link(
    client: TestClient, db_session: Session
):
    host, event, ga, _ = _seed_host_event(db_session)
    host_headers = _login(client, "promo-host@example.com")

    created = client.post(
        "/api/v1/promos/ambassadors",
        headers=host_headers,
        json={
            "referral_code": "abiodun",
            "display_name": "Abiodun",
            "event_id": str(event.id),
            "commission_rate_percent": "8",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["event_id"] == str(event.id)
    assert body["event_slug"] == event.slug
    assert body["event_title"] == event.title

    click = client.post(
        "/api/v1/promos/referrals/click",
        json={
            "referral_code": "abiodun",
            "event_id": str(event.id),
            "landing_path": f"/events/{event.slug}?ref=abiodun",
        },
    )
    assert click.status_code == 201

    buyer = _register(client, "event-scoped-buyer@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "referral_code": "abiodun",
        },
    )
    assert order.status_code == 201, order.text
    assert order.json()["referral_code"] == "abiodun"

    patched = client.patch(
        f"/api/v1/promos/ambassadors/{body['id']}",
        headers=host_headers,
        json={"event_id": str(event.id)},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["event_slug"] == event.slug


def test_host_wide_referral_click_without_event(
    client: TestClient, db_session: Session
):
    _seed_host_event(db_session)
    host_headers = _login(client, "promo-host@example.com")
    created = client.post(
        "/api/v1/promos/ambassadors",
        headers=host_headers,
        json={
            "referral_code": "widehost",
            "display_name": "Wide Host",
            "commission_rate_percent": "5",
        },
    )
    assert created.status_code == 201, created.text
    amb_id = created.json()["id"]

    click = client.post(
        "/api/v1/promos/referrals/click",
        json={
            "referral_code": "widehost",
            "landing_path": "/events?ref=widehost",
        },
    )
    assert click.status_code == 201, click.text

    listed = client.get("/api/v1/promos/ambassadors", headers=host_headers)
    assert listed.status_code == 200
    row = next(a for a in listed.json() if a["id"] == amb_id)
    assert row["clicks"] >= 1


def test_duplicate_abuse_prevention(client: TestClient, db_session: Session):
    _, event, ga, _ = _seed_host_event(db_session)
    host_headers = _login(client, "promo-host@example.com")
    client.post(
        "/api/v1/promos/codes",
        headers=host_headers,
        json={
            "code": "ONCEUSER",
            "discount_type": "fixed",
            "discount_value": "1000",
            "event_id": str(event.id),
            "max_per_user": 1,
            "usage_limit": 10,
        },
    )
    buyer = _register(client, "promo-buyer@example.com")
    first = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "promo_code": "ONCEUSER",
        },
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "promo_code": "ONCEUSER",
        },
    )
    assert second.status_code == 400
    assert "already used" in second.json()["detail"].lower()
