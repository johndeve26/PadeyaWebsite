"""Analytics dimensions: privacy scrubbing, IP hash, idempotency."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.dimensions import hash_ip, scrub_metadata
from app.analytics.models import AnalyticsEvent
from app.analytics.taxonomy import TrackedAction
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


def _seed(db: Session) -> Event:
    user = User(
        email="dim-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Dim Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Dim Host",
        slug="dim-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="x"))
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title="Dimensions Night",
        slug="dimensions-night",
        description="Enough characters for event description body.",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
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
            price=Decimal("1000.00"),
            quantity=50,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=4,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    db.refresh(event)
    return event


def test_scrub_metadata_strips_pii_and_payment():
    cleaned = scrub_metadata(
        {
            "ticket_type_id": "abc",
            "email": "buyer@example.com",
            "card_number": "4111111111111111",
            "venue_address": "12 Secret St",
            "ip": "1.2.3.4",
            "promo_code": "EARLY",
            "nested": {"email": "x"},
        }
    )
    assert cleaned == {"ticket_type_id": "abc", "promo_code": "EARLY"}


def test_hash_ip_is_stable_and_not_raw():
    a = hash_ip("203.0.113.10")
    b = hash_ip("203.0.113.10")
    assert a == b
    assert a is not None
    assert "203.0.113.10" not in a
    assert len(a) == 64


def test_track_event_stores_dimensions(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/event",
        json={
            "tracked_action": "ticket_type_selected",
            "target_event_id": str(event.id),
            "anonymous_id": "anon-1",
            "session_id": "sess-dim-1",
            "request_id": "req-dim-1",
            "utm_source": "instagram",
            "utm_medium": "social",
            "utm_campaign": "summer",
            "landing_page": "/events?ref=ig",
            "current_path": f"/events/{event.slug}/checkout",
            "previous_path": f"/events/{event.slug}",
            "device_type": "mobile",
            "country": "NG",
            "city": "Lagos",
            "metadata": {
                "ticket_type_id": "tt-1",
                "ticket_type_name": "GA",
                "ticket_price": 1000,
                "email": "should-strip@example.com",
            },
            "require_known_action": True,
        },
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"},
    )
    assert res.status_code == 200, res.text
    row = (
        db_session.query(AnalyticsEvent)
        .filter(AnalyticsEvent.request_id == "req-dim-1")
        .one()
    )
    assert row.event_name == TrackedAction.TICKET_TYPE_SELECTED
    assert row.target_event_id == event.id
    assert row.anonymous_id == "anon-1"
    assert row.source == "instagram"
    assert row.medium == "social"
    assert row.campaign == "summer"
    assert row.city == "Lagos"
    assert row.country == "NG"
    assert row.ip_hash is not None
    assert "email" not in (row.event_metadata or {})
    assert row.event_metadata["ticket_type_name"] == "GA"
    assert row.properties["ticket_type_name"] == "GA"
    assert row.is_bot is False
    assert row.device_type in {"mobile", "desktop"}  # UA may override client hint
    assert row.received_at is not None


def test_request_id_idempotent(client: TestClient, db_session: Session):
    event = _seed(db_session)
    body = {
        "tracked_action": "event_share_click",
        "target_event_id": str(event.id),
        "request_id": "req-idem-1",
        "require_known_action": True,
    }
    first = client.post("/api/v1/analytics/track/event", json=body)
    second = client.post("/api/v1/analytics/track/event", json=body)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert (
        db_session.query(AnalyticsEvent)
        .filter(AnalyticsEvent.request_id == "req-idem-1")
        .count()
        == 1
    )
