"""Phase 14 — Ambassadors fraud controls."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ambassadors.fraud import (
    commission_blocked_for_host_owner,
    hash_tracking_ip,
    is_self_referral,
)
from app.core.config import get_settings
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.promos.ambassador_domain import AmbassadorFraudFlag
from app.promos.models import AmbassadorCampaign, AmbassadorSale
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    return _login(client, email)


def _seed(db: Session, *, allow_host_owner: bool = False) -> tuple[Host, User, Event, TicketType, AmbassadorCampaign]:
    host_user = User(
        email=f"fraud-host-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Fraud Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Fraud Host",
        slug=f"fraud-host-{uuid4().hex[:8]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Fraud Night",
        slug=f"fraud-night-{uuid4().hex[:8]}",
        description="Fraud controls test event",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        open_ambassadors_enabled=True,
        open_ambassador_commission_percent=Decimal("10.00"),
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
    campaign = AmbassadorCampaign(
        host_id=host.id,
        event_id=event.id,
        name="Fraud Campaign",
        status="public_open",
        source="host",
        created_by_user_id=host_user.id,
        campaign_type="event_tickets",
        commission_percent=Decimal("10.00"),
        commission_type="percentage",
        commission_value=Decimal("10.00"),
        applies_to="tickets",
        allow_host_owner_commission=allow_host_owner,
        merch_included=False,
    )
    db.add(campaign)
    db.commit()
    return host, host_user, event, ga, campaign


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
                "id": 441122,
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


def test_self_referral_helper():
    a = uuid4()
    assert is_self_referral(ambassador_user_id=a, buyer_user_id=a)
    assert not is_self_referral(ambassador_user_id=a, buyer_user_id=uuid4())
    assert not is_self_referral(ambassador_user_id=None, buyer_user_id=a)


def test_host_owner_join_blocked_unless_allowed(
    client: TestClient, db_session: Session
):
    _host, host_user, event, _ga, campaign = _seed(db_session, allow_host_owner=False)
    headers = _login(client, host_user.email)
    blocked = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=headers,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    assert blocked.status_code == 403

    campaign.allow_host_owner_commission = True
    db_session.commit()
    allowed = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=headers,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    assert allowed.status_code == 201, allowed.text


def test_host_owner_commission_blocked_finalize_clean(
    client: TestClient, db_session: Session
):
    _host, host_user, event, ga, campaign = _seed(db_session, allow_host_owner=True)
    host_headers = _login(client, host_user.email)
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=host_headers,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    assert joined.status_code == 201
    code = joined.json()["referral_code"]
    campaign.allow_host_owner_commission = False
    db_session.commit()

    buyer_email = f"fraud-buyer2-{uuid4().hex[:6]}@example.com"
    buyer = _register(client, buyer_email)
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
    _pay_order(client, body["id"], body["reference"], body["total_amount"], buyer_email)
    db_session.expire_all()
    sales = db_session.query(AmbassadorSale).all()
    assert all(s.status == "reversed" or s.commission_owed == 0 for s in sales) or len(sales) == 0
    # Prefer: no sale created
    assert len([s for s in sales if s.status != "reversed"]) == 0


def test_track_click_rate_limit(client: TestClient, db_session: Session):
    _host, _host_user, event, _ga, campaign = _seed(db_session)
    amb = _register(client, f"fraud-amb-{uuid4().hex[:6]}@example.com", "Amb")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    assert joined.status_code == 201
    code = joined.json()["referral_code"]

    settings = get_settings()
    original = settings.ambassador_track_rate_limit_per_minute
    settings.ambassador_track_rate_limit_per_minute = 3
    try:
        last = None
        for i in range(5):
            last = client.post(
                "/api/v1/promos/referrals/click",
                json={
                    "referral_code": code,
                    "event_id": str(event.id),
                    "landing_path": f"/events/{event.slug}",
                },
            )
            if last.status_code == 429:
                break
        assert last is not None
        assert last.status_code == 429
    finally:
        settings.ambassador_track_rate_limit_per_minute = original


def test_click_spike_flagged(client: TestClient, db_session: Session):
    _host, _host_user, event, _ga, campaign = _seed(db_session)
    # Need domain participant for domain track-click — join via domain API if available.
    amb = _register(client, f"spike-amb-{uuid4().hex[:6]}@example.com", "Spike Amb")
    # Create domain participation via /ambassadors/join
    joined = client.post(
        "/api/v1/ambassadors/join",
        headers=amb,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    if joined.status_code not in {200, 201}:
        # Fall back: enable domain join by ensuring campaign status active
        campaign.status = "active"
        campaign.visibility = "public_open"
        db_session.commit()
        joined = client.post(
            "/api/v1/ambassadors/join",
            headers=amb,
            json={"accept_terms": True, "campaign_id": str(campaign.id)},
        )
    assert joined.status_code in {200, 201}, joined.text
    code = joined.json()["ambassador_code"]

    settings = get_settings()
    original_threshold = settings.ambassador_click_spike_threshold
    settings.ambassador_click_spike_threshold = 3
    try:
        with patch(
            "app.runtime_settings.get_runtime_setting",
            side_effect=lambda key, *, db=None, settings=None: (
                3 if key == "ambassador_click_spike_threshold"
                else 300 if key == "ambassador_click_spike_window_seconds"
                else get_settings().__dict__.get(key)
            ),
        ), patch("app.ambassadors.referral_tracking.DUPLICATE_WINDOW_SECONDS", 0):
            for i in range(4):
                resp = client.post(
                    "/api/v1/ambassadors/track-click",
                    json={
                        "ambassador_code": code,
                        "campaign_id": str(campaign.id),
                        "event_id": str(event.id),
                        "landing_url": f"https://padeya.test/events/{event.slug}?ref={code}&n={i}",
                    },
                )
                assert resp.status_code == 200, resp.text
            flags = db_session.query(AmbassadorFraudFlag).all()
            assert any(f.flag_type == "click_spike" for f in flags)
            assert hash_tracking_ip("127.0.0.1") is not None
    finally:
        settings.ambassador_click_spike_threshold = original_threshold


def test_ticket_cancel_reverses_commission(client: TestClient, db_session: Session):
    _host, _host_user, event, ga, campaign = _seed(db_session)
    amb = _register(client, f"cancel-amb-{uuid4().hex[:6]}@example.com", "Cancel Amb")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    assert joined.status_code == 201
    code = joined.json()["referral_code"]

    buyer_email = f"cancel-buyer-{uuid4().hex[:6]}@example.com"
    buyer = _register(client, buyer_email)
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
    _pay_order(client, body["id"], body["reference"], body["total_amount"], buyer_email)

    db_session.expire_all()
    sales = [
        s
        for s in db_session.query(AmbassadorSale).all()
        if str(s.order_id) == body["id"]
    ]
    assert len(sales) == 1
    assert sales[0].status != "reversed"

    tickets = client.get("/api/v1/tickets/mine", headers=buyer)
    assert tickets.status_code == 200, tickets.text
    ticket_rows = tickets.json()
    if isinstance(ticket_rows, dict):
        ticket_rows = ticket_rows.get("tickets") or ticket_rows.get("items") or []
    assert ticket_rows
    ticket_id = ticket_rows[0]["id"]

    cancel = client.post(
        f"/api/v1/tickets/{ticket_id}/cancel",
        headers=buyer,
        json={"password": "securepass1", "reason": "Changed plans"},
    )
    assert cancel.status_code == 200, cancel.text
    db_session.expire_all()
    sale = db_session.get(AmbassadorSale, sales[0].id)
    assert sale is not None
    assert sale.status == "reversed"
