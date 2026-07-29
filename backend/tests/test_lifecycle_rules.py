"""Lifecycle rules: archive, withdraw, support cases, unused deletes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> None:
    r = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Lifecycle",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text


def _event_payload(title: str = "Lifecycle Event"):
    start = datetime.now(UTC) + timedelta(days=10)
    end = start + timedelta(hours=3)
    return {
        "title": title,
        "description": "Lifecycle rules coverage for Pàdéyá events.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "venue_name": "Hall",
        "city": "Lagos",
        "state": "Lagos",
        "venue": {
            "name": "Hall",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    }


def test_event_archive_completed(client: TestClient, assign_role):
    headers = _auth(client, "arch-host@example.com")
    _onboard(client, headers, "Archive Host")
    event = client.post(
        "/api/v1/events", headers=headers, json=_event_payload("Archive Me")
    ).json()
    client.post(f"/api/v1/events/by-id/{event['id']}/submit", headers=headers)

    admin_email = "arch-admin@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": "securepass1", "full_name": "Admin", "gender": "prefer_not_to_say"},
    )
    assign_role(admin_email, "super_admin")
    admin = _auth(client, admin_email, "Admin")
    # re-login after role assign
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "securepass1"},
    )
    admin = {"Authorization": f"Bearer {login.json()['access_token']}"}

    client.post(f"/api/v1/events/by-id/{event['id']}/approve", headers=admin)
    # Force complete via cancel then archive path: cancel published
    cancelled = client.post(
        f"/api/v1/events/by-id/{event['id']}/cancel", headers=headers
    )
    assert cancelled.status_code == 200
    archived = client.post(
        f"/api/v1/events/by-id/{event['id']}/archive", headers=headers
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"


def test_support_case_lifecycle(client: TestClient, assign_role):
    buyer = _auth(client, "case-buyer@example.com", "Buyer")
    created = client.post(
        "/api/v1/support/cases",
        headers=buyer,
        json={
            "subject": "Ticket issue",
            "category": "ticketing",
            "body": "I cannot see my ticket QR on Pàdéyá.",
        },
    )
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    assert created.json()["status"] == "open"

    support_email = "case-support@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": support_email,
            "password": "securepass1",
            "full_name": "Support",
        "gender": "prefer_not_to_say"},
    )
    assign_role(support_email, "support_agent")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": support_email, "password": "securepass1"},
    )
    support = {"Authorization": f"Bearer {login.json()['access_token']}"}

    replied = client.post(
        f"/api/v1/support/cases/{case_id}/messages",
        headers=support,
        json={"body": "We are looking into this."},
    )
    assert replied.status_code == 200
    note = client.post(
        f"/api/v1/support/cases/{case_id}/notes",
        headers=support,
        json={"body": "Internal: check payment webhook."},
    )
    assert note.status_code == 200
    assert len(note.json()["internal_notes"]) >= 1

    resolved = client.post(
        f"/api/v1/support/cases/{case_id}/resolve", headers=support
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    archived = client.post(
        f"/api/v1/support/cases/{case_id}/archive", headers=support
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None


def test_ai_admin_template_deactivate(client: TestClient, assign_role):
    email = "ai-admin@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "AI Admin", "gender": "prefer_not_to_say"},
    )
    assign_role(email, "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    templates = client.get("/api/v1/ai/admin/templates", headers=headers)
    assert templates.status_code == 200
    assert len(templates.json()) >= 1
    tid = templates.json()[0]["id"]

    deactivated = client.post(
        f"/api/v1/ai/admin/templates/{tid}/deactivate", headers=headers
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    logs = client.get("/api/v1/ai/admin/usage-logs", headers=headers)
    assert logs.status_code == 200
