"""Publish-first on host submit (admin reviews flagged listings later)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Auto Publish Host", "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": "Auto Publish Host",
            "bio": "Testing auto publish",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text


def _event_payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=12)
    end = start + timedelta(hours=4)
    payload = {
        "title": "Auto Publish Night",
        "description": "Event should publish immediately when the host submits.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "venue_name": "Main Hall",
        "address": "1 Test Street",
        "city": "Lagos",
        "state": "Lagos",
        "capacity": 100,
        "venue": {
            "name": "Main Hall",
            "address": "1 Test Street",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    }
    payload.update(overrides)
    return payload


def test_submit_publishes_and_flags_for_admin_review(
    client: TestClient, assign_role
):
    headers = _auth_headers(client, "auto-publish-host@example.com")
    _onboard(client, headers)
    created = client.post("/api/v1/events", headers=headers, json=_event_payload()).json()

    submitted = client.post(
        f"/api/v1/events/by-id/{created['id']}/submit",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    body = submitted.json()
    assert body["status"] == "published"
    assert body["admin_flagged"] is True
    assert body["published_at"]

    public = client.get(f"/api/v1/events/{body['slug']}")
    assert public.status_code == 200

    admin_email = "auto-publish-admin@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": "securepass1", "full_name": "Admin", "gender": "prefer_not_to_say"},
    )
    assign_role(admin_email, "super_admin")
    admin_headers = {
        "Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': admin_email, 'password': 'securepass1'}).json()['access_token']}"
    }

    pending = client.get("/api/v1/events/admin/pending", headers=admin_headers)
    assert pending.status_code == 200
    assert any(row["id"] == body["id"] for row in pending.json())

    cleared = client.post(
        f"/api/v1/events/by-id/{body['id']}/approve",
        headers=admin_headers,
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["status"] == "published"
    assert cleared.json()["admin_flagged"] is False
