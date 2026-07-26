"""Event and ticket-type lifecycle: pause, resume, cancel, discard, deactivate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Lifecycle Host"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> None:
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Lifecycle tests",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text


def _event_payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=10)
    end = start + timedelta(hours=4)
    payload = {
        "title": "Lifecycle Night",
        "description": "Testing pause resume cancel discard flows on Pàdéyá.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "venue_name": "The Dome",
        "address": "12 Marina",
        "city": "Lagos",
        "state": "Lagos",
        "capacity": 200,
        "venue": {
            "name": "The Dome",
            "address": "12 Marina",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    }
    payload.update(overrides)
    return payload


def _create_and_publish(client: TestClient, headers: dict[str, str], assign_role, title: str) -> dict:
    event = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title=title),
    ).json()
    client.post(f"/api/v1/events/by-id/{event['id']}/submit", headers=headers)

    admin_email = f"admin-{title.replace(' ', '').lower()}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": "securepass1", "full_name": "Admin"},
    )
    assign_role(admin_email, "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "securepass1"},
    )
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    approved = client.post(
        f"/api/v1/events/by-id/{event['id']}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "published"
    return approved.json()


def test_pause_resume_cancel_event(client: TestClient, assign_role):
    headers = _auth_headers(client, "life-pause@example.com")
    _onboard(client, headers, "Pause Host")
    event = _create_and_publish(client, headers, assign_role, "Pause Me")

    paused = client.post(f"/api/v1/events/by-id/{event['id']}/pause", headers=headers)
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    resumed = client.post(f"/api/v1/events/by-id/{event['id']}/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "published"

    cancelled = client.post(f"/api/v1/events/by-id/{event['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # Cannot cancel again
    again = client.post(f"/api/v1/events/by-id/{event['id']}/cancel", headers=headers)
    assert again.status_code == 400


def test_postpone_event_keeps_published(client: TestClient, assign_role):
    headers = _auth_headers(client, "life-postpone@example.com")
    _onboard(client, headers, "Postpone Host")
    event = _create_and_publish(client, headers, assign_role, "Postpone Me")

    new_start = datetime.now(UTC) + timedelta(days=30)
    new_end = new_start + timedelta(hours=5)
    postponed = client.post(
        f"/api/v1/events/by-id/{event['id']}/postpone",
        headers=headers,
        json={
            "start_datetime": new_start.isoformat(),
            "end_datetime": new_end.isoformat(),
        },
    )
    assert postponed.status_code == 200, postponed.text
    body = postponed.json()
    assert body["status"] == "published"
    assert body["start_datetime"].startswith(new_start.strftime("%Y-%m-%d"))
    assert body["end_datetime"].startswith(new_end.strftime("%Y-%m-%d"))

    bad = client.post(
        f"/api/v1/events/by-id/{event['id']}/postpone",
        headers=headers,
        json={
            "start_datetime": new_end.isoformat(),
            "end_datetime": new_start.isoformat(),
        },
    )
    assert bad.status_code == 422


def test_discard_draft_only(client: TestClient):
    headers = _auth_headers(client, "life-discard@example.com")
    _onboard(client, headers, "Discard Host")
    draft = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title="Discard Draft"),
    ).json()

    deleted = client.delete(f"/api/v1/events/by-id/{draft['id']}", headers=headers)
    assert deleted.status_code == 200

    missing = client.get(f"/api/v1/events/by-id/{draft['id']}", headers=headers)
    assert missing.status_code == 404


def test_ticket_type_deactivate_and_delete_unused(client: TestClient):
    headers = _auth_headers(client, "life-tt@example.com")
    _onboard(client, headers, "Ticket Host")
    event = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title="Ticket Lifecycle"),
    ).json()

    created = client.post(
        f"/api/v1/events/by-id/{event['id']}/ticket-types",
        headers=headers,
        json={
            "name": "GA",
            "type": "regular",
            "price": "5000",
            "quantity": 100,
            "visibility": "public",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    tt_id = created.json()["id"]

    deactivated = client.post(
        f"/api/v1/events/by-id/{event['id']}/ticket-types/{tt_id}/deactivate",
        headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"

    deleted = client.delete(
        f"/api/v1/events/by-id/{event['id']}/ticket-types/{tt_id}",
        headers=headers,
    )
    assert deleted.status_code == 200

    listing = client.get(
        f"/api/v1/events/by-id/{event['id']}/ticket-types",
        headers=headers,
    )
    assert listing.status_code == 200
    assert all(t["id"] != tt_id for t in listing.json())


def test_auto_complete_past_published_on_mine(client: TestClient, assign_role, db_session):
    """Published events whose end_datetime has passed become completed on /mine."""
    from uuid import UUID

    from app.events.models import Event

    headers = _auth_headers(client, "life-autocomple@example.com")
    _onboard(client, headers, "Auto Complete Host")
    event = _create_and_publish(client, headers, assign_role, "Already Over")

    row = db_session.get(Event, UUID(event["id"]))
    assert row is not None
    row.start_datetime = datetime.now(UTC) - timedelta(days=2)
    row.end_datetime = datetime.now(UTC) - timedelta(hours=1)
    db_session.commit()

    mine = client.get("/api/v1/events/mine", headers=headers)
    assert mine.status_code == 200, mine.text
    matched = next(e for e in mine.json() if e["id"] == event["id"])
    assert matched["status"] == "completed"

    detail = client.get(f"/api/v1/events/by-id/{event['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
