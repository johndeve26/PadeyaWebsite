"""Dedupe, trust gates, and bot filtering for analytics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent, EventImpression, PageView
from app.analytics.taxonomy import TrackedAction
from app.analytics.utils import (
    generate_dedupe_key,
    is_likely_bot,
    normalize_utm_params,
    visitor_identity,
)
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


def _seed(db: Session) -> Event:
    user = User(
        email="dedupe-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Dedupe Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Dedupe Host",
        slug="dedupe-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="x"))
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title="Dedupe Night",
        slug="dedupe-night",
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


def test_utils_bot_utm_dedupe_key():
    assert is_likely_bot("Googlebot/2.1")
    assert not is_likely_bot("Mozilla/5.0 (iPhone)")
    utm = normalize_utm_params(utm_source="IG", source=None)
    assert utm["source"] == "ig"
    assert utm["utm_source"] == "ig"
    key = generate_dedupe_key(
        "impression",
        target_event_id="11111111-1111-1111-1111-111111111111",
        session_id="sess-1",
        list_context="home",
    )
    assert key is not None
    assert "ctx:home" in key
    assert visitor_identity(anonymous_id="a1") == "a:a1"


def test_client_cannot_emit_payment_success(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/event",
        json={
            "tracked_action": TrackedAction.PAYMENT_SUCCESS,
            "target_event_id": str(event.id),
            "session_id": "sess-pay",
            "metadata": {"conversion_value": "9999", "amount": "9999"},
        },
    )
    assert res.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(AnalyticsEvent)) == 0


def test_client_cannot_send_conversion_amount(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/conversion",
        json={
            "stage": "checkout_start",
            "tracked_action": TrackedAction.CHECKOUT_PAGE_VIEW,
            "target_event_id": str(event.id),
            "session_id": "sess-amt",
            "amount": "5000.00",
        },
    )
    assert res.status_code == 403


def test_client_cannot_emit_checkout_complete(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/conversion",
        json={
            "stage": "checkout_complete",
            "target_event_id": str(event.id),
            "session_id": "sess-cc",
        },
    )
    assert res.status_code == 403


def test_impression_deduped_per_session_context(client: TestClient, db_session: Session):
    event = _seed(db_session)
    body = {
        "target_event_id": str(event.id),
        "session_id": "sess-imp-dedupe",
        "anonymous_id": "anon-imp",
        "tracked_action": TrackedAction.EVENT_CARD_IMPRESSION,
        "source": "listing",
        "metadata": {"list_context": "home_featured"},
    }
    assert client.post("/api/v1/analytics/track/impression", json=body).status_code == 200
    assert client.post("/api/v1/analytics/track/impression", json=body).status_code == 200
    imps = int(
        db_session.scalar(select(func.count()).select_from(EventImpression)) or 0
    )
    stream = int(
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.event_name == TrackedAction.EVENT_CARD_IMPRESSION)
        )
        or 0
    )
    assert imps == 1
    assert stream == 1

    # Different list context counts again
    body2 = {**body, "metadata": {"list_context": "search_results"}}
    assert client.post("/api/v1/analytics/track/impression", json=body2).status_code == 200
    assert (
        db_session.scalar(select(func.count()).select_from(EventImpression)) or 0
    ) == 2


def test_detail_view_unique_window_but_total_page_views(
    client: TestClient, db_session: Session
):
    event = _seed(db_session)
    body = {
        "path": f"/events/{event.slug}",
        "target_event_id": str(event.id),
        "host_id": str(event.host_id),
        "session_id": "sess-detail",
        "anonymous_id": "anon-detail",
        "tracked_action": TrackedAction.EVENT_DETAIL_VIEW,
    }
    assert client.post("/api/v1/analytics/track/page-view", json=body).status_code == 200
    assert client.post("/api/v1/analytics/track/page-view", json=body).status_code == 200
    totals = int(db_session.scalar(select(func.count()).select_from(PageView)) or 0)
    uniques = int(
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.event_name == TrackedAction.EVENT_DETAIL_VIEW)
        )
        or 0
    )
    assert totals == 2
    assert uniques == 1


def test_clicks_count_every_time(client: TestClient, db_session: Session):
    event = _seed(db_session)
    body = {
        "target_event_id": str(event.id),
        "session_id": "sess-click",
        "anonymous_id": "anon-click",
        "tracked_action": TrackedAction.EVENT_CARD_CLICK,
        "click_target": "card",
    }
    assert client.post("/api/v1/analytics/track/click", json=body).status_code == 200
    assert client.post("/api/v1/analytics/track/click", json=body).status_code == 200
    from app.analytics.models import EventClick

    assert (
        db_session.scalar(select(func.count()).select_from(EventClick)) or 0
    ) == 2
    stream = list(
        db_session.scalars(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_name == TrackedAction.EVENT_CARD_CLICK
            )
        )
    )
    assert len(stream) == 2
    # First is unique_click
    assert stream[0].event_metadata and stream[0].event_metadata.get("unique_click") is True
    assert stream[1].event_metadata and stream[1].event_metadata.get("unique_click") is False


def test_bot_flagged_on_stream(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/event",
        json={
            "tracked_action": TrackedAction.EVENT_DETAIL_VIEW,
            "target_event_id": str(event.id),
            "host_id": str(event.host_id),
            "session_id": "sess-bot",
            "anonymous_id": "anon-bot",
            "request_id": "bot-1",
            "user_agent": "Mozilla/5.0 (compatible; Googlebot/2.1)",
        },
    )
    assert res.status_code == 200
    row = db_session.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.request_id == "bot-1")
    )
    assert row is not None
    assert row.is_bot is True
