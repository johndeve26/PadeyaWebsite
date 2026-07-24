"""Fan Connect privacy & safety — eligibility, suggestions, requests, messaging."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.fan_connect import constants as C
from app.fan_connect.eligibility import ensure_connect_settings
from app.fan_connect.scoring import FanConnectScoringService
from app.hosts.models import Host, HostProfile
from app.messaging.relationships import ensure_settings as ensure_message_settings
from app.payments.models import Order, OrderItem
from app.passport.models import FanBadge, UserBadge
from app.passport.seed import seed_fan_badges
from app.passport.service import ensure_passport
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def _auth(client: TestClient, email: str, name: str = "Fan") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _user(db: Session, email: str) -> User:
    return db.query(User).filter(User.email == email).one()


def _age(db: Session, user: User) -> None:
    user.created_at = datetime.now(UTC) - timedelta(days=45)
    db.commit()


def _enable(
    client: TestClient,
    headers: dict[str, str],
    *,
    requests: bool = True,
    same_events: bool = True,
    similar: bool = True,
    city: bool = True,
    policy: str = "public_passports",
) -> None:
    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={
            "fan_connect_enabled": True,
            "allow_connection_requests": requests,
            "discoverable_for_same_events": same_events,
            "discoverable_for_similar_interests": similar,
            "show_public_city": city,
            "request_policy": policy,
        },
    )
    assert r.status_code == 200, r.text


def _passport(
    db: Session,
    user: User,
    username: str,
    *,
    visibility: str = "public",
    categories: list[str] | None = None,
    city: str = "Lagos",
) -> None:
    p = ensure_passport(db, user)
    p.username = username
    p.visibility = visibility
    p.display_name = user.full_name or username
    p.appear_in_directory = visibility == "public"
    p.favorite_categories = list(categories or ["Nightlife"])
    p.show_badges = True
    _ = city  # public city comes from safe event attendance, not passport fields
    db.commit()


def _award_shared_badges(db: Session, *users: User, count: int = 3) -> None:
    """Shared public badges push category-only pairs over SCORE_MIN_SHOW."""
    seed_fan_badges(db)
    badges = list(
        db.scalars(select(FanBadge).where(FanBadge.is_active.is_(True)).limit(count)).all()
    )
    assert len(badges) >= count
    for user in users:
        for badge in badges:
            exists = db.scalar(
                select(UserBadge).where(
                    UserBadge.user_id == user.id,
                    UserBadge.badge_id == badge.id,
                )
            )
            if exists is None:
                db.add(UserBadge(user_id=user.id, badge_id=badge.id))
    db.commit()


def _seed_host(db: Session, email: str, name: str = "Safety Host") -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name=name,
        slug=email.split("@")[0].replace(".", "-") + "-" + uuid4().hex[:4],
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db.commit()
    return host


def _follow(db: Session, *, fan: User, host: Host) -> None:
    exists = (
        db.query(HostFollower)
        .filter(HostFollower.user_id == fan.id, HostFollower.host_id == host.id)
        .first()
    )
    if exists is None:
        db.add(HostFollower(host_id=host.id, user_id=fan.id, marketing_opt_in=False))
        db.commit()


def _public_checked_in(
    db: Session,
    *,
    host: Host,
    buyer: User,
    slug: str,
    title: str = "Public Safety Night",
    ticket_name: str = "GA",
    ticket_type: str = "regular",
) -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) - timedelta(days=3)
    event = Event(
        title=title,
        slug=slug,
        description="Public Fan Connect safety fixture event with enough description text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name="Public Hall",
        address="99 Hidden VIP Compound",
        status="published",
        visibility="listed",
        event_type="public",
        location_visibility="city_only",
        featured=False,
        published_at=start - timedelta(days=1),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name=ticket_name,
        type=ticket_type,
        price=Decimal("25000.00"),
        quantity=50,
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
        reference=f"PDY-SAFE-{uuid4().hex[:10]}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("25000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("25000.00"),
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
        unit_price=Decimal("25000.00"),
        line_total=Decimal("25000.00"),
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
            status="checked_in",
            ticket_type_name=tt.name,
            holder_name=buyer.full_name,
            holder_email=buyer.email,
            checked_in_at=datetime.now(UTC),
        )
    )
    db.commit()
    return event


def _attend(db: Session, *, buyer: User, event: Event) -> None:
    tt = db.query(TicketType).filter(TicketType.event_id == event.id).one()
    order = Order(
        reference=f"PDY-SAFE-ATT-{uuid4().hex[:10]}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=tt.price,
        discount_amount=Decimal("0"),
        total_amount=tt.price,
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
        unit_price=tt.price,
        line_total=tt.price,
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
            status="checked_in",
            ticket_type_name=tt.name,
            holder_name=buyer.full_name,
            holder_email=buyer.email,
            checked_in_at=datetime.now(UTC),
        )
    )
    db.commit()


def _pair_with_shared_event(
    client: TestClient,
    db: Session,
    *,
    prefix: str,
) -> tuple[dict[str, str], dict[str, str], User, User, Host, Event]:
    host = _seed_host(db, f"{prefix}-host@example.com")
    h_a = _auth(client, f"{prefix}-a@example.com", "Viewer A")
    h_b = _auth(client, f"{prefix}-b@example.com", "Target B")
    a = _user(db, f"{prefix}-a@example.com")
    b = _user(db, f"{prefix}-b@example.com")
    _age(db, a)
    _age(db, b)
    _passport(db, a, f"{prefix}a")
    _passport(db, b, f"{prefix}b")
    _enable(client, h_a)
    _enable(client, h_b)
    event = _public_checked_in(
        db,
        host=host,
        buyer=a,
        slug=f"{prefix}-night",
        title="Safety Public Night",
        ticket_name="VIP Table",
        ticket_type="vip",
    )
    _attend(db, buyer=b, event=event)
    return h_a, h_b, a, b, host, event


def _assert_no_private_leak(payload) -> None:
    blob = str(payload).lower()
    for banned in (
        "secret",
        "hidden vip compound",
        "vip table",
        "@example.com",
        "paystack",
        "pdy-safe",
        "25000",
        "order_id",
        "payment",
        "locked vault",
        "shipping",
        "+234",
    ):
        assert banned not in blob, banned


# --- Eligibility -------------------------------------------------------------


def test_private_passport_excluded(client: TestClient, db_session: Session):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcpriv"
    )
    _passport(db_session, b, "fcprivb", visibility="private")

    can = client.get("/api/v1/fan-connect/can-connect/fcprivb", headers=h_a)
    assert can.status_code == 200
    assert can.json()["allowed"] is False
    assert "passport_not_public" in can.json()["denials"]

    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert sug.status_code == 200
    assert all(i["username"] != "fcprivb" for i in sug.json()["items"])


def test_unlisted_passport_excluded(client: TestClient, db_session: Session):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcunl"
    )
    _passport(db_session, b, "fcunlb", visibility="unlisted")

    can = client.get("/api/v1/fan-connect/can-connect/fcunlb", headers=h_a)
    assert can.status_code == 200
    assert can.json()["allowed"] is False
    assert "passport_not_public" in can.json()["denials"]

    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert all(i["username"] != "fcunlb" for i in sug.json()["items"])


def test_fan_connect_disabled_excluded(client: TestClient, db_session: Session):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcoff"
    )
    off = client.patch(
        "/api/v1/fan-connect/settings",
        headers=h_b,
        json={"fan_connect_enabled": False, "allow_connection_requests": False},
    )
    assert off.status_code == 200

    can = client.get("/api/v1/fan-connect/can-connect/fcoffb", headers=h_a)
    assert can.json()["allowed"] is False
    assert "target_connect_off" in can.json()["denials"]

    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert all(i["username"] != "fcoffb" for i in sug.json()["items"])


def test_requests_disabled_excluded(client: TestClient, db_session: Session):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcreq"
    )
    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=h_b,
        json={"allow_connection_requests": False},
    )
    assert r.status_code == 200

    can = client.get("/api/v1/fan-connect/can-connect/fcreqb", headers=h_a)
    assert can.json()["allowed"] is False
    assert "target_requests_off" in can.json()["denials"]

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "fcreqb"},
    )
    assert req.status_code == 403


def test_blocked_users_excluded_from_suggestions(
    client: TestClient, db_session: Session
):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcblk"
    )
    # Visible before block
    sug0 = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert any(i["username"] == "fcblkb" for i in sug0.json()["items"])

    blocked = client.post(
        "/api/v1/fan-connect/block",
        headers=h_a,
        json={"username": "fcblkb", "reason": "demo block"},
    )
    assert blocked.status_code == 204, blocked.text

    can = client.get("/api/v1/fan-connect/can-connect/fcblkb", headers=h_a)
    assert can.json()["allowed"] is False
    denials = can.json()["denials"]
    assert "blocked" in denials or "connection_blocked" in denials

    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert all(i["username"] != "fcblkb" for i in sug.json()["items"])


def test_suspended_users_excluded(client: TestClient, db_session: Session):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcsus"
    )
    settings = ensure_message_settings(db_session, b)
    settings.messaging_suspended_at = datetime.now(UTC)
    db_session.commit()

    can = client.get("/api/v1/fan-connect/can-connect/fcsusb", headers=h_a)
    assert can.json()["allowed"] is False
    assert "messaging_suspended" in can.json()["denials"]

    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert all(i["username"] != "fcsusb" for i in sug.json()["items"])


def test_admin_hidden_users_excluded(client: TestClient, db_session: Session):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fchide"
    )
    pp = ensure_passport(db_session, b)
    pp.admin_hidden_at = datetime.now(UTC)
    db_session.commit()

    # Username resolve 404s for admin-hidden
    can = client.get("/api/v1/fan-connect/can-connect/fchideb", headers=h_a)
    assert can.status_code == 404

    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert all(i["username"] != "fchideb" for i in sug.json()["items"])


# --- Suggestions -------------------------------------------------------------


def test_same_public_event_produces_suggestion(client: TestClient, db_session: Session):
    h_a, _h_b, _a, _b, _host, _event = _pair_with_shared_event(
        client, db_session, prefix="fcev"
    )
    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert sug.status_code == 200, sug.text
    match = next((i for i in sug.json()["items"] if i["username"] == "fcevb"), None)
    assert match is not None
    assert match["score"] >= C.SCORE_MIN_SHOW
    reason_codes = {r["code"] for r in match["reasons"]}
    assert reason_codes & {
        C.REASON_SHARED_CHECKED_IN,
        C.REASON_SHARED_PUBLIC_EVENT,
        C.REASON_SHARED_UPCOMING_EVENT,
    }
    for r in match["reasons"]:
        assert r["code"] in C.SAFE_REASON_CODES
    _assert_no_private_leak(match)


def test_same_host_follow_produces_suggestion(client: TestClient, db_session: Session):
    h1 = _seed_host(db_session, "fc-host-a@example.com", "Host Alpha")
    h2 = _seed_host(db_session, "fc-host-b@example.com", "Host Beta")
    ha = _auth(client, "fc-hostsug-a@example.com", "HostSug A")
    hb = _auth(client, "fc-hostsug-b@example.com", "HostSug B")
    a = _user(db_session, "fc-hostsug-a@example.com")
    b = _user(db_session, "fc-hostsug-b@example.com")
    _age(db_session, a)
    _age(db_session, b)
    _passport(db_session, a, "hostsuga", categories=["Nightlife", "Music", "Comedy"])
    _passport(db_session, b, "hostsugb", categories=["Nightlife", "Music", "Comedy"])
    _enable(client, ha)
    _enable(client, hb)
    for host in (h1, h2):
        _follow(db_session, fan=a, host=host)
        _follow(db_session, fan=b, host=host)

    sug = client.get("/api/v1/fan-connect/suggestions", headers=ha)
    assert sug.status_code == 200, sug.text
    match = next((i for i in sug.json()["items"] if i["username"] == "hostsugb"), None)
    assert match is not None
    assert match["score"] >= C.SCORE_MIN_SHOW
    assert any(r["code"] == C.REASON_SHARED_HOST for r in match["reasons"])
    _assert_no_private_leak(match)


def test_shared_category_produces_suggestion(client: TestClient, db_session: Session):
    """Shared passport categories + place/city affinity must clear SCORE_MIN_SHOW.

    Category alone (+15) is below the floor under the exact weighted model; badges
    no longer add score points (reason labels only).
    """
    host = _seed_host(db_session, "fc-catsug-host@example.com", "Cat Host")
    ha = _auth(client, "fc-catsug-a@example.com", "Cat A")
    hb = _auth(client, "fc-catsug-b@example.com", "Cat B")
    a = _user(db_session, "fc-catsug-a@example.com")
    b = _user(db_session, "fc-catsug-b@example.com")
    _age(db_session, a)
    _age(db_session, b)
    cats = ["Nightlife", "Music", "Comedy", "Tech"]
    _passport(db_session, a, "catsuga", categories=cats)
    _passport(db_session, b, "catsugb", categories=cats)
    _award_shared_badges(db_session, a, b, count=3)
    _enable(client, ha, same_events=False, similar=True)
    _enable(client, hb, same_events=False, similar=True)

    # Shared public-safe attendance → city/area/scene place signals
    event = _public_checked_in(
        db_session,
        host=host,
        buyer=a,
        slug="fc-cat-nightlife",
        title="Category Nightlife Night",
    )
    _attend(db_session, buyer=b, event=event)

    sug = client.get("/api/v1/fan-connect/suggestions", headers=ha)
    assert sug.status_code == 200, sug.text
    match = next((i for i in sug.json()["items"] if i["username"] == "catsugb"), None)
    assert match is not None
    assert match["score"] >= C.SCORE_MIN_SHOW
    assert any(r["code"] == C.REASON_SHARED_CATEGORY for r in match["reasons"])
    for r in match["reasons"]:
        assert r["code"] in C.SAFE_REASON_CODES
    _assert_no_private_leak(match)


def test_score_below_threshold_hidden(client: TestClient, db_session: Session):
    ha = _auth(client, "fc-low-a@example.com", "Low A")
    hb = _auth(client, "fc-low-b@example.com", "Low B")
    a = _user(db_session, "fc-low-a@example.com")
    b = _user(db_session, "fc-low-b@example.com")
    _age(db_session, a)
    _age(db_session, b)
    # Single weak category overlap → score well under 40
    _passport(db_session, a, "lowa", categories=["Gospel"])
    _passport(db_session, b, "lowb", categories=["Gospel"])
    _enable(client, ha, same_events=False, similar=True, city=False)
    _enable(client, hb, same_events=False, similar=True, city=False)

    sug = client.get("/api/v1/fan-connect/suggestions", headers=ha)
    assert sug.status_code == 200
    assert all(i["username"] != "lowb" for i in sug.json()["items"])


def test_safe_reasons_generated_unsafe_never():
    svc = FanConnectScoringService()
    reasons = svc.safe_reasons(
        db=None,  # type: ignore[arg-type]
        shared={
            "_upcoming_event_titles": ["Safety Public Night"],
            "_shared_host_names": ["Safety Host"],
            "categories": ["Nightlife"],
            "_has_shared_checked_in": True,
            "_checked_in_category_names": ["Nightlife"],
            "_has_shared_upcoming": False,
            "_shared_badges": [{"slug": "first-checkin", "name": "First Check-in"}],
            "_has_shared_city": True,
            "_shared_cities": ["Lagos"],
            # Poison fields — must never surface as reason codes/labels
            "ticket_type": "VIP Table",
            "order_reference": "PDY-SAFE-SECRET",
            "amount": "25000",
            "venue_address": "99 Hidden VIP Compound",
            "vault_url": "https://evil.example/locked-vault",
        },
    )
    assert reasons
    for r in reasons:
        assert r["code"] in C.SAFE_REASON_CODES
        label = r["label"].lower()
        assert "vip" not in label
        assert "25000" not in label
        assert "pdy-safe" not in label
        assert "hidden vip" not in label
        assert "vault" not in label
        assert "@" not in label
    unsafe_codes = {
        "vip_ticket",
        "spend_amount",
        "private_event",
        "hidden_venue",
        "payment",
        "order",
        "vault",
    }
    assert not (unsafe_codes & {r["code"] for r in reasons})


# --- Privacy payloads --------------------------------------------------------


def test_connect_surfaces_never_expose_vip_order_or_venue(
    client: TestClient, db_session: Session
):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcleak"
    )
    can = client.get("/api/v1/fan-connect/can-connect/fcleakb", headers=h_a)
    assert can.status_code == 200
    assert can.json()["allowed"] is True
    _assert_no_private_leak(can.json())

    sug = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    match = next(i for i in sug.json()["items"] if i["username"] == "fcleakb")
    _assert_no_private_leak(match)
    for r in match["reasons"]:
        assert r["code"] in C.SAFE_REASON_CODES
        assert "vip" not in r["label"].lower()


# --- Requests ----------------------------------------------------------------


def test_duplicate_request_blocked(client: TestClient, db_session: Session):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcdup"
    )
    first = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "fcdupb", "message": "First"},
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "fcdupb", "message": "Again"},
    )
    # Pending pairs are denied before the conflict branch (403) or may 409.
    assert second.status_code in {403, 409}
    if second.status_code == 403:
        detail = second.json().get("detail") or {}
        denials = detail.get("denials") if isinstance(detail, dict) else []
        assert "request_pending" in denials


def test_user_can_enable_and_disable_connect_removes_from_suggestions(
    client: TestClient, db_session: Session
):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fctog"
    )
    sug_on = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert any(i["username"] == "fctogb" for i in sug_on.json()["items"])

    disabled = client.patch(
        "/api/v1/fan-connect/settings",
        headers=h_b,
        json={
            "fan_connect_enabled": False,
            "allow_connection_requests": False,
            "discoverable_for_same_events": False,
            "discoverable_for_similar_interests": False,
        },
    )
    assert disabled.status_code == 200
    assert disabled.json()["fan_connect_enabled"] is False

    sug_off = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert all(i["username"] != "fctogb" for i in sug_off.json()["items"])

    enabled = client.patch(
        "/api/v1/fan-connect/settings",
        headers=h_b,
        json={
            "fan_connect_enabled": True,
            "allow_connection_requests": True,
            "discoverable_for_same_events": True,
            "discoverable_for_similar_interests": True,
        },
    )
    assert enabled.status_code == 200
    assert enabled.json()["fan_connect_enabled"] is True

    sug_again = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert any(i["username"] == "fctogb" for i in sug_again.json()["items"])


# --- Messaging ---------------------------------------------------------------


def test_blocked_after_accept_cannot_send_and_third_party_cannot_read(
    client: TestClient, db_session: Session
):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcmsg"
    )
    h_c = _auth(client, "fcmsg-c@example.com", "Stranger C")

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "fcmsgb"},
    )
    assert req.status_code == 200, req.text
    conn_id = req.json()["id"]
    acc = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/accept",
        headers=h_b,
    )
    assert acc.status_code == 200, acc.text
    thread_id = acc.json()["thread_id"]
    assert thread_id

    # Third party cannot read fan_fan thread
    stranger = client.get(f"/api/v1/messages/{thread_id}", headers=h_c)
    assert stranger.status_code in {403, 404}

    # Block then send denied
    assert (
        client.post(
            "/api/v1/fan-connect/block",
            headers=h_a,
            json={"username": "fcmsgb"},
        ).status_code
        == 204
    )
    denied = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=h_a,
        json={"body": "Should not send"},
    )
    assert denied.status_code == 403


def test_admin_message_report_required_for_fan_fan_moderation(
    client: TestClient, db_session: Session, assign_role
):
    h_a, h_b, a, b, _host, _ev = _pair_with_shared_event(
        client, db_session, prefix="fcadm"
    )
    h_admin = _auth(client, "fcadm-admin@example.com", "Admin")
    assign_role("fcadm-admin@example.com", "super_admin")

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "fcadmb"},
    )
    assert req.status_code == 200
    acc = client.post(
        f"/api/v1/fan-connect/requests/{req.json()['id']}/accept",
        headers=h_b,
    )
    assert acc.status_code == 200
    thread_id = acc.json()["thread_id"]

    # Admin has no browse path into unreported fan_fan threads
    direct = client.get(f"/api/v1/messages/{thread_id}", headers=h_admin)
    assert direct.status_code in {403, 404}

    listed_before = client.get("/api/v1/admin/message-reports", headers=h_admin)
    assert listed_before.status_code == 200
    assert all(
        str(thread_id) != (i.get("thread_id") or "")
        for i in listed_before.json()["items"]
    )

    reported = client.post(
        f"/api/v1/messages/{thread_id}/report",
        headers=h_a,
        json={"reason": "Harassment in Fan Connect chat"},
    )
    assert reported.status_code == 201, reported.text

    listed = client.get("/api/v1/admin/message-reports", headers=h_admin)
    assert listed.status_code == 200
    item = next(
        (i for i in listed.json()["items"] if i.get("thread_id") == str(thread_id)),
        None,
    )
    assert item is not None
    assert item.get("thread_type") == "fan_fan"

    detail = client.get(
        f"/api/v1/admin/message-reports/{item['id']}", headers=h_admin
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body.get("thread_type") == "fan_fan"
    _assert_no_private_leak(body)


# --- Settings defaults (opt-out) -------------------------------------


def test_settings_disable_from_on_defaults(client: TestClient, db_session: Session):
    headers = _auth(client, "fc-en@example.com")
    before = client.get("/api/v1/fan-connect/settings", headers=headers).json()
    assert before["fan_connect_enabled"] is True
    assert before["allow_connection_requests"] is True

    after = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={
            "fan_connect_enabled": False,
            "allow_connection_requests": False,
            "discoverable_for_same_events": False,
        },
    )
    assert after.status_code == 200
    data = after.json()
    assert data["fan_connect_enabled"] is False
    assert data["allow_connection_requests"] is False
    assert data["hide_private_events_always"] is True

    user = _user(db_session, "fc-en@example.com")
    row = ensure_connect_settings(db_session, user)
    assert row.fan_connect_enabled is False
