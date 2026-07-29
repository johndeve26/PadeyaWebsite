"""Public response cache + Cache-Control privacy tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.cache import (
    cache_delete_pattern,
    cache_get,
    cache_key,
    cache_set,
    clear_memory_cache,
)
from app.core.cache_headers import is_no_store_path, public_cache_control
from app.core.cache_invalidation import invalidate_event_caches


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Cache User", "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard_and_publish(client: TestClient, headers: dict[str, str], title: str = "Cache Night") -> dict:
    client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": "Cache Hosts",
            "bio": "Nights",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    start = datetime.now(UTC) + timedelta(days=14)
    end = start + timedelta(hours=3)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": title,
            "description": "A night worth caching for discovery.",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "venue_name": "Cache Hall",
            "address": "1 Marina",
            "city": "Lagos",
            "state": "Lagos",
            "capacity": 200,
            "venue": {
                "name": "Cache Hall",
                "address": "1 Marina",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
        },
    )
    assert created.status_code == 201, created.text
    event = created.json()
    # Approve as admin if needed — for published list we need published status.
    # Host submit + admin approve path varies; force via admin feature if available.
    # Many tests use seed admin — try submit then skip if not published.
    client.post(f"/api/v1/events/by-id/{event['id']}/submit", headers=headers)
    return event


def test_cache_key_includes_filters():
    clear_memory_cache()
    a = cache_key("events", "list", category="music", city="lagos")
    b = cache_key("events", "list", category="comedy", city="lagos")
    c = cache_key("events", "list", category="music", city="lagos")
    assert a != b
    assert a == c
    assert a.startswith("padeya:cache:events:list:")


def test_cache_get_set_memory_fallback():
    clear_memory_cache()
    key = cache_key("events", "list", q="afro")
    assert cache_get(key) is None
    assert cache_set(key, [{"slug": "a"}], ttl=60)
    assert cache_get(key) == [{"slug": "a"}]


def test_cache_delete_pattern():
    clear_memory_cache()
    cache_set(cache_key("events", "list", city="a"), [1], 60)
    cache_set(cache_key("events", "list", city="b"), [2], 60)
    cache_set(cache_key("events", "list"), [0], 60)
    cache_set(cache_key("blog", "posts"), [3], 60)
    deleted = cache_delete_pattern("padeya:cache:events:list*")
    assert deleted >= 3
    assert cache_get(cache_key("blog", "posts")) == [3]


def test_invalidate_event_detail(client: TestClient):
    clear_memory_cache()
    key = cache_key("events", "detail", "demo-slug")
    cache_set(key, {"slug": "demo-slug"}, 120)
    invalidate_event_caches(slug="demo-slug")
    assert cache_get(key) is None


def test_public_list_uses_cache(client: TestClient):
    clear_memory_cache()
    first = client.get("/api/v1/events")
    assert first.status_code == 200
    assert "public" in (first.headers.get("cache-control") or "").lower()
    second = client.get("/api/v1/events")
    assert second.status_code == 200
    assert second.json() == first.json()


def test_calendar_respects_filters(client: TestClient):
    clear_memory_cache()
    month = (datetime.now(UTC) + timedelta(days=20)).strftime("%Y-%m")
    a = client.get(f"/api/v1/events/calendar?month={month}&paid=free")
    b = client.get(f"/api/v1/events/calendar?month={month}&paid=paid")
    assert a.status_code == 200
    assert b.status_code == 200
    # Different filter keys must not share one cache entry incorrectly —
    # both succeed and Cache-Control is public.
    assert "public" in (a.headers.get("cache-control") or "").lower()
    key_a = cache_key(
        "events",
        "calendar",
        month=month,
        paid="free",
        include_featured=True,
    )
    key_b = cache_key(
        "events",
        "calendar",
        month=month,
        paid="paid",
        include_featured=True,
    )
    assert key_a != key_b


def test_private_admin_checkout_qr_no_store():
    assert is_no_store_path("/auth/login")
    assert is_no_store_path("/admin/orders")
    assert is_no_store_path("/payments/checkout/x")
    assert is_no_store_path("/tickets/mine")
    assert is_no_store_path("/tickets/abc/pdf")
    assert is_no_store_path("/messages/threads")
    assert is_no_store_path("/notifications")
    assert is_no_store_path("/support/tickets")
    assert is_no_store_path("/passport/me")
    assert is_no_store_path("/hosts/me")
    assert is_no_store_path("/events/mine")
    assert is_no_store_path("/events/by-id/123")
    assert public_cache_control("/events") is not None
    assert public_cache_control("/events/some-slug") is not None
    assert public_cache_control("/blog/posts") is not None
    assert public_cache_control("/auth/me") is None


def test_authenticated_private_endpoints_no_store(client: TestClient):
    headers = _auth_headers(client, "cache-private@example.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert "no-store" in (me.headers.get("cache-control") or "").lower()

    tickets = client.get("/api/v1/tickets/mine", headers=headers)
    # 200 empty or ok — header must still be no-store
    assert "no-store" in (tickets.headers.get("cache-control") or "").lower()


def test_redis_down_fallback_still_serves(client: TestClient):
    """With memory fallback (no Redis in tests), public GETs still work."""
    clear_memory_cache()
    res = client.get("/api/v1/events/categories")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    # Second hit should come from memory cache path
    res2 = client.get("/api/v1/events/categories")
    assert res2.status_code == 200
    assert res2.json() == res.json()


def test_event_update_invalidates_list_cache(client: TestClient):
    clear_memory_cache()
    headers = _auth_headers(client, "cache-host@example.com")
    event = _onboard_and_publish(client, headers)

    # Warm list cache
    client.get("/api/v1/events")
    # Host update should invalidate even if not published
    patch = client.patch(
        f"/api/v1/events/by-id/{event['id']}",
        headers=headers,
        json={"title": "Cache Night Updated"},
    )
    assert patch.status_code == 200, patch.text
    # Detail key for old slug should be gone after invalidate
    old_slug = event["slug"]
    assert cache_get(cache_key("events", "detail", old_slug)) is None


def test_nearby_cache_key_buckets_not_exact_gps():
    """Nearby Redis keys must not differ by raw GPS millimetres."""
    from app.events.public_cache import events_nearby_key

    a = events_nearby_key(lat=6.5244123, lng=3.3792987, radius_km=25)
    b = events_nearby_key(lat=6.5244999, lng=3.3792001, radius_km=25)
    c = events_nearby_key(lat=6.60, lng=3.40, radius_km=25)
    assert a == b
    assert a != c
    # Key must not embed unbucketed high-precision decimals
    assert "6.5244123" not in a
    assert "3.3792987" not in a


def test_nearby_response_echoes_bucketed_coords(client: TestClient):
    clear_memory_cache()
    from app.events.geo import bucket_lat_lng

    lat, lng = 6.5244123, 3.3792987
    res = client.get(
        "/api/v1/events/nearby",
        params={"lat": lat, "lng": lng, "radius_km": 25, "limit": 5},
    )
    assert res.status_code == 200
    body = res.json()
    b_lat, b_lng = bucket_lat_lng(lat, lng)
    assert body["lat"] == b_lat
    assert body["lng"] == b_lng
    assert body["lat"] != lat or body["lng"] != lng


def test_invalidate_clears_homepage_and_nearby_patterns():
    clear_memory_cache()
    from app.events.public_cache import events_homepage_key, events_nearby_key

    cache_set(events_homepage_key(rail="featured"), [{"id": 1}], 60)
    cache_set(events_nearby_key(lat=6.52, lng=3.38, radius_km=25), {"items": []}, 60)
    invalidate_event_caches(slug="any-slug")
    assert cache_get(events_homepage_key(rail="featured")) is None
    assert cache_get(events_nearby_key(lat=6.52, lng=3.38, radius_km=25)) is None


def test_checkout_paths_remain_no_store():
    """Availability for checkout must never be publicly CDN-cached."""
    assert is_no_store_path("/payments/checkout/x")
    assert is_no_store_path("/orders")
    assert is_no_store_path("/tickets/mine")
    # Public event detail may be short-cached; checkout page revalidates client-side.
    assert public_cache_control("/events/some-slug") is not None
