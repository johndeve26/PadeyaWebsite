"""Event calendar month grouping + discovery endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.events.calendar_service import (
    list_calendar_month,
    parse_month,
)


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Cal Host"},
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
                "bio": "Calendar tests",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
        ).status_code
        == 201
    )


def _payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=20)
    # Anchor to mid-month-ish of the start month for stable grouping
    start = start.replace(hour=18, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=4)
    body = {
        "title": "Calendar Night",
        "description": "Calendar discovery coverage for Pàdéyá events with enough detail.",
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
    client: TestClient,
    headers: dict[str, str],
    assign_role,
    event_id: str,
    admin_email: str,
):
    assert (
        client.post(
            f"/api/v1/events/by-id/{event_id}/submit", headers=headers
        ).status_code
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
        client.post(
            f"/api/v1/events/by-id/{event_id}/approve", headers=admin
        ).status_code
        == 200
    )
    return admin


def test_parse_month_valid():
    assert parse_month("2026-07") == (2026, 7)


@pytest.mark.parametrize(
    "raw",
    ["", "2026", "2026-13", "1999-01", "july", "2026/07"],
)
def test_parse_month_invalid(raw: str):
    with pytest.raises(ValueError):
        parse_month(raw)


def test_calendar_invalid_month_returns_400(client: TestClient):
    res = client.get("/api/v1/events/calendar", params={"month": "not-a-month"})
    assert res.status_code == 400
    assert "YYYY-MM" in res.json()["detail"]


def test_calendar_empty_month(client: TestClient, db_session):
    # Far-future empty month — no published events
    payload = list_calendar_month(db_session, month="2099-01")
    assert payload["month"] == "2099-01"
    assert payload["days"] == []
    assert payload["total_events"] == 0
    assert payload["featured_event"] is None

    res = client.get("/api/v1/events/calendar", params={"month": "2099-01"})
    assert res.status_code == 200
    body = res.json()
    assert body["month"] == "2099-01"
    assert body["days"] == []
    assert body["total_events"] == 0


def test_calendar_groups_by_day(client: TestClient, assign_role, db_session):
    headers = _auth_headers(client, "cal-host@example.com")
    _onboard(client, headers, "Cal Host")

    day_a = datetime.now(UTC) + timedelta(days=25)
    day_a = day_a.replace(hour=19, minute=0, second=0, microsecond=0)
    day_b = day_a + timedelta(days=2)

    created = []
    for title, start in (
        ("Night One", day_a),
        ("Night Two Same Day", day_a + timedelta(hours=1)),
        ("Night Three", day_b),
    ):
        end = start + timedelta(hours=3)
        res = client.post(
            "/api/v1/events",
            headers=headers,
            json=_payload(
                title=title,
                start_datetime=start.isoformat(),
                end_datetime=end.isoformat(),
            ),
        )
        assert res.status_code == 201, res.text
        created.append(res.json())

    for i, event in enumerate(created):
        _publish(
            client,
            headers,
            assign_role,
            event["id"],
            f"cal-admin-{i}@example.com",
        )

    month = f"{day_a.year:04d}-{day_a.month:02d}"
    res = client.get("/api/v1/events/calendar", params={"month": month})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["month"] == month
    assert body["total_events"] == 3
    assert len(body["days"]) == 2

    day_keys = {d["date"] for d in body["days"]}
    assert day_a.date().isoformat() in day_keys
    assert day_b.date().isoformat() in day_keys

    same_day = next(d for d in body["days"] if d["date"] == day_a.date().isoformat())
    assert same_day["event_count"] == 2
    assert len(same_day["events"]) == 2
    assert {e["title"] for e in same_day["events"]} == {
        "Night One",
        "Night Two Same Day",
    }

    # Compact shape
    sample = same_day["events"][0]
    for key in ("id", "slug", "title", "start_datetime", "featured", "is_free"):
        assert key in sample


def test_calendar_featured_fallback(client: TestClient, assign_role, db_session):
    headers = _auth_headers(client, "cal-feat-host@example.com")
    _onboard(client, headers, "Feat Host")

    early = datetime.now(UTC) + timedelta(days=18)
    early = early.replace(hour=17, minute=0, second=0, microsecond=0)
    later = early + timedelta(days=3)

    early_res = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Sooner Night",
            start_datetime=early.isoformat(),
            end_datetime=(early + timedelta(hours=3)).isoformat(),
        ),
    )
    later_res = client.post(
        "/api/v1/events",
        headers=headers,
        json=_payload(
            title="Later Featured",
            start_datetime=later.isoformat(),
            end_datetime=(later + timedelta(hours=3)).isoformat(),
        ),
    )
    assert early_res.status_code == 201
    assert later_res.status_code == 201
    early_id = early_res.json()["id"]
    later_id = later_res.json()["id"]

    admin = _publish(
        client, headers, assign_role, early_id, "cal-feat-admin@example.com"
    )
    _publish(
        client, headers, assign_role, later_id, "cal-feat-admin-2@example.com"
    )

    month = f"{early.year:04d}-{early.month:02d}"

    # No featured flag → fallback is earliest upcoming in month
    res = client.get(
        "/api/v1/events/calendar",
        params={"month": month, "include_featured": True},
    )
    assert res.status_code == 200
    featured = res.json()["featured_event"]
    assert featured is not None
    assert featured["title"] == "Sooner Night"

    # Feature the later event → preferred over sooner
    assert (
        client.post(
            f"/api/v1/events/admin/{later_id}/feature", headers=admin
        ).status_code
        == 200
    )

    res2 = client.get(
        "/api/v1/events/calendar",
        params={"month": month, "include_featured": True},
    )
    assert res2.status_code == 200
    featured2 = res2.json()["featured_event"]
    assert featured2 is not None
    assert featured2["title"] == "Later Featured"
    assert featured2["featured"] is True

    # include_featured=false omits spotlight
    res3 = client.get(
        "/api/v1/events/calendar",
        params={"month": month, "include_featured": False},
    )
    assert res3.status_code == 200
    assert res3.json()["featured_event"] is None

    # Sanity: host filter with unknown host yields empty
    empty = list_calendar_month(
        db_session, month=month, host_id=uuid4(), include_featured=True
    )
    assert empty["total_events"] == 0
    assert empty["featured_event"] is None
