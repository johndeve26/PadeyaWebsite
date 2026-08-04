"""Blog public API, admin CMS, sanitization, SEO-safe unpublished 404s."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.blog.sanitize import sanitize_html
from app.blog.seed import seed_blog_content
from app.blog.service import render_body_html
from app.core.http_errors import NOT_FOUND_CODE


def _register(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Blog Admin",
        "gender": "prefer_not_to_say"},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _admin(client: TestClient, db: Session, assign_role, email: str) -> dict[str, str]:
    headers = _register(client, email)
    assign_role(email, "super_admin")
    return headers


def test_xss_content_is_sanitized():
    dirty = '<script>alert(1)</script><p onclick="x">Hi</p><a href="javascript:alert(1)">x</a>'
    clean = sanitize_html(dirty)
    assert "<script" not in clean.lower()
    assert "onclick" not in clean.lower()
    assert 'href="javascript:' not in clean.lower()
    html = render_body_html("Hello **safe**\n\n[bad](javascript:alert(1))")
    assert "<strong>safe</strong>" in html
    assert 'href="javascript:' not in html.lower()


def test_seed_and_public_index(client: TestClient, db_session: Session, assign_role):
    seeded = seed_blog_content(db_session)
    assert seeded["posts"] >= 1
    res = client.get("/api/v1/blog/posts")
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert all(p["status"] == "published" for p in res.json())


def test_blog_detail_and_unpublished_404(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "blog-pub@example.com")
    seed_blog_content(db_session)
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Draft only secret",
            "slug": "draft-only-secret",
            "body": "Secret draft body",
            "excerpt": "Nope",
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    missing = client.get("/api/v1/blog/posts/draft-only-secret")
    assert missing.status_code == 404
    assert missing.json()["code"] == NOT_FOUND_CODE

    pub = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/publish", headers=headers
    )
    assert pub.status_code == 200
    ok = client.get("/api/v1/blog/posts/draft-only-secret")
    assert ok.status_code == 200
    assert ok.json()["slug"] == "draft-only-secret"
    assert "admin_notes" not in ok.json() or ok.json().get("admin_notes") in (None, "")


def test_admin_create_draft_and_publish(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "blog-admin2@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Host growth tips",
            "body": "## Hello\n\nGrow on Pàdéyá.",
            "excerpt": "Tips",
        },
    )
    assert create.status_code == 201
    assert create.json()["status"] == "draft"
    pid = create.json()["id"]
    published = client.post(
        f"/api/v1/admin/blog/posts/{pid}/publish", headers=headers
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"


def test_create_post_idempotent_with_client_creation_id(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "blog-idem@example.com")
    key = str(uuid.uuid4())
    payload = {
        "title": "Idempotent draft",
        "body": "Once only",
        "client_creation_id": key,
    }
    first = client.post("/api/v1/admin/blog/posts", headers=headers, json=payload)
    second = client.post("/api/v1/admin/blog/posts", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    listed = client.get("/api/v1/admin/blog/posts", headers=headers)
    assert listed.status_code == 200
    matches = [p for p in listed.json() if p.get("title") == "Idempotent draft"]
    assert len(matches) == 1


def test_category_and_tag_pages_api(
    client: TestClient, db_session: Session, assign_role
):
    seed_blog_content(db_session)
    cats = client.get("/api/v1/blog/categories")
    assert cats.status_code == 200
    assert len(cats.json()) >= 1
    slug = cats.json()[0]["slug"]
    filtered = client.get(f"/api/v1/blog/posts?category={slug}")
    assert filtered.status_code == 200
    tags = client.get("/api/v1/blog/tags")
    assert tags.status_code == 200
    if tags.json():
        tslug = tags.json()[0]["slug"]
        assert client.get(f"/api/v1/blog/posts?tag={tslug}").status_code == 200


def test_admin_force_delete_post(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "blog-force-del@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Force delete me",
            "slug": "force-delete-me",
            "body": "Gone forever",
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    bad = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/force-delete",
        headers=headers,
        json={"reason": "ab"},
    )
    assert bad.status_code == 422

    force = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/force-delete",
        headers=headers,
        json={"reason": "Test cleanup"},
    )
    assert force.status_code == 200, force.text
    assert force.json()["message"] == "Blog post permanently deleted"

    gone = client.get(f"/api/v1/admin/blog/posts/{post_id}", headers=headers)
    assert gone.status_code == 404


def test_admin_archive_rejects_already_archived_post(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "blog-archive-twice@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Archive twice",
            "slug": "archive-twice",
            "body": "Once is enough",
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    first = client.delete(f"/api/v1/admin/blog/posts/{post_id}", headers=headers)
    assert first.status_code == 204

    second = client.delete(f"/api/v1/admin/blog/posts/{post_id}", headers=headers)
    assert second.status_code == 400
    assert second.json()["detail"] == "Post is already archived"
