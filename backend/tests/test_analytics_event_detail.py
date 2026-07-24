"""Detailed per-event analytics host/admin endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.analytics.taxonomy import TrackedAction
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(
    db: Session, *, email: str = "det-host@example.com", slug: str = "det-host"
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Detail Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Detail Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Detail analytics host"))
    db.commit()
    return host, host_user


def _seed_admin(db: Session) -> User:
    admin = User(
        email="det-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Detail Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db, "super_admin"))
    db.add(admin)
    db.commit()
    return admin


def _seed_event(db: Session, host: Host, *, slug: str = "det-event") -> Event:
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Detail Night",
        slug=slug,
        description="Event used for detailed analytics endpoints.",
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
            quantity_sold=2,
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


def _track(
    db: Session,
    *,
    event: Event,
    action: str,
    source: str | None = None,
    medium: str | None = None,
    anonymous_id: str = "anon-1",
    session_id: str = "sess-1",
    user_id=None,
    metadata: dict | None = None,
    is_bot: bool = False,
    device_type: str | None = "mobile",
    city: str | None = "Lagos",
):
    db.add(
        AnalyticsEvent(
            event_name=action,
            target_event_id=event.id,
            host_id=event.host_id,
            user_id=user_id,
            anonymous_id=anonymous_id,
            session_id=session_id,
            source=source,
            medium=medium,
            utm_source=source,
            utm_medium=medium,
            device_type=device_type,
            city=city,
            country="NG",
            browser="Chrome",
            event_metadata=metadata,
            is_bot=is_bot,
            occurred_at=datetime.now(UTC),
        )
    )


def test_host_event_overview_funnel_and_export(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    event = _seed_event(db_session, host)
    tt = db_session.query(TicketType).filter_by(event_id=event.id).one()

    _track(db_session, event=event, action=TrackedAction.EVENT_CARD_IMPRESSION)
    _track(
        db_session,
        event=event,
        action=TrackedAction.EVENT_CARD_IMPRESSION,
        anonymous_id="anon-2",
        session_id="sess-2",
    )
    _track(db_session, event=event, action=TrackedAction.EVENT_CARD_CLICK)
    _track(db_session, event=event, action=TrackedAction.EVENT_DETAIL_VIEW)
    _track(
        db_session,
        event=event,
        action=TrackedAction.TICKET_TYPE_SELECTED,
        metadata={"ticket_type_id": str(tt.id)},
    )
    _track(db_session, event=event, action=TrackedAction.CHECKOUT_PAGE_VIEW)
    _track(db_session, event=event, action=TrackedAction.CHECKOUT_PAYMENT_STARTED)
    # Bot should be excluded by default
    _track(
        db_session,
        event=event,
        action=TrackedAction.EVENT_CARD_IMPRESSION,
        anonymous_id="bot",
        session_id="bot-sess",
        is_bot=True,
    )
    db_session.add(
        Order(
            reference="PDY-DET-1",
            event_id=event.id,
            buyer_user_id=host_user.id,
            status="paid",
            currency="NGN",
            subtotal_amount=Decimal("5000.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("5000.00"),
            buyer_email=host_user.email,
            buyer_name=host_user.full_name or "Buyer",
            paid_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    headers = _login(client, host_user.email)
    overview = client.get(
        f"/api/v1/host/events/{event.id}/analytics/overview",
        headers=headers,
    )
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["impressions"] == 2
    assert body["event_card_clicks"] == 1
    assert body["event_detail_views"] == 1
    assert body["ticket_selections"] == 1
    assert body["checkout_starts"] == 1
    assert body["purchases"] >= 1
    assert body["filters"]["include_bots"] is False

    funnel = client.get(
        f"/api/v1/host/events/{event.id}/analytics/funnel",
        headers=headers,
    )
    assert funnel.status_code == 200, funnel.text
    assert funnel.json()["payment_starts"] == 1

    timeseries = client.get(
        f"/api/v1/host/events/{event.id}/analytics/timeseries",
        headers=headers,
    )
    assert timeseries.status_code == 200, timeseries.text
    assert timeseries.json()["granularity"] in {"hour", "day", "week"}

    sources = client.get(
        f"/api/v1/host/events/{event.id}/analytics/sources",
        headers=headers,
    )
    assert sources.status_code == 200, sources.text
    assert len(sources.json()["buckets"]) >= 1

    tickets = client.get(
        f"/api/v1/host/events/{event.id}/analytics/tickets",
        headers=headers,
    )
    assert tickets.status_code == 200, tickets.text
    assert tickets.json()["ticket_types"][0]["name"] == "GA"

    audience = client.get(
        f"/api/v1/host/events/{event.id}/analytics/audience",
        headers=headers,
    )
    assert audience.status_code == 200, audience.text
    assert audience.json()["follower_conversion"] is not None

    export = client.get(
        f"/api/v1/host/events/{event.id}/analytics/export",
        headers=headers,
    )
    assert export.status_code == 200, export.text
    assert "text/csv" in export.headers.get("content-type", "")
    assert "impressions" in export.text


def test_host_event_analytics_scoped(client: TestClient, db_session: Session):
    host_a, user_a = _seed_host(db_session, email="a@example.com", slug="host-a")
    host_b, _ = _seed_host(db_session, email="b@example.com", slug="host-b")
    event_b = _seed_event(db_session, host_b, slug="foreign-event")

    headers = _login(client, user_a.email)
    resp = client.get(
        f"/api/v1/host/events/{event_b.id}/analytics/overview",
        headers=headers,
    )
    assert resp.status_code == 404
    _ = host_a


def test_admin_event_analytics_leaderboard_compare_export(
    client: TestClient, db_session: Session
):
    host, _ = _seed_host(db_session)
    event = _seed_event(db_session, host)
    admin = _seed_admin(db_session)
    _track(
        db_session,
        event=event,
        action=TrackedAction.EVENT_DETAIL_VIEW,
        source="instagram",
        medium="social",
    )
    db_session.commit()

    headers = _login(client, admin.email)
    detail = client.get(
        f"/api/v1/admin/events/{event.id}/analytics",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    assert "overview" in detail.json()
    assert "funnel" in detail.json()

    board = client.get(
        "/api/v1/admin/analytics/events/leaderboard",
        headers=headers,
        params={"sort_by": "detail_views"},
    )
    assert board.status_code == 200, board.text
    assert board.json()["sort_by"] == "detail_views"
    assert any(str(r["event_id"]) == str(event.id) for r in board.json()["events"])

    channels = client.get(
        "/api/v1/admin/analytics/events/channels",
        headers=headers,
    )
    assert channels.status_code == 200, channels.text
    assert "buckets" in channels.json()

    compare = client.get(
        "/api/v1/admin/analytics/events/compare",
        headers=headers,
        params=[("event_ids", str(event.id))],
    )
    assert compare.status_code == 200, compare.text
    assert len(compare.json()["events"]) == 1

    export = client.get(
        "/api/v1/admin/analytics/events/export",
        headers=headers,
    )
    assert export.status_code == 200, export.text
    assert "revenue" in export.text


def test_buyer_cannot_access_host_event_analytics(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session)
    event = _seed_event(db_session, host)
    buyer = User(
        email="det-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    buyer_role = get_role_by_name(db_session, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db_session.add(buyer)
    db_session.commit()

    headers = _login(client, buyer.email)
    resp = client.get(
        f"/api/v1/host/events/{event.id}/analytics/overview",
        headers=headers,
    )
    assert resp.status_code == 403
