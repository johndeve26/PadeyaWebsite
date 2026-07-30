"""Privacy-aware gender field — registration, visibility, serializers."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.fan_connect import constants as FC
from app.fan_connect.eligibility import canonical_pair
from app.fan_connect.models import FanConnection, FanConnectionBlock
from app.hosts.models import Host, HostProfile
from app.passport.models import FanPassport
from app.passport.service import ensure_passport
from app.users.gender import (
    DEFAULT_GENDER_VISIBILITY,
    can_view_gender,
    gender_display_payload,
    host_shows_personal_gender,
)
from app.users.models import User
from tests.helpers.auth import register_json


def _auth_headers(client: TestClient, email: str, *, gender: str = "male") -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, gender=gender),
    )
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_male_female_prefer(client: TestClient, db_session: Session):
    for gender in ("male", "female", "prefer_not_to_say"):
        email = f"gender-{gender}-{uuid4().hex[:8]}@example.com"
        res = client.post(
            "/api/v1/auth/register",
            json=register_json(email=email, gender=gender),
        )
        assert res.status_code == 201, res.text
        me = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {res.json()['access_token']}"},
        )
        assert me.status_code == 200
        body = me.json()
        assert body["gender"] == gender
        assert body["gender_visibility"] == DEFAULT_GENDER_VISIBILITY
        assert body["gender_visible"] is True
        assert DEFAULT_GENDER_VISIBILITY == "public"


@pytest.mark.parametrize(
    "bad",
    ["M", "F", "man", "woman", "Male", "", 1, ["male"], {"gender": "male"}],
)
def test_register_rejects_invalid_gender(client: TestClient, bad):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"bad-g-{uuid4().hex[:8]}@example.com",
            "password": "securepass1",
            "username": f"badg{uuid4().hex[:6]}",
            "gender": bad,
        },
    )
    assert res.status_code == 422


def test_register_requires_gender(client: TestClient):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"nogender-{uuid4().hex[:8]}@example.com",
            "password": "securepass1",
            "username": f"nog{uuid4().hex[:6]}",
        },
    )
    assert res.status_code == 422


def test_existing_null_gender_login_ok(client: TestClient, db_session: Session):
    headers = _auth_headers(client, f"legacy-g-{uuid4().hex[:8]}@example.com")
    me = client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]
    user = db_session.get(User, UUID(user_id))
    assert user is not None
    user.gender = None
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"login": me.json()["email"], "password": "securepass1"},
    )
    assert login.status_code == 200
    me2 = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me2.status_code == 200
    assert me2.json()["gender"] is None


def test_profile_update_gender_and_visibility(client: TestClient):
    headers = _auth_headers(
        client, f"upd-g-{uuid4().hex[:8]}@example.com", gender="male"
    )
    res = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"gender": "female", "gender_visibility": "private"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["gender"] == "female"
    assert body["gender_short"] == "F"
    assert body["gender_visibility"] == "private"


def test_visibility_matrix(client: TestClient, db_session: Session):
    h_a = _auth_headers(client, f"va-{uuid4().hex[:8]}@example.com", gender="male")
    h_b = _auth_headers(client, f"vb-{uuid4().hex[:8]}@example.com", gender="female")
    a = client.get("/api/v1/users/me", headers=h_a).json()
    b = client.get("/api/v1/users/me", headers=h_b).json()
    owner = db_session.get(User, UUID(a["id"]))
    viewer = db_session.get(User, UUID(b["id"]))
    assert owner and viewer

    # default public — anyone can see
    payload = gender_display_payload(
        db_session, viewer=viewer, profile_owner=owner, relationship_context="profile"
    )
    assert payload["gender_visible"] is True
    assert payload["gender"] == "male"

    # owner always sees
    own = gender_display_payload(
        db_session, viewer=owner, profile_owner=owner, relationship_context="profile"
    )
    assert own["gender"] == "male"
    assert own["gender_visible"] is True

    # connections_only — unrelated cannot see
    owner.gender_visibility = "connections_only"
    db_session.commit()
    payload = gender_display_payload(
        db_session, viewer=viewer, profile_owner=owner, relationship_context="profile"
    )
    assert payload["gender_visible"] is False
    assert payload["gender"] is None

    # public
    owner.gender_visibility = "public"
    db_session.commit()
    anon = gender_display_payload(
        db_session, viewer=None, profile_owner=owner, relationship_context="profile"
    )
    assert anon["gender"] == "male"
    assert anon["gender_short"] == "M"

    # private hidden from other
    owner.gender_visibility = "private"
    db_session.commit()
    assert (
        gender_display_payload(
            db_session, viewer=viewer, profile_owner=owner, relationship_context="profile"
        )["gender_visible"]
        is False
    )


def test_connect_request_exception_and_accepted(client: TestClient, db_session: Session):
    h_a = _auth_headers(client, f"ca-{uuid4().hex[:8]}@example.com", gender="male")
    h_b = _auth_headers(client, f"cb-{uuid4().hex[:8]}@example.com", gender="female")
    a = client.get("/api/v1/users/me", headers=h_a).json()
    b = client.get("/api/v1/users/me", headers=h_b).json()
    owner = db_session.get(User, UUID(a["id"]))
    viewer = db_session.get(User, UUID(b["id"]))
    assert owner and viewer
    owner.gender_visibility = "connections_only"
    db_session.commit()

    # pending request — connect_request context allows
    low, high = canonical_pair(owner.id, viewer.id)
    conn = FanConnection(
        user_low_id=low,
        user_high_id=high,
        requester_user_id=viewer.id,
        recipient_user_id=owner.id,
        status=FC.STATUS_REQUEST_SENT,
    )
    db_session.add(conn)
    db_session.commit()

    assert can_view_gender(
        db_session,
        viewer=viewer,
        profile_owner=owner,
        relationship_context="connect_request",
    )
    assert not can_view_gender(
        db_session,
        viewer=viewer,
        profile_owner=owner,
        relationship_context="profile",
    )

    # accepted
    conn.status = FC.STATUS_CONNECTED
    db_session.commit()
    assert can_view_gender(
        db_session,
        viewer=viewer,
        profile_owner=owner,
        relationship_context="profile",
    )

    # blocked loses access
    db_session.add(
        FanConnectionBlock(
            blocker_user_id=owner.id,
            blocked_user_id=viewer.id,
            reason="test",
        )
    )
    db_session.commit()
    assert not can_view_gender(
        db_session,
        viewer=viewer,
        profile_owner=owner,
        relationship_context="profile",
    )
    assert not can_view_gender(
        db_session,
        viewer=viewer,
        profile_owner=owner,
        relationship_context="connect_request",
    )


def test_private_hidden_in_api_payload(client: TestClient, db_session: Session):
    h_a = _auth_headers(client, f"pa-{uuid4().hex[:8]}@example.com", gender="male")
    h_b = _auth_headers(client, f"pb-{uuid4().hex[:8]}@example.com")
    a = client.get("/api/v1/users/me", headers=h_a).json()
    owner = db_session.get(User, UUID(a["id"]))
    assert owner
    owner.gender_visibility = "private"
    passport = ensure_passport(db_session, owner)
    passport.visibility = "public"
    db_session.commit()

    page = client.get(f"/api/v1/f/{passport.username}")
    assert page.status_code == 200
    body = page.json()
    assert body["gender"] is None
    assert body["gender_visible"] is False
    assert body.get("gender") is None


def test_org_host_hides_personal_gender():
    assert host_shows_personal_gender(["dj-artist"]) is True
    assert host_shows_personal_gender(["venue-operator"]) is False
    assert host_shows_personal_gender(["lifestyle-brand", "dj-artist"]) is False
    assert host_shows_personal_gender([]) is True


def test_passport_owner_sees_gender_settings(client: TestClient):
    headers = _auth_headers(
        client, f"pp-{uuid4().hex[:8]}@example.com", gender="female"
    )
    res = client.get("/api/v1/passport/me", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["gender"] == "female"
    assert body["gender_short"] == "F"
    assert body["gender_visibility"] == "public"


def test_mass_assignment_visibility_on_register_ignored(client: TestClient):
    email = f"mass-{uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={
            **register_json(email=email, gender="male"),
            "gender_visibility": "private",
        },
    )
    assert res.status_code == 201
    me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {res.json()['access_token']}"},
    ).json()
    assert me["gender_visibility"] == "public"
