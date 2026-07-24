"""Nearby event discovery — Haversine ranking + privacy-safe coords."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.events.geo import discovery_point, haversine_km
from app.events.models import Event


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Near Host"},
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
                "bio": "Nearby tests",
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
        "title": "Nearby Studio Night",
        "description": "Nearby discovery coverage for Pàdéyá events with enough detail.",
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
        "approximate_latitude": "6.45",
        "approximate_longitude": "3.48",
        "approximate_map_label": "Lekki Phase 1 area",
        "public_location_label": "Lekki Phase 1, Lagos",
        "location_visibility": "full_public",
        "reveal_timing": "immediately",
        "refund_policy_type": "admin_controlled",
        "ticket_types": [
            {
                "name": "General",
                "type": "regular",
                "price": "1000.00",
                "quantity": 50,
                "min_per_order": 1,
                "max_per_order": 4,
                "visibility": "public",
            }
        ],
    }
    body.update(overrides)
    return body


def _publish(
    client: TestClient, headers: dict[str, str], assign_role, event_id: str, admin_email: str
):
    assert (
        client.post(f"/api/v1/events/by-id/{event_id}/submit", headers=headers).status_code
        == 200
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": "securepass1", "full_name": "Admin"},
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


def test_haversine_known_distance():
    d = haversine_km(6.5244, 3.3792, 6.4698, 3.5852)
    assert 15 < d < 35


def test_bucket_lat_lng_privacy_grid():
    from app.events.geo import bucket_lat_lng

    a = bucket_lat_lng(6.5244123, 3.3792987)
    b = bucket_lat_lng(6.5244999, 3.3792001)
    assert a == b
    assert a != (6.5244123, 3.3792987)

def test_nearby_orders_closest_first(client: TestClient, assign_role):
    headers = _auth_headers(client, "near-host@example.com")
    _onboard(client, headers, "Near Host")

    near = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Near Night",
            latitude="6.5244",
            longitude="3.3792",
            start_datetime=(datetime.now(UTC) + timedelta(days=5)).isoformat(),
            end_datetime=(datetime.now(UTC) + timedelta(days=5, hours=4)).isoformat(),
        ),
    ).json()
    far = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Far Night",
            latitude="9.0765",
            longitude="7.3986",
            city="Abuja",
            state="FCT",
            start_datetime=(datetime.now(UTC) + timedelta(days=6)).isoformat(),
            end_datetime=(datetime.now(UTC) + timedelta(days=6, hours=4)).isoformat(),
        ),
    ).json()
    _publish(client, headers, assign_role, near["id"], "near-admin1@example.com")
    _publish(client, headers, assign_role, far["id"], "near-admin2@example.com")

    res = client.get(
        "/api/v1/events/nearby",
        params={"lat": 6.52, "lng": 3.38, "radius_km": 100, "limit": 20},
    )
    assert res.status_code == 200, res.text
    titles = [i["title"] for i in res.json()["items"]]
    assert "Near Night" in titles
    if "Far Night" in titles:
        assert titles.index("Near Night") < titles.index("Far Night")
    near_item = next(i for i in res.json()["items"] if i["title"] == "Near Night")
    assert near_item["distance_km"] is not None
    assert near_item["distance_label"]
    assert near_item["latitude"] == "6.5244"


def test_radius_excludes_far_events(client: TestClient, assign_role):
    headers = _auth_headers(client, "radius-host@example.com")
    _onboard(client, headers, "Radius Host")
    far = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Abuja Far",
            latitude="9.0765",
            longitude="7.3986",
            city="Abuja",
        ),
    ).json()
    _publish(client, headers, assign_role, far["id"], "radius-admin@example.com")

    tight = client.get(
        "/api/v1/events/nearby",
        params={"lat": 6.52, "lng": 3.38, "radius_km": 25},
    )
    assert tight.status_code == 200
    titles = [i["title"] for i in tight.json()["items"]]
    assert "Abuja Far" not in titles


def test_events_without_coords_excluded(client: TestClient, assign_role):
    headers = _auth_headers(client, "nocoords@example.com")
    _onboard(client, headers, "No Coords")
    row = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="No Pin Night",
            latitude=None,
            longitude=None,
            approximate_latitude=None,
            approximate_longitude=None,
            city=None,
            area=None,
        ),
    ).json()
    _publish(client, headers, assign_role, row["id"], "nocoords-admin@example.com")

    res = client.get(
        "/api/v1/events/nearby",
        params={"lat": 6.52, "lng": 3.38, "radius_km": 50},
    )
    assert res.status_code == 200
    titles = [i["title"] for i in res.json()["items"]]
    assert "No Pin Night" not in titles


def test_hidden_until_payment_does_not_leak_exact_coords(client: TestClient, assign_role):
    headers = _auth_headers(client, "secret-near@example.com")
    _onboard(client, headers, "Secret Host")
    row = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Secret Nearby",
            location_visibility="hidden_until_payment",
            reveal_timing="after_payment",
            public_location_label="Lekki — exact venue after purchase.",
        ),
    ).json()
    _publish(client, headers, assign_role, row["id"], "secret-near-admin@example.com")

    res = client.get(
        "/api/v1/events/nearby",
        params={"lat": 6.45, "lng": 3.48, "radius_km": 25},
    )
    assert res.status_code == 200, res.text
    item = next(i for i in res.json()["items"] if i["title"] == "Secret Nearby")
    assert item["latitude"] is None
    assert item["longitude"] is None
    assert item["distance_km"] is not None
    assert item["distance_is_approximate"] is True
    assert "Palm Close" not in (item.get("address") or "")


def test_invalid_radius_rejected(client: TestClient):
    res = client.get(
        "/api/v1/events/nearby",
        params={"lat": 6.5, "lng": 3.3, "radius_km": 7},
    )
    assert res.status_code == 400


def test_discovery_point_none_without_coords():
    event = Event(
        title="x",
        slug="x-nearby",
        description="desc long enough",
        start_datetime=datetime.now(UTC) + timedelta(days=1),
        end_datetime=datetime.now(UTC) + timedelta(days=1, hours=2),
        host_id=__import__("uuid").uuid4(),
        status="published",
        visibility="listed",
        latitude=None,
        longitude=None,
        location_visibility="full_public",
    )
    assert discovery_point(event) is None
