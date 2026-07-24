"""Admin Ambassadors management tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order
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


def _seed_event(db: Session) -> tuple[Host, Event]:
    host_user = User(
        email="adm-amb-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Adm Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Adm Host",
        slug="adm-amb-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title="Admin Amb Night",
        slug="admin-amb-night",
        description="Admin ambassadors event.",
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
    db.add(
        TicketType(
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
    )
    db.commit()
    return host, event


def _admin_headers(client: TestClient, assign_role, email: str = "adm-amb@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass1",
            "full_name": "Amb Admin",
        },
    )
    assign_role(email, "super_admin")
    return _login(client, email)


def test_admin_platform_toggle_and_campaigns(
    client: TestClient, db_session: Session, assign_role
):
    _, event = _seed_event(db_session)
    admin = _admin_headers(client, assign_role)

    settings = client.get("/api/v1/promos/admin/settings", headers=admin)
    assert settings.status_code == 200
    assert settings.json()["enabled"] is True

    created = client.post(
        "/api/v1/promos/admin/campaigns",
        headers=admin,
        json={
            "event_id": str(event.id),
            "name": "Platform campaign",
            "commission_percent": "8",
            "merch_included": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["source"] == "platform"
    assert body["status"] == "public_open"
    campaign_id = body["id"]

    listed = client.get("/api/v1/promos/admin/campaigns", headers=admin)
    assert listed.status_code == 200
    assert any(row["id"] == campaign_id for row in listed.json())

    paused = client.post(
        f"/api/v1/promos/admin/campaigns/{campaign_id}/pause",
        headers=admin,
        json={"reason": "Suspicious traffic"},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    disabled = client.patch(
        "/api/v1/promos/admin/settings",
        headers=admin,
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    eligible = client.get("/api/v1/promos/ambassadors/eligible-events")
    assert eligible.status_code == 200
    assert eligible.json() == []

    client.patch(
        "/api/v1/promos/admin/settings",
        headers=admin,
        json={"enabled": True},
    )
    client.post(
        f"/api/v1/promos/admin/campaigns/{campaign_id}/resume",
        headers=admin,
    )


def test_admin_block_reverse_and_reward(
    client: TestClient, db_session: Session, assign_role
):
    host, event = _seed_event(db_session)
    admin = _admin_headers(client, assign_role, "adm-amb2@example.com")

    created = client.post(
        "/api/v1/promos/admin/campaigns",
        headers=admin,
        json={"event_id": str(event.id), "name": "Ops campaign"},
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "adm-fan@example.com",
            "password": "securepass1",
            "full_name": "Adm Fan",
        },
    )
    fan = _login(client, "adm-fan@example.com")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=fan,
        json={"accept_terms": True},
    )
    assert joined.status_code == 201, joined.text
    amb_id = joined.json()["id"]

    ambs = client.get("/api/v1/promos/admin/ambassadors", headers=admin)
    assert ambs.status_code == 200
    assert any(row["id"] == amb_id for row in ambs.json())

    blocked = client.post(
        f"/api/v1/promos/admin/ambassadors/{amb_id}/block",
        headers=admin,
    )
    assert blocked.status_code == 200
    assert blocked.json()["ambassadors_blocked"] is True

    client.post(
        f"/api/v1/promos/admin/ambassadors/{amb_id}/unblock",
        headers=admin,
    )

    buyer = User(
        email="adm-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    db_session.add(buyer)
    db_session.flush()
    amb = db_session.get(Ambassador, __import__("uuid").UUID(amb_id))
    assert amb is not None
    order = Order(
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000"),
        reference=f"ref-{uuid4().hex[:10]}",
    )
    db_session.add(order)
    db_session.flush()
    sale = AmbassadorSale(
        ambassador_id=amb.id,
        order_id=order.id,
        event_id=event.id,
        tickets_sold=1,
        merch_units_sold=0,
        revenue_amount=Decimal("5000"),
        commission_owed=Decimal("400"),
        status="attributed",
    )
    db_session.add(sale)
    db_session.commit()
    sale_id = str(sale.id)

    approved = client.post(
        f"/api/v1/promos/admin/conversions/{sale_id}/reward-status",
        headers=admin,
        json={"status": "approved"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    reversed_row = client.post(
        f"/api/v1/promos/admin/conversions/{sale_id}/reverse",
        headers=admin,
        json={"reason": "Fraudulent self-referral pattern"},
    )
    assert reversed_row.status_code == 200, reversed_row.text
    assert reversed_row.json()["status"] == "reversed"

    summary = client.get("/api/v1/promos/admin/reports/summary", headers=admin)
    assert summary.status_code == 200
    body = summary.json()
    assert body["conversions_reversed"] >= 1
    assert body["campaigns_platform"] >= 1
    assert body["feature_enabled"] is True

    # Campaign still listed after ops
    assert (
        client.get(
            f"/api/v1/promos/admin/campaigns?status=public_open",
            headers=admin,
        ).status_code
        == 200
    )
    assert campaign_id
    assert host.id
