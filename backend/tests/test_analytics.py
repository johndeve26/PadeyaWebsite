"""Advanced analytics: tracking, access control, conversion, exports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.aggregations import compute_conversion_rate
from app.analytics.models import AnalyticsEvent, ConversionEvent, EventClick, EventImpression, PageView
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
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
    db: Session, *, email: str = "an-host@example.com", slug: str = "an-host"
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Analytics Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Analytics Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Analytics host"))
    db.commit()
    return host, host_user


def _seed_event(db: Session, host: Host, *, slug: str = "an-event") -> Event:
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Analytics Night",
        slug=slug,
        description="Event used for analytics tracking and dashboards.",
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
            price=Decimal("4000.00"),
            quantity=100,
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


def test_analytics_event_tracking(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session)
    event = _seed_event(db_session, host)

    pv = client.post(
        "/api/v1/analytics/track/page-view",
        json={
            "path": f"/events/{event.slug}",
            "host_id": str(host.id),
            "event_id": str(event.id),
            "session_id": "sess-1",
        },
    )
    assert pv.status_code == 200, pv.text
    assert pv.json()["accepted"] is True

    imp = client.post(
        "/api/v1/analytics/track/impression",
        json={"event_id": str(event.id), "session_id": "sess-1", "source": "listing"},
    )
    assert imp.status_code == 200, imp.text

    click = client.post(
        "/api/v1/analytics/track/click",
        json={
            "event_id": str(event.id),
            "session_id": "sess-1",
            "click_target": "get_tickets",
        },
    )
    assert click.status_code == 200, click.text

    conv = client.post(
        "/api/v1/analytics/track/conversion",
        json={
            "stage": "checkout_start",
            "event_id": str(event.id),
            "session_id": "sess-1",
        },
    )
    assert conv.status_code == 200, conv.text

    assert db_session.query(PageView).count() == 1
    assert db_session.query(EventImpression).count() == 1
    assert db_session.query(EventClick).count() == 1
    assert db_session.query(ConversionEvent).count() >= 3  # impression+click+checkout
    assert db_session.query(AnalyticsEvent).count() >= 3


def test_host_analytics_access_control(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    _seed_event(db_session, host)
    other, other_user = _seed_host(
        db_session, email="an-other@example.com", slug="an-other"
    )
    _seed_event(db_session, other, slug="other-event")

    buyer = User(
        email="an-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(buyer)
    db_session.commit()

    denied = client.get(
        "/api/v1/analytics/host/summary", headers=_login(client, buyer.email)
    )
    assert denied.status_code in (403, 404)

    ok = client.get(
        "/api/v1/analytics/host/summary", headers=_login(client, host_user.email)
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["host_id"] == str(host.id)
    assert "tickets_sold" in body
    assert "conversion_rate" in body

    # Other host can load their own summary, not cross-host data via this endpoint
    other_sum = client.get(
        "/api/v1/analytics/host/summary", headers=_login(client, other_user.email)
    )
    assert other_sum.status_code == 200
    assert other_sum.json()["host_id"] == str(other.id)


def test_admin_analytics_access(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="an-admin-h@example.com", slug="an-adh")
    _seed_event(db_session, host, slug="admin-ev")

    host_headers = _login(client, host_user.email)
    blocked = client.get("/api/v1/analytics/admin/summary", headers=host_headers)
    assert blocked.status_code == 403

    admin = User(
        email="an-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    db_session.add(admin)
    db_session.commit()

    admin_headers = _login(client, admin.email)
    summary = client.get("/api/v1/analytics/admin/summary", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert data["total_hosts"] >= 1
    assert data["total_events"] >= 1
    assert "gross_revenue" in data
    assert "fraud_signals" in data

    revenue = client.get("/api/v1/analytics/admin/revenue", headers=admin_headers)
    assert revenue.status_code == 200
    support = client.get("/api/v1/analytics/admin/support", headers=admin_headers)
    assert support.status_code == 200
    assert "note" in support.json()


def test_conversion_calculations(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="an-conv@example.com", slug="an-conv")
    event = _seed_event(db_session, host, slug="conv-event")

    for i in range(10):
        client.post(
            "/api/v1/analytics/track/click",
            json={
                "event_id": str(event.id),
                "session_id": f"c-{i}",
                "anonymous_id": f"a-{i}",
            },
        )
    from app.analytics.trusted import emit_payment_success
    from uuid import uuid4

    for _ in range(2):
        emit_payment_success(
            db_session,
            order_id=uuid4(),
            event_id=event.id,
            host_id=host.id,
            buyer_user_id=None,
            amount=Decimal("1000.00"),
            ticket_count=1,
        )
    db_session.commit()

    summary = client.get(
        "/api/v1/analytics/host/summary",
        headers=_login(client, host_user.email),
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["event_clicks"] == 10
    assert body["checkout_completes"] == 2
    assert float(body["conversion_rate"]) == 20.0

    assert compute_conversion_rate(
        {"click": 10, "checkout_complete": 2, "impression": 0}
    ) == Decimal("20.0")


def test_export_permissions(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="an-exp@example.com", slug="an-exp")
    _seed_event(db_session, host, slug="exp-event")

    buyer = User(
        email="an-exp-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(buyer)
    db_session.commit()

    denied = client.get(
        "/api/v1/analytics/host/export.csv",
        headers=_login(client, buyer.email),
    )
    assert denied.status_code in (403, 404)

    host_csv = client.get(
        "/api/v1/analytics/host/export.csv",
        headers=_login(client, host_user.email),
    )
    assert host_csv.status_code == 200, host_csv.text
    assert "tickets_sold" in host_csv.text
    assert "text/csv" in host_csv.headers.get("content-type", "")

    admin = User(
        email="an-exp-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    db_session.add(admin)
    db_session.commit()

    admin_csv = client.get(
        "/api/v1/analytics/admin/export.csv",
        headers=_login(client, admin.email),
    )
    assert admin_csv.status_code == 200, admin_csv.text
    assert "gross_revenue" in admin_csv.text

    # Host cannot export admin CSV
    host_admin = client.get(
        "/api/v1/analytics/admin/export.csv",
        headers=_login(client, host_user.email),
    )
    assert host_admin.status_code == 403


def test_host_event_analytics_scoped(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="an-ev@example.com", slug="an-evh")
    event = _seed_event(db_session, host, slug="scoped-ev")
    other, _ = _seed_host(db_session, email="an-ev2@example.com", slug="an-evh2")
    foreign = _seed_event(db_session, other, slug="foreign-ev")

    headers = _login(client, host_user.email)
    ok = client.get(f"/api/v1/analytics/host/events/{event.id}", headers=headers)
    assert ok.status_code == 200, ok.text
    assert ok.json()["event_id"] == str(event.id)

    denied = client.get(f"/api/v1/analytics/host/events/{foreign.id}", headers=headers)
    assert denied.status_code == 404


def test_host_team_analytics_view_events(
    client: TestClient, db_session: Session
) -> None:
    """host_staff with team analytics.view_events must not be blocked by analytics.view_own."""
    from app.hosts.models import HostTeamMember
    from app.teams.workspace_pref import set_active_workspace

    host, _owner = _seed_host(
        db_session, email="an-team-h@example.com", slug="an-team-h"
    )
    _seed_event(db_session, host, slug="team-analytics-ev")
    member = User(
        email="an-team-member@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Analytics Staff",
        is_active=True,
    )
    member.roles.append(get_role_by_name(db_session, "host_staff"))
    db_session.add(member)
    db_session.flush()
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=member.id,
            role="viewer",
            role_label="Analytics",
            status="active",
            permissions_json={
                "_replace": True,
                "analytics.view_events": True,
            },
        )
    )
    db_session.commit()
    set_active_workspace(db_session, user=member, host_id=host.id)
    db_session.commit()

    headers = _login(client, member.email)
    summary = client.get("/api/v1/analytics/host/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["host_id"] == str(host.id)
