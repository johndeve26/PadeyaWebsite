"""Admin event flag + review surfaces."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory
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


def _seed_published_event(db: Session) -> tuple[Event, User]:
    suffix = uuid.uuid4().hex[:8]
    host_user = User(
        email=f"flag-host-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Flag Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    admin = User(
        email=f"flag-admin-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Flag Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db, "super_admin"))
    db.add_all([host_user, admin])
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Flag Host Org",
        slug=f"flag-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Flaggable Night",
        slug=f"flaggable-night-{suffix}",
        description="Event used for admin flag tests with enough text for validation.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        status="published",
        city="Lagos",
        venue_name="Flag Hall",
        published_at=datetime.now(UTC),
        capacity=100,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event, admin


def test_admin_can_flag_and_clear_event(client: TestClient, db_session: Session):
    event, admin = _seed_published_event(db_session)
    headers = _login(client, admin.email)

    flagged = client.post(
        f"/api/v1/events/by-id/{event.id}/flag",
        headers=headers,
        json={"reason": "Suspicious ticket pricing pattern"},
    )
    assert flagged.status_code == 200, flagged.text
    body = flagged.json()
    assert body["admin_flagged"] is True
    assert body["admin_flag_reason"] == "Suspicious ticket pricing pattern"
    assert body["status"] == "published"

    listed = client.get("/api/v1/events/admin/all", headers=headers)
    assert listed.status_code == 200
    row = next(r for r in listed.json() if r["id"] == str(event.id))
    assert row["admin_flagged"] is True

    cleared = client.post(
        f"/api/v1/events/by-id/{event.id}/clear-flag",
        headers=headers,
        json={"reason": "Reviewed — ok"},
    )
    assert cleared.status_code == 200
    assert cleared.json()["admin_flagged"] is False
    assert cleared.json()["admin_flag_reason"] is None


def test_flag_requires_reason(client: TestClient, db_session: Session):
    event, admin = _seed_published_event(db_session)
    headers = _login(client, admin.email)
    res = client.post(
        f"/api/v1/events/by-id/{event.id}/flag",
        headers=headers,
        json={"reason": "no"},
    )
    assert res.status_code == 422
