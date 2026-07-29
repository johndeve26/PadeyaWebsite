"""FanConnectScoringService — weights, threshold, safe labels."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.fan_connect import constants as C
from app.fan_connect.scoring import FanConnectScoringService
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from app.passport.service import ensure_passport


def test_compute_score_weights_and_clamp():
    svc = FanConnectScoringService()
    shared = {
        "_has_shared_upcoming": True,
        "_both_ticketed_upcoming": True,
        "_has_shared_checked_in": True,
        "_has_friend_of_friend": True,
        "_shared_host_count": 3,
        "_shared_category_count": 5,
        "_has_shared_city": True,
        "_passport_complete": True,
        "_both_recently_active": True,
        "_mutual_connection_count": 2,
        "_penalty_recently_declined": False,
        "_penalty_too_many_outgoing": False,
        "_penalty_low_trust": False,
        "_penalty_report_risk": False,
    }
    score, breakdown = svc.compute_score(shared)
    assert breakdown["upcoming_event"] == 35
    assert "upcoming_tickets_extra" not in breakdown
    assert breakdown["checked_in_event"] == 25
    assert breakdown["friend_of_friend"] == 20
    assert breakdown["shared_hosts"] == 20
    assert breakdown["shared_categories"] == 15
    assert breakdown["shared_city"] == 10
    assert breakdown["recently_active"] == 5
    assert breakdown["passport_complete"] == 5
    assert score == 100  # clamped

    penalized = dict(shared)
    penalized["_penalty_recently_declined"] = True
    penalized["_has_shared_upcoming"] = False
    penalized["_both_ticketed_upcoming"] = False
    penalized["_has_friend_of_friend"] = False
    # 25+20+15+10+5+5 - 40 = 40
    score2, _ = svc.compute_score(penalized)
    assert score2 == 40


def test_recommendation_labels_and_min_show():
    svc = FanConnectScoringService()
    assert svc.recommendation_label(85) == C.LABEL_STRONG
    assert svc.recommendation_label(70) == C.LABEL_GOOD
    assert svc.recommendation_label(45) == C.LABEL_SIMILAR
    assert svc.recommendation_label(39) is None


def test_safe_reasons_never_unsafe_copy():
    svc = FanConnectScoringService()
    reasons = svc.safe_reasons(
        db=None,  # type: ignore[arg-type]
        shared={
            "_upcoming_event_titles": ["Afrobeats Night Live"],
            "_shared_host_names": ["DJ Maze"],
            "categories": ["comedy"],
            "_checked_in_category_names": ["tech"],
            "_has_shared_checked_in": True,
            "_has_shared_upcoming": True,
            "_shared_badges": [
                {"slug": "event-merch", "name": "Merch Collector", "criteria_key": "merch"}
            ],
            "_has_shared_city": True,
            "_shared_cities": ["Lagos"],
        },
    )
    labels = " ".join(r["label"].lower() for r in reasons)
    assert "afrobeats night live" in labels
    assert "dj maze" in labels
    assert "comedy" in labels
    assert "merch" in labels
    assert "vip" not in labels
    assert "₦" not in labels
    assert "private" not in labels
    assert "hidden" not in labels
    for r in reasons:
        assert r["code"] in C.SAFE_REASON_CODES


def _auth(client: TestClient, email: str, name: str = "Fan") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _user(db_session: Session, email: str) -> User:
    return db_session.query(User).filter(User.email == email).one()


def _age_user(db_session: Session, user: User) -> None:
    user.created_at = datetime.now(UTC) - timedelta(days=30)
    db_session.commit()


def _enable_connect(client: TestClient, headers: dict[str, str]) -> None:
    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={
            "fan_connect_enabled": True,
            "allow_connection_requests": True,
            "discoverable_for_same_events": True,
            "discoverable_for_similar_interests": True,
            "request_policy": "public_passports",
            "show_public_city": True,
        },
    )
    assert r.status_code == 200, r.text


def _public_passport(db_session: Session, user: User, username: str) -> None:
    p = ensure_passport(db_session, user)
    p.username = username
    p.visibility = "public"
    p.display_name = user.full_name or username
    p.appear_in_directory = True
    p.favorite_categories = ["Afrobeats"]
    db_session.commit()


def _seed_host(db_session: Session, email: str) -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Score Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add(user)
    db_session.flush()
    host = Host(
        user_id=user.id,
        display_name="Score Host",
        slug=email.split("@")[0].replace(".", "-"),
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db_session.commit()
    return host


def _upcoming_ticket(
    db_session: Session, *, host: Host, buyer: User, slug: str, title: str
) -> Event:
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title=title,
        slug=slug,
        description="Upcoming public night for Fan Connect scoring tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name="Public Hall",
        address="12 Secret Street",
        status="published",
        visibility="listed",
        event_type="public",
        location_visibility="city_only",
        featured=False,
        published_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(event)
    db_session.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("5000.00"),
        quantity=100,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db_session.add(tt)
    db_session.flush()
    order = Order(
        reference=f"PDY-SC-{slug.upper()}-{uuid4().hex[:8]}",
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
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt.name,
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(
        Ticket(
            public_code=new_public_ticket_code(),
            order_id=order.id,
            order_item_id=item.id,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_user_id=buyer.id,
            status="active",
            ticket_type_name=tt.name,
            holder_name=buyer.full_name,
            holder_email=buyer.email,
        )
    )
    db_session.commit()
    return event


def _attend_upcoming(db_session: Session, *, buyer: User, event: Event) -> None:
    tt = db_session.query(TicketType).filter(TicketType.event_id == event.id).one()
    order = Order(
        reference=f"PDY-SC-ATT-{uuid4().hex[:10]}",
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
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt.name,
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(
        Ticket(
            public_code=new_public_ticket_code(),
            order_id=order.id,
            order_item_id=item.id,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_user_id=buyer.id,
            status="active",
            ticket_type_name=tt.name,
            holder_name=buyer.full_name,
            holder_email=buyer.email,
        )
    )
    db_session.commit()


def test_suggestions_require_score_threshold(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "fc-score-host@example.com")
    h_a = _auth(client, "fc-score-a@example.com", "Score A")
    h_b = _auth(client, "fc-score-b@example.com", "Score B")
    a = _user(db_session, "fc-score-a@example.com")
    b = _user(db_session, "fc-score-b@example.com")
    _age_user(db_session, a)
    _age_user(db_session, b)
    _public_passport(db_session, a, "scorea")
    _public_passport(db_session, b, "scoreb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)

    event = _upcoming_ticket(
        db_session,
        host=host,
        buyer=a,
        slug="score-upcoming-night",
        title="Afrobeats Night Live",
    )
    _attend_upcoming(db_session, buyer=b, event=event)

    r = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "total" in body and "page" in body
    items = body["items"]
    match = next((i for i in items if i["username"] == "scoreb"), None)
    assert match is not None
    assert match["score"] >= C.SCORE_MIN_SHOW
    assert match["match_label"] in {
        C.LABEL_STRONG,
        C.LABEL_GOOD,
        C.LABEL_SIMILAR,
    }
    assert match["score_band"] in {
        C.SCORE_BAND_STRONG,
        C.SCORE_BAND_GOOD,
        C.SCORE_BAND_SIMILAR,
    }
    assert match["cta_state"] == C.CTA_CONNECT
    assert match["connection_status"]
    assert match["reasons"]
    blob = str(match).lower()
    assert "vip" not in blob
    assert "secret street" not in blob
    assert "@example.com" not in blob
    assert any("afrobeats night live" in (x["label"].lower()) for x in match["reasons"])

    by_event = client.get(
        f"/api/v1/events/{event.slug}/fan-connect",
        headers=h_a,
    )
    assert by_event.status_code == 200, by_event.text
    assert any(i["username"] == "scoreb" for i in by_event.json()["items"])
