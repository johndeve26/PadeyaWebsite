"""Phase 1 — API/query latency: events list, maintenance cache, RBAC memo."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.request_context import (
    get_auth_load_counters,
    reset_auth_load_counters,
    reset_user_rbac_cache,
)
from app.maintenance.decision_cache import (
    get_cached_off_allow,
    invalidate_maintenance_decision_cache,
    store_off_allow,
)
from app.users.service import get_user_by_id


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Perf User", "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str = "Perf Host") -> dict:
    res = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Perf host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def _event_payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=14)
    end = start + timedelta(hours=3)
    payload = {
        "title": "Perf Night",
        "description": ("Long marketplace description. " * 40).strip(),
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "venue_name": "The Dome",
        "address": "12 Marina",
        "city": "Lagos",
        "state": "Lagos",
        "capacity": 200,
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


def _publish_event(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(**overrides),
    )
    assert created.status_code == 201, created.text
    event = created.json()
    client.post(f"/api/v1/events/by-id/{event['id']}/submit", headers=headers)
    return client.get(f"/api/v1/events/by-id/{event['id']}", headers=headers).json()


def test_events_list_sql_filters_and_lean_dto(client: TestClient):
    headers = _auth_headers(client, "perf-list@example.com")
    _onboard(client, headers, "List Host")
    published = _publish_event(client, headers, title="Lagos Jazz Card Night", city="Lagos")
    tt = client.post(
        f"/api/v1/events/by-id/{published['id']}/ticket-types",
        headers=headers,
        json={
            "name": "GA",
            "type": "General Admission",
            "price": "5000",
            "quantity": 100,
        },
    )
    assert tt.status_code == 201, tt.text

    listing = client.get("/api/v1/events", params={"q": "Jazz", "limit": 50})
    assert listing.status_code == 200, listing.text
    rows = listing.json()
    assert any(e["id"] == published["id"] for e in rows)
    hit = next(e for e in rows if e["id"] == published["id"])

    assert hit["agenda_items"] == []
    assert hit["people"] == []
    assert hit["media"] == []
    assert hit["checkout_questions"] == []
    assert hit.get("venue") in (None, {})
    assert hit["seo_title"] is None
    assert hit["what_to_expect"] is None
    assert len(hit["description"]) <= 160
    assert all(tt.get("access_code") is None for tt in hit.get("ticket_types") or [])

    city = client.get("/api/v1/events", params={"city": "lagos"})
    assert city.status_code == 200
    assert any(e["id"] == published["id"] for e in city.json())

    paid = client.get("/api/v1/events", params={"paid": "paid"})
    assert paid.status_code == 200
    assert any(e["id"] == published["id"] for e in paid.json())

    free = client.get("/api/v1/events", params={"paid": "free"})
    assert free.status_code == 200
    assert all(e["id"] != published["id"] for e in free.json())

    limited = client.get("/api/v1/events", params={"limit": 1})
    assert limited.status_code == 200
    assert len(limited.json()) <= 1

    oversized = client.get("/api/v1/events", params={"limit": 500})
    assert oversized.status_code == 422


def test_events_list_excludes_ended_and_draft(client: TestClient, db_session: Session):
    headers = _auth_headers(client, "perf-ended@example.com")
    _onboard(client, headers, "Ended Host")
    draft = client.post(
        "/api/v1/events",
        headers=headers,
        json=_event_payload(title="Still Draft"),
    ).json()
    live = _publish_event(client, headers, title="Live Card")

    from app.events.models import Event

    past = _publish_event(client, headers, title="Already Over")
    row = db_session.get(Event, UUID(past["id"]))
    assert row is not None
    row.start_datetime = datetime.now(UTC) - timedelta(days=3)
    row.end_datetime = datetime.now(UTC) - timedelta(days=2)
    db_session.commit()

    listing = client.get("/api/v1/events")
    assert listing.status_code == 200
    ids = {e["id"] for e in listing.json()}
    assert draft["id"] not in ids
    assert past["id"] not in ids
    assert live["id"] in ids


def test_events_list_ordering_start_datetime(client: TestClient):
    headers = _auth_headers(client, "perf-order@example.com")
    _onboard(client, headers, "Order Host")
    later = _publish_event(
        client,
        headers,
        title="Later Night",
        start_datetime=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        end_datetime=(datetime.now(UTC) + timedelta(days=30, hours=3)).isoformat(),
    )
    sooner = _publish_event(
        client,
        headers,
        title="Sooner Night",
        start_datetime=(datetime.now(UTC) + timedelta(days=5)).isoformat(),
        end_datetime=(datetime.now(UTC) + timedelta(days=5, hours=3)).isoformat(),
    )
    rows = client.get("/api/v1/events").json()
    ids = [e["id"] for e in rows]
    assert ids.index(sooner["id"]) < ids.index(later["id"])


def test_maintenance_off_cache_skips_db(client: TestClient):
    invalidate_maintenance_decision_cache()
    # Warm path once so mode=off is known.
    assert client.get("/health").status_code == 200
    store_off_allow(mode="off", ttl=30)
    assert get_cached_off_allow() is True

    with patch("app.maintenance.middleware.database.SessionLocal") as mock_session:
        res = client.get("/api/v1/events")
        assert res.status_code == 200
        mock_session.assert_not_called()

    invalidate_maintenance_decision_cache()


def test_maintenance_toggle_propagates_after_invalidate(
    client: TestClient, db_session: Session, assign_role
):
    from app.maintenance.service import get_or_create_settings

    invalidate_maintenance_decision_cache()
    store_off_allow(mode="off", ttl=60)
    assert client.get("/api/v1/events").status_code == 200

    settings = get_or_create_settings(db_session)
    settings.mode = "active"
    settings.message = "Phase1 maint"
    db_session.commit()
    # Without invalidation, cache would incorrectly allow — prove invalidate works.
    invalidate_maintenance_decision_cache()
    blocked = client.get("/api/v1/events")
    assert blocked.status_code == 503

    settings.mode = "off"
    db_session.commit()
    invalidate_maintenance_decision_cache()
    assert client.get("/api/v1/events").status_code == 200


def test_rbac_request_memo_same_session(db_session: Session, client: TestClient):
    headers = _auth_headers(client, "perf-rbac@example.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    user_id = UUID(me.json()["id"])

    reset_auth_load_counters()
    reset_user_rbac_cache()
    u1 = get_user_by_id(db_session, user_id)
    u2 = get_user_by_id(db_session, user_id)
    assert u1 is not None and u2 is not None
    assert u1 is u2
    counters = get_auth_load_counters()
    assert counters.user_loads == 1
    assert counters.roles_loads == 1


def test_rbac_memo_does_not_cross_sessions(db_session: Session, client: TestClient):
    from app.core.database import SessionLocal

    headers = _auth_headers(client, "perf-rbac2@example.com")
    user_id = UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])

    reset_auth_load_counters()
    reset_user_rbac_cache()
    first = get_user_by_id(db_session, user_id)
    other = SessionLocal()
    try:
        second = get_user_by_id(other, user_id)
        assert first is not None and second is not None
        assert first is not second
        assert get_auth_load_counters().user_loads == 2
    finally:
        other.close()


def test_suspended_user_still_blocked(client: TestClient, db_session: Session, assign_role):
    headers = _auth_headers(client, "perf-suspend@example.com")
    _onboard(client, headers)
    me = client.get("/api/v1/auth/me", headers=headers).json()

    from app.users.models import User

    user = db_session.get(User, UUID(me["id"]))
    assert user is not None
    user.is_active = False
    user.account_status = "suspended"
    db_session.commit()

    res = client.get("/api/v1/hosts/me", headers=headers)
    assert res.status_code in {401, 403}


def test_sponsor_public_hides_private_fields(client: TestClient, db_session: Session):
    from app.sponsorships.models import Sponsor

    sponsor = Sponsor(
        owner_user_id=None,
        user_id=None,
        company_name="Public Perf Brand",
        display_name="Public Perf Brand",
        slug="public-perf-brand",
        sponsor_type="brand",
        contact_name="PR",
        contact_email="pr@perf.example.com",
        status="active",
        verification_status="verified",
        visibility="public",
        onboarding_status="active",
        short_bio="Verified sponsor",
        industry="Tech",
        categories=["nightlife"],
    )
    db_session.add(sponsor)
    db_session.commit()

    resp = client.get("/api/v1/sponsors/public/public-perf-brand")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    blob = json.dumps(body).lower()
    assert "budget" not in blob
    assert "team_members" not in body
    assert body.get("slug") == "public-perf-brand"


def test_legacy_public_routes_share_payload_shape(client: TestClient):
    headers = _auth_headers(client, "perf-legacy@example.com")
    host = _onboard(client, headers, "Legacy Perf Host")
    _publish_event(client, headers, title="Legacy Live Show")

    a = client.get(f"/api/v1/legacy/{host['slug']}")
    b = client.get(f"/api/v1/u/{host['slug']}/legacy")
    assert a.status_code == 200, a.text
    assert b.status_code == 200, b.text
    body_a, body_b = a.json(), b.json()
    for key in (
        "display_name",
        "username",
        "upcoming_events",
        "past_events",
        "stats",
        "reviews",
        "share_path",
    ):
        assert key in body_a
        assert key in body_b
    assert body_a["username"] == host["slug"]
    assert body_b["username"] == host["slug"]
