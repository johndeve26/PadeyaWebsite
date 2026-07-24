"""Public /legacy/discover/hosts marketplace listing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile, HostVerification
from app.users.models import User
from app.users.service import get_role_by_name


def test_discover_hosts_returns_safe_public_fields(
    client: TestClient, db_session: Session
) -> None:
    host_user = User(
        email="discover-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Discover Host",
        is_active=True,
    )
    host_role = get_role_by_name(db_session, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db_session.add(host_user)
    db_session.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Discover Host",
        slug="discover-host",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(
        HostProfile(
            host_id=host.id,
            bio="Public bio only.",
            city="Lagos",
            avatar_url="https://cdn.example.com/avatar.jpg",
        )
    )
    db_session.add(HostVerification(host_id=host.id, status="verified"))

    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Upcoming Discover Night",
        slug="upcoming-discover-night",
        description="Listed upcoming event for discovery cards.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name="Secret Hall",
        address="12 Hidden Street",
        status="published",
        visibility="listed",
        location_visibility="city_only",
        featured=False,
        published_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(event)
    db_session.commit()

    from app.core.cache import cache_delete, cache_key

    cache_delete(cache_key("legacy", "discover", "hosts"))

    res = client.get("/api/v1/legacy/discover/hosts")
    assert res.status_code == 200
    rows = res.json()
    assert isinstance(rows, list)
    match = next((r for r in rows if r["username"] == "discover-host"), None)
    assert match is not None
    assert match["display_name"] == "Discover Host"
    assert match["verified"] is True
    assert match["primary_city"] == "Lagos"
    assert match["upcoming_events_count"] >= 1
    assert match["share_path"] == "/@discover-host"
    assert "email" not in match
    assert match["next_upcoming_event"] is not None
    assert match["next_upcoming_event"]["title"] == "Upcoming Discover Night"
    assert match["next_upcoming_event"]["city"] == "Lagos"
    # Private venue details must never appear on discovery cards.
    blob = str(match)
    assert "Secret Hall" not in blob
    assert "Hidden Street" not in blob


def test_discover_hosts_excludes_hosts_without_listed_events(
    client: TestClient, db_session: Session
) -> None:
    host_user = User(
        email="no-event-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="No Event Host",
        is_active=True,
    )
    host_role = get_role_by_name(db_session, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db_session.add(host_user)
    db_session.flush()

    host = Host(
        user_id=host_user.id,
        display_name="No Event Host",
        slug="no-event-host",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(
        HostProfile(host_id=host.id, bio="Legacy only.", city="Lagos")
    )
    db_session.commit()

    from app.core.cache import cache_delete, cache_key

    cache_delete(cache_key("legacy", "discover", "hosts"))

    res = client.get("/api/v1/legacy/discover/hosts")
    assert res.status_code == 200
    usernames = {row["username"] for row in res.json()}
    assert "no-event-host" not in usernames
