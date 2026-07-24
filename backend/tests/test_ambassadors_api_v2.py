"""Phase 10 Ambassadors domain API tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.promos.ambassador_domain import AmbassadorConversion, AmbassadorParticipant
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session, *, tag: str) -> tuple[str, str, Event, Host]:
    host_email = f"v2-host-{tag}@example.com"
    amb_email = f"v2-amb-{tag}@example.com"
    host_user = User(
        email=host_email,
        password_hash=hash_password("securepass1"),
        full_name="V2 Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="V2 Host",
        slug=f"v2-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    amb_user = User(
        email=amb_email,
        password_hash=hash_password("securepass1"),
        full_name="V2 Amb",
        is_active=True,
    )
    db.add(amb_user)
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=9)
    event = Event(
        title="V2 Amb Night",
        slug=f"v2-amb-night-{tag}",
        description="Phase 10 API",
        category_id=category.id if category else None,
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
    return host_email, amb_email, event, host


def test_host_create_join_track_and_me_flow(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, amb_email, event, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    amb_h = _login(client, amb_email)

    created = client.post(
        "/api/v1/host/ambassadors/campaigns",
        headers=host_h,
        json={
            "event_id": str(event.id),
            "name": "V2 Event Ambassadors",
            "campaign_type": "event",
            "commission_type": "percentage",
            "commission_value": "8",
            "visibility": "public_open",
            "status": "active",
            "cookie_window_days": 30,
        },
    )
    assert created.status_code == 201, created.text
    campaign = created.json()
    assert campaign["campaign_type"] == "event"
    assert campaign["visibility"] == "public_open"
    assert campaign["is_joinable"] is True

    eligible = client.get("/api/v1/ambassadors/eligible-events")
    assert eligible.status_code == 200
    assert any(e["slug"] == event.slug for e in eligible.json())

    status = client.get(f"/api/v1/events/{event.slug}/ambassador-status")
    assert status.status_code == 200
    assert status.json()["enabled"] is True

    join = client.post(
        f"/api/v1/events/{event.slug}/ambassador/join",
        headers=amb_h,
        json={"accept_terms": True},
    )
    assert join.status_code == 200, join.text
    participant = join.json()
    code = participant["ambassador_code"]
    assert code

    me = client.get("/api/v1/ambassadors/me", headers=amb_h)
    assert me.status_code == 200
    assert me.json()["status"] == "active"

    campaigns = client.get("/api/v1/ambassadors/me/campaigns", headers=amb_h)
    assert campaigns.status_code == 200
    assert len(campaigns.json()) == 1

    links = client.get("/api/v1/ambassadors/me/links", headers=amb_h)
    assert links.status_code == 200
    assert links.json()[0]["event_path"].endswith(f"?ref={code}")

    link = client.get(
        f"/api/v1/events/{event.slug}/ambassador/link", headers=amb_h
    )
    assert link.status_code == 200
    assert link.json()["ambassador_code"] == code

    click = client.post(
        "/api/v1/ambassadors/track-click",
        json={
            "ambassador_code": code,
            "event_id": str(event.id),
            "session_id": "sess-v2",
            "landing_url": f"/events/{event.slug}?ref={code}",
        },
    )
    assert click.status_code == 200, click.text
    assert click.json()["ok"] is True
    assert click.json()["attribution_id"]

    checkout = client.post(
        "/api/v1/ambassadors/track-checkout-started",
        json={
            "ambassador_code": code,
            "event_id": str(event.id),
            "session_id": "sess-v2",
            "source": "code",
        },
    )
    assert checkout.status_code == 200, checkout.text

    earnings = client.get("/api/v1/ambassadors/me/earnings", headers=amb_h)
    assert earnings.status_code == 200
    assert earnings.json()["confirmed_conversions"] == 0

    parts = client.get(
        f"/api/v1/host/ambassadors/campaigns/{campaign['id']}/participants",
        headers=host_h,
    )
    assert parts.status_code == 200
    assert len(parts.json()) == 1
    assert parts.json()[0]["clicks"] == 1

    analytics = client.get("/api/v1/host/ambassadors/analytics", headers=host_h)
    assert analytics.status_code == 200
    assert analytics.json()["clicks"] == 1
    assert analytics.json()["active_participants"] == 1

    paused = client.post(
        f"/api/v1/host/ambassadors/campaigns/{campaign['id']}/pause",
        headers=host_h,
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"


def test_admin_block_and_reverse(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    host_email, amb_email, event, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    amb_h = _login(client, amb_email)

    admin_email = f"v2-admin-{tag}@example.com"
    db_session.add(
        User(
            email=admin_email,
            password_hash=hash_password("securepass1"),
            full_name="V2 Admin",
            is_active=True,
        )
    )
    db_session.commit()
    assign_role(admin_email, "super_admin")
    admin_h = _login(client, admin_email)

    created = client.post(
        "/api/v1/host/ambassadors/campaigns",
        headers=host_h,
        json={
            "event_id": str(event.id),
            "name": "Admin path campaign",
            "campaign_type": "event",
            "commission_value": "5",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]

    join = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign_id},
    )
    assert join.status_code == 200, join.text
    participant_id = join.json()["id"]
    code = join.json()["ambassador_code"]

    # Seed a conversion via code lookup (avoids cross-session UUID bind quirks).
    db_session.expire_all()
    participant = db_session.scalar(
        select(AmbassadorParticipant).where(
            AmbassadorParticipant.ambassador_code == code
        )
    )
    assert participant is not None
    conversion_id = uuid4()
    conversion = AmbassadorConversion(
        id=conversion_id,
        campaign_id=participant.campaign_id,
        participant_id=participant.id,
        conversion_type="ticket",
        gross_amount=Decimal("5000"),
        eligible_amount=Decimal("5000"),
        commission_amount=Decimal("250"),
        status="approved",
        dedupe_key=f"test:{uuid4()}",
        verified_at=datetime.now(UTC),
    )
    db_session.add(conversion)
    db_session.commit()

    profiles = client.get("/api/v1/admin/ambassadors", headers=admin_h)
    assert profiles.status_code == 200
    assert len(profiles.json()) >= 1

    blocked = client.post(
        f"/api/v1/admin/ambassadors/participants/{participant_id}/block",
        headers=admin_h,
        json={"reason": "abuse"},
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"

    reversed_row = client.post(
        f"/api/v1/admin/ambassadors/conversions/{conversion_id}/reverse",
        headers=admin_h,
        json={"reason": "fraudulent referral"},
    )
    assert reversed_row.status_code == 200
    assert reversed_row.json()["status"] == "reversed"

    # Idempotent reverse
    again = client.post(
        f"/api/v1/admin/ambassadors/conversions/{conversion_id}/reverse",
        headers=admin_h,
        json={"reason": "again"},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "reversed"
