"""Host ambassador campaign lifecycle tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.promos.models import Ambassador
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _register(client: TestClient, email: str, name: str = "Fan") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    return _login(client, email)


def _seed(db: Session) -> tuple[Host, Event, TicketType]:
    host_user = User(
        email="camp-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Camp Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Camp Host",
        slug="camp-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title="Campaign Night",
        slug="campaign-night",
        description="Event for ambassador campaign tests.",
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
    db.commit()
    return host, event, ga


def test_create_pause_resume_campaign(client: TestClient, db_session: Session):
    _, event, _ = _seed(db_session)
    host = _login(client, "camp-host@example.com")

    created = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Open promo",
            "commission_percent": "7.5",
            "merch_included": False,
            "status": "public_open",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "public_open"
    assert body["is_live"] is True
    assert body["merch_included"] is False
    campaign_id = body["id"]

    db_session.expire_all()
    event_row = db_session.get(Event, event.id)
    assert event_row is not None
    assert event_row.open_ambassadors_enabled is True
    assert event_row.open_ambassador_commission_percent == Decimal("7.50")

    paused = client.post(
        f"/api/v1/promos/campaigns/{campaign_id}/pause",
        headers=host,
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    assert paused.json()["is_live"] is False

    db_session.expire_all()
    assert db_session.get(Event, event.id).open_ambassadors_enabled is False

    resumed = client.post(
        f"/api/v1/promos/campaigns/{campaign_id}/resume",
        headers=host,
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "public_open"


def test_join_via_campaign_and_remove(client: TestClient, db_session: Session):
    _, event, _ = _seed(db_session)
    host = _login(client, "camp-host@example.com")
    created = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Open promo",
            "commission_percent": "10",
            "merch_included": True,
        },
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    fan = _register(client, "camp-fan@example.com", "Camp Fan")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=fan,
        json={"accept_terms": True},
    )
    assert joined.status_code == 201, joined.text
    amb_id = joined.json()["id"]

    board = client.get(
        f"/api/v1/promos/campaigns/{campaign_id}/leaderboard",
        headers=host,
    )
    assert board.status_code == 200
    assert len(board.json()) == 1

    removed = client.post(
        f"/api/v1/promos/campaigns/{campaign_id}/ambassadors/{amb_id}/remove",
        headers=host,
    )
    assert removed.status_code == 200

    db_session.expire_all()
    amb = db_session.get(Ambassador, UUID(amb_id))
    assert amb is not None
    assert amb.status == "removed"

    rejoin = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=fan,
        json={"accept_terms": True},
    )
    assert rejoin.status_code == 403


def test_one_open_campaign_per_event(client: TestClient, db_session: Session):
    _, event, _ = _seed(db_session)
    host = _login(client, "camp-host@example.com")
    first = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Campaign A",
            "campaign_type": "event_tickets",
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Campaign B",
            "campaign_type": "event_tickets",
        },
    )
    assert second.status_code == 409
    # Different type is allowed on the same event.
    merch = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Merch campaign",
            "campaign_type": "event_merch",
        },
    )
    assert merch.status_code == 201, merch.text
