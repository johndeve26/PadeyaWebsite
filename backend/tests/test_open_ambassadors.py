"""Open Event Ambassadors: join, attribution, self-referral guard."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.promos.models import Ambassador, AmbassadorSale
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
        email="open-amb-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Open Amb Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Open Amb Host",
        slug="open-amb-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Open Amb Night",
        slug="open-amb-night",
        description="Event used for open Event Ambassadors tests.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
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


def _pay_order(client: TestClient, order_id: str, reference: str, amount: str, buyer_email: str):
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
                "id": 881122,
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


def test_open_join_requires_enabled(client: TestClient, db_session: Session):
    _, event, _ = _seed_open_event(db_session)
    event.open_ambassadors_enabled = False
    db_session.commit()

    user = _register(client, "amb-join@example.com", "Ada Amb")
    blocked = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=user,
        json={"accept_terms": True},
    )
    assert blocked.status_code == 400
    assert "not enabled" in blocked.json()["detail"].lower()


def test_eligible_events_and_earnings_summary(client: TestClient, db_session: Session):
    _, event, _ = _seed_open_event(db_session)
    listed = client.get("/api/v1/promos/ambassadors/eligible-events")
    assert listed.status_code == 200
    rows = listed.json()
    assert any(r["id"] == str(event.id) for r in rows)
    assert any(r["slug"] == "open-amb-night" for r in rows)

    amb_user = _register(client, "amb-summary@example.com", "Summary Amb")
    client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb_user,
        json={"accept_terms": True},
    )
    summary = client.get(
        "/api/v1/promos/ambassador/earnings-summary",
        headers=amb_user,
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["enrollments_active"] == 1
    assert body["estimated_earnings"] == "0.00"
    assert body["payout_status"] in {"unavailable", "estimated"}


def test_open_join_requires_terms(client: TestClient, db_session: Session):
    _, event, _ = _seed_open_event(db_session)
    user = _register(client, "amb-terms@example.com", "Terms Amb")
    refused = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=user,
        json={"accept_terms": False},
    )
    assert refused.status_code == 400
    assert "terms" in refused.json()["detail"].lower()


def test_open_join_blocked_user(client: TestClient, db_session: Session):
    _, event, _ = _seed_open_event(db_session)
    user = _register(client, "amb-blocked@example.com", "Blocked Amb")
    row = db_session.query(User).filter_by(email="amb-blocked@example.com").one()
    row.ambassadors_blocked = True
    db_session.commit()

    refused = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=user,
        json={"accept_terms": True},
    )
    assert refused.status_code == 403
    assert "blocked" in refused.json()["detail"].lower()


def test_open_join_and_program(client: TestClient, db_session: Session):
    _, event, _ = _seed_open_event(db_session)

    program = client.get(f"/api/v1/promos/events/{event.id}/ambassadors/program")
    assert program.status_code == 200
    assert program.json()["enabled"] is True
    assert program.json()["commission_percent"] == "8.00"
    assert program.json()["terms_version"]

    amb_user = _register(client, "amb-join@example.com", "Ada Amb")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb_user,
        json={"accept_terms": True},
    )
    assert joined.status_code == 201, joined.text
    body = joined.json()
    assert body["program_kind"] == "open_event"
    assert body["event_id"] == str(event.id)
    assert body["commission_rate_percent"] == "8.00"
    assert body["referral_code"]
    assert body["status"] == "active"

    # Join must not create host-team or event-staff access
    from app.checkins.models import EventStaffAssignment
    from app.hosts.models import HostTeamMember

    amb_row = (
        db_session.query(User).filter_by(email="amb-join@example.com").one()
    )
    assert (
        db_session.query(HostTeamMember).filter_by(user_id=amb_row.id).count() == 0
    )
    assert (
        db_session.query(EventStaffAssignment)
        .filter_by(user_id=amb_row.id)
        .count()
        == 0
    )

    me = client.get(
        f"/api/v1/promos/events/{event.id}/ambassadors/me",
        headers=amb_user,
    )
    assert me.status_code == 200
    assert me.json()["referral_code"] == body["referral_code"]

    enrollments = client.get("/api/v1/promos/ambassador/enrollments", headers=amb_user)
    assert enrollments.status_code == 200
    assert len(enrollments.json()["enrollments"]) == 1


def test_open_attribution_and_self_referral(client: TestClient, db_session: Session):
    _, event, ga = _seed_open_event(db_session)
    amb_user = _register(client, "amb-attrib@example.com", "Tola Open")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb_user,
        json={"accept_terms": True},
    )
    assert joined.status_code == 201, joined.text
    code = joined.json()["referral_code"]

    click = client.post(
        "/api/v1/promos/referrals/click",
        json={
            "referral_code": code,
            "event_id": str(event.id),
            "landing_path": f"/events/open-amb-night?ref={code}",
        },
    )
    assert click.status_code == 201

    # Self-referral: ambassador buys with own code — no attribution
    self_order = client.post(
        "/api/v1/orders",
        headers=amb_user,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "referral_code": code,
        },
    )
    assert self_order.status_code == 201, self_order.text
    self_body = self_order.json()
    assert self_body.get("referral_code") in (None, "")
    assert self_body.get("ambassador_id") in (None, "")

    buyer = _register(client, "open-buyer@example.com")
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
    assert body["referral_code"] == code

    _pay_order(client, body["id"], body["reference"], body["total_amount"], "open-buyer@example.com")

    db_session.expire_all()
    sales = db_session.query(AmbassadorSale).all()
    sale = next(s for s in sales if str(s.order_id) == body["id"])
    assert sale.tickets_sold == 1
    assert sale.revenue_amount == Decimal("5000.00")
    assert sale.commission_owed == Decimal("400.00")  # 8% of 5000

    dash = client.get("/api/v1/promos/ambassador/me", headers=amb_user)
    assert dash.status_code == 200
    assert dash.json()["tickets_sold"] == 1
    # Ambassador dashboards must not expose payment / order refs (phase 13)
    for sale in dash.json()["sales"]:
        assert "order_reference" not in sale
        assert "order_id" not in sale
        assert "buyer_email" not in sale


def test_open_leave_and_rejoin(client: TestClient, db_session: Session):
    _, event, _ = _seed_open_event(db_session)
    amb_user = _register(client, "amb-leave@example.com", "Leave Amb")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb_user,
        json={"accept_terms": True},
    )
    assert joined.status_code == 201
    code = joined.json()["referral_code"]

    left = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/leave",
        headers=amb_user,
    )
    assert left.status_code == 200

    row = (
        db_session.query(Ambassador)
        .filter_by(event_id=event.id, referral_code=code)
        .one()
    )
    assert row.status == "inactive"

    again = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb_user,
        json={"accept_terms": True},
    )
    assert again.status_code == 201
    assert again.json()["status"] == "active"
    assert again.json()["referral_code"] == code
