"""Location privacy rules for Event Studio."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
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
            "bio": "We throw great nights",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text


def _payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=10)
    end = start + timedelta(hours=4)
    payload = {
        "title": "Secret Garden Night",
        "description": "A premium night with privacy-aware venue details for serious hosts.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "venue_name": "Hidden Courtyard",
        "address": "14 Palm Close, Lekki Phase 1",
        "city": "Lagos",
        "state": "Lagos",
        "public_location_label": "Lekki Phase 1, Lagos — exact venue revealed after purchase.",
        "location_visibility": "hidden_until_payment",
        "reveal_timing": "after_payment",
        "reveal_note": "Exact venue revealed after purchase.",
        "capacity": 200,
        "venue": {
            "name": "Hidden Courtyard",
            "address": "14 Palm Close, Lekki Phase 1",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    }
    payload.update(overrides)
    return payload


def test_public_api_hides_address_until_payment(client: TestClient, assign_role):
    host_headers = _auth_headers(client, "privacy-host@example.com")
    _onboard(client, host_headers, "Privacy Host")
    created = client.post(
        "/api/v1/events",
        headers=host_headers,
        json=_payload(),
    )
    assert created.status_code == 201, created.text
    event = created.json()
    assert event["address"] == "14 Palm Close, Lekki Phase 1"

    client.post(f"/api/v1/events/by-id/{event['id']}/submit", headers=host_headers)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "privacy-admin@example.com",
            "password": "securepass1",
            "full_name": "Admin",
        },
    )
    assign_role("privacy-admin@example.com", "super_admin")
    admin = _auth_headers(client, "privacy-admin@example.com")
    # login again after role assign
    admin = {
        "Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': 'privacy-admin@example.com', 'password': 'securepass1'}).json()['access_token']}"
    }
    approved = client.post(f"/api/v1/events/by-id/{event['id']}/approve", headers=admin)
    assert approved.status_code == 200, approved.text

    public = client.get(f"/api/v1/events/{event['slug']}")
    assert public.status_code == 200, public.text
    body = public.json()
    assert body["address"] is None
    assert body["location_address_revealed"] is False
    assert "Lekki" in (body["public_location_label"] or "")
    assert body["venue"] is None or body["venue"]["address"] is None
    assert "Palm Close" not in (body.get("seo_description") or "")
    assert "Palm Close" not in (body.get("seo_title") or "")
    assert "Palm Close" not in (body.get("social_share_description") or "")

    host_view = client.get(f"/api/v1/events/by-id/{event['id']}", headers=host_headers)
    assert host_view.status_code == 200
    assert host_view.json()["address"] == "14 Palm Close, Lekki Phase 1"


def test_public_api_scrubs_private_address_from_seo_fields(
    client: TestClient, assign_role
):
    host_headers = _auth_headers(client, "seo-privacy-host@example.com")
    _onboard(client, host_headers, "SEO Privacy Host")
    street = "14 Palm Close, Lekki Phase 1"
    created = client.post(
        "/api/v1/events",
        headers=host_headers,
        json=_payload(
            title="SEO Leak Check",
            seo_title=f"Party at {street}",
            seo_description=f"Meet at {street} for the best night.",
            social_share_title=f"Tonight @ {street}",
            social_share_description=f"Address: {street}",
            hashtags=[f"#{street.replace(' ', '')}"],
            discoverable_keywords=[street, "Lagos"],
        ),
    )
    assert created.status_code == 201, created.text
    event = created.json()
    client.post(f"/api/v1/events/by-id/{event['id']}/submit", headers=host_headers)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "seo-privacy-admin@example.com",
            "password": "securepass1",
            "full_name": "Admin",
        },
    )
    assign_role("seo-privacy-admin@example.com", "super_admin")
    admin = {
        "Authorization": (
            "Bearer "
            + client.post(
                "/api/v1/auth/login",
                json={
                    "email": "seo-privacy-admin@example.com",
                    "password": "securepass1",
                },
            ).json()["access_token"]
        )
    }
    assert (
        client.post(f"/api/v1/events/by-id/{event['id']}/approve", headers=admin).status_code
        == 200
    )

    public = client.get(f"/api/v1/events/{event['slug']}").json()
    assert "Palm Close" not in (public.get("seo_title") or "")
    assert "Palm Close" not in (public.get("seo_description") or "")
    assert "Palm Close" not in (public.get("social_share_title") or "")
    assert "Palm Close" not in (public.get("social_share_description") or "")
    joined_tags = " ".join(public.get("hashtags") or [])
    joined_kw = " ".join(public.get("discoverable_keywords") or [])
    assert "Palm Close" not in joined_tags
    assert "Palm Close" not in joined_kw


def test_area_only_keeps_city_hides_street(client: TestClient, assign_role):
    host_headers = _auth_headers(client, "area-host@example.com")
    _onboard(client, host_headers, "Area Host")
    created = client.post(
        "/api/v1/events",
        headers=host_headers,
        json=_payload(
            title="Area Only Night",
            location_visibility="area_only",
            public_location_label="Victoria Island, Lagos",
        ),
    ).json()
    client.post(f"/api/v1/events/by-id/{created['id']}/submit", headers=host_headers)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "area-admin@example.com",
            "password": "securepass1",
            "full_name": "Admin",
        },
    )
    assign_role("area-admin@example.com", "super_admin")
    admin_token = client.post(
        "/api/v1/auth/login",
        json={"email": "area-admin@example.com", "password": "securepass1"},
    ).json()["access_token"]
    client.post(
        f"/api/v1/events/by-id/{created['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    public = client.get(f"/api/v1/events/{created['slug']}").json()
    assert public["address"] is None
    assert public["city"] == "Lagos" or "Victoria" in (public["public_location_label"] or "")


def test_studio_nested_agenda_and_people(client: TestClient):
    headers = _auth_headers(client, "studio-host@example.com")
    _onboard(client, headers, "Studio Host")
    start = datetime.now(UTC) + timedelta(days=12)
    response = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Studio Nested Event",
            agenda_items=[
                {
                    "title": "Doors Open",
                    "type": "doors_open",
                    "start_time": start.isoformat(),
                    "sort_order": 0,
                },
                {
                    "title": "Headliner",
                    "type": "performance",
                    "start_time": (start + timedelta(hours=1)).isoformat(),
                    "sort_order": 1,
                },
            ],
            people=[
                {
                    "name": "DJ Nova",
                    "role": "Headliner",
                    "bio": "Afrobeats selector",
                    "sort_order": 0,
                }
            ],
            checkout_questions=[
                {
                    "label": "Phone number",
                    "type": "phone",
                    "required": True,
                    "help_text": "Include country code",
                    "sort_order": 0,
                }
            ],
            event_type="secret_location",
            visibility="unlisted",
            refund_policy_type="admin_controlled",
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["agenda_items"]) == 2
    assert body["people"][0]["name"] == "DJ Nova"
    assert body["checkout_questions"][0]["type"] == "phone"
    assert body["checkout_questions"][0]["help_text"] == "Include country code"
    assert body["publish_checklist"]["basics_complete"] is True
