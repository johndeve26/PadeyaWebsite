"""Fan Passport Directory privacy matrix and admin moderation."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PRIVATE, VISIBILITY_PUBLIC, VISIBILITY_UNLISTED


def _auth(client: TestClient, email: str, name: str = "Fan") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _configure(
    client: TestClient,
    headers: dict[str, str],
    *,
    username: str,
    visibility: str,
    appear_in_directory: bool = False,
    **extra: object,
) -> None:
    client.get("/api/v1/passport/me", headers=headers)
    body = {
        "username": username,
        "visibility": visibility,
        "appear_in_directory": appear_in_directory,
        "display_name": username.replace("_", " ").title(),
        "tagline": "Demo tagline",
        **extra,
    }
    res = client.patch(
        "/api/v1/dashboard/passport/settings",
        headers=headers,
        json=body,
    )
    assert res.status_code == 200, res.text


def test_directory_privacy_matrix(client: TestClient, db_session: Session) -> None:
    private_h = _auth(client, "dir-private@example.com", "Private")
    unlisted_h = _auth(client, "dir-unlisted@example.com", "Unlisted")
    public_off_h = _auth(client, "dir-public-off@example.com", "Public Off")
    public_on_h = _auth(client, "dir-public-on@example.com", "Public On")

    _configure(
        client,
        private_h,
        username="dir_private",
        visibility=VISIBILITY_PRIVATE,
        appear_in_directory=True,  # must be forced off
    )
    _configure(
        client,
        unlisted_h,
        username="dir_unlisted",
        visibility=VISIBILITY_UNLISTED,
        appear_in_directory=True,  # must be forced off
    )
    _configure(
        client,
        public_off_h,
        username="dir_public_off",
        visibility=VISIBILITY_PUBLIC,
        appear_in_directory=False,
    )
    _configure(
        client,
        public_on_h,
        username="dir_public_on",
        visibility=VISIBILITY_PUBLIC,
        appear_in_directory=True,
    )

    listing = client.get("/api/v1/fans")
    assert listing.status_code == 200
    usernames = {item["username"] for item in listing.json()["items"]}
    assert "dir_public_on" in usernames
    assert "dir_private" not in usernames
    assert "dir_unlisted" not in usernames
    assert "dir_public_off" not in usernames

    assert client.get("/api/v1/f/dir_private").status_code == 404
    assert client.get("/api/v1/f/dir_unlisted").status_code == 200
    assert client.get("/api/v1/f/dir_public_off").status_code == 200
    assert client.get("/api/v1/f/dir_public_on").status_code == 200

    # Settings: private cannot remain directory-visible
    priv_settings = client.get(
        "/api/v1/dashboard/passport/settings", headers=private_h
    )
    assert priv_settings.json()["appear_in_directory"] is False


def test_directory_serializer_omits_private_fields(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth(client, "dir-safe@example.com", "Safe Fan")
    _configure(
        client,
        headers,
        username="dir_safe",
        visibility=VISIBILITY_PUBLIC,
        appear_in_directory=True,
    )
    res = client.get("/api/v1/fans?q=dir_safe")
    assert res.status_code == 200
    assert res.json()["total"] >= 1
    card = res.json()["items"][0]
    blob = str(card)
    assert "email" not in card
    assert "order" not in blob.lower()
    assert "payment" not in blob.lower()
    assert "phone" not in blob.lower()
    assert card["share_path"] == "/f/dir_safe"


def test_admin_hide_and_restore_fan(
    client: TestClient, db_session: Session, assign_role
) -> None:
    fan_h = _auth(client, "dir-hide-fan@example.com", "Hide Me")
    _configure(
        client,
        fan_h,
        username="dir_hide_me",
        visibility=VISIBILITY_PUBLIC,
        appear_in_directory=True,
    )
    me = client.get("/api/v1/passport/me", headers=fan_h)
    user_id = me.json()["user_id"]

    admin_h = _auth(client, "dir-admin@example.com", "Dir Admin")
    assign_role("dir-admin@example.com", "super_admin")
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "dir-admin@example.com", "password": "securepass1"},
    )
    admin_h = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    listed = client.get("/api/v1/fans?q=dir_hide_me")
    assert any(i["username"] == "dir_hide_me" for i in listed.json()["items"])

    hide = client.patch(
        f"/api/v1/admin/fans/{user_id}/hide",
        headers=admin_h,
        json={"reason": "Demo moderation hide"},
    )
    assert hide.status_code == 200
    assert hide.json()["admin_hidden"] is True

    assert client.get("/api/v1/fans?q=dir_hide_me").json()["total"] == 0
    assert client.get("/api/v1/f/dir_hide_me").status_code == 404

    restore = client.patch(
        f"/api/v1/admin/fans/{user_id}/restore",
        headers=admin_h,
        json={"reason": "Cleared after review"},
    )
    assert restore.status_code == 200
    assert restore.json()["admin_hidden"] is False
    assert client.get("/api/v1/f/dir_hide_me").status_code == 200
    assert any(
        i["username"] == "dir_hide_me"
        for i in client.get("/api/v1/fans?q=dir_hide_me").json()["items"]
    )


def test_user_settings_scoped_to_self(client: TestClient, db_session: Session) -> None:
    from sqlalchemy import select

    a = _auth(client, "dir-owner@example.com", "Owner")
    b = _auth(client, "dir-other@example.com", "Other")
    _configure(
        client,
        a,
        username="dir_owner_fan",
        visibility=VISIBILITY_PUBLIC,
        appear_in_directory=True,
        display_name="Owner Fan",
    )
    other = client.patch(
        "/api/v1/dashboard/passport/settings",
        headers=b,
        json={"display_name": "Hijack", "appear_in_directory": True},
    )
    assert other.status_code == 200
    owner = db_session.scalar(
        select(FanPassport).where(FanPassport.username == "dir_owner_fan")
    )
    assert owner is not None
    assert owner.display_name == "Owner Fan"
    me_b = client.get("/api/v1/dashboard/passport/settings", headers=b)
    assert me_b.json()["display_name"] == "Hijack"
