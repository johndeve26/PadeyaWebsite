"""Fan event recommendations — API integration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile, HostVerification
from app.passport.models import FanPassport
from app.users.models import User
from app.users.service import get_role_by_name


def _buyer(client: TestClient, db_session: Session, email: str) -> tuple[User, str]:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Fan Buyer",
        is_active=True,
    )
    role = get_role_by_name(db_session, "buyer")
    assert role is not None
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()
    db_session.add(
        FanPassport(
            user_id=user.id,
            display_name="Fan Buyer",
            username=email.split("@")[0],
            visibility="public",
            favorite_categories=["music"],
        )
    )
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200
    return user, login.json()["access_token"]


def _host_with_event(
    db_session: Session,
    *,
    slug: str,
    title: str,
    city: str = "Lagos",
    featured: bool = False,
) -> tuple[Host, Event]:
    host_user = User(
        email=f"{slug}@host.example.com",
        password_hash=hash_password("securepass1"),
        full_name=title,
        is_active=True,
    )
    host_role = get_role_by_name(db_session, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db_session.add(host_user)
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name=title,
        slug=slug,
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(
        HostProfile(host_id=host.id, bio="Bio", city=city, avatar_url="https://x/a.jpg")
    )
    db_session.add(HostVerification(host_id=host.id, status="verified"))
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=4)
    event = Event(
        title=title,
        slug=f"{slug}-night",
        description="Listed event for recommendations",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city=city,
        venue_name="Hall",
        address="Hidden street",
        status="published",
        visibility="listed",
        location_visibility="city_only",
        featured=featured,
        published_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(event)
    db_session.commit()
    return host, event


def test_event_recommendations_requires_auth(client: TestClient) -> None:
    res = client.get("/api/v1/events/recommendations")
    assert res.status_code == 401


def test_followed_host_boosts_event(
    client: TestClient, db_session: Session
) -> None:
    host, _event = _host_with_event(
        db_session, slug="rec-host", title="Rec Host Night", featured=True
    )
    fan, token = _buyer(client, db_session, "fan-ev-rec@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()

    res = client.get(
        "/api/v1/events/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "recommended"
    slugs = [row["event"]["slug"] for row in data["events"]]
    assert "rec-host-night" in slugs
    match = next(r for r in data["events"] if r["event"]["slug"] == "rec-host-night")
    assert match["score"] >= 35
    assert match["flags"]["from_followed_host"] is True
    assert any(r["code"] == "followed_host" for r in match["reasons"])


def test_dismiss_suppresses_event(client: TestClient, db_session: Session) -> None:
    host, event = _host_with_event(
        db_session, slug="dismiss-ev", title="Dismiss Me", featured=True
    )
    fan, token = _buyer(client, db_session, "fan-ev-dismiss@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()

    before = client.get(
        "/api/v1/events/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert before.status_code == 200
    assert any(e["event"]["slug"] == "dismiss-ev-night" for e in before.json()["events"])

    fb = client.post(
        f"/api/v1/events/recommendations/{event.id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "dismissed"},
    )
    assert fb.status_code == 200

    after = client.get(
        "/api/v1/events/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.status_code == 200
    assert not any(
        e["event"]["slug"] == "dismiss-ev-night" for e in after.json()["events"]
    )


def test_safe_reason_labels(client: TestClient, db_session: Session) -> None:
    _host_with_event(db_session, slug="safe-ev", title="Safe Event")
    _, token = _buyer(client, db_session, "fan-ev-safe@example.com")

    res = client.get(
        "/api/v1/events/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    forbidden = ("vip", "table", "spend", "vault", "message", "private", "ai ")
    for row in res.json()["events"]:
        for reason in row["reasons"]:
            label = reason["label"].lower()
            for word in forbidden:
                assert word not in label


def test_excludes_context_event_from_detail(
    client: TestClient, db_session: Session
) -> None:
    host, event = _host_with_event(
        db_session, slug="ctx-ev", title="Context Event", featured=True
    )
    fan, token = _buyer(client, db_session, "fan-ev-ctx@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()

    res = client.get(
        "/api/v1/events/recommendations",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "context_event_id": str(event.id),
            "exclude_event_id": str(event.id),
            "limit": 20,
        },
    )
    assert res.status_code == 200
    ids = [row["event"]["id"] for row in res.json()["events"]]
    assert str(event.id) not in ids
