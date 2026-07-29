"""Structured map fields + privacy-safe public map modes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.events.maps import resolve_public_map
from app.events.models import Event


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Map Host", "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> None:
    assert (
        client.post(
            "/api/v1/hosts/onboard",
            headers=headers,
            json={
                "display_name": name,
                "bio": "Map tests",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
        ).status_code
        == 201
    )


def _payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=12)
    end = start + timedelta(hours=4)
    body = {
        "title": "Map Studio Night",
        "description": "Structured map location privacy coverage for Pàdéyá events.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "timezone": "Africa/Lagos",
        "venue_name": "Palm Hall",
        "address": "14 Palm Close, Lekki Phase 1",
        "city": "Lagos",
        "state": "Lagos",
        "country": "Nigeria",
        "area": "Lekki",
        "latitude": "6.4698",
        "longitude": "3.5852",
        "google_maps_share_url": "https://maps.google.com/?q=6.4698,3.5852",
        "approximate_latitude": "6.45",
        "approximate_longitude": "3.48",
        "approximate_map_label": "Lekki Phase 1 area",
        "public_location_label": "Lekki Phase 1, Lagos",
        "location_visibility": "full_public",
        "reveal_timing": "immediately",
        "refund_policy_type": "admin_controlled",
        "venue": {
            "name": "Palm Hall",
            "address": "14 Palm Close, Lekki Phase 1",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
            "latitude": "6.4698",
            "longitude": "3.5852",
        },
    }
    body.update(overrides)
    return body


def _publish(client: TestClient, headers: dict[str, str], assign_role, event_id: str, admin_email: str):
    assert client.post(f"/api/v1/events/by-id/{event_id}/submit", headers=headers).status_code == 200
    client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": "securepass1", "full_name": "Admin", "gender": "prefer_not_to_say"},
    )
    assign_role(admin_email, "super_admin")
    token = client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "securepass1"},
    ).json()["access_token"]
    admin = {"Authorization": f"Bearer {token}"}
    assert client.post(f"/api/v1/events/by-id/{event_id}/approve", headers=admin).status_code == 200


def test_full_public_exact_map(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-full@example.com")
    _onboard(client, headers, "Full Map Host")
    created = client.post("/api/v1/events", headers=headers, json=_payload()).json()
    _publish(client, headers, assign_role, created["id"], "map-full-admin@example.com")

    public = client.get(f"/api/v1/events/{created['slug']}").json()
    assert public["location_map_mode"] == "exact"
    assert public["latitude"] == "6.4698"
    assert public["longitude"] == "3.5852"
    assert public["map_latitude"] == "6.4698"
    assert public["address"] == "14 Palm Close, Lekki Phase 1"
    assert public["map_open_url"]
    assert "google" in public["map_open_url"]


def test_area_only_approximate_map_hides_exact(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-area@example.com")
    _onboard(client, headers, "Area Map Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Area Map Night",
            location_visibility="area_only",
            reveal_timing="after_payment",
        ),
    ).json()
    _publish(client, headers, assign_role, created["id"], "map-area-admin@example.com")

    public = client.get(f"/api/v1/events/{created['slug']}").json()
    assert public["address"] is None
    assert public["latitude"] is None
    assert public["longitude"] is None
    assert public["google_maps_share_url"] is None
    assert public["location_map_mode"] == "approximate"
    assert public["map_latitude"] == "6.45"
    assert public["map_longitude"] == "3.48"
    assert "Palm Close" not in (public.get("seo_description") or "")


def test_hidden_until_payment_approximate_map(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-hide@example.com")
    _onboard(client, headers, "Hide Map Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Hidden Map Night",
            location_visibility="hidden_until_payment",
            reveal_timing="after_payment",
            public_location_label="Lekki — exact venue after purchase.",
        ),
    ).json()
    _publish(client, headers, assign_role, created["id"], "map-hide-admin@example.com")

    public = client.get(f"/api/v1/events/{created['slug']}").json()
    assert public["location_map_mode"] == "approximate"
    assert public["latitude"] is None
    assert public["map_latitude"] == "6.45"
    assert public["location_address_revealed"] is False


def test_online_only_no_physical_map(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-online@example.com")
    _onboard(client, headers, "Online Map Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Online Map Night",
            location_visibility="online_only",
            event_type="online",
            online_event_url="https://meet.example.com/x",
            public_location_label="Online Event",
            latitude=None,
            longitude=None,
            approximate_latitude=None,
            approximate_longitude=None,
        ),
    ).json()
    _publish(client, headers, assign_role, created["id"], "map-online-admin@example.com")

    public = client.get(f"/api/v1/events/{created['slug']}").json()
    assert public["location_map_mode"] == "none"
    assert public["map_latitude"] is None
    assert public["map_open_url"] is None
    assert public["address"] is None


def test_resolve_public_map_uses_city_centroid_fallback():
    event = Event(
        title="Centroid",
        slug="centroid-map",
        description="Enough text for basics.",
        start_datetime=datetime.now(UTC) + timedelta(days=2),
        end_datetime=datetime.now(UTC) + timedelta(days=2, hours=2),
        host_id=__import__("uuid").uuid4(),
        city="Lagos",
        location_visibility="area_only",
    )
    payload = resolve_public_map(event, reveal_exact=False)
    assert payload["location_map_mode"] == "approximate"
    assert payload["map_latitude"] == "6.5244"
