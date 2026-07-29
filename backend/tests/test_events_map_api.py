"""GET /events/map — privacy-safe compact pins for map discovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


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
                "bio": "Map API tests",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
        ).status_code
        == 201
    )


def _payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=14)
    end = start + timedelta(hours=3)
    body = {
        "title": "Map Discovery Night",
        "description": "Compact map endpoint privacy coverage for Pàdéyá.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "timezone": "Africa/Lagos",
        "venue_name": "Secret Palm Hall",
        "address": "14 Palm Close, Lekki Phase 1",
        "city": "Lagos",
        "state": "Lagos",
        "country": "Nigeria",
        "area": "Lekki",
        "latitude": "6.469800",
        "longitude": "3.585200",
        "approximate_latitude": "6.45",
        "approximate_longitude": "3.48",
        "approximate_map_label": "Lekki area",
        "public_location_label": "Lekki, Lagos",
        "location_visibility": "full_public",
        "reveal_timing": "immediately",
        "refund_policy_type": "admin_controlled",
        "venue": {
            "name": "Secret Palm Hall",
            "address": "14 Palm Close, Lekki Phase 1",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
            "latitude": "6.469800",
            "longitude": "3.585200",
        },
        "ticket_types": [
            {
                "name": "General",
                "price": 5000,
                "quantity": 100,
                "visibility": "public",
            }
        ],
    }
    body.update(overrides)
    return body


def _publish(
    client: TestClient,
    headers: dict[str, str],
    assign_role,
    event_id: str,
    admin_email: str,
) -> None:
    assert (
        client.post(f"/api/v1/events/by-id/{event_id}/submit", headers=headers).status_code
        == 200
    )
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
    assert (
        client.post(f"/api/v1/events/by-id/{event_id}/approve", headers=admin).status_code
        == 200
    )


# Lagos-ish viewport covering Lekki exact + approximate pins
_BOUNDS = {
    "north": 6.7,
    "south": 6.3,
    "east": 3.8,
    "west": 3.2,
}


def test_map_endpoint_returns_compact_safe_fields(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-api-full@example.com")
    _onboard(client, headers, "Map API Host")
    created = client.post("/api/v1/events", headers=headers, json=_payload()).json()
    _publish(client, headers, assign_role, created["id"], "map-api-full-admin@example.com")

    res = client.get("/api/v1/events/map", params=_BOUNDS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] >= 1
    item = next(i for i in data["items"] if i["id"] == created["id"])

    assert item["slug"]
    assert item["title"]
    assert item["latitude"] == "6.469800" or item["latitude"].startswith("6.4698")
    assert item["longitude"]
    assert item["location_map_mode"] == "exact"
    assert item["price_label"]
    assert "address" not in item
    assert "formatted_address" not in item
    assert "google_place_id" not in item
    assert "ticket_types" not in item
    assert "online_event_url" not in item


def test_map_hidden_until_payment_does_not_leak_exact_coords(
    client: TestClient, assign_role
):
    headers = _auth_headers(client, "map-api-hidden@example.com")
    _onboard(client, headers, "Hidden Map Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(location_visibility="hidden_until_payment"),
    ).json()
    _publish(
        client, headers, assign_role, created["id"], "map-api-hidden-admin@example.com"
    )

    res = client.get("/api/v1/events/map", params=_BOUNDS)
    assert res.status_code == 200
    item = next(i for i in res.json()["items"] if i["id"] == created["id"])

    assert item["location_visibility"] == "hidden_until_payment"
    assert item["location_map_mode"] == "approximate"
    # Approximate / area coords — not the exact venue pin.
    assert item["latitude"] != "6.469800"
    assert item["longitude"] != "3.585200"
    assert "Palm Close" not in (item.get("public_location_label") or "")
    assert item.get("location_privacy_message")


def test_map_area_only_uses_approximate_pin(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-api-area@example.com")
    _onboard(client, headers, "Area Map Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(location_visibility="area_only"),
    ).json()
    _publish(client, headers, assign_role, created["id"], "map-api-area-admin@example.com")

    res = client.get("/api/v1/events/map", params=_BOUNDS)
    item = next(i for i in res.json()["items"] if i["id"] == created["id"])
    assert item["location_map_mode"] == "approximate"
    assert item["latitude"] == "6.45"
    assert item["longitude"] == "3.48"


def test_map_online_only_excluded_from_pins(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-api-online@example.com")
    _onboard(client, headers, "Online Map Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            location_visibility="online_only",
            event_type="online",
            latitude=None,
            longitude=None,
            approximate_latitude=None,
            approximate_longitude=None,
            venue=None,
        ),
    ).json()
    _publish(
        client, headers, assign_role, created["id"], "map-api-online-admin@example.com"
    )

    res = client.get("/api/v1/events/map", params=_BOUNDS)
    assert res.status_code == 200
    ids = {i["id"] for i in res.json()["items"]}
    assert created["id"] not in ids


def test_map_events_outside_bounds_excluded(client: TestClient, assign_role):
    headers = _auth_headers(client, "map-api-bounds@example.com")
    _onboard(client, headers, "Bounds Map Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            city="Abuja",
            area="Maitama",
            latitude="9.0765",
            longitude="7.3986",
            approximate_latitude="9.08",
            approximate_longitude="7.40",
            venue={
                "name": "Abuja Hall",
                "address": "1 Maitama Ave",
                "city": "Abuja",
                "state": "FCT",
                "country": "Nigeria",
                "latitude": "9.0765",
                "longitude": "7.3986",
            },
        ),
    ).json()
    _publish(
        client, headers, assign_role, created["id"], "map-api-bounds-admin@example.com"
    )

    res = client.get("/api/v1/events/map", params=_BOUNDS)
    ids = {i["id"] for i in res.json()["items"]}
    assert created["id"] not in ids


def test_map_invalid_bounds_rejected(client: TestClient):
    res = client.get(
        "/api/v1/events/map",
        params={"north": 1, "south": 2, "east": 3, "west": 1},
    )
    assert res.status_code == 400
