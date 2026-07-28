"""Unified username + display name profile updates."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hosts.models import Host
from app.passport.models import FanPassport
from tests.helpers.auth import register_json


def test_profile_update_syncs_username_and_display_name(
    client: TestClient, db_session: Session
) -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json=register_json(
            email="profile-sync@example.com",
            username="dj_sync",
            full_name="DJ Sync",
        ),
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])

    host = Host(
        user_id=user_id,
        display_name="DJ Sync",
        slug="dj_sync",
        status="active",
    )
    db_session.add(host)
    db_session.commit()

    updated = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"display_name": "DJ Maze", "username": "dj_maze"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["full_name"] == "DJ Maze"
    assert body["username"] == "dj_maze"

    passport = db_session.scalar(
        select(FanPassport).where(FanPassport.user_id == user_id)
    )
    assert passport is not None
    assert passport.username == "dj_maze"
    assert passport.display_name == "DJ Maze"

    host_row = db_session.scalar(select(Host).where(Host.user_id == user_id))
    assert host_row is not None
    assert host_row.slug == "dj_maze"
    assert host_row.display_name == "DJ Maze"
