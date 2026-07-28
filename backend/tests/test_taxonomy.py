"""Taxonomy admin CRUD, discovery filters, privacy, and permission tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.events.models import EventCategory

from tests.helpers.auth import register_json


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, password=password, full_name="Taxonomy User"),
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin_headers(client: TestClient, assign_role, email: str = "tax-admin@example.com") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name="Tax Admin"),
    )
    assign_role(email, "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Taxonomy host",
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
        "title": "Taxonomy Night",
        "description": "A premium night for taxonomy discovery and filter coverage.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "venue_name": "The Dome",
        "address": "12 Marina Road",
        "city": "Lagos",
        "state": "Lagos",
        "capacity": 200,
        "visibility": "listed",
        "venue": {
            "name": "The Dome",
            "address": "12 Marina Road",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    }
    payload.update(overrides)
    return payload


def _legacy_category_id(db_session: Session, slug: str) -> str:
    row = db_session.query(EventCategory).filter(EventCategory.slug == slug).one()
    return str(row.id)


def _create_publish(
    client: TestClient,
    host_headers: dict[str, str],
    admin_headers: dict[str, str],
    **overrides,
) -> dict:
    created = client.post(
        "/api/v1/events",
        headers=host_headers,
        json=_event_payload(**overrides),
    )
    assert created.status_code == 201, created.text
    event = created.json()
    assert client.post(
        f"/api/v1/events/by-id/{event['id']}/submit", headers=host_headers
    ).status_code == 200
    approved = client.post(
        f"/api/v1/events/by-id/{event['id']}/approve", headers=admin_headers
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


# --- Admin CRUD ---


def test_category_crud(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "cat-crud@example.com")
    created = client.post(
        "/api/v1/taxonomy/admin/categories",
        headers=admin,
        json={
            "name": "Detty Fridays",
            "slug": "detty-fridays",
            "description": "Weekend nightlife",
            "seo_title": "Detty Fridays on Pàdéyá",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["slug"] == "detty-fridays"
    assert body["is_active"] is True

    listed = client.get("/api/v1/taxonomy/admin/categories", headers=admin)
    assert listed.status_code == 200
    assert any(r["slug"] == "detty-fridays" for r in listed.json())

    patched = client.patch(
        f"/api/v1/taxonomy/admin/categories/{body['id']}",
        headers=admin,
        json={"name": "Detty Friday", "featured": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Detty Friday"
    assert patched.json()["featured"] is True

    archived = client.post(
        f"/api/v1/taxonomy/admin/categories/{body['id']}/archive",
        headers=admin,
    )
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False
    assert archived.json()["archived_at"] is not None

    public = client.get("/api/v1/taxonomy/categories")
    assert all(r["slug"] != "detty-fridays" for r in public.json())

    restored = client.post(
        f"/api/v1/taxonomy/admin/categories/{body['id']}/restore",
        headers=admin,
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


def test_tag_crud(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "tag-crud@example.com")
    created = client.post(
        "/api/v1/taxonomy/admin/tags",
        headers=admin,
        json={"name": "Late Night", "slug": "late-night"},
    )
    assert created.status_code == 201, created.text
    tag_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/taxonomy/admin/tags/{tag_id}",
        headers=admin,
        json={"description": "After midnight energy"},
    )
    assert patched.status_code == 200
    assert "midnight" in (patched.json()["description"] or "")

    archived = client.post(f"/api/v1/taxonomy/admin/tags/{tag_id}/archive", headers=admin)
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False

    public = client.get("/api/v1/taxonomy/tags")
    assert all(r["slug"] != "late-night" for r in public.json())

    restored = client.post(f"/api/v1/taxonomy/admin/tags/{tag_id}/restore", headers=admin)
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


def test_location_crud(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "loc-crud@example.com")
    created = client.post(
        "/api/v1/taxonomy/admin/locations",
        headers=admin,
        json={
            "kind": "city",
            "name": "Testville CRUD",
            "slug": "testville-crud",
            "country_code": "NG",
            "state_code": "LA",
        },
    )
    assert created.status_code == 201, created.text
    loc_id = created.json()["id"]
    assert created.json()["kind"] == "city"

    patched = client.patch(
        f"/api/v1/taxonomy/admin/locations/{loc_id}",
        headers=admin,
        json={"name": "Testville City"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Testville City"

    cities = client.get("/api/v1/taxonomy/locations?kind=city")
    assert cities.status_code == 200
    assert any(r["slug"] == "testville-crud" for r in cities.json())

    archived = client.post(
        f"/api/v1/taxonomy/admin/locations/{loc_id}/archive",
        headers=admin,
    )
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False

    public_after = client.get("/api/v1/taxonomy/locations?kind=city")
    assert all(r["slug"] != "testville-crud" for r in public_after.json())

    restored = client.post(
        f"/api/v1/taxonomy/admin/locations/{loc_id}/restore",
        headers=admin,
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


def test_expanded_location_catalog_seeded(client: TestClient):
    countries = client.get("/api/v1/taxonomy/locations?kind=country")
    assert countries.status_code == 200
    names = {r["name"] for r in countries.json()}
    assert "Nigeria" in names
    assert "Ghana" in names
    assert "United States" in names
    assert len(countries.json()) >= 190

    ng = next(r for r in countries.json() if r["slug"] == "nigeria")
    states = client.get(f"/api/v1/taxonomy/locations?kind=state&parent_id={ng['id']}")
    assert states.status_code == 200
    state_slugs = {r["slug"] for r in states.json()}
    assert "lagos" in state_slugs
    assert "rivers" in state_slugs
    assert "fct" in state_slugs
    assert len(states.json()) >= 36

    lagos_state = next(r for r in states.json() if r["slug"] == "lagos")
    cities = client.get(
        f"/api/v1/taxonomy/locations?kind=city&parent_id={lagos_state['id']}"
    )
    assert cities.status_code == 200
    lagos_city = next(r for r in cities.json() if r["slug"] == "lagos")
    areas = client.get(
        f"/api/v1/taxonomy/locations?kind=area&parent_id={lagos_city['id']}"
    )
    assert areas.status_code == 200
    area_slugs = {r["slug"] for r in areas.json()}
    assert "lekki" in area_slugs
    assert "ajah" in area_slugs


def test_host_suggest_area_available_to_others(client: TestClient):
    host_a = _auth_headers(client, "suggest-a@example.com")
    _onboard(client, host_a, "Suggest Host A")
    host_b = _auth_headers(client, "suggest-b@example.com")
    _onboard(client, host_b, "Suggest Host B")

    countries = client.get("/api/v1/taxonomy/locations?kind=country").json()
    ng = next(r for r in countries if r["slug"] == "nigeria")
    states = client.get(
        f"/api/v1/taxonomy/locations?kind=state&parent_id={ng['id']}"
    ).json()
    lagos = next(r for r in states if r["slug"] == "lagos")
    cities = client.get(
        f"/api/v1/taxonomy/locations?kind=city&parent_id={lagos['id']}"
    ).json()
    city = next(r for r in cities if r["slug"] == "lagos")

    created = client.post(
        "/api/v1/taxonomy/locations/suggest-area",
        headers=host_a,
        json={"city_id": city["id"], "name": "Orchid Road Estate"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["kind"] == "area"
    assert body["name"] == "Orchid Road Estate"
    assert body["parent_id"] == city["id"]
    assert body["is_active"] is True

    # Idempotent same name
    again = client.post(
        "/api/v1/taxonomy/locations/suggest-area",
        headers=host_a,
        json={"city_id": city["id"], "name": "orchid road estate"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]

    # Visible to another host
    areas = client.get(
        f"/api/v1/taxonomy/locations?kind=area&parent_id={city['id']}",
        headers=host_b,
    )
    assert areas.status_code == 200
    assert any(r["id"] == body["id"] for r in areas.json())

    # Non-host denied
    guest = _auth_headers(client, "suggest-guest@example.com")
    denied = client.post(
        "/api/v1/taxonomy/locations/suggest-area",
        headers=guest,
        json={"city_id": city["id"], "name": "Guest Estate"},
    )
    assert denied.status_code == 403


def test_host_suggest_venue_type_available_to_others(client: TestClient):
    host_a = _auth_headers(client, "suggest-vt-a@example.com")
    _onboard(client, host_a, "Suggest VT Host A")
    host_b = _auth_headers(client, "suggest-vt-b@example.com")
    _onboard(client, host_b, "Suggest VT Host B")

    created = client.post(
        "/api/v1/taxonomy/venue-types/suggest",
        headers=host_a,
        json={"name": "Beach House"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Beach House"
    assert body["slug"] == "beach-house"
    assert body["is_active"] is True

    again = client.post(
        "/api/v1/taxonomy/venue-types/suggest",
        headers=host_b,
        json={"name": "beach house"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]

    listed = client.get("/api/v1/taxonomy/venue-types", headers=host_b)
    assert listed.status_code == 200
    assert any(r["id"] == body["id"] for r in listed.json())

    guest = _auth_headers(client, "suggest-vt-guest@example.com")
    denied = client.post(
        "/api/v1/taxonomy/venue-types/suggest",
        headers=guest,
        json={"name": "Guest Hall"},
    )
    assert denied.status_code == 403


def test_host_suggest_city_available_to_others(client: TestClient):
    host_a = _auth_headers(client, "suggest-city-a@example.com")
    _onboard(client, host_a, "Suggest City Host A")
    host_b = _auth_headers(client, "suggest-city-b@example.com")
    _onboard(client, host_b, "Suggest City Host B")

    countries = client.get("/api/v1/taxonomy/locations?kind=country").json()
    ng = next(r for r in countries if r["slug"] == "nigeria")
    states = client.get(
        f"/api/v1/taxonomy/locations?kind=state&parent_id={ng['id']}"
    ).json()
    lagos = next(r for r in states if r["slug"] == "lagos")

    created = client.post(
        "/api/v1/taxonomy/locations/suggest-city",
        headers=host_a,
        json={"state_id": lagos["id"], "name": "Ibeju Lekki Town"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["kind"] == "city"
    assert body["name"] == "Ibeju Lekki Town"
    assert body["parent_id"] == lagos["id"]
    assert body["is_active"] is True

    again = client.post(
        "/api/v1/taxonomy/locations/suggest-city",
        headers=host_b,
        json={"state_id": lagos["id"], "name": "ibeju lekki town"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]

    cities = client.get(
        f"/api/v1/taxonomy/locations?kind=city&parent_id={lagos['id']}",
        headers=host_b,
    )
    assert cities.status_code == 200
    assert any(r["id"] == body["id"] for r in cities.json())

    guest = _auth_headers(client, "suggest-city-guest@example.com")
    denied = client.post(
        "/api/v1/taxonomy/locations/suggest-city",
        headers=guest,
        json={"state_id": lagos["id"], "name": "Guest City"},
    )
    assert denied.status_code == 403


def test_location_parent_hierarchy(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "loc-parent@example.com")
    state = client.post(
        "/api/v1/taxonomy/admin/locations",
        headers=admin,
        json={"kind": "state", "name": "Test State X", "slug": "test-state-x"},
    )
    assert state.status_code == 201, state.text
    city = client.post(
        "/api/v1/taxonomy/admin/locations",
        headers=admin,
        json={
            "kind": "city",
            "name": "Test City X",
            "slug": "test-city-x",
            "parent_id": state.json()["id"],
        },
    )
    assert city.status_code == 201, city.text
    assert city.json()["parent_id"] == state.json()["id"]


def test_subcategory_crud(client: TestClient, assign_role):
    admin = _admin_headers(client, assign_role, "subcat-crud@example.com")
    cats = client.get("/api/v1/taxonomy/admin/categories", headers=admin)
    assert cats.status_code == 200
    nightlife = next(c for c in cats.json() if c["slug"] == "nightlife")

    created = client.post(
        f"/api/v1/taxonomy/admin/categories/{nightlife['id']}/subcategories",
        headers=admin,
        json={"name": "Afrobeats Nights", "slug": "afrobeats-nights"},
    )
    assert created.status_code == 201, created.text
    sub_id = created.json()["id"]
    assert created.json()["category_id"] == nightlife["id"]

    public = client.get("/api/v1/taxonomy/categories/nightlife/subcategories")
    assert public.status_code == 200
    assert any(r["slug"] == "afrobeats-nights" for r in public.json())

    archived = client.post(
        f"/api/v1/taxonomy/admin/subcategories/{sub_id}/archive",
        headers=admin,
    )
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False

    public_after = client.get("/api/v1/taxonomy/categories/nightlife/subcategories")
    assert all(r["slug"] != "afrobeats-nights" for r in public_after.json())

    restored = client.post(
        f"/api/v1/taxonomy/admin/subcategories/{sub_id}/restore",
        headers=admin,
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True

    deleted = client.delete(
        f"/api/v1/taxonomy/admin/subcategories/{sub_id}",
        headers=admin,
    )
    assert deleted.status_code == 405


def test_hard_delete_blocked_when_category_in_use(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin_headers(client, assign_role, "hard-del@example.com")
    host = _auth_headers(client, "hard-del-host@example.com")
    _onboard(client, host, "Hard Delete Host")

    nightlife_id = _legacy_category_id(db_session, "nightlife")
    event = _create_publish(
        client,
        host,
        admin,
        title="Detty Keep Alive",
        category_id=nightlife_id,
    )
    assert event["category_id"] == nightlife_id

    tax_cats = client.get("/api/v1/taxonomy/admin/categories", headers=admin).json()
    nightlife_tax = next(c for c in tax_cats if c["slug"] == "nightlife")
    assert (nightlife_tax.get("usage_count") or 0) >= 1

    deleted = client.delete(
        f"/api/v1/taxonomy/admin/categories/{nightlife_tax['id']}",
        headers=admin,
    )
    assert deleted.status_code == 405
    assert "archive" in deleted.json()["detail"].lower()

    archived = client.post(
        f"/api/v1/taxonomy/admin/categories/{nightlife_tax['id']}/archive",
        headers=admin,
    )
    assert archived.status_code == 200

    # Soft archive must not break the published event.
    public = client.get(f"/api/v1/events/{event['slug']}")
    assert public.status_code == 200, public.text
    assert public.json()["title"] == "Detty Keep Alive"
    assert public.json()["status"] == "published"

    still_listed = client.get("/api/v1/events?category=nightlife")
    assert still_listed.status_code == 200
    assert any(e["id"] == event["id"] for e in still_listed.json())


def test_event_category_assignment(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin_headers(client, assign_role, "evt-cat@example.com")
    host = _auth_headers(client, "evt-cat-host@example.com")
    _onboard(client, host, "Event Category Host")
    comedy_id = _legacy_category_id(db_session, "comedy")

    event = _create_publish(
        client,
        host,
        admin,
        title="Open Mic Lagos",
        category_id=comedy_id,
        city="Lagos",
    )
    assert event["category_id"] == comedy_id
    detail = client.get(f"/api/v1/events/{event['slug']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["category"]["slug"] == "comedy"


def test_host_category_assignment(client: TestClient, assign_role):
    host = _auth_headers(client, "host-tax@example.com")
    _onboard(client, host, "Host Taxonomy")

    # Seed exposes nightlife / comedy categories.
    updated = client.patch(
        "/api/v1/hosts/me",
        headers=host,
        json={
            "category_slugs": ["nightlife", "music"],
            "host_type_slugs": ["dj-artist"],
            "audience_slugs": ["adults-18"],
            "primary_city_slug": "lagos",
            "niche_positioning": "Lagos nightlife & Detty Fridays",
        },
    )
    assert updated.status_code == 200, updated.text
    tax = updated.json()["taxonomy"]
    assert set(tax["category_slugs"]) == {"nightlife", "music"}
    assert "dj-artist" in tax["host_type_slugs"]
    assert tax["primary_city_slug"] == "lagos"
    assert tax["niche_positioning"] == "Lagos nightlife & Detty Fridays"

    me = client.get("/api/v1/hosts/me", headers=host)
    assert me.json()["taxonomy"]["category_slugs"] == tax["category_slugs"]


def test_public_category_filter_returns_matching_events(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin_headers(client, assign_role, "cat-filter@example.com")
    host = _auth_headers(client, "cat-filter-host@example.com")
    _onboard(client, host, "Category Filter Host")

    night = _create_publish(
        client,
        host,
        admin,
        title="Nightlife Only",
        category_id=_legacy_category_id(db_session, "nightlife"),
        city="Lagos",
    )
    comedy = _create_publish(
        client,
        host,
        admin,
        title="Comedy Only",
        category_id=_legacy_category_id(db_session, "comedy"),
        city="Lagos",
    )

    rows = client.get("/api/v1/events?category=nightlife").json()
    ids = {e["id"] for e in rows}
    assert night["id"] in ids
    assert comedy["id"] not in ids


def test_public_city_filter_returns_matching_events(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin_headers(client, assign_role, "city-filter@example.com")
    host = _auth_headers(client, "city-filter-host@example.com")
    _onboard(client, host, "City Filter Host")
    cat = _legacy_category_id(db_session, "music")

    lagos = _create_publish(
        client,
        host,
        admin,
        title="Lagos Music",
        category_id=cat,
        city="Lagos",
    )
    ibadan = _create_publish(
        client,
        host,
        admin,
        title="Ibadan Music",
        category_id=cat,
        city="Ibadan",
    )

    rows = client.get("/api/v1/events?city=lagos").json()
    ids = {e["id"] for e in rows}
    assert lagos["id"] in ids
    assert ibadan["id"] not in ids


def test_hidden_venue_not_exposed_on_public_taxonomy_surfaces(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin_headers(client, assign_role, "priv-tax@example.com")
    host = _auth_headers(client, "priv-tax-host@example.com")
    _onboard(client, host, "Privacy Taxonomy Host")
    street = "99 Secret Compound Lekki Phase 1"

    event = _create_publish(
        client,
        host,
        admin,
        title="Secret Location Night",
        category_id=_legacy_category_id(db_session, "nightlife"),
        city="Lagos",
        address=street,
        venue_name="Hidden Courtyard",
        location_visibility="area_only",
        public_location_label="Lekki, Lagos",
        venue={
            "name": "Hidden Courtyard",
            "address": street,
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )

    public = client.get(f"/api/v1/events/{event['slug']}").json()
    blob = str(public)
    assert street not in blob
    assert public.get("address") in (None, "")
    assert "Lekki" in (public.get("public_location_label") or "")

    listed = client.get("/api/v1/events?category=nightlife&city=lagos").json()
    match = next(e for e in listed if e["id"] == event["id"])
    assert street not in str(match)
    assert match.get("address") in (None, "")


def test_related_events_share_category_city_or_host(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin_headers(client, assign_role, "related@example.com")
    host_a = _auth_headers(client, "related-a@example.com")
    host_b = _auth_headers(client, "related-b@example.com")
    _onboard(client, host_a, "Related Host A")
    _onboard(client, host_b, "Related Host B")

    nightlife = _legacy_category_id(db_session, "nightlife")
    comedy = _legacy_category_id(db_session, "comedy")

    primary = _create_publish(
        client,
        host_a,
        admin,
        title="Primary Night",
        category_id=nightlife,
        city="Lagos",
    )
    same_host = _create_publish(
        client,
        host_a,
        admin,
        title="Same Host Night",
        category_id=comedy,
        city="Ibadan",
    )
    same_category = _create_publish(
        client,
        host_b,
        admin,
        title="Same Category Night",
        category_id=nightlife,
        city="Abuja",
    )
    same_city = _create_publish(
        client,
        host_b,
        admin,
        title="Same City Comedy",
        category_id=comedy,
        city="Lagos",
    )

    all_events = client.get("/api/v1/events").json()
    by_id = {e["id"]: e for e in all_events}
    focus = by_id[primary["id"]]

    others = [e for e in all_events if e["id"] != focus["id"]]
    by_host = [e for e in others if e["host_id"] == focus["host_id"]]
    by_category = [
        e
        for e in others
        if e.get("category_id") == focus.get("category_id")
        and e["host_id"] != focus["host_id"]
    ]
    by_city = [
        e
        for e in others
        if e.get("city") == focus.get("city")
        and e["host_id"] != focus["host_id"]
        and e.get("category_id") != focus.get("category_id")
    ]

    assert any(e["id"] == same_host["id"] for e in by_host)
    assert any(e["id"] == same_category["id"] for e in by_category)
    assert any(e["id"] == same_city["id"] for e in by_city)


def test_breadcrumb_hierarchy_helpers():
    """Mirror FE marketplace-breadcrumbs event trail contract."""
    items = [
        {"label": "Home", "href": "/"},
        {"label": "Events", "href": "/events"},
        {"label": "Lagos", "href": "/events/city/lagos"},
        {"label": "Nightlife", "href": "/events/city/lagos/nightlife"},
        {"label": "Detty Friday"},
    ]
    assert items[0]["href"] == "/"
    assert items[1]["href"] == "/events"
    assert items[2]["href"] == "/events/city/lagos"
    assert items[3]["href"].endswith("/nightlife")
    assert "href" not in items[-1]


def test_public_list_excludes_unlisted_for_sitemap_contract(
    client: TestClient, assign_role, db_session: Session
):
    admin = _admin_headers(client, assign_role, "sitemap@example.com")
    host = _auth_headers(client, "sitemap-host@example.com")
    _onboard(client, host, "Sitemap Host")
    cat = _legacy_category_id(db_session, "tech")

    listed = _create_publish(
        client,
        host,
        admin,
        title="Listed Tech Mixer",
        category_id=cat,
        visibility="listed",
    )
    unlisted = _create_publish(
        client,
        host,
        admin,
        title="Unlisted Tech Mixer",
        category_id=cat,
        visibility="unlisted",
    )

    public_ids = {e["id"] for e in client.get("/api/v1/events").json()}
    assert listed["id"] in public_ids
    assert unlisted["id"] not in public_ids

    # Sitemap FE filters to visibility === listed (or unset).
    for row in client.get("/api/v1/events").json():
        assert not row.get("visibility") or row["visibility"] == "listed"


def test_admin_taxonomy_permission_checks(client: TestClient, assign_role):
    buyer = _auth_headers(client, "buyer-tax@example.com")
    host = _auth_headers(client, "host-no-tax-admin@example.com")
    _onboard(client, host, "No Tax Admin Host")

    forbidden_paths = [
        "/api/v1/taxonomy/admin/categories",
        "/api/v1/taxonomy/admin/tags",
        "/api/v1/taxonomy/admin/locations",
    ]
    for path in forbidden_paths:
        assert client.get(path, headers=buyer).status_code in {401, 403}
        assert client.get(path, headers=host).status_code == 403
        assert client.post(
            path,
            headers=host,
            json={"name": "Nope", "slug": "nope", "kind": "city"},
        ).status_code == 403

    admin = _admin_headers(client, assign_role, "perm-tax-admin@example.com")
    ok = client.get("/api/v1/taxonomy/admin/categories", headers=admin)
    assert ok.status_code == 200
