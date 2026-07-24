"""Directional Fan Connect decline cooldown + marketplace visibility."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.fan_connect.models import FanConnection
from app.fan_connect.platform_settings import DECLINE_COOLDOWN_DAYS_KEY
from app.runtime_settings.models import RuntimeSetting
from tests.test_fan_connect import (
    _attend_existing,
    _auth,
    _checked_in,
    _enable_connect,
    _public_passport,
    _seed_host,
    _user,
)


def _shared_setup(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "fc-dir-host@example.com")
    h_a = _auth(client, "fc-dir-a@example.com", "Dir A")
    h_b = _auth(client, "fc-dir-b@example.com", "Dir B")
    a = _user(db_session, "fc-dir-a@example.com")
    b = _user(db_session, "fc-dir-b@example.com")
    _public_passport(db_session, a, "dira", categories=["Afrobeats"])
    _public_passport(db_session, b, "dirb", categories=["Afrobeats"])
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    shared = _checked_in(db_session, host=host, buyer=a, slug="dir-shared-night")
    _attend_existing(db_session, host=host, buyer=b, event=shared)
    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "dirb"},
    )
    assert req.status_code == 200, req.text
    conn_id = req.json()["id"]
    dec = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/decline",
        headers=h_b,
        json={"cooldown_days": 7},
    )
    assert dec.status_code == 200
    return h_a, h_b, conn_id, a, b


def test_directional_cooldown_requester_blocked_decliner_can_request(
    client: TestClient, db_session: Session
):
    h_a, h_b, conn_id, _, _ = _shared_setup(client, db_session)

    again = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "dirb"},
    )
    assert again.status_code == 403
    assert "decline_cooldown" in again.json()["detail"]["denials"]

    reverse = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_b,
        json={"username": "dira"},
    )
    assert reverse.status_code == 200, reverse.text
    assert reverse.json()["status"] == "request_sent"
    assert reverse.json()["direction"] == "outgoing"

    conn = db_session.get(FanConnection, UUID(conn_id))
    assert conn is not None
    assert conn.requester_user_id != conn.recipient_user_id


def test_marketplace_still_shows_after_decline(
    client: TestClient, db_session: Session
):
    h_a, h_b, _, _, _ = _shared_setup(client, db_session)

    sug_a = client.get("/api/v1/fan-connect/suggestions", headers=h_a)
    assert sug_a.status_code == 200
    usernames_a = {item["username"] for item in sug_a.json()["items"]}
    assert "dirb" in usernames_a

    sug_b = client.get("/api/v1/fan-connect/suggestions", headers=h_b)
    assert sug_b.status_code == 200
    usernames_b = {item["username"] for item in sug_b.json()["items"]}
    assert "dira" in usernames_b

    card_b = next(i for i in sug_b.json()["items"] if i["username"] == "dira")
    assert card_b.get("can_send_connect_request") is True
    assert card_b.get("viewer_declined_target") is True

    card_a = next(i for i in sug_a.json()["items"] if i["username"] == "dirb")
    assert card_a.get("can_send_connect_request") is False
    assert card_a.get("cta_state") == "decline_cooldown"


def test_cooldown_expiry_allows_requester_retry(
    client: TestClient, db_session: Session
):
    h_a, _, conn_id, _, _ = _shared_setup(client, db_session)
    conn = db_session.get(FanConnection, UUID(conn_id))
    assert conn is not None
    conn.requester_cooldown_until = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    ok = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "dirb"},
    )
    assert ok.status_code == 200, ok.text


def test_decline_uses_admin_default_cooldown(
    client: TestClient, db_session: Session
):
    row = RuntimeSetting(
        key=DECLINE_COOLDOWN_DAYS_KEY,
        category="fan_connect",
        value_type="number",
        value_plain=30,
        source="db",
    )
    db_session.add(row)
    db_session.commit()

    host = _seed_host(db_session, "fc-adm-host@example.com")
    h_a = _auth(client, "fc-adm-a@example.com", "Adm A")
    h_b = _auth(client, "fc-adm-b@example.com", "Adm B")
    a = _user(db_session, "fc-adm-a@example.com")
    b = _user(db_session, "fc-adm-b@example.com")
    _public_passport(db_session, a, "adma", categories=["Afrobeats"])
    _public_passport(db_session, b, "admb", categories=["Afrobeats"])
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    shared = _checked_in(db_session, host=host, buyer=a, slug="adm-shared-night")
    _attend_existing(db_session, host=host, buyer=b, event=shared)

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "admb"},
    )
    assert req.status_code == 200
    conn_id = req.json()["id"]
    dec = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/decline",
        headers=h_b,
        json={},
    )
    assert dec.status_code == 200
    conn = db_session.get(FanConnection, UUID(conn_id))
    assert conn is not None
    assert conn.requester_cooldown_until is not None
    delta = conn.requester_cooldown_until - conn.declined_at
    assert 29 <= delta.days <= 30


def test_admin_can_update_default_cooldown(
    client: TestClient, db_session: Session, assign_role
):
    _auth(client, "fc-adm-a@example.com", "Adm A")
    assign_role("fc-adm-a@example.com", "super_admin")
    h_admin = _auth(client, "fc-adm-a@example.com", "Adm A")
    patched = client.patch(
        "/api/v1/admin/fan-connect/settings",
        headers=h_admin,
        json={"decline_cooldown_days_default": 14},
    )
    assert patched.status_code == 200
    assert patched.json()["decline_cooldown_days_default"] == 14

    bad = client.patch(
        "/api/v1/admin/fan-connect/settings",
        headers=h_admin,
        json={"decline_cooldown_days_default": 400},
    )
    assert bad.status_code == 422


def test_reverse_request_accept_connects(
    client: TestClient, db_session: Session
):
    h_a, h_b, _, _, _ = _shared_setup(client, db_session)
    rev = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_b,
        json={"username": "dira"},
    )
    assert rev.status_code == 200
    conn_id = rev.json()["id"]
    acc = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/accept",
        headers=h_a,
    )
    assert acc.status_code == 200
    assert acc.json()["status"] == "connected"
