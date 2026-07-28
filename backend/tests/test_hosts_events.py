"""Host onboarding and event management tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.helpers.auth import register_json


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, password=password, full_name="Test User"),
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str = "Lagos Live") -> dict:
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "We throw great nights",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _event_payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=10)
    end = start + timedelta(hours=4)
    payload = {
        "title": "Afrobeats Night",
        "description": "A premium night of music and culture in the city.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "venue_name": "The Dome",
        "address": "12 Marina",
        "city": "Lagos",
        "state": "Lagos",
        "capacity": 500,
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


def test_host_onboarding(client: TestClient):
    headers = _auth_headers(client, "host1@example.com")
    host = _onboard(client, headers)
    assert host["display_name"] == "Lagos Live"
    assert host["slug"]
    assert host["profile"]["city"] == "Lagos"

    me = client.get("/api/v1/hosts/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["id"] == host["id"]

    profile = client.get("/api/v1/auth/me", headers=headers)
    assert "host" in profile.json()["roles"]


def test_event_creation(client: TestClient):
    headers = _auth_headers(client, "host2@example.com")
    _onboard(client, headers, "City Hosts")
    response = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["slug"]
    assert body["venue"]["name"] == "The Dome"


def test_event_editing_permissions(client: TestClient):
    host_a = _auth_headers(client, "hosta@example.com")
    host_b = _auth_headers(client, "hostb@example.com")
    _onboard(client, host_a, "Host A")
    _onboard(client, host_b, "Host B")

    created = client.post(
        "/api/v1/events",
        headers=host_a,
        json=_event_payload(title="Private Draft"),
    ).json()

    allowed = client.patch(
        f"/api/v1/events/by-id/{created['id']}",
        headers=host_a,
        json={"title": "Updated Draft Night"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["title"] == "Updated Draft Night"

    denied = client.patch(
        f"/api/v1/events/by-id/{created['id']}",
        headers=host_b,
        json={"title": "Hijacked"},
    )
    # Unrelated host: 404 (hide existence). Wrong-permission team: 403.
    assert denied.status_code in {403, 404}


def test_public_event_visibility(client: TestClient):
    headers = _auth_headers(client, "hostpub@example.com")
    _onboard(client, headers, "Public Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title="Hidden Until Published"),
    ).json()

    listing = client.get("/api/v1/events")
    assert listing.status_code == 200
    assert all(e["id"] != created["id"] for e in listing.json())

    detail = client.get(f"/api/v1/events/{created['slug']}")
    assert detail.status_code == 404

    client.post(f"/api/v1/events/by-id/{created['id']}/submit", headers=headers)
    submitted = client.get(f"/api/v1/events/by-id/{created['id']}", headers=headers).json()
    assert submitted["status"] == "published"
    assert any(e["id"] == created["id"] for e in client.get("/api/v1/events").json())
    detail_after = client.get(f"/api/v1/events/{created['slug']}")
    assert detail_after.status_code == 200


def test_admin_approval_rejection(client: TestClient, assign_role):
    host_headers = _auth_headers(client, "hostadmin@example.com")
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "super@example.com",
            "password": "securepass1",
            "full_name": "Super Admin",
        },
    )
    assign_role("super@example.com", "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "super@example.com", "password": "securepass1"},
    )
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    _onboard(client, host_headers, "Review Host")
    event = client.post(
        "/api/v1/events",
        headers=host_headers,
        json=_event_payload(title="Needs Approval"),
    ).json()
    client.post(f"/api/v1/events/by-id/{event['id']}/submit", headers=host_headers)
    submitted = client.get(
        f"/api/v1/events/by-id/{event['id']}", headers=host_headers
    ).json()
    assert submitted["status"] == "published"
    assert submitted["admin_flagged"] is True

    pending = client.get("/api/v1/events/admin/pending", headers=admin_headers)
    assert pending.status_code == 200
    assert any(e["id"] == event["id"] for e in pending.json())

    approved = client.post(
        f"/api/v1/events/by-id/{event['id']}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "published"
    assert approved.json()["admin_flagged"] is False

    public = client.get("/api/v1/events", params={"q": "Needs Approval"})
    assert any(e["id"] == event["id"] for e in public.json())
    detail = client.get(f"/api/v1/events/{event['slug']}")
    assert detail.status_code == 200

    event2 = client.post(
        "/api/v1/events",
        headers=host_headers,
        json=_event_payload(title="Will Be Rejected"),
    ).json()
    client.post(f"/api/v1/events/by-id/{event2['id']}/submit", headers=host_headers)
    rejected = client.post(
        f"/api/v1/events/by-id/{event2['id']}/reject",
        headers=admin_headers,
        json={"reason": "Incomplete venue details"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert "Incomplete" in rejected.json()["rejection_reason"]


def test_custom_ticket_type_kind(client: TestClient):
    headers = _auth_headers(client, "custom-ticket@example.com")
    _onboard(client, headers, "Custom Ticket Host")
    event = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title="Custom Tier Night"),
    ).json()

    created = client.post(
        f"/api/v1/events/by-id/{event['id']}/ticket-types",
        headers=headers,
        json={
            "name": "Backstage Pass",
            "type": "Backstage Pass",
            "price": "45000",
            "quantity": 25,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["type"] == "backstage_pass"
    assert body["name"] == "Backstage Pass"


def test_event_slug_update(client: TestClient):
    headers = _auth_headers(client, "slug-host@example.com")
    _onboard(client, headers, "Slug Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title="Original Slug Night"),
    ).json()

    updated = client.patch(
        f"/api/v1/events/by-id/{created['id']}",
        headers=headers,
        json={"slug": "custom-afrobeats-night"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["slug"] == "custom-afrobeats-night"

    other = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title="Another Night"),
    ).json()
    conflict = client.patch(
        f"/api/v1/events/by-id/{other['id']}",
        headers=headers,
        json={"slug": "custom-afrobeats-night"},
    )
    assert conflict.status_code == 409
