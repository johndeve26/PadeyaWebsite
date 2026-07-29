"""Notification center list, filters, and mark-read."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.notifications.categories import kind_matches_category, normalize_category
from app.notifications.service import notify_user
from app.users.models import User
from sqlalchemy import select


def test_category_helpers():
    assert normalize_category("Fan Connect") == "fan_connect"
    assert kind_matches_category("ticket.confirmed", "tickets")
    assert kind_matches_category("merch.ready_for_pickup", "merch")
    assert kind_matches_category("message.host_reply", "messages")
    assert kind_matches_category("fan_connect.request", "fan_connect")
    assert kind_matches_category("host.ticket_sale", "host")
    assert kind_matches_category("sponsor.inquiry_status", "sponsor")
    assert kind_matches_category("admin.report", "admin")
    assert not kind_matches_category("ticket.confirmed", "merch")


def test_notification_center_list_filter_and_read(
    client: TestClient, db_session: Session
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "center-user@example.com",
            "password": "Password123!",
            "full_name": "Center User",
        "gender": "prefer_not_to_say"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    user = db_session.scalar(
        select(User).where(User.email == "center-user@example.com")
    )
    assert user is not None

    notify_user(
        db_session,
        user_id=user.id,
        kind="ticket.confirmed",
        title="Ticket confirmed",
        body="Your tickets are ready on Pàdéyá.",
        link_path="/dashboard/tickets",
        send_push=False,
        dedupe_key="center:ticket:1",
    )
    notify_user(
        db_session,
        user_id=user.id,
        kind="merch.ready_for_pickup",
        title="Pickup ready",
        body="Your merch is ready at the stand.",
        link_path="/dashboard/merchandise",
        send_push=False,
        dedupe_key="center:merch:1",
    )
    notify_user(
        db_session,
        user_id=user.id,
        kind="message.host_reply",
        title="You have a new message.",
        body="Open Pàdéyá to read it.",
        link_path="/dashboard/messages",
        send_push=False,
        dedupe_key="center:msg:1",
    )
    notify_user(
        db_session,
        user_id=user.id,
        kind="fan_connect.message",
        title="You have a new message.",
        body="Open Pàdéyá to read it.",
        link_path="/dashboard/messages",
        send_push=False,
        dedupe_key="center:fcmsg:1",
    )
    db_session.commit()

    all_rows = client.get("/api/v1/notifications", headers=headers)
    assert all_rows.status_code == 200
    assert all_rows.json()["total"] >= 2
    assert all_rows.json()["unread_count"] >= 2
    assert all(
        not str(item["kind"]).startswith("message")
        and item["kind"] != "fan_connect.message"
        for item in all_rows.json()["items"]
    )

    fc = client.get(
        "/api/v1/notifications",
        headers=headers,
        params={"category": "fan_connect"},
    )
    assert fc.status_code == 200
    assert all(
        item["kind"] != "fan_connect.message" for item in fc.json()["items"]
    )

    msg_rows = client.get(
        "/api/v1/notifications",
        headers=headers,
        params={"category": "messages"},
    )
    assert msg_rows.status_code == 200
    assert msg_rows.json()["total"] >= 1

    unread_only = client.get(
        "/api/v1/notifications",
        headers=headers,
        params={"unread_only": True, "limit": 10},
    )
    assert unread_only.status_code == 200
    assert unread_only.json()["total"] >= 2
    assert all(item["read_at"] is None for item in unread_only.json()["items"])
    assert all(
        not str(item["kind"]).startswith("message")
        and item["kind"] != "fan_connect.message"
        for item in unread_only.json()["items"]
    )

    tickets = client.get(
        "/api/v1/notifications",
        headers=headers,
        params={"category": "tickets"},
    )
    assert tickets.status_code == 200
    assert tickets.json()["total"] >= 1
    assert all(
        str(item["kind"]).startswith("ticket") for item in tickets.json()["items"]
    )

    merch = client.get(
        "/api/v1/notifications",
        headers=headers,
        params={"category": "merch"},
    )
    assert merch.status_code == 200
    assert merch.json()["total"] >= 1

    unread = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread.status_code == 200
    before = unread.json()["unread_count"]
    assert before >= 2

    ticket_id = tickets.json()["items"][0]["id"]
    marked = client.post(
        f"/api/v1/notifications/{ticket_id}/read",
        headers=headers,
    )
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    after_one = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert after_one.json()["unread_count"] == before - 1

    all_read = client.post("/api/v1/notifications/read-all", headers=headers)
    assert all_read.status_code == 200
    assert all_read.json()["marked"] >= 1

    zero = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert zero.json()["unread_count"] == 0
