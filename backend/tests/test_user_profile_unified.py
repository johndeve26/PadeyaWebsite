"""Unified username + display name + avatar profile updates."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hosts.models import Host, HostProfile
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


def test_profile_avatar_syncs_passport_and_host(
    client: TestClient, db_session: Session
) -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json=register_json(
            email="avatar-sync@example.com",
            username="avatar_sync",
            full_name="Avatar Sync",
        ),
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])

    host = Host(
        user_id=user_id,
        display_name="Avatar Sync",
        slug="avatar_sync",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, avatar_url="https://cdn.example/old.jpg"))
    db_session.commit()

    photo = "https://cdn.example.com/unified-avatar.png"
    updated = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"avatar_url": photo},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["avatar_url"] == photo

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["avatar_url"] == photo

    passport = db_session.scalar(
        select(FanPassport).where(FanPassport.user_id == user_id)
    )
    assert passport is not None
    assert passport.avatar_url == photo

    profile = db_session.scalar(
        select(HostProfile).where(HostProfile.host_id == host.id)
    )
    assert profile is not None
    assert profile.avatar_url == photo

    # Passport settings also sync to host
    photo2 = "https://cdn.example.com/from-passport.webp"
    passport_res = client.patch(
        "/api/v1/dashboard/passport/settings",
        headers=headers,
        json={"avatar_url": photo2},
    )
    assert passport_res.status_code == 200, passport_res.text
    db_session.expire_all()
    passport = db_session.scalar(
        select(FanPassport).where(FanPassport.user_id == user_id)
    )
    profile = db_session.scalar(
        select(HostProfile).where(HostProfile.host_id == host.id)
    )
    assert passport is not None and passport.avatar_url == photo2
    assert profile is not None and profile.avatar_url == photo2


def test_fan_can_upload_account_avatar(client: TestClient, db_session: Session) -> None:
    """Fans without a host profile can upload via /users/me/avatar."""
    from io import BytesIO

    from PIL import Image

    reg = client.post(
        "/api/v1/auth/register",
        json=register_json(
            email="fan-avatar@example.com",
            username="fan_avatar",
            full_name="Fan Avatar",
        ),
    )
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    user_id = UUID(
        client.get("/api/v1/auth/me", headers=headers).json()["id"]
    )

    buf = BytesIO()
    Image.new("RGB", (8, 8), (20, 180, 80)).save(buf, format="PNG")
    png = buf.getvalue()
    upload = client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", BytesIO(png), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    url = upload.json()["url"]
    assert url

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["avatar_url"] == url

    passport = db_session.scalar(
        select(FanPassport).where(FanPassport.user_id == user_id)
    )
    assert passport is not None
    assert passport.avatar_url == url


def test_fan_can_upload_via_legacy_media_staging(
    client: TestClient, db_session: Session
) -> None:
    """Old passport UI posted to /events/media/upload — fans must still succeed."""
    from io import BytesIO

    from PIL import Image

    reg = client.post(
        "/api/v1/auth/register",
        json=register_json(
            email="fan-legacy-upload@example.com",
            username="fan_legacy_up",
            full_name="Fan Legacy",
        ),
    )
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    user_id = UUID(
        client.get("/api/v1/auth/me", headers=headers).json()["id"]
    )

    buf = BytesIO()
    Image.new("RGB", (8, 8), (40, 120, 200)).save(buf, format="PNG")
    png = buf.getvalue()

    for media_type in ("other", "avatar"):
        upload = client.post(
            "/api/v1/events/media/upload",
            headers=headers,
            data={"media_type": media_type},
            files={"file": ("avatar.png", BytesIO(png), "image/png")},
        )
        assert upload.status_code == 200, upload.text
        url = upload.json()["url"]
        assert url
        db_session.expire_all()
        passport = db_session.scalar(
            select(FanPassport).where(FanPassport.user_id == user_id)
        )
        assert passport is not None
        assert passport.avatar_url == url

