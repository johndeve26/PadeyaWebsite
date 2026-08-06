"""Analytics requirement coverage: track validation, reports, authz, privacy, rollups."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.analytics.rollup_models import EventDailyAnalytics, EventTicketTypeAnalytics
from app.analytics.rollups import recalculate_all_for_event_day, recalculate_event_daily
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


def _seed(
    db: Session,
    *,
    email: str = "cov-host@example.com",
    slug: str = "cov-host",
    event_slug: str = "cov-night",
) -> tuple[Host, User, Event, TicketType]:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Coverage Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Coverage Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Coverage host"))
    start = datetime.now(UTC) + timedelta(days=4)
    event = Event(
        title="Coverage Night",
        slug=event_slug,
        description="Event for analytics requirement coverage tests.",
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
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("4000.00"),
        quantity=80,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.commit()
    db.refresh(event)
    db.refresh(tt)
    return host, user, event, tt


def _add_stream(
    db: Session,
    *,
    event: Event,
    action: str,
    anonymous_id: str,
    session_id: str,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    metadata: dict | None = None,
    is_bot: bool = False,
):
    db.add(
        AnalyticsEvent(
            event_name=action,
            target_event_id=event.id,
            host_id=event.host_id,
            anonymous_id=anonymous_id,
            session_id=session_id,
            source=source,
            medium=medium,
            campaign=campaign,
            utm_source=source,
            utm_medium=medium,
            utm_campaign=campaign,
            device_type="mobile",
            city="Lagos",
            country="NG",
            browser="Chrome",
            event_metadata=metadata,
            is_bot=is_bot,
            occurred_at=datetime.now(UTC),
        )
    )


# --- Track validation ---


def test_track_rejects_unknown_event_name(client: TestClient, db_session: Session):
    _, _, event, _ = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": "not_a_real_action",
            "target_event_id": str(event.id),
            "session_id": "sess-unknown",
            "anonymous_id": "anon-unknown",
        },
    )
    assert res.status_code in {400, 422}


def test_track_rejects_oversized_metadata(client: TestClient, db_session: Session):
    _, _, event, _ = _seed(db_session)
    meta = {f"key_{i}": "x" * 20 for i in range(100)}
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.EVENT_SHARE_CLICK,
            "target_event_id": str(event.id),
            "session_id": "sess-big",
            "anonymous_id": "anon-big",
            "metadata": meta,
        },
    )
    assert res.status_code == 422


def test_client_cannot_spoof_payment_success_or_revenue(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed(db_session)
    forbidden = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.PAYMENT_SUCCESS,
            "target_event_id": str(event.id),
            "session_id": "sess-spoof",
            "anonymous_id": "anon-spoof",
            "metadata": {"conversion_value": "99999", "amount": "99999"},
        },
    )
    assert forbidden.status_code == 403
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.event_name == TrackedAction.PAYMENT_SUCCESS)
        )
        or 0
    ) == 0

    # Allowed client action must still strip revenue keys from metadata
    ok = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.CHECKOUT_PAGE_VIEW,
            "target_event_id": str(event.id),
            "session_id": "sess-strip",
            "anonymous_id": "anon-strip",
            "request_id": "strip-rev-1",
            "metadata": {
                "conversion_value": "5000",
                "amount": "5000",
                "list_context": "checkout",
            },
        },
    )
    assert ok.status_code == 200, ok.text
    row = db_session.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.request_id == "strip-rev-1")
    )
    assert row is not None
    meta = row.event_metadata or {}
    assert "conversion_value" not in meta
    assert "amount" not in meta
    assert meta.get("list_context") == "checkout"


def test_track_persists_anonymous_session_and_utm(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.EVENT_DETAIL_VIEW,
            "target_event_id": str(event.id),
            "anonymous_id": "anon-created-99",
            "session_id": "sess-created-99",
            "utm_source": "whatsapp",
            "utm_medium": "social",
            "utm_campaign": "whatsapp-broadcast",
            "request_id": "utm-store-1",
        },
    )
    assert res.status_code == 200, res.text
    row = db_session.get(AnalyticsEvent, UUID(res.json()["id"]))
    assert row is not None
    assert row.anonymous_id == "anon-created-99"
    assert row.session_id == "sess-created-99"
    assert row.utm_source == "whatsapp"
    assert row.source == "whatsapp"
    assert row.utm_medium == "social"
    assert row.utm_campaign == "whatsapp-broadcast"
    assert row.campaign == "whatsapp-broadcast"


def test_impression_dedupe_works(client: TestClient, db_session: Session):
    _, _, event, _ = _seed(db_session)
    body = {
        "event_name": TrackedAction.EVENT_CARD_IMPRESSION,
        "target_event_id": str(event.id),
        "session_id": "sess-imp-cov",
        "anonymous_id": "anon-imp-cov",
        "metadata": {"list_context": "events_grid"},
    }
    assert client.post("/api/v1/analytics/track", json=body).status_code == 200
    assert client.post("/api/v1/analytics/track", json=body).status_code == 200
    # Unified track may always write stream — use impression endpoint for strict dedupe
    body2 = {
        "tracked_action": TrackedAction.EVENT_CARD_IMPRESSION,
        "target_event_id": str(event.id),
        "session_id": "sess-imp-cov-2",
        "anonymous_id": "anon-imp-cov-2",
        "metadata": {"list_context": "homepage_featured"},
    }
    assert (
        client.post("/api/v1/analytics/track/impression", json=body2).status_code == 200
    )
    assert (
        client.post("/api/v1/analytics/track/impression", json=body2).status_code == 200
    )
    stream = int(
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.event_name == TrackedAction.EVENT_CARD_IMPRESSION,
                AnalyticsEvent.session_id == "sess-imp-cov-2",
            )
        )
        or 0
    )
    assert stream == 1


def test_private_venue_details_not_leaked_in_metadata(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.VENUE_REVEAL_INFO_VIEW,
            "target_event_id": str(event.id),
            "session_id": "sess-venue",
            "anonymous_id": "anon-venue",
            "request_id": "venue-leak-1",
            "metadata": {
                "venue_address": "12 Hidden Courtyard, Lekki",
                "private_address": "Gate B, code 4411",
                "hidden_address": "secret",
                "online_event_url": "https://zoom.example/private",
                "join_url": "https://meet.example/xyz",
                "email": "buyer@example.com",
                "phone": "+2348012345678",
                "list_context": "event_detail",
            },
        },
    )
    assert res.status_code == 200, res.text
    row = db_session.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.request_id == "venue-leak-1")
    )
    assert row is not None
    meta = row.event_metadata or {}
    for banned in (
        "venue_address",
        "private_address",
        "hidden_address",
        "online_event_url",
        "join_url",
        "email",
        "phone",
    ):
        assert banned not in meta
    assert meta.get("list_context") == "event_detail"
    # Response must not echo private venue fields
    assert "12 Hidden Courtyard" not in res.text
    assert "Gate B" not in res.text


# --- Report calculations ---


def test_overview_funnel_sources_and_ticket_type_calculate(
    client: TestClient, db_session: Session
):
    host, host_user, event, tt = _seed(db_session)

    for i in range(5):
        _add_stream(
            db_session,
            event=event,
            action=TrackedAction.EVENT_CARD_IMPRESSION,
            anonymous_id=f"a-imp-{i}",
            session_id=f"s-imp-{i}",
            source="instagram",
            medium="social",
            campaign="early-bird-drop",
        )
    for i in range(3):
        _add_stream(
            db_session,
            event=event,
            action=TrackedAction.EVENT_CARD_CLICK,
            anonymous_id=f"a-clk-{i}",
            session_id=f"s-clk-{i}",
            source="instagram",
            medium="social",
            campaign="early-bird-drop",
        )
    for i in range(2):
        _add_stream(
            db_session,
            event=event,
            action=TrackedAction.EVENT_DETAIL_VIEW,
            anonymous_id=f"a-view-{i}",
            session_id=f"s-view-{i}",
            source="instagram",
            medium="social",
            campaign="early-bird-drop",
        )
    _add_stream(
        db_session,
        event=event,
        action=TrackedAction.TICKET_TYPE_SELECTED,
        anonymous_id="a-sel",
        session_id="s-sel",
        source="instagram",
        medium="social",
        campaign="early-bird-drop",
        metadata={"ticket_type_id": str(tt.id)},
    )
    _add_stream(
        db_session,
        event=event,
        action=TrackedAction.CHECKOUT_PAGE_VIEW,
        anonymous_id="a-chk",
        session_id="s-chk",
        source="instagram",
        medium="social",
        campaign="early-bird-drop",
    )
    _add_stream(
        db_session,
        event=event,
        action=TrackedAction.CHECKOUT_PAYMENT_STARTED,
        anonymous_id="a-pay",
        session_id="s-pay",
        source="instagram",
        medium="social",
        campaign="early-bird-drop",
    )
    # Bot noise excluded from host KPIs
    _add_stream(
        db_session,
        event=event,
        action=TrackedAction.EVENT_CARD_IMPRESSION,
        anonymous_id="bot",
        session_id="bot",
        source="instagram",
        is_bot=True,
    )
    db_session.add(
        Order(
            reference="PDY-COV-1",
            event_id=event.id,
            buyer_user_id=host_user.id,
            status="paid",
            currency="NGN",
            subtotal_amount=Decimal("4000.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("4000.00"),
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
    ov = overview.json()
    assert ov["impressions"] == 5
    assert ov["event_card_clicks"] == 3
    assert ov["event_detail_views"] == 2
    assert ov["ticket_selections"] == 1
    assert ov["checkout_starts"] == 1
    assert ov["purchases"] >= 1
    assert "buyer_email" not in ov
    assert host_user.email not in overview.text

    funnel = client.get(
        f"/api/v1/host/events/{event.id}/analytics/funnel",
        headers=headers,
    )
    assert funnel.status_code == 200, funnel.text
    fn = funnel.json()
    assert fn["impressions"] == 5
    assert fn["card_clicks"] == 3
    assert fn["detail_views"] == 2
    assert fn["ticket_selections"] == 1
    assert fn["checkout_starts"] == 1
    assert fn["payment_starts"] == 1
    assert fn["purchases"] >= 1

    sources = client.get(
        f"/api/v1/host/events/{event.id}/analytics/sources",
        headers=headers,
    )
    assert sources.status_code == 200, sources.text
    body = sources.json()
    buckets = body["buckets"]
    assert any(
        b.get("source_bucket") == "social" and b.get("impressions", 0) >= 5
        for b in buckets
    )
    campaigns = body.get("utm_campaigns") or []
    assert any(
        (c.get("source") or "").lower() == "instagram"
        and (c.get("campaign") or "") == "early-bird-drop"
        and c.get("impressions", 0) >= 5
        for c in campaigns
    )

    tickets = client.get(
        f"/api/v1/host/events/{event.id}/analytics/tickets",
        headers=headers,
    )
    assert tickets.status_code == 200, tickets.text
    types = tickets.json()["ticket_types"]
    assert types
    ga = next(t for t in types if t["name"] == "GA")
    assert ga["selections"] >= 1
    assert str(ga["ticket_type_id"]) == str(tt.id)


# --- Authz / export ---


def test_host_only_own_event_admin_platform_and_export_permissions(
    client: TestClient, db_session: Session
):
    host_a, user_a, event_a, _ = _seed(
        db_session, email="own-a@example.com", slug="own-a", event_slug="own-a-night"
    )
    _, user_b, event_b, _ = _seed(
        db_session, email="own-b@example.com", slug="own-b", event_slug="own-b-night"
    )
    admin = User(
        email="cov-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Coverage Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    buyer = User(
        email="cov-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Coverage Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add_all([admin, buyer])
    db_session.commit()
    _ = host_a

    host_headers = _login(client, user_a.email)
    assert (
        client.get(
            f"/api/v1/host/events/{event_a.id}/analytics/overview",
            headers=host_headers,
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/host/events/{event_b.id}/analytics/overview",
            headers=host_headers,
        ).status_code
        == 404
    )

    # Host event export ok for own; foreign blocked
    own_export = client.get(
        f"/api/v1/host/events/{event_a.id}/analytics/export",
        headers=host_headers,
    )
    assert own_export.status_code == 200
    assert "text/csv" in own_export.headers.get("content-type", "")
    foreign_export = client.get(
        f"/api/v1/host/events/{event_b.id}/analytics/export",
        headers=host_headers,
    )
    assert foreign_export.status_code == 404

    # Host cannot use admin platform event analytics export
    assert (
        client.get(
            "/api/v1/admin/analytics/events/export",
            headers=host_headers,
        ).status_code
        == 403
    )

    admin_headers = _login(client, admin.email)
    assert (
        client.get(
            f"/api/v1/admin/events/{event_b.id}/analytics",
            headers=admin_headers,
        ).status_code
        == 200
    )
    board = client.get(
        "/api/v1/admin/analytics/events/leaderboard",
        headers=admin_headers,
    )
    assert board.status_code == 200
    admin_export = client.get(
        "/api/v1/admin/analytics/events/export",
        headers=admin_headers,
    )
    assert admin_export.status_code == 200
    assert "revenue" in admin_export.text

    buyer_headers = _login(client, buyer.email)
    assert (
        client.get(
            f"/api/v1/host/events/{event_a.id}/analytics/overview",
            headers=buyer_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/host/events/{event_a.id}/analytics/export",
            headers=buyer_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/v1/admin/analytics/events/export",
            headers=buyer_headers,
        ).status_code
        == 403
    )
    _ = user_b


# --- Rollups ---


def test_rollup_idempotency_preserves_counts(db_session: Session):
    _, _, event, tt = _seed(
        db_session, email="roll@example.com", slug="roll-h", event_slug="roll-night"
    )
    # Rollups bucket by UTC day; stream rows use datetime.now(UTC).
    day = datetime.now(UTC).date()
    for i in range(3):
        _add_stream(
            db_session,
            event=event,
            action=TrackedAction.EVENT_CARD_IMPRESSION,
            anonymous_id=f"r{i}",
            session_id=f"rs{i}",
        )
    _add_stream(
        db_session,
        event=event,
        action=TrackedAction.TICKET_TYPE_IMPRESSION,
        anonymous_id="rtt",
        session_id="rtts",
        metadata={"ticket_type_id": str(tt.id)},
    )
    _add_stream(
        db_session,
        event=event,
        action=TrackedAction.TICKET_TYPE_SELECTED,
        anonymous_id="rts",
        session_id="rtss",
        metadata={"ticket_type_id": str(tt.id)},
    )
    db_session.commit()

    first = recalculate_all_for_event_day(db_session, event_id=event.id, day=day)
    db_session.commit()
    daily = first["daily"]
    assert isinstance(daily, EventDailyAnalytics)
    impressions = daily.impressions
    daily_id = daily.id

    second = recalculate_event_daily(db_session, event_id=event.id, day=day)
    db_session.commit()
    assert second.id == daily_id
    assert second.impressions == impressions

    third = recalculate_all_for_event_day(db_session, event_id=event.id, day=day)
    db_session.commit()
    assert third["daily"].id == daily_id
    assert third["daily"].impressions == impressions

    tt_rows = list(
        db_session.scalars(
            select(EventTicketTypeAnalytics).where(
                EventTicketTypeAnalytics.event_id == event.id,
                EventTicketTypeAnalytics.date == day,
                EventTicketTypeAnalytics.ticket_type_id == tt.id,
            )
        ).all()
    )
    assert len(tt_rows) == 1
    assert tt_rows[0].impressions >= 1
    assert tt_rows[0].selections >= 1
