"""Featured Placement Slots / Pàdéyá Picks tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.events.models import EventCategory


def _admin(client: TestClient, assign_role, email: str = "picks-admin@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Picks Admin"},
    )
    assign_role(email, "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _host_event(client: TestClient, assign_role, email: str, title: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Host"},
    )
    assign_role(email, "host")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": f"Host {email}",
            "bio": "Picks host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    start = datetime.now(UTC) + timedelta(days=5)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": title,
            "description": "A published night for Pàdéyá Picks placement coverage.",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=3)).isoformat(),
            "venue_name": "Arena",
            "city": "Lagos",
            "state": "Lagos",
            "visibility": "listed",
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    assert (
        client.post(
            f"/api/v1/events/by-id/{event_id}/submit", headers=headers
        ).status_code
        == 200
    )
    admin = _admin(client, assign_role, f"approve-{email}")
    approved = client.post(
        f"/api/v1/events/by-id/{event_id}/approve", headers=admin
    )
    assert approved.status_code == 200, approved.text
    return event_id


def test_padeya_picks_global_events_context(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "picks-h1@example.com", "Picks Night One")
    e2 = _host_event(client, assign_role, "picks-h2@example.com", "Picks Night Two")
    admin = _admin(client, assign_role, "picks-ops@example.com")

    empty = client.get("/api/v1/events/padeya-picks", params={"context": "events"})
    assert empty.status_code == 200
    assert empty.json() == []

    slots = client.get(
        "/api/v1/admin/featured-placements",
        headers=admin,
        params={"context_type": "events"},
    )
    assert slots.status_code == 200
    assert len(slots.json()) == 2
    assert {s["slot_number"] for s in slots.json()} == {1, 2}
    assert slots.json()[0]["slot_label"] == "Primary Spotlight"
    assert slots.json()[1]["slot_label"] == "Secondary Spotlight"

    a1 = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "events", "event_id": e1},
    )
    assert a1.status_code == 200, a1.text
    assert a1.json()["event_id"] == e1
    assert a1.json()["context_type"] == "events_page"
    assert a1.json()["placement_type"] == "events_page"
    assert a1.json()["status"] == "active"

    a2 = client.put(
        "/api/v1/admin/featured-placements/2",
        headers=admin,
        json={"context_type": "events", "event_id": e2},
    )
    assert a2.status_code == 200, a2.text

    dup = client.put(
        "/api/v1/admin/featured-placements/2",
        headers=admin,
        json={"context_type": "events", "event_id": e1},
    )
    assert dup.status_code == 409

    picks = client.get("/api/v1/events/padeya-picks", params={"context": "events"})
    assert picks.status_code == 200
    assert [p["id"] for p in picks.json()] == [e1, e2]

    # Default context is events
    assert [p["id"] for p in client.get("/api/v1/events/padeya-picks").json()] == [
        e1,
        e2,
    ]

    cleared = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "events", "event_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["event_id"] is None
    picks2 = client.get("/api/v1/events/padeya-picks", params={"context": "events"})
    assert [p["id"] for p in picks2.json()] == [e2]


def test_padeya_picks_set_upsert_and_status(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "set-h1@example.com", "Set Night One")
    e2 = _host_event(client, assign_role, "set-h2@example.com", "Set Night Two")
    admin = _admin(client, assign_role, "set-ops@example.com")

    created = client.put(
        "/api/v1/admin/featured-placements/sets",
        headers=admin,
        json={
            "context_type": "events_page",
            "slot_1": {"event_id": e1},
            "slot_2": {"event_id": e2},
            "title_override": "Weekend Picks",
            "badge_text": "Pàdéyá Picks",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["id"]
    assert body["display_title"] == "Weekend Picks"
    assert body["status"] == "active"
    assert [s["event_id"] for s in body["slots"]] == [e1, e2]

    set_id = body["id"]
    fetched = client.get(
        f"/api/v1/admin/featured-placements/sets/{set_id}",
        headers=admin,
    )
    assert fetched.status_code == 200
    assert fetched.json()["title_override"] == "Weekend Picks"

    deactivated = client.post(
        f"/api/v1/admin/featured-placements/sets/{set_id}/status",
        headers=admin,
        json={"status": "draft"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "draft"

    archived = client.post(
        f"/api/v1/admin/featured-placements/sets/{set_id}/status",
        headers=admin,
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_padeya_picks_city_and_category_contexts(
    client: TestClient, assign_role, db_session: Session
):
    e1 = _host_event(client, assign_role, "ctx-h1@example.com", "Lagos Spotlight")
    e2 = _host_event(client, assign_role, "ctx-h2@example.com", "Nightlife Spotlight")
    e3 = _host_event(client, assign_role, "ctx-h3@example.com", "Lagos Nightlife Spot")
    admin = _admin(client, assign_role, "ctx-ops@example.com")

    lagos = client.get("/api/v1/taxonomy/locations/city/lagos").json()["location"]
    nightlife = (
        db_session.query(EventCategory).filter(EventCategory.slug == "nightlife").first()
    )
    assert nightlife is not None

    city_assign = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={
            "context_type": "city",
            "location_id": lagos["id"],
            "event_id": e1,
        },
    )
    assert city_assign.status_code == 200, city_assign.text

    cat_assign = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={
            "context_type": "category",
            "category_id": str(nightlife.id),
            "event_id": e2,
        },
    )
    assert cat_assign.status_code == 200, cat_assign.text

    combo = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={
            "context_type": "city_category",
            "location_id": lagos["id"],
            "category_id": str(nightlife.id),
            "event_id": e3,
        },
    )
    assert combo.status_code == 200, combo.text

    city_picks = client.get(
        "/api/v1/events/padeya-picks",
        params={
            "context": "city",
            "location_kind": "city",
            "location_slug": "lagos",
        },
    )
    assert city_picks.status_code == 200
    assert [p["id"] for p in city_picks.json()] == [e1]

    cat_picks = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "category", "category": "nightlife"},
    )
    assert [p["id"] for p in cat_picks.json()] == [e2]

    combo_picks = client.get(
        "/api/v1/events/padeya-picks",
        params={
            "context": "city_category",
            "location_kind": "city",
            "location_slug": "lagos",
            "category": "nightlife",
        },
    )
    assert [p["id"] for p in combo_picks.json()] == [e3]

    homepage = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "global_homepage", "event_id": e1},
    )
    assert homepage.status_code == 200
    home_picks = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "global_homepage"},
    )
    assert [p["id"] for p in home_picks.json()] == [e1]

    contexts = client.get(
        "/api/v1/admin/featured-placements/contexts",
        headers=admin,
    )
    assert contexts.status_code == 200
    titles = {c["display_title"] for c in contexts.json()}
    assert "Global Pàdéyá Picks" in titles
    assert "Lagos Pàdéyá Picks" in titles
    assert "Nightlife Pàdéyá Picks" in titles
    assert "Lagos Nightlife Pàdéyá Picks" in titles


def test_padeya_picks_area_page_context(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "area-h1@example.com", "Lekki Spotlight")
    admin = _admin(client, assign_role, "area-ops@example.com")

    lekki = client.get("/api/v1/taxonomy/locations/area/lekki")
    assert lekki.status_code == 200, lekki.text
    area = lekki.json()["location"]
    assert isinstance(lekki.json().get("siblings"), list)

    assigned = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={
            "context_type": "area_page",
            "location_id": area["id"],
            "event_id": e1,
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["placement_type"] == "area_page"
    assert assigned.json()["area_id"] == area["id"]

    picks = client.get(
        "/api/v1/events/padeya-picks",
        params={
            "context": "area_page",
            "location_kind": "area",
            "location_slug": "lekki",
        },
    )
    assert picks.status_code == 200
    assert [p["id"] for p in picks.json()] == [e1]


def test_location_kind_slug_resolve_and_filter(
    client: TestClient, assign_role, db_session: Session
):
    detail = client.get("/api/v1/taxonomy/locations/city/lagos")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["location"]["kind"] == "city"
    assert body["location"]["slug"] == "lagos"
    assert any(a["slug"] == "nigeria" for a in body["ancestors"])
    assert any(c["slug"] == "lekki" for c in body["children"])

    state = client.get("/api/v1/taxonomy/locations/state/lagos")
    assert state.status_code == 200
    assert state.json()["location"]["kind"] == "state"

    admin = _admin(client, assign_role, "loc-filter-admin@example.com")
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "loc-filter-host@example.com",
            "password": "securepass1",
            "full_name": "Loc Host",
        },
    )
    assign_role("loc-filter-host@example.com", "host")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "loc-filter-host@example.com", "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": "Loc Host",
            "bio": "Location filter host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    lekki = client.get("/api/v1/taxonomy/locations/area/lekki").json()["location"]
    nightlife = (
        db_session.query(EventCategory).filter(EventCategory.slug == "nightlife").first()
    )
    start = datetime.now(UTC) + timedelta(days=8)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Lekki Rooftop",
            "description": "Area-scoped night for location hub descendant filters.",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=4)).isoformat(),
            "venue_name": "Rooftop",
            "city": "Lagos",
            "state": "Lagos",
            "location_id": lekki["id"],
            "category_id": str(nightlife.id) if nightlife else None,
            "visibility": "listed",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json().get("location", {}).get("slug") == "lekki"
    event_id = created.json()["id"]
    assert (
        client.post(
            f"/api/v1/events/by-id/{event_id}/submit", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/events/by-id/{event_id}/approve", headers=admin
        ).status_code
        == 200
    )

    in_area = client.get(
        "/api/v1/events",
        params={"location_kind": "area", "location_slug": "lekki"},
    )
    assert any(e["id"] == event_id for e in in_area.json())

    in_city = client.get(
        "/api/v1/events",
        params={"location_kind": "city", "location_slug": "lagos"},
    )
    assert any(e["id"] == event_id for e in in_city.json())

    in_state = client.get(
        "/api/v1/events",
        params={"location_kind": "state", "location_slug": "lagos"},
    )
    assert any(e["id"] == event_id for e in in_state.json())

    in_nigeria = client.get(
        "/api/v1/events",
        params={"location_kind": "country", "location_slug": "nigeria"},
    )
    assert any(e["id"] == event_id for e in in_nigeria.json())

    in_ibadan = client.get(
        "/api/v1/events",
        params={"location_kind": "city", "location_slug": "ibadan"},
    )
    assert all(e["id"] != event_id for e in in_ibadan.json())


def _host_headers(client: TestClient, assign_role, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Host User"},
    )
    assign_role(email, "host")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _draft_event(client: TestClient, assign_role, email: str, title: str) -> str:
    headers = _host_headers(client, assign_role, email)
    client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": f"Host {email}",
            "bio": "Draft host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    start = datetime.now(UTC) + timedelta(days=5)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": title,
            "description": "Draft event must not activate as a featured placement.",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=3)).isoformat(),
            "venue_name": "Draft Hall",
            "city": "Lagos",
            "state": "Lagos",
            "visibility": "listed",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "draft"
    return created.json()["id"]


def test_featured_placement_create_update_archive(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "life-h1@example.com", "Lifecycle One")
    e2 = _host_event(client, assign_role, "life-h2@example.com", "Lifecycle Two")
    e3 = _host_event(client, assign_role, "life-h3@example.com", "Lifecycle Three")
    admin = _admin(client, assign_role, "life-ops@example.com")

    created = client.put(
        "/api/v1/admin/featured-placements/sets",
        headers=admin,
        json={
            "context_type": "homepage",
            "slot_1": {"event_id": e1},
            "slot_2": {"event_id": e2},
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    set_id = created.json()["id"]
    assert [s["event_id"] for s in created.json()["slots"]] == [e1, e2]

    updated = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "homepage", "event_id": e3},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["event_id"] == e3
    assert updated.json()["status"] == "active"

    picks = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    )
    assert [p["id"] for p in picks.json()] == [e3, e2]

    archived = client.post(
        f"/api/v1/admin/featured-placements/sets/{set_id}/status",
        headers=admin,
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    ).json() == []


def test_only_admin_can_manage_featured_placements(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "auth-h1@example.com", "Auth Night")
    host = _host_headers(client, assign_role, "auth-host-mgr@example.com")

    denied_list = client.get(
        "/api/v1/admin/featured-placements",
        headers=host,
        params={"context_type": "events_page"},
    )
    assert denied_list.status_code == 403

    denied_assign = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=host,
        json={"context_type": "events_page", "event_id": e1},
    )
    assert denied_assign.status_code == 403

    anon = client.put(
        "/api/v1/admin/featured-placements/1",
        json={"context_type": "events_page", "event_id": e1},
    )
    assert anon.status_code in {401, 403}


def test_only_published_events_can_be_activated(client: TestClient, assign_role):
    draft_id = _draft_event(
        client, assign_role, "draft-h1@example.com", "Draft Cannot Feature"
    )
    admin = _admin(client, assign_role, "draft-ops@example.com")

    res = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "events_page", "event_id": draft_id},
    )
    assert res.status_code == 400, res.text
    assert "published" in res.json()["detail"].lower()


def test_slot_uniqueness_per_context(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "uniq-h1@example.com", "Unique Night")
    admin = _admin(client, assign_role, "uniq-ops@example.com")

    first = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "events_page", "event_id": e1},
    )
    assert first.status_code == 200, first.text

    conflict = client.put(
        "/api/v1/admin/featured-placements/2",
        headers=admin,
        json={"context_type": "events_page", "event_id": e1},
    )
    assert conflict.status_code == 409

    # Same event may appear in a different context.
    other = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "homepage", "event_id": e1},
    )
    assert other.status_code == 200, other.text


def test_expired_placements_not_returned_as_active(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "exp-h1@example.com", "Expired Spotlight")
    admin = _admin(client, assign_role, "exp-ops@example.com")
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    assigned = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={
            "context_type": "events_page",
            "event_id": e1,
            "ends_at": past,
            "status": "active",
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "expired"

    picks = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "events_page"},
    )
    assert picks.status_code == 200
    assert picks.json() == []


def test_future_scheduled_placements_not_returned_early(client: TestClient, assign_role):
    e1 = _host_event(client, assign_role, "sched-h1@example.com", "Scheduled Spotlight")
    admin = _admin(client, assign_role, "sched-ops@example.com")
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()

    assigned = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={
            "context_type": "homepage",
            "event_id": e1,
            "starts_at": future,
            "status": "scheduled",
        },
    )
    assert assigned.status_code == 200, assigned.text

    picks = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    )
    assert picks.json() == []


def test_padeya_picks_hide_private_venue_address(client: TestClient, assign_role):
    admin = _admin(client, assign_role, "pick-priv-ops@example.com")
    headers = _host_headers(client, assign_role, "pick-priv-host@example.com")
    client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": "Privacy Picks Host",
            "bio": "Hidden venue host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    street = "77 Hidden Compound Road Lekki"
    start = datetime.now(UTC) + timedelta(days=6)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Hidden Address Pick",
            "description": "Placement pick must not leak street address.",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=3)).isoformat(),
            "venue_name": "Secret Courtyard",
            "address": street,
            "city": "Lagos",
            "state": "Lagos",
            "location_visibility": "area_only",
            "public_location_label": "Lekki, Lagos",
            "visibility": "listed",
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    assert (
        client.post(
            f"/api/v1/events/by-id/{event_id}/submit", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/events/by-id/{event_id}/approve", headers=admin
        ).status_code
        == 200
    )

    assigned = client.put(
        "/api/v1/admin/featured-placements/1",
        headers=admin,
        json={"context_type": "homepage", "event_id": event_id},
    )
    assert assigned.status_code == 200, assigned.text

    picks = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    )
    assert picks.status_code == 200
    assert len(picks.json()) == 1
    blob = str(picks.json())
    assert street not in blob
    assert picks.json()[0].get("address") in (None, "")
    assert "Lekki" in (picks.json()[0].get("public_location_label") or "")


def test_empty_admin_placements_return_no_public_picks(client: TestClient, assign_role):
    """Public API returns [] when no admin placements; FE fallback fills elsewhere."""
    _admin(client, assign_role, "empty-ops@example.com")
    empty = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "events_page"},
    )
    assert empty.status_code == 200
    assert empty.json() == []


def test_listing_admin_padeya_pick_assign_clear_and_public(
    client: TestClient, assign_role
):
    e1 = _host_event(client, assign_role, "listing-pick-h1@example.com", "Listing Pick One")
    e2 = _host_event(client, assign_role, "listing-pick-h2@example.com", "Listing Pick Two")
    admin = _admin(client, assign_role, "listing-pick-ops@example.com")

    a1 = client.post(
        "/api/v1/admin/featured-placements/listing-picks",
        headers=admin,
        json={"event_id": e1, "context_type": "homepage"},
    )
    assert a1.status_code == 200, a1.text
    assert a1.json()["event_id"] == e1
    assert a1.json()["slot_number"] == 1
    assert a1.json()["status"] == "active"
    assert a1.json()["placement_type"] == "homepage"

    a2 = client.post(
        f"/api/v1/events/admin/{e2}/padeya-pick",
        headers=admin,
        params={"context_type": "homepage"},
    )
    assert a2.status_code == 200, a2.text

    picks = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    )
    assert picks.status_code == 200
    assert [p["id"] for p in picks.json()] == [e1, e2]

    full = client.post(
        "/api/v1/admin/featured-placements/listing-picks",
        headers=admin,
        json={
            "event_id": e1,
            "context_type": "homepage",
            "slot_number": 1,
        },
    )
    # Idempotent re-assign of same event
    assert full.status_code == 200, full.text

    e3 = _host_event(client, assign_role, "listing-pick-h3@example.com", "Listing Pick Three")
    conflict = client.post(
        "/api/v1/admin/featured-placements/listing-picks",
        headers=admin,
        json={"event_id": e3, "context_type": "homepage"},
    )
    assert conflict.status_code == 409

    replaced = client.post(
        f"/api/v1/events/admin/{e3}/padeya-pick",
        headers=admin,
        params={"context_type": "homepage", "slot_number": 2},
    )
    assert replaced.status_code == 200, replaced.text

    picks2 = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    )
    assert [p["id"] for p in picks2.json()] == [e1, e3]

    swapped = client.post(
        "/api/v1/admin/featured-placements/listing-picks/swap",
        headers=admin,
        json={"context_type": "homepage"},
    )
    assert swapped.status_code == 200, swapped.text
    assert [s["event_id"] for s in swapped.json()] == [e3, e1]

    picks3 = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    )
    assert [p["id"] for p in picks3.json()] == [e3, e1]

    cleared = client.post(
        f"/api/v1/events/admin/{e3}/unpadeya-pick",
        headers=admin,
        params={"context_type": "homepage"},
    )
    assert cleared.status_code == 200, cleared.text

    picks4 = client.get(
        "/api/v1/events/padeya-picks",
        params={"context": "homepage"},
    )
    assert [p["id"] for p in picks4.json()] == [e1]


def test_listing_padeya_pick_rejects_unpublished(client: TestClient, assign_role):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "draft-host@example.com",
            "password": "securepass1",
            "full_name": "Draft Host",
        },
    )
    assign_role("draft-host@example.com", "host")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "draft-host@example.com", "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": "Draft Host",
            "bio": "Draft",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    start = datetime.now(UTC) + timedelta(days=5)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Still a draft",
            "description": "Not published yet for Pàdéyá Pick coverage.",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=3)).isoformat(),
            "venue_name": "Arena",
            "city": "Lagos",
            "state": "Lagos",
            "visibility": "listed",
        },
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]
    admin = _admin(client, assign_role, "draft-pick-ops@example.com")
    res = client.post(
        "/api/v1/admin/featured-placements/listing-picks",
        headers=admin,
        json={"event_id": draft_id, "context_type": "homepage"},
    )
    assert res.status_code == 400
    assert "published" in res.json()["detail"].lower()
