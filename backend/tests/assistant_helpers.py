"""Shared helpers for Pàdéyá assistant tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name

_DEFAULT_FLAGS = {
    "assistant_enabled": True,
    "assistant_public_enabled": True,
    "assistant_authenticated_enabled": True,
    "assistant_actions_enabled": True,
    "assistant_event_search_enabled": True,
    "assistant_support_drafts_enabled": True,
    "assistant_admin_enabled": False,
    "assistant_knowledge_sync_enabled": False,
}


def enable_assistant(monkeypatch, **flags: Any):
    """Enable assistant feature flags on the cached Settings instance."""
    settings = get_settings()
    merged = {**_DEFAULT_FLAGS, **flags}
    for key, value in merged.items():
        monkeypatch.setattr(settings, key, value)
    get_settings.cache_clear()
    # Re-bind after cache clear so subsequent get_settings() see patched attrs
    settings2 = get_settings()
    for key, value in merged.items():
        monkeypatch.setattr(settings2, key, value)
    return settings2


def login(client: TestClient, email: str) -> dict[str, str]:
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login_resp.status_code == 200, login_resp.text
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}


# Back-compat alias used by some suites
_login = login


def seed_user(
    db: Session,
    *,
    email: str,
    role: str = "buyer",
    full_name: str = "Test User",
) -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=full_name,
        is_active=True,
        is_verified=True,
    )
    role_row = get_role_by_name(db, role)
    assert role_row is not None, f"Unknown role: {role}"
    user.roles.append(role_row)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_host(
    db: Session,
    *,
    email: str = "asst-host@example.com",
    slug: str = "asst-host",
    display_name: str = "Assistant Host",
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=display_name,
        is_active=True,
        is_verified=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name=display_name,
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Assistant test host"))
    db.commit()
    db.refresh(host)
    db.refresh(host_user)
    return host, host_user


def seed_published_event(
    db: Session,
    host: Host,
    *,
    title: str = "Lagos Night Market",
    slug: str = "lagos-night-market-asst",
    city: str = "Lagos",
) -> Event:
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title=title,
        slug=slug,
        description=f"{title} — culture and music in {city} with enough text.",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=5),
        city=city,
        venue_name="The Yard",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        capacity=300,
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("5000.00"),
            quantity=200,
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


def parse_sse_events(raw: str) -> list[tuple[str, str]]:
    """Parse SSE text into (event, data) pairs."""
    events: list[tuple[str, str]] = []
    event_name = "message"
    data_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line == "" and data_lines:
            events.append((event_name, "\n".join(data_lines)))
            event_name = "message"
            data_lines = []
    if data_lines:
        events.append((event_name, "\n".join(data_lines)))
    return events
