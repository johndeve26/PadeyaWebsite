"""Blog comments — guest + auth create, public profile linking, moderation."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.blog.seed import seed_blog_content
from app.passport.service import ensure_passport
from app.users.models import User


def _register(client: TestClient, email: str, full_name: str = "Commenter") -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": full_name,
        "gender": "prefer_not_to_say"},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _admin(client: TestClient, db: Session, assign_role, email: str) -> dict[str, str]:
    headers = _register(client, email, full_name="Blog Admin")
    assign_role(email, "super_admin")
    return headers


def _published_slug(client: TestClient, db: Session, assign_role) -> str:
    seed_blog_content(db)
    res = client.get("/api/v1/blog/posts")
    assert res.status_code == 200
    assert len(res.json()) >= 1
    return res.json()[0]["slug"]


def test_guest_can_comment_without_email(
    client: TestClient, db_session: Session, assign_role
):
    slug = _published_slug(client, db_session, assign_role)
    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        json={
            "body": "Name only — no email.",
            "guest_name": "Ada Guest",
            "website": "",
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["display_name"] == "Ada Guest"
    assert res.json()["is_guest"] is True


def test_guest_can_comment(client: TestClient, db_session: Session, assign_role):
    slug = _published_slug(client, db_session, assign_role)
    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        json={
            "body": "Great write-up from a guest.",
            "guest_name": "Ada Guest",
            "guest_email": "ada@example.com",
            "website": "",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["display_name"] == "Ada Guest"
    assert data["is_guest"] is True
    assert data["passport_path"] is None
    assert data["body"] == "Great write-up from a guest."

    listed = client.get(f"/api/v1/blog/posts/{slug}/comments")
    assert listed.status_code == 200
    assert any(c["id"] == data["id"] for c in listed.json())


def test_guest_requires_name(client: TestClient, db_session: Session, assign_role):
    slug = _published_slug(client, db_session, assign_role)
    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        json={"body": "Missing name", "website": ""},
    )
    assert res.status_code == 422


def test_authenticated_comment_public_passport_is_linkable(
    client: TestClient, db_session: Session, assign_role
):
    slug = _published_slug(client, db_session, assign_role)
    headers = _register(client, "public-commenter@example.com", full_name="Public Fan")
    user = db_session.query(User).filter_by(email="public-commenter@example.com").one()
    passport = ensure_passport(db_session, user)
    passport.username = "publicfan"
    passport.display_name = "Public Fan"
    passport.visibility = "public"
    db_session.commit()

    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        headers=headers,
        json={"body": "Love this from my passport."},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["is_guest"] is False
    assert data["display_name"] == "Public Fan"
    assert data["passport_path"] == "/f/publicfan"
    assert data["is_mine"] is True


def test_private_passport_not_linkable(
    client: TestClient, db_session: Session, assign_role
):
    slug = _published_slug(client, db_session, assign_role)
    headers = _register(client, "private-commenter@example.com", full_name="Private Fan")
    user = db_session.query(User).filter_by(email="private-commenter@example.com").one()
    passport = ensure_passport(db_session, user)
    passport.username = "privatefan"
    passport.display_name = "Private Fan"
    passport.visibility = "private"
    db_session.commit()

    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        headers=headers,
        json={"body": "Quiet fan here."},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["display_name"] == "Private Fan"
    assert data["passport_path"] is None


def test_unlisted_passport_not_linkable_on_blog(
    client: TestClient, db_session: Session, assign_role
):
    slug = _published_slug(client, db_session, assign_role)
    headers = _register(client, "unlisted-commenter@example.com", full_name="Unlisted Fan")
    user = db_session.query(User).filter_by(email="unlisted-commenter@example.com").one()
    passport = ensure_passport(db_session, user)
    passport.username = "unlistedfan"
    passport.display_name = "Unlisted Fan"
    passport.visibility = "unlisted"
    db_session.commit()

    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        headers=headers,
        json={"body": "Unlisted should not advertise."},
    )
    assert res.status_code == 201, res.text
    assert res.json()["passport_path"] is None


def test_honeypot_does_not_persist(client: TestClient, db_session: Session, assign_role):
    slug = _published_slug(client, db_session, assign_role)
    before = client.get(f"/api/v1/blog/posts/{slug}/comments").json()
    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        json={
            "body": "I am a bot",
            "guest_name": "Bot",
            "website": "http://spam.example",
        },
    )
    assert res.status_code == 201
    after = client.get(f"/api/v1/blog/posts/{slug}/comments").json()
    assert len(after) == len(before)


def test_author_can_withdraw_own_comment(
    client: TestClient, db_session: Session, assign_role
):
    slug = _published_slug(client, db_session, assign_role)
    headers = _register(client, "withdraw@example.com")
    created = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        headers=headers,
        json={"body": "I'll take this back."},
    )
    assert created.status_code == 201
    comment_id = created.json()["id"]

    gone = client.delete(f"/api/v1/blog/comments/{comment_id}", headers=headers)
    assert gone.status_code == 204

    listed = client.get(f"/api/v1/blog/posts/{slug}/comments").json()
    assert all(c["id"] != comment_id for c in listed)


def test_admin_hide_and_restore(client: TestClient, db_session: Session, assign_role):
    slug = _published_slug(client, db_session, assign_role)
    admin = _admin(client, db_session, assign_role, "blog-mod@example.com")
    created = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        json={
            "body": "Needs moderation",
            "guest_name": "Temp Guest",
            "website": "",
        },
    )
    assert created.status_code == 201
    comment_id = created.json()["id"]

    hidden = client.post(
        f"/api/v1/admin/blog/comments/{comment_id}/hide", headers=admin
    )
    assert hidden.status_code == 200
    assert hidden.json()["status"] == "hidden"

    listed = client.get(f"/api/v1/blog/posts/{slug}/comments").json()
    assert all(c["id"] != comment_id for c in listed)

    restored = client.post(
        f"/api/v1/admin/blog/comments/{comment_id}/restore", headers=admin
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "published"

    listed2 = client.get(f"/api/v1/blog/posts/{slug}/comments").json()
    assert any(c["id"] == comment_id for c in listed2)


def test_strips_html_from_body(client: TestClient, db_session: Session, assign_role):
    slug = _published_slug(client, db_session, assign_role)
    res = client.post(
        f"/api/v1/blog/posts/{slug}/comments",
        json={
            "body": '<script>alert(1)</script>Nice post',
            "guest_name": "Safe Guest",
            "website": "",
        },
    )
    assert res.status_code == 201
    assert "<script" not in res.json()["body"].lower()
    assert "Nice post" in res.json()["body"]
