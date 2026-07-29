"""Phase 15 — Ambassadors email / in-app / push notifications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.email.models import EmailEvent
from app.email.templates import TEMPLATES, get_template
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.messaging.models import InAppNotification
from app.promos.models import AmbassadorCampaign
from app.push.templates import KIND_ALIASES, TEMPLATES as PUSH_TEMPLATES
from app.users.models import User
from app.users.service import get_role_by_name


REQUIRED_EMAIL = [
    "ambassador_joined",
    "ambassador_first_sale",
    "ambassador_commission_payable",
    "ambassador_payout_ready",
    "ambassador_reward_rejected",
    "ambassador_reward_reversed",
    "ambassador_campaign_paused",
    "ambassador_campaign_ended",
    "host_ambassador_milestone",
    "host_ambassador_team_reward_action",
    "host_ambassador_suspicious_reversal",
]

REQUIRED_PUSH = [
    "ambassador_joined",
    "ambassador_first_sale",
    "ambassador_commission_payable",
    "ambassador_payout_ready",
    "ambassador_reward_rejected",
    "ambassador_reward_reversed",
    "ambassador_campaign_paused",
    "ambassador_campaign_ended",
    "host_ambassador_milestone",
    "host_ambassador_team_reward_action",
    "host_ambassador_suspicious_reversal",
]


def _login(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    return _login(client, email)


def _seed(db: Session) -> tuple[Host, User, Event, TicketType, AmbassadorCampaign]:
    host_user = User(
        email=f"notif-host-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Notif Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Notif Host",
        slug=f"notif-host-{uuid4().hex[:8]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Notif Night",
        slug=f"notif-night-{uuid4().hex[:8]}",
        description="Ambassador notifications test",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        open_ambassadors_enabled=True,
        open_ambassador_commission_percent=Decimal("10.00"),
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
    campaign = AmbassadorCampaign(
        host_id=host.id,
        event_id=event.id,
        name="Notif Campaign",
        status="public_open",
        source="host",
        created_by_user_id=host_user.id,
        campaign_type="event_tickets",
        commission_percent=Decimal("10.00"),
        commission_type="percentage",
        commission_value=Decimal("10.00"),
        applies_to="tickets",
        merch_included=False,
    )
    db.add(campaign)
    db.commit()
    return host, host_user, event, ga, campaign


def test_ambassador_email_and_push_templates_registered():
    for name in REQUIRED_EMAIL:
        assert name in TEMPLATES
        tpl = get_template(name)
        body = tpl.body_fn(
            {
                "event_title": "Lagos Night",
                "campaign_name": "Event Ambassadors",
                "sale_count": 10,
            }
        )
        text = " ".join(body)
        assert "Lagos Night" in text or "Pàdéyá" in text
        assert "@" not in text
        assert "psk_" not in text.lower()
        assert "order_id" not in text.lower()
    for name in REQUIRED_PUSH:
        assert name in PUSH_TEMPLATES
    assert KIND_ALIASES["ambassador.joined"] == "ambassador_joined"
    assert KIND_ALIASES["ambassador.first_sale"] == "ambassador_first_sale"
    assert KIND_ALIASES["host.ambassador_milestone"] == "host_ambassador_milestone"


def test_join_enqueues_ambassador_joined(
    client: TestClient, db_session: Session
):
    _host, _host_user, event, _ga, campaign = _seed(db_session)
    email = f"notif-amb-{uuid4().hex[:6]}@example.com"
    headers = _register(client, email, "Notif Amb")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=headers,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    assert joined.status_code == 201, joined.text

    events = (
        db_session.query(EmailEvent)
        .filter(EmailEvent.template == "ambassador_joined")
        .all()
    )
    assert any(e.recipient_email == email for e in events)

    notifs = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.kind == "ambassador.joined")
        .all()
    )
    assert notifs
    body = notifs[0].body or ""
    assert "Notif Night" in body
    assert "psk_" not in body.lower()
    assert "@example.com" not in body


def test_campaign_pause_notifies_participants(
    client: TestClient, db_session: Session
):
    host, host_user, event, _ga, campaign = _seed(db_session)
    amb_email = f"pause-amb-{uuid4().hex[:6]}@example.com"
    amb = _register(client, amb_email, "Pause Amb")
    joined = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=amb,
        json={"accept_terms": True, "campaign_id": str(campaign.id)},
    )
    assert joined.status_code == 201

    host_headers = _login(client, host_user.email)
    paused = client.post(
        f"/api/v1/promos/campaigns/{campaign.id}/pause",
        headers=host_headers,
    )
    assert paused.status_code == 200, paused.text

    emails = (
        db_session.query(EmailEvent)
        .filter(EmailEvent.template == "ambassador_campaign_paused")
        .all()
    )
    assert any(e.recipient_email == amb_email for e in emails)
    notifs = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.kind == "ambassador.campaign_paused")
        .all()
    )
    assert notifs
