"""Invite-field lookup preview (privacy-safe)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.passport.privacy import VISIBILITY_PRIVATE, VISIBILITY_PUBLIC
from app.passport.service import ensure_passport
from app.users.models import User


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> dict:
    r = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Lookup host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_invite_lookup_email_preview(client: TestClient):
    host_h = _auth(client, "lookup-email-host@example.com", "Lookup Email Host")
    _onboard(client, host_h, "Lookup Email Host Co")

    preview = client.get(
        "/api/v1/host/team/invites/lookup",
        headers=host_h,
        params={"identifier": "staff@example.com"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["invite_method"] == "email"
    assert body["valid"] is True
    assert body["found"] is True
    assert body["message"] == "Invite will be sent to this email."
    assert body["masked_email"]
    assert "staff@example.com" not in body["masked_email"]
    assert body["username"] is None


def test_invite_lookup_username_found_and_unknown(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "lookup-uname-host@example.com", "Lookup Uname Host")
    _onboard(client, host_h, "Lookup Uname Host Co")
    _auth(client, "lookup-member@example.com", "Lookup Member")
    member = db_session.scalar(
        select(User).where(User.email == "lookup-member@example.com")
    )
    assert member is not None
    passport = ensure_passport(db_session, member)
    passport.username = "lookup_member"
    passport.display_name = "Lookup Member"
    passport.avatar_url = "https://cdn.example.com/lookup.png"
    passport.visibility = VISIBILITY_PUBLIC
    db_session.commit()

    found = client.get(
        "/api/v1/host/team/invites/lookup",
        headers=host_h,
        params={"identifier": "@lookup_member"},
    )
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["invite_method"] == "username"
    assert body["found"] is True
    assert body["username"] == "@lookup_member"
    assert body["display_name"] == "Lookup Member"
    assert body["avatar_url"] == "https://cdn.example.com/lookup.png"
    assert body["message"] == "This user will receive an invite."
    assert body["masked_email"] is None
    assert "lookup-member@example.com" not in found.text

    missing = client.get(
        "/api/v1/host/team/invites/lookup",
        headers=host_h,
        params={"identifier": "@no_such_lookup_user"},
    )
    assert missing.status_code == 200
    miss = missing.json()
    assert miss["found"] is False
    assert miss["message"] == "No Pàdéyá user found with that username."


def test_invite_lookup_private_avatar_hidden(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "lookup-private-host@example.com", "Private Host")
    _onboard(client, host_h, "Private Host Co")
    _auth(client, "private-member@example.com", "Private Member")
    member = db_session.scalar(
        select(User).where(User.email == "private-member@example.com")
    )
    assert member is not None
    passport = ensure_passport(db_session, member)
    passport.username = "private_member"
    passport.display_name = "Private Member"
    passport.avatar_url = "https://cdn.example.com/private.png"
    passport.visibility = VISIBILITY_PRIVATE
    db_session.commit()

    preview = client.get(
        "/api/v1/host/team/invites/lookup",
        headers=host_h,
        params={"identifier": "private_member"},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["found"] is True
    assert body["display_name"] == "Private Member"
    assert body["avatar_url"] is None
