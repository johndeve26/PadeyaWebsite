"""Blog AI Studio — permissions, structured JSON, revisions, autosave, safety."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.blog.sanitize import validate_image_url
from app.blog.studio.rate_limit import reset_studio_rate_limits


def _register(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Studio Tester",
        "gender": "prefer_not_to_say"},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _admin(client: TestClient, db: Session, assign_role, email: str) -> dict[str, str]:
    headers = _register(client, email)
    assign_role(email, "super_admin")
    return headers


@pytest.fixture(autouse=True)
def _clear_studio_limits():
    reset_studio_rate_limits()
    yield
    reset_studio_rate_limits()


def test_anonymous_studio_forbidden(client: TestClient):
    res = client.post("/api/v1/admin/blog/ai/seo-brief", json={"title": "x"})
    assert res.status_code in (401, 403)


def test_fan_host_without_perms_403(client: TestClient, db_session: Session, assign_role):
    headers = _register(client, "studio-fan@example.com")
    res = client.post(
        "/api/v1/admin/blog/ai/seo-brief",
        headers=headers,
        json={"title": "Nightlife", "force_template": True},
    )
    assert res.status_code == 403

    assign_role("studio-fan@example.com", "host")
    res2 = client.post(
        "/api/v1/admin/blog/ai/titles",
        headers=headers,
        json={"title": "Nightlife", "force_template": True},
    )
    assert res2.status_code == 403


def test_super_admin_seo_brief_titles_outline(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "studio-admin@example.com")
    brief = {
        "topic": "Discovering events",
        "primary_keyword": "Pàdéyá events",
        "tone": "practical",
    }
    seo = client.post(
        "/api/v1/admin/blog/ai/seo-brief",
        headers=headers,
        json={"brief": brief, "title": "Discovering events", "force_template": True},
    )
    assert seo.status_code == 200, seo.text
    data = seo.json()
    assert "title_options" in data
    assert data["primary_keyword"]
    assert "Pàdéyá" in (data.get("meta_title") or "") or "padeya" in (
        data.get("proposed_slug") or ""
    ).lower()

    titles = client.post(
        "/api/v1/admin/blog/ai/titles",
        headers=headers,
        json={"brief": brief, "title": "Discovering events", "force_template": True},
    )
    assert titles.status_code == 200, titles.text
    assert len(titles.json()["titles"]) >= 3
    assert all("title" in t for t in titles.json()["titles"])

    outline = client.post(
        "/api/v1/admin/blog/ai/outline",
        headers=headers,
        json={"brief": brief, "title": "Discovering events", "force_template": True},
    )
    assert outline.status_code == 200, outline.text
    body = outline.json()
    assert body.get("approved") is False
    assert len(body["sections"]) >= 1
    assert all(s.get("level") in (2, 3) for s in body["sections"])


def test_full_draft_never_publishes(client: TestClient, db_session: Session, assign_role):
    headers = _admin(client, db_session, assign_role, "studio-draft@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Studio draft post",
            "slug": "studio-draft-post",
            "body": "Draft body",
            "excerpt": "ex",
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]
    assert create.json()["status"] == "draft"

    outline = client.post(
        "/api/v1/admin/blog/ai/outline",
        headers=headers,
        json={"title": "Studio draft post", "force_template": True},
    ).json()

    full = client.post(
        "/api/v1/admin/blog/ai/full-draft",
        headers=headers,
        json={
            "blog_post_id": post_id,
            "outline": outline,
            "title": "Studio draft post",
            "force_template": True,
        },
    )
    assert full.status_code == 200, full.text
    payload = full.json()
    assert payload["draft_status"] == "draft"
    assert payload["status"] in ("complete", "partial")

    got = client.get(f"/api/v1/admin/blog/posts/{post_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["status"] == "draft"


def test_internal_links_only_real_urls(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "studio-links@example.com")
    from app.blog.seed import seed_blog_content

    seed_blog_content(db_session)
    res = client.post(
        "/api/v1/admin/blog/ai/internal-links",
        headers=headers,
        json={"title": "events", "force_template": True},
    )
    assert res.status_code == 200, res.text
    links = res.json()["links"]
    assert links
    for link in links:
        url = link["target_url"]
        assert url.startswith("/")
        assert "://" not in url
        assert url.startswith("/blog/") or url in {
            "/events",
            "/hosts",
            "/help",
            "/blog",
            "/pricing",
        }


def test_fact_review_needs_verification(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "studio-facts@example.com")
    res = client.post(
        "/api/v1/admin/blog/ai/fact-review",
        headers=headers,
        json={
            "body": "Pàdéyá hosted 10000 events last year with perfect safety.",
            "force_template": True,
        },
    )
    assert res.status_code == 200, res.text
    claims = res.json()["claims"]
    assert claims
    for c in claims:
        assert c["review_status"] == "Needs verification"
        assert c["source_required"] is True
        assert c["source_urls"] == []


def test_revision_create_and_restore(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "studio-rev@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Revision original",
            "slug": "revision-original",
            "body": "Version one body",
            "excerpt": "e1",
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    ck = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/revisions/checkpoint",
        headers=headers,
        json={"summary": "manual checkpoint"},
    )
    assert ck.status_code == 200, ck.text
    rev_id = ck.json()["id"]

    client.patch(
        f"/api/v1/admin/blog/posts/{post_id}",
        headers=headers,
        json={"title": "Revision changed", "body": "Version two body"},
    )

    restored = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/revisions/{rev_id}/restore",
        headers=headers,
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["title"] == "Revision original"
    assert "Version one" in restored.json()["body"]


def test_autosave_conflict_409(client: TestClient, db_session: Session, assign_role):
    headers = _admin(client, db_session, assign_role, "studio-as@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Autosave post",
            "slug": "autosave-post",
            "body": "body",
            "excerpt": "e",
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]
    version = create.json()["content_version"]

    ok = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/autosave",
        headers=headers,
        json={"body": "updated", "expected_content_version": version},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["content_version"] == version + 1

    conflict = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/autosave",
        headers=headers,
        json={"body": "stale", "expected_content_version": version},
    )
    assert conflict.status_code == 409


def test_rate_limit_429(client: TestClient, db_session: Session, assign_role, monkeypatch):
    import app.blog.studio.rate_limit as rl

    monkeypatch.setattr(rl, "STUDIO_AI_PER_MINUTE", 2)
    headers = _admin(client, db_session, assign_role, "studio-rl@example.com")
    for _ in range(2):
        res = client.post(
            "/api/v1/admin/blog/ai/seo-brief",
            headers=headers,
            json={"title": "Rate", "force_template": True},
        )
        assert res.status_code == 200, res.text
    limited = client.post(
        "/api/v1/admin/blog/ai/seo-brief",
        headers=headers,
        json={"title": "Rate", "force_template": True},
    )
    assert limited.status_code == 429


def test_malformed_path_uses_template_fallback(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "studio-fb@example.com")
    # force_template ensures structured JSON without network keys
    res = client.post(
        "/api/v1/admin/blog/ai/outline",
        headers=headers,
        json={"title": "Fallback outline", "force_template": True},
    )
    assert res.status_code == 200, res.text
    assert res.json()["sections"]


def test_image_url_validation_still_intact():
    with pytest.raises(ValueError):
        validate_image_url("javascript:alert(1)")
    with pytest.raises(ValueError):
        validate_image_url("data:image/png;base64,xxx")
    assert validate_image_url("https://cdn.example.com/cover.jpg") == (
        "https://cdn.example.com/cover.jpg"
    )


def test_ai_operations_no_secrets(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "studio-ops@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Ops post",
            "slug": "ops-post-studio",
            "body": "body",
            "excerpt": "e",
        },
    )
    post_id = create.json()["id"]
    client.post(
        "/api/v1/admin/blog/ai/seo-brief",
        headers=headers,
        json={
            "blog_post_id": post_id,
            "title": "Ops",
            "force_template": True,
            "client_request_id": "req-1",
        },
    )
    ops = client.get(
        f"/api/v1/admin/blog/posts/{post_id}/ai-operations", headers=headers
    )
    assert ops.status_code == 200, ops.text
    blob = ops.text.lower()
    assert "api_key" not in blob
    assert "sk-" not in blob
    assert "authorization" not in blob
    assert ops.json()
    assert ops.json()[0]["success"] is True
    assert ops.json()[0]["operation"] == "seo_brief"


def test_seo_score_local(client: TestClient, db_session: Session, assign_role):
    headers = _admin(client, db_session, assign_role, "studio-seo@example.com")
    res = client.post(
        "/api/v1/admin/blog/ai/seo-score",
        headers=headers,
        json={
            "title": "Discover events on Pàdéyá this weekend",
            "seo_title": "Discover events on Pàdéyá",
            "seo_description": "A practical guide for fans and hosts discovering nightlife and tickets on Pàdéyá.",
            "slug": "discover-events-on-padeya",
            "body": "## Intro\n\nPàdéyá events help fans find nights out.\n\n## Steps\n\nMore words " * 80,
            "focus_keyword": "pàdéyá events",
        },
    )
    assert res.status_code == 200, res.text
    assert "title_length" in res.json()


def test_preview_endpoint(client: TestClient, db_session: Session, assign_role):
    headers = _admin(client, db_session, assign_role, "studio-prev@example.com")
    create = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Preview draft",
            "slug": "preview-draft-studio",
            "body": "secret draft",
            "excerpt": "e",
        },
    )
    post_id = create.json()["id"]
    prev = client.get(f"/api/v1/admin/blog/preview/{post_id}", headers=headers)
    assert prev.status_code == 200
    assert prev.json()["status"] == "draft"
    assert prev.json()["body"] == "secret draft"
