"""Host CRM follow, audience, segments, and announcements tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import AnnouncementRecipient, AudienceSegment, HostAnnouncement
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


@pytest.fixture
def announcement_dispatch_sends(monkeypatch):
    """Tests use log/dev email env; host blast requires real delivery."""
    from app.email.config import email_runtime
    from app.email.provider import SendResult

    monkeypatch.setattr(
        "app.email.config.assert_host_announcement_email_delivery",
        lambda db: email_runtime(db=db),
    )
    monkeypatch.setattr(
        "app.crm.service.send_email",
        lambda **kwargs: SendResult(ok=True, provider="smtp"),
    )


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(db: Session) -> tuple[Host, User]:
    host_user = User(
        email="crm-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="CRM Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="CRM Host",
        slug="crm-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="CRM test host"))
    db.commit()
    return host, host_user


def _seed_buyer_ticket(
    db: Session,
    host: Host,
    *,
    email: str,
    checked_in: bool = False,
    ended: bool = True,
    vip: bool = False,
) -> User:
    buyer = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="CRM Buyer",
        is_active=True,
    )
    role = get_role_by_name(db, "buyer")
    assert role is not None
    buyer.roles.append(role)
    db.add(buyer)
    db.flush()

    category = db.query(EventCategory).first()
    if ended:
        start = datetime.now(UTC) - timedelta(days=3)
        end = datetime.now(UTC) - timedelta(days=2)
        status = "completed"
    else:
        start = datetime.now(UTC) + timedelta(days=3)
        end = start + timedelta(hours=3)
        status = "published"

    event = Event(
        title=f"CRM Event {email}",
        slug=f"crm-event-{email.split('@')[0]}",
        description="Event used for CRM audience segment tests with detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=end,
        city="Lagos",
        status=status,
        featured=False,
        published_at=start - timedelta(days=1),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="VIP" if vip else "GA",
        type="vip" if vip else "regular",
        price=Decimal("5000.00"),
        quantity=100,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.flush()
    order = Order(
        reference=f"PDY-CRM-{email.split('@')[0].upper()}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt.name,
    )
    db.add(item)
    db.flush()
    db.add(
        Ticket(
            public_code=new_public_ticket_code(),
            order_id=order.id,
            order_item_id=item.id,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_user_id=buyer.id,
            status="checked_in" if checked_in else "active",
            ticket_type_name=tt.name,
            holder_name=buyer.full_name,
            holder_email=buyer.email,
            checked_in_at=datetime.now(UTC) if checked_in else None,
        )
    )
    db.commit()
    return buyer


def test_follow_unfollow_host(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    buyer = _register(client, "follower@example.com", "Follower")

    followed = client.post(
        "/api/v1/crm/follow",
        headers=buyer,
        json={"host_slug": "crm-host"},
    )
    assert followed.status_code == 201, followed.text
    assert followed.json()["username"] == "crm-host"
    assert followed.json()["marketing_opt_in"] is False

    from app.messaging.models import InAppNotification
    from sqlalchemy import select

    host_notif = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == host_user.id,
            InAppNotification.kind == "host.new_follower",
        )
    )
    assert host_notif is not None
    assert host_notif.link_path == "/host/followers"

    listing = client.get("/api/v1/crm/me/following", headers=buyer)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    opt = client.patch(
        f"/api/v1/crm/me/following/{host.id}",
        headers=buyer,
        json={"marketing_opt_in": True},
    )
    assert opt.status_code == 200
    assert opt.json()["marketing_opt_in"] is True

    removed = client.delete(f"/api/v1/crm/follow/{host.id}", headers=buyer)
    assert removed.status_code == 204
    assert client.get("/api/v1/crm/me/following", headers=buyer).json() == []


def test_follow_updates_public_legacy_follower_count(
    client: TestClient, db_session: Session
):
    """Public Legacy stats must reflect live follows even when score is stale."""
    from sqlalchemy import select

    from app.legacy.models import HostLegacyScore
    from app.legacy.seed import seed_legacy_tiers

    host, _ = _seed_host(db_session)
    seed_legacy_tiers(db_session)
    db_session.add(
        HostLegacyScore(
            host_id=host.id,
            events_hosted=0,
            completed_events=0,
            tickets_sold=0,
            verified_checkins=0,
            review_count=0,
            followers=0,
            composite_score=0,
            legacy_status="New Host",
        )
    )
    db_session.commit()

    before = client.get(f"/api/v1/u/{host.slug}/legacy")
    assert before.status_code == 200, before.text
    assert before.json()["stats"]["followers"] == 0

    buyer = _register(client, "legacy-follower@example.com", "Legacy Follower")
    followed = client.post(
        "/api/v1/crm/follow",
        headers=buyer,
        json={"host_slug": host.slug},
    )
    assert followed.status_code == 201, followed.text

    after = client.get(f"/api/v1/u/{host.slug}/legacy")
    assert after.status_code == 200, after.text
    assert after.json()["stats"]["followers"] == 1

    score = db_session.scalar(
        select(HostLegacyScore).where(HostLegacyScore.host_id == host.id)
    )
    assert score is not None
    assert score.followers == 1

    removed = client.delete(f"/api/v1/crm/follow/{host.id}", headers=buyer)
    assert removed.status_code == 204

    unfollowed = client.get(f"/api/v1/u/{host.slug}/legacy")
    assert unfollowed.json()["stats"]["followers"] == 0
    score = db_session.scalar(
        select(HostLegacyScore).where(HostLegacyScore.host_id == host.id)
    )
    assert score is not None
    assert score.followers == 0


def test_follow_by_host_id(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session)
    buyer = _register(client, "follow-by-id@example.com", "Follow By Id")

    followed = client.post(
        "/api/v1/crm/follow",
        headers=buyer,
        json={"host_id": str(host.id)},
    )
    assert followed.status_code == 201, followed.text
    assert followed.json()["host_id"] == str(host.id)


def test_follow_unknown_placeholder_host_id_returns_404(
    client: TestClient, db_session: Session
):
    _seed_host(db_session)
    buyer = _register(client, "follow-bad-id@example.com", "Bad Id")

    missing = client.post(
        "/api/v1/crm/follow",
        headers=buyer,
        json={"host_id": "00000000-0000-4000-8000-000000000001"},
    )
    assert missing.status_code == 404

    ok = client.post(
        "/api/v1/crm/follow",
        headers=buyer,
        json={"host_slug": "crm-host"},
    )
    assert ok.status_code == 201, ok.text


def test_follow_requires_host_target(client: TestClient, db_session: Session):
    _seed_host(db_session)
    buyer = _register(client, "follow-empty@example.com", "Empty")

    res = client.post("/api/v1/crm/follow", headers=buyer, json={})
    assert res.status_code == 422


def test_host_audience_access_control(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session)
    _seed_buyer_ticket(db_session, host, email="buyer-a@example.com", checked_in=True)

    stranger = _register(client, "stranger@example.com")
    denied = client.get("/api/v1/crm/host/audience", headers=stranger)
    assert denied.status_code == 404

    host_headers = _login(client, "crm-host@example.com")
    ok = client.get("/api/v1/crm/host/audience", headers=host_headers)
    assert ok.status_code == 200, ok.text
    assert ok.json()["past_buyers"] >= 1
    assert ok.json()["checked_in_attendees"] >= 1


def test_segment_creation(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session)
    _seed_buyer_ticket(db_session, host, email="seg-buyer@example.com", vip=True)
    host_headers = _login(client, "crm-host@example.com")

    segments = client.get("/api/v1/crm/host/segments", headers=host_headers)
    assert segments.status_code == 200
    assert len(segments.json()) >= 10

    created = client.post(
        "/api/v1/crm/host/segments",
        headers=host_headers,
        json={
            "name": "My VIP list",
            "segment_key": "vip_buyers",
            "description": "Custom VIP segment",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["segment_key"] == "vip_buyers"
    assert created.json()["is_system"] is False
    assert created.json()["member_count"] >= 1

    # Ensure system segment persisted
    row = (
        db_session.query(AudienceSegment)
        .filter_by(host_id=host.id, slug="vip-buyers")
        .one()
    )
    assert row.is_system is True

    deleted = client.delete(
        f"/api/v1/crm/host/segments/{created.json()['id']}",
        headers=host_headers,
    )
    assert deleted.status_code == 200

    system_delete = client.delete(
        f"/api/v1/crm/host/segments/{row.id}",
        headers=host_headers,
    )
    assert system_delete.status_code == 400


def test_announcement_creation_and_recipients(
    client: TestClient, db_session: Session, announcement_dispatch_sends
):
    host, _ = _seed_host(db_session)
    follower = _register(client, "ann-follower@example.com", "Ann Follower")
    client.post(
        "/api/v1/crm/follow",
        headers=follower,
        json={"host_id": str(host.id)},
    )
    client.patch(
        f"/api/v1/crm/me/following/{host.id}",
        headers=follower,
        json={"marketing_opt_in": True},
    )
    # Second follower opted out (default)
    opted_out = _register(client, "ann-out@example.com", "Opt Out")
    client.post(
        "/api/v1/crm/follow",
        headers=opted_out,
        json={"host_id": str(host.id)},
    )

    host_headers = _login(client, "crm-host@example.com")
    draft = client.post(
        "/api/v1/crm/host/announcements",
        headers=host_headers,
        json={
            "title": "Cancel me",
            "body_email": "This draft will be cancelled.",
            "channel": "email",
            "segment_key": "followers",
        },
    )
    assert draft.status_code == 201, draft.text
    cancelled = client.post(
        f"/api/v1/crm/host/announcements/{draft.json()['id']}/cancel",
        headers=host_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    created = client.post(
        "/api/v1/crm/host/announcements",
        headers=host_headers,
        json={
            "title": "Weekend show",
            "body_email": "Join us this weekend for a special night.",
            "body_whatsapp": "Weekend show — see you there!",
            "channel": "both",
            "segment_key": "followers",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["recipient_count"] == 2
    assert body["whatsapp_export"] is not None
    assert "WhatsApp broadcast not sent" in body["whatsapp_export"]

    recipients = body["recipients"]
    statuses = {r["email"]: r["status"] for r in recipients}
    assert statuses["ann-follower@example.com"] == "pending"
    assert statuses["ann-out@example.com"] == "skipped"

    announcement = (
        db_session.query(HostAnnouncement).filter_by(title="Weekend show").one()
    )
    assert (
        db_session.query(AnnouncementRecipient)
        .filter_by(announcement_id=announcement.id)
        .count()
        == 2
    )

    dispatched = client.post(
        f"/api/v1/crm/host/announcements/{body['id']}/dispatch-email",
        headers=host_headers,
    )
    assert dispatched.status_code == 200
    assert dispatched.json()["emailed"] == 1
    assert dispatched.json()["skipped"] == 1

    # Sent announcements cannot be cancelled
    cancel_sent = client.post(
        f"/api/v1/crm/host/announcements/{body['id']}/cancel",
        headers=host_headers,
    )
    assert cancel_sent.status_code == 400


def test_dispatch_reconciles_late_marketing_opt_in(
    client: TestClient, db_session: Session, announcement_dispatch_sends
):
    """Opt-in after draft creation should still receive email on dispatch."""
    host, _ = _seed_host(db_session)
    follower = _register(client, "late-opt@example.com", "Late Opt")
    client.post(
        "/api/v1/crm/follow",
        headers=follower,
        json={"host_id": str(host.id)},
    )
    host_headers = _login(client, "crm-host@example.com")
    created = client.post(
        "/api/v1/crm/host/announcements",
        headers=host_headers,
        json={
            "title": "Late opt-in test",
            "body_email": "You should get this after opting in.",
            "channel": "email",
            "segment_key": "followers",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["recipients"][0]["status"] == "skipped"

    client.patch(
        f"/api/v1/crm/me/following/{host.id}",
        headers=follower,
        json={"marketing_opt_in": True},
    )

    dispatched = client.post(
        f"/api/v1/crm/host/announcements/{body['id']}/dispatch-email",
        headers=host_headers,
    )
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["emailed"] == 1
    assert dispatched.json()["skipped"] == 0


def test_dispatch_rejects_log_only_email(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session)
    follower = _register(client, "log-mode@example.com", "Log Mode")
    client.post(
        "/api/v1/crm/follow",
        headers=follower,
        json={"host_id": str(host.id)},
    )
    client.patch(
        f"/api/v1/crm/me/following/{host.id}",
        headers=follower,
        json={"marketing_opt_in": True},
    )
    host_headers = _login(client, "crm-host@example.com")
    created = client.post(
        "/api/v1/crm/host/announcements",
        headers=host_headers,
        json={
            "title": "Log only",
            "body_email": "Should not fake-send in log mode.",
            "channel": "email",
            "segment_key": "followers",
        },
    )
    assert created.status_code == 201
    dispatched = client.post(
        f"/api/v1/crm/host/announcements/{created.json()['id']}/dispatch-email",
        headers=host_headers,
    )
    assert dispatched.status_code == 503
    assert "dev/log mode" in dispatched.json()["detail"].lower()


def test_recipient_targeting_past_buyers(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session)
    _seed_buyer_ticket(db_session, host, email="target@example.com", checked_in=False, ended=True)
    host_headers = _login(client, "crm-host@example.com")

    members = client.get(
        "/api/v1/crm/host/audience/members",
        headers=host_headers,
        params={"segment_key": "past_buyers"},
    )
    assert members.status_code == 200
    emails = {m["email"] for m in members.json()}
    assert "target@example.com" in emails
    member = next(m for m in members.json() if m["email"] == "target@example.com")
    assert member["display_name"] == "CRM B."

    no_shows = client.get(
        "/api/v1/crm/host/audience/members",
        headers=host_headers,
        params={"segment_key": "no_shows"},
    )
    assert no_shows.status_code == 200
    assert any(m["email"] == "target@example.com" for m in no_shows.json())
