"""Fan Connect suggestion upgrade — scoring weights, geo privacy, dismiss, modes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.fan_connect import constants as C
from app.fan_connect.diversity import mix_suggestions
from app.fan_connect.models import FanConnectSuggestionFeedback, FanConnection
from app.fan_connect.scoring import FanConnectScoringService
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from app.passport.service import ensure_passport


def test_compute_score_exact_weights_and_clamp():
    svc = FanConnectScoringService()
    shared = {
        "_has_shared_upcoming": True,
        "_has_shared_checked_in": True,
        "_has_friend_of_friend": True,
        "_mutual_connection_count": 2,
        "_shared_host_count": 3,
        "_shared_category_count": 2,
        "_passport_complete": True,
        "_both_recently_active": True,
        "_nearby_distance_points": C.SCORE_NEARBY_WITHIN_2KM,
        "_has_shared_city": True,
        "_has_shared_area_zone": True,
        "_similar_attended_categories": True,
        "_similar_venue_types": True,
        "_similar_host_types": True,
        "_often_same_area_city": True,
        "_same_scene": True,
        "_boost_similar_views": True,
        "_boost_similar_connects": True,
        "_penalty_dismissed": False,
        "_penalty_repeatedly_ignored": False,
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
    assert "mutual_connection" not in breakdown  # not stacked with FoF
    assert breakdown["shared_hosts"] == 20  # capped
    assert breakdown["shared_categories"] == 15
    assert breakdown["passport_complete"] == 5
    assert breakdown["recently_active"] == 5
    assert breakdown["nearby_distance"] == 25
    assert breakdown["shared_city"] == 10
    assert breakdown["shared_area_zone"] == 10
    assert score == 100  # clamped

    # Closer distance beats farther when isolating the geo signal
    far = {"_nearby_distance_points": C.SCORE_NEARBY_WITHIN_25KM}
    near = {"_nearby_distance_points": C.SCORE_NEARBY_WITHIN_2KM}
    s_far, _ = svc.compute_score(far)
    s_near, _ = svc.compute_score(near)
    assert s_near > s_far


def test_fof_boost_not_double_counted_with_mutual():
    svc = FanConnectScoringService()
    with_fof = {
        "_has_friend_of_friend": True,
        "_mutual_connection_count": 3,
    }
    score, breakdown = svc.compute_score(with_fof)
    assert breakdown["friend_of_friend"] == 20
    assert score == 20


def test_diversity_mixer_does_not_pure_distance_dominate():
    cards = []
    for i in range(12):
        cards.append(
            (
                90 - i,
                {"user_id": f"n{i}", "username": f"near{i}"},
                ["nearby"],
            )
        )
    cards.append((50, {"user_id": "e1", "username": "event1"}, ["shared_event"]))
    cards.append((48, {"user_id": "f1", "username": "fof1"}, ["fof"]))
    cards.append((45, {"user_id": "fr1", "username": "fresh1"}, ["fresh"]))
    mixed = mix_suggestions(cards, limit=12, mode=C.MODE_MIXED)
    usernames = {c["username"] for c in mixed}
    assert "event1" in usernames or "fof1" in usernames or "fresh1" in usernames
    # Not all 12 slots from nearby-only monoculture when other buckets exist
    nearby_count = sum(1 for c in mixed if c["username"].startswith("near"))
    assert nearby_count < 12


def test_safe_reasons_include_fof_and_never_gps():
    svc = FanConnectScoringService()
    reasons = svc.safe_reasons(
        db=None,  # type: ignore[arg-type]
        shared={
            "_upcoming_event_titles": ["Afrobeats Night Live"],
            "_shared_host_names": ["Mainland Vibes"],
            "categories": ["nightlife"],
            "_has_friend_of_friend": True,
            "_mutual_connection_count": 3,
            "_distance_label": "2.4 km away",
            "_has_shared_city": True,
            "_shared_cities": ["Lagos"],
        },
    )
    labels = " ".join(r["label"].lower() for r in reasons)
    assert "afrobeats night live" in labels
    assert "mainland vibes" in labels
    assert "mutual" in labels
    assert "2.4 km away" in labels
    assert "latitude" not in labels
    assert "longitude" not in labels
    assert "6.52" not in labels


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


def _public_passport(db_session: Session, user: User, username: str, **extra) -> None:
    p = ensure_passport(db_session, user)
    p.username = username
    p.visibility = "public"
    p.display_name = user.full_name or username
    p.appear_in_directory = True
    p.favorite_categories = extra.get("favorite_categories", ["Afrobeats"])
    p.avatar_url = extra.get("avatar_url", "https://cdn.example/a.jpg")
    p.tagline = extra.get("tagline", "Out for the night")
    db_session.commit()


def _seed_host(db_session: Session, email: str) -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Sug Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add(user)
    db_session.flush()
    host = Host(
        user_id=user.id,
        display_name="Sug Host",
        slug=email.split("@")[0].replace(".", "-"),
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db_session.commit()
    return host


def _public_event(
    db_session: Session,
    *,
    host: Host,
    slug: str,
    title: str,
    city: str = "Lagos",
    area: str | None = "Lekki",
    lat: str | None = "6.4698",
    lng: str | None = "3.5852",
    days: int = 10,
) -> Event:
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=days)
    event = Event(
        title=title,
        slug=slug,
        description="Public night for Fan Connect suggestion upgrade tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city=city,
        area=area,
        venue_name="Public Hall",
        address="12 Secret Street",
        latitude=lat,
        longitude=lng,
        approximate_latitude=lat,
        approximate_longitude=lng,
        status="published",
        visibility="listed",
        event_type="public",
        location_visibility="city_only",
        featured=False,
        published_at=datetime.now(UTC) - timedelta(days=1),
        venue_type="club",
    )
    db_session.add(event)
    db_session.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("5000.00"),
        quantity=100,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db_session.add(tt)
    db_session.commit()
    return event


def _ticket(db_session: Session, *, buyer: User, event: Event) -> None:
    tt = db_session.query(TicketType).filter(TicketType.event_id == event.id).one()
    order = Order(
        reference=f"PDY-SUG-{uuid4().hex[:10]}",
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


def test_same_event_strong_boost_and_no_private_leak(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, "sug-host@example.com")
    h_a = _auth(client, "sug-a@example.com", "Sug A")
    h_b = _auth(client, "sug-b@example.com", "Sug B")
    a = _user(db_session, "sug-a@example.com")
    b = _user(db_session, "sug-b@example.com")
    _age_user(db_session, a)
    _age_user(db_session, b)
    _public_passport(db_session, a, "suga")
    _public_passport(db_session, b, "sugb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)

    event = _public_event(
        db_session, host=host, slug="sug-afro-night", title="Afrobeat Night Live"
    )
    _ticket(db_session, buyer=a, event=event)
    _ticket(db_session, buyer=b, event=event)

    r = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert r.status_code == 200, r.text
    body = r.json()
    match = next((i for i in body["items"] if i["username"] == "sugb"), None)
    assert match is not None
    assert match["score"] >= C.SCORE_MIN_SHOW
    assert match["user_id"]
    blob = str(match).lower()
    assert "secret street" not in blob
    assert "latitude" not in blob
    assert "@example.com" not in blob
    assert any("afrobeat night live" in x["label"].lower() for x in match["reasons"])


def test_closer_user_ranks_higher_when_geo_provided(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, "sug-geo-host@example.com")
    h_a = _auth(client, "sug-geo-a@example.com", "Geo A")
    h_near = _auth(client, "sug-geo-near@example.com", "Geo Near")
    h_far = _auth(client, "sug-geo-far@example.com", "Geo Far")
    a = _user(db_session, "sug-geo-a@example.com")
    near_u = _user(db_session, "sug-geo-near@example.com")
    far_u = _user(db_session, "sug-geo-far@example.com")
    for u in (a, near_u, far_u):
        _age_user(db_session, u)
    _public_passport(db_session, a, "geoa", favorite_categories=["Afrobeats"])
    _public_passport(db_session, near_u, "geonear", favorite_categories=["Afrobeats"])
    _public_passport(db_session, far_u, "geofar", favorite_categories=["Afrobeats"])
    _enable_connect(client, h_a)
    _enable_connect(client, h_near)
    _enable_connect(client, h_far)

    near_ev = _public_event(
        db_session,
        host=host,
        slug="sug-near-lekki",
        title="Lekki Night",
        lat="6.4698",
        lng="3.5852",
        area="Lekki",
    )
    far_ev = _public_event(
        db_session,
        host=host,
        slug="sug-far-abuja",
        title="Abuja Night",
        city="Abuja",
        area="Abuja",
        lat="9.0765",
        lng="7.3986",
        days=12,
    )
    # Actor + near share Lekki; actor + far share only category — give far a ticket too
    _ticket(db_session, buyer=a, event=near_ev)
    _ticket(db_session, buyer=near_u, event=near_ev)
    _ticket(db_session, buyer=far_u, event=far_ev)
    # Also give actor ticket to far so both can match on upcoming if needed — actually
    # for ranking we pass actor lat near Lekki so near gets distance boost.
    r = client.get(
        "/api/v1/fan-connect/suggestions",
        headers=h_a,
        params={"lat": 6.47, "lng": 3.585, "radius_km": 25, "mode": "mixed"},
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    near_i = next((i for i in items if i["username"] == "geonear"), None)
    far_i = next((i for i in items if i["username"] == "geofar"), None)
    assert near_i is not None
    if far_i is not None:
        assert near_i["score"] >= far_i["score"]
    blob = str(items).lower()
    assert "6.47" not in blob  # actor GPS not echoed
    assert "latitude" not in blob


def test_dismiss_excludes_and_more_like_this_records(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, "sug-dis-host@example.com")
    h_a = _auth(client, "sug-dis-a@example.com", "Dis A")
    h_b = _auth(client, "sug-dis-b@example.com", "Dis B")
    a = _user(db_session, "sug-dis-a@example.com")
    b = _user(db_session, "sug-dis-b@example.com")
    _age_user(db_session, a)
    _age_user(db_session, b)
    _public_passport(db_session, a, "disa")
    _public_passport(db_session, b, "disb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    event = _public_event(
        db_session, host=host, slug="sug-dis-night", title="Dismiss Night"
    )
    _ticket(db_session, buyer=a, event=event)
    _ticket(db_session, buyer=b, event=event)

    listed = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    match = next(i for i in listed.json()["items"] if i["username"] == "disb")
    uid = match["user_id"]

    mlt = client.post(
        f"/api/v1/fan-connect/suggestions/{uid}/more-like-this", headers=h_a
    )
    assert mlt.status_code == 200, mlt.text
    fb = (
        db_session.query(FanConnectSuggestionFeedback)
        .filter_by(actor_user_id=a.id, target_user_id=b.id, action="more_like_this")
        .count()
    )
    assert fb >= 1

    d = client.post(
        f"/api/v1/fan-connect/suggestions/{uid}/dismiss",
        headers=h_a,
        json={"reason": "not_interested"},
    )
    assert d.status_code == 200, d.text
    after = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert all(i["username"] != "disb" for i in after.json()["items"])


def test_location_preference_saves_city_not_raw_gps(
    client: TestClient, db_session: Session
):
    h = _auth(client, "sug-loc@example.com", "Loc Fan")
    _enable_connect(client, h)
    r = client.post(
        "/api/v1/fan-connect/location/preference",
        headers=h,
        json={"city": "Lagos", "area": "Lekki", "precision": "city"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["city"] == "Lagos"
    assert body["area"] == "Lekki"
    assert body["latitude_approx"] is None
    assert body["longitude_approx"] is None

    # Query lat/lng on suggestions must not auto-persist
    client.get(
        "/api/v1/fan-connect/suggestions",
        headers=h,
        params={"lat": 6.5244, "lng": 3.3792},
    )
    again = client.get("/api/v1/fan-connect/location/preference", headers=h)
    assert again.status_code == 200
    assert again.json()["latitude_approx"] is None


def test_fof_mode_and_interests_mode(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "sug-fof-host@example.com")
    h_a = _auth(client, "sug-fof-a@example.com", "FoF A")
    h_b = _auth(client, "sug-fof-b@example.com", "FoF B")
    h_c = _auth(client, "sug-fof-c@example.com", "FoF C")
    a = _user(db_session, "sug-fof-a@example.com")
    b = _user(db_session, "sug-fof-b@example.com")
    c = _user(db_session, "sug-fof-c@example.com")
    for u, un in ((a, "fofa"), (b, "fofb"), (c, "fofc")):
        _age_user(db_session, u)
        _public_passport(db_session, u, un, favorite_categories=["Comedy"])
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    _enable_connect(client, h_c)

    # Connect A↔B and B↔C so A and C are FoF
    now = datetime.now(UTC)
    for left, right, req in ((a, b, a), (b, c, b)):
        low, high = (left.id, right.id) if left.id < right.id else (right.id, left.id)
        recipient = right if req.id == left.id else left
        db_session.add(
            FanConnection(
                user_low_id=low,
                user_high_id=high,
                requester_user_id=req.id,
                recipient_user_id=recipient.id,
                status=C.STATUS_CONNECTED,
                accepted_at=now,
                score=50,
            )
        )
    db_session.commit()

    event = _public_event(
        db_session, host=host, slug="sug-fof-comedy", title="Comedy Night FoF"
    )
    _ticket(db_session, buyer=a, event=event)
    _ticket(db_session, buyer=c, event=event)

    fof = client.get(
        "/api/v1/fan-connect/suggestions",
        headers=h_a,
        params={"mode": "connections_of_connections"},
    )
    assert fof.status_code == 200, fof.text
    assert any(i["username"] == "fofc" for i in fof.json()["items"]) or fof.json().get(
        "empty_title"
    )

    interests = client.get(
        "/api/v1/fan-connect/suggestions",
        headers=h_a,
        params={"mode": "same_interests"},
    )
    assert interests.status_code == 200
    if not interests.json()["items"]:
        assert "interest" in (interests.json().get("empty_description") or "").lower()
