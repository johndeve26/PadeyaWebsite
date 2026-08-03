"""Admin permanent event delete for test cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.events.models import Event
from tests.helpers.auth import register_json


def _auth(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, password="securepass1", full_name="User"),
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _relogin(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_force_delete_completed_event(
    client: TestClient, assign_role, db_session: Session
):
    host_h = _auth(client, "fd-event-host@example.com")
    onboard = client.post(
        "/api/v1/hosts/onboard",
        headers=host_h,
        json={
            "display_name": "Force Delete Host",
            "bio": "Test",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert onboard.status_code == 201, onboard.text

    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=3)
    created = client.post(
        "/api/v1/events",
        headers=host_h,
        json={
            "title": "Test Night To Delete",
            "description": "Temporary test event for permanent delete.",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "venue_name": "Test Hall",
            "city": "Lagos",
            "capacity": 100,
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]

    # Mark completed so discard would normally refuse
    row = db_session.get(Event, UUID(event_id))
    assert row is not None
    row.status = "completed"
    db_session.commit()

    admin_email = "fd-event-admin@example.com"
    _auth(client, admin_email)
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    short = client.post(
        f"/api/v1/events/admin/{event_id}/force-delete",
        headers=admin,
        json={"reason": "ab"},
    )
    assert short.status_code in {400, 422}

    ok = client.post(
        f"/api/v1/events/admin/{event_id}/force-delete",
        headers=admin,
        json={"reason": "Removing test event"},
    )
    assert ok.status_code == 200, ok.text

    db_session.expire_all()
    assert db_session.get(Event, UUID(event_id)) is None

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "events.force_delete",
                AuditLog.resource_id == str(event_id),
            )
        )
    )
    assert audits
    assert audits[-1].details.get("force_delete") is True
    assert audits[-1].details.get("reason") == "Removing test event"
