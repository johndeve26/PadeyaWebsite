"""Analytics storage: rollups, dedupe keys, extended stream dimensions."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.dedupe import build_dedupe_key, claim_dedupe_key
from app.analytics.dimensions import hash_user_agent
from app.analytics.models import AnalyticsEvent
from app.analytics.rollup_models import (
    AnalyticsDedupeKey,
    EventDailyAnalytics,
)
from app.analytics.rollups import (
    recalculate_all_for_event_day,
    recalculate_event_daily,
    recalculate_range,
    resolve_rollup_window,
    run_rollups,
)
from app.analytics.taxonomy import TrackedAction
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


def _seed(db: Session) -> Event:
    user = User(
        email="storage-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Storage Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Storage Host",
        slug="storage-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="x"))
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title="Storage Night",
        slug="storage-night",
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


def test_track_persists_path_utm_and_ua_hash(client: TestClient, db_session: Session):
    event = _seed(db_session)
    rid = "storage-dims-1"
    res = client.post(
        "/api/v1/analytics/track/event",
        json={
            "tracked_action": TrackedAction.EVENT_DETAIL_VIEW,
            "target_event_id": str(event.id),
            "host_id": str(event.host_id),
            "session_id": "sess-storage-1",
            "anonymous_id": "anon-storage-1",
            "request_id": rid,
            "path": "/events/storage-night",
            "utm_source": "ig",
            "utm_medium": "social",
            "utm_campaign": "launch",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            "metadata": {"ticket_type_id": str(event.id), "page_section": "hero"},
        },
    )
    assert res.status_code == 200, res.text
    row = db_session.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.request_id == rid)
    )
    assert row is not None
    assert row.path == "/events/storage-night"
    assert row.current_path == "/events/storage-night"
    assert row.utm_source == "ig"
    assert row.source == "ig"
    assert row.utm_medium == "social"
    assert row.utm_campaign == "launch"
    assert row.user_agent_hash == hash_user_agent(row.user_agent)
    assert row.device_type == "mobile"


def test_dedupe_key_claim_is_idempotent(db_session: Session):
    key = build_dedupe_key(
        "impression",
        target_event_id=None,
        session_id="sess-a",
        extra="listing",
    )
    # Without event id + with session — still builds
    assert key is not None
    assert claim_dedupe_key(db_session, dedupe_key=key, scope="impression") is True
    db_session.commit()
    assert claim_dedupe_key(db_session, dedupe_key=key, scope="impression") is False
    count = len(list(db_session.scalars(select(AnalyticsDedupeKey))))
    assert count == 1


def test_impression_session_dedupe_skips_duplicate_stream(
    client: TestClient, db_session: Session
):
    event = _seed(db_session)
    body = {
        "target_event_id": str(event.id),
        "session_id": "sess-imp-1",
        "anonymous_id": "anon-imp-1",
        "tracked_action": TrackedAction.EVENT_CARD_IMPRESSION,
        "source": "listing",
    }
    assert client.post("/api/v1/analytics/track/impression", json=body).status_code == 200
    assert client.post("/api/v1/analytics/track/impression", json=body).status_code == 200
    stream = list(
        db_session.scalars(
            select(AnalyticsEvent).where(
                AnalyticsEvent.target_event_id == event.id,
                AnalyticsEvent.event_name == TrackedAction.EVENT_CARD_IMPRESSION,
            )
        )
    )
    assert len(stream) == 1


def test_recalculate_daily_rollup(client: TestClient, db_session: Session):
    event = _seed(db_session)
    # Rollups bucket by UTC day; track endpoints stamp occurred_at in UTC.
    day = datetime.now(UTC).date()
    for action in (
        TrackedAction.EVENT_CARD_IMPRESSION,
        TrackedAction.EVENT_CARD_CLICK,
        TrackedAction.EVENT_DETAIL_VIEW,
        TrackedAction.CHECKOUT_PAGE_VIEW,
    ):
        assert (
            client.post(
                "/api/v1/analytics/track/event",
                json={
                    "tracked_action": action,
                    "target_event_id": str(event.id),
                    "host_id": str(event.host_id),
                    "session_id": f"sess-{action}",
                    "anonymous_id": f"anon-{action}",
                    "request_id": f"rollup-{action}",
                    "utm_source": "google",
                    "utm_medium": "cpc",
                    "utm_campaign": "spring",
                    "device_type": "desktop",
                    "browser": "Chrome",
                    "country": "NG",
                    "city": "Lagos",
                },
            ).status_code
            == 200
        )

    from app.analytics.trusted import emit_payment_success
    from uuid import uuid4

    emit_payment_success(
        db_session,
        order_id=uuid4(),
        event_id=event.id,
        host_id=event.host_id,
        buyer_user_id=None,
        amount=Decimal("2000.00"),
        ticket_count=2,
    )
    db_session.commit()

    result = recalculate_all_for_event_day(db_session, event_id=event.id, day=day)
    db_session.commit()
    daily = result["daily"]
    assert isinstance(daily, EventDailyAnalytics)
    assert daily.impressions >= 1
    assert daily.card_clicks >= 1
    assert daily.detail_views >= 1
    assert daily.checkout_starts >= 1
    assert daily.payment_successes >= 1
    assert daily.tickets_sold == 2
    assert daily.gross_revenue == Decimal("2000.00")
    assert daily.conversion_view_to_purchase is not None

    # Idempotent recalculate
    again = recalculate_event_daily(db_session, event_id=event.id, day=day)
    db_session.commit()
    assert again.id == daily.id
    assert again.impressions == daily.impressions


def test_resolve_rollup_window_and_range(db_session: Session):
    event = _seed(db_session)
    day = date(2026, 1, 15)
    occurred = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    db_session.add(
        AnalyticsEvent(
            event_name=TrackedAction.EVENT_DETAIL_VIEW,
            target_event_id=event.id,
            host_id=event.host_id,
            occurred_at=occurred,
            received_at=occurred,
            is_bot=False,
            session_id="range-sess",
            anonymous_id="range-anon",
        )
    )
    db_session.commit()

    start, end = resolve_rollup_window(last_days=7, today=date(2026, 1, 20))
    assert start == date(2026, 1, 14)
    assert end == date(2026, 1, 20)

    start, end = resolve_rollup_window(
        date_from=date(2026, 1, 1), date_to=date(2026, 1, 31)
    )
    assert start == date(2026, 1, 1)
    assert end == date(2026, 1, 31)

    stats = recalculate_range(
        db_session,
        date_from=date(2026, 1, 14),
        date_to=date(2026, 1, 16),
        event_id=event.id,
        commit_every=1,
    )
    assert stats["events"] == 1
    assert stats["days"] == 3
    assert stats["event_days"] == 3

    daily = db_session.scalar(
        select(EventDailyAnalytics).where(
            EventDailyAnalytics.event_id == event.id,
            EventDailyAnalytics.date == day,
        )
    )
    assert daily is not None
    assert daily.detail_views >= 1

    # Idempotent second pass
    again = run_rollups(
        db_session,
        date_from=date(2026, 1, 14),
        date_to=date(2026, 1, 16),
        event_id=event.id,
    )
    assert again["event_days"] == 3
    db_session.refresh(daily)
    assert daily.detail_views >= 1


def test_run_analytics_rollups_cli_args():
    from scripts.run_analytics_rollups import build_parser, main

    parser = build_parser()
    args = parser.parse_args(
        ["--date-from", "2026-01-01", "--date-to", "2026-01-31"]
    )
    assert args.date_from == date(2026, 1, 1)
    assert args.date_to == date(2026, 1, 31)
    assert parser.parse_args(["--last-days", "7"]).last_days == 7
    assert main(["--date-from", "2026-01-31", "--date-to", "2026-01-01"]) == 2
    assert main(["--last-days", "0"]) == 2
    assert main(["--date-from", "2026-01-01"]) == 2
