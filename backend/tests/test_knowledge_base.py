"""Knowledge Base / Help Center API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.http_errors import NOT_FOUND_CODE
from app.knowledge_base.sanitize import sanitize_html
from app.knowledge_base.seed import seed_knowledge_base
from app.knowledge_base.service import render_body_html
from app.knowledge_base.video import parse_video_url


def _register(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "KB Admin",
        },
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _admin(client: TestClient, db: Session, assign_role, email: str) -> dict[str, str]:
    headers = _register(client, email)
    assign_role(email, "super_admin")
    return headers


def test_xss_content_is_sanitized():
    dirty = (
        '<script>alert(1)</script><p onclick="x">Hi</p>'
        '<a href="javascript:alert(1)">x</a>'
    )
    clean = sanitize_html(dirty)
    assert "<script" not in clean.lower()
    assert "onclick" not in clean.lower()
    assert 'href="javascript:' not in clean.lower()
    html = render_body_html("Hello **safe**\n\n[bad](javascript:alert(1))")
    assert "<strong>safe</strong>" in html
    assert 'href="javascript:' not in html.lower()


def test_video_safe_embed_only():
    yt = parse_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert yt["provider"] == "youtube"
    assert yt["embed_url"] and "youtube-nocookie.com" in yt["embed_url"]
    assert "javascript:" not in (yt["embed_url"] or "")

    vm = parse_video_url("https://vimeo.com/123456789")
    assert vm["provider"] == "vimeo"
    assert vm["embed_url"] and "player.vimeo.com" in vm["embed_url"]

    ext = parse_video_url("https://example.com/video.mp4")
    assert ext["provider"] == "external"
    assert ext["embed_url"] is None

    try:
        parse_video_url("javascript:alert(1)")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_seed_and_public_help_index(client: TestClient, db_session: Session):
    seeded = seed_knowledge_base(db_session)
    assert seeded["categories"] >= 1 or seeded["articles"] >= 1 or seeded["updated"] >= 1
    res = client.get("/api/v1/help/articles")
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert all(a["status"] == "published" for a in res.json())
    cats = client.get("/api/v1/help/categories")
    assert cats.status_code == 200
    assert len(cats.json()) >= 10


def test_draft_404_and_publish(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "kb-pub@example.com")
    create = client.post(
        "/api/v1/admin/knowledge-base/articles",
        headers=headers,
        json={
            "title": "Draft only secret KB",
            "slug": "draft-only-secret-kb",
            "body": "Secret draft body",
            "excerpt": "Nope",
            "audiences": ["fan"],
        },
    )
    assert create.status_code == 201, create.text
    article_id = create.json()["id"]
    assert create.json()["status"] == "draft"

    missing = client.get("/api/v1/help/articles/draft-only-secret-kb")
    assert missing.status_code == 404
    assert missing.json()["code"] == NOT_FOUND_CODE

    pub = client.post(
        f"/api/v1/admin/knowledge-base/articles/{article_id}/publish",
        headers=headers,
    )
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"

    ok = client.get("/api/v1/help/articles/draft-only-secret-kb")
    assert ok.status_code == 200
    assert ok.json()["slug"] == "draft-only-secret-kb"
    assert "body_html" in ok.json()


def test_search_and_feedback(
    client: TestClient, db_session: Session, assign_role
):
    seed_knowledge_base(db_session)
    found = client.get("/api/v1/help/articles?q=tickets")
    assert found.status_code == 200
    assert len(found.json()) >= 1

    article = found.json()[0]
    fb = client.post(
        f"/api/v1/help/articles/{article['id']}/feedback",
        json={"is_helpful": True, "comment": "Clear steps"},
    )
    assert fb.status_code == 200
    assert fb.json()["helpful_count"] >= 1


def test_admin_video_article_and_audience_filter(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "kb-video@example.com")
    create = client.post(
        "/api/v1/admin/knowledge-base/articles",
        headers=headers,
        json={
            "title": "Host video tip",
            "slug": "host-video-tip",
            "body": "## Watch\n\nSafe embed only.",
            "content_type": "video",
            "audiences": ["host"],
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "status": "draft",
        },
    )
    assert create.status_code == 201, create.text
    article_id = create.json()["id"]
    assert create.json()["video_provider"] == "youtube"

    bad = client.patch(
        f"/api/v1/admin/knowledge-base/articles/{article_id}",
        headers=headers,
        json={"video_url": "javascript:alert(1)"},
    )
    assert bad.status_code == 400

    client.post(
        f"/api/v1/admin/knowledge-base/articles/{article_id}/publish",
        headers=headers,
    )
    detail = client.get("/api/v1/help/articles/host-video-tip")
    assert detail.status_code == 200
    assert detail.json()["video_embed_url"]
    assert "youtube-nocookie.com" in detail.json()["video_embed_url"]

    hosts = client.get("/api/v1/help/articles?audience=host")
    assert hosts.status_code == 200
    assert any(a["slug"] == "host-video-tip" for a in hosts.json())


def test_archive_hides_from_public(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin(client, db_session, assign_role, "kb-arch@example.com")
    create = client.post(
        "/api/v1/admin/knowledge-base/articles",
        headers=headers,
        json={
            "title": "Soon archived",
            "slug": "soon-archived-kb",
            "body": "Temp",
            "status": "draft",
        },
    )
    article_id = create.json()["id"]
    client.post(
        f"/api/v1/admin/knowledge-base/articles/{article_id}/publish",
        headers=headers,
    )
    assert client.get("/api/v1/help/articles/soon-archived-kb").status_code == 200
    arch = client.post(
        f"/api/v1/admin/knowledge-base/articles/{article_id}/archive",
        headers=headers,
    )
    assert arch.status_code == 200
    assert arch.json()["status"] == "archived"
    assert client.get("/api/v1/help/articles/soon-archived-kb").status_code == 404


def test_topic_suggestions_and_seed_coverage(client: TestClient, db_session: Session):
    seed_knowledge_base(db_session)
    res = client.get("/api/v1/help/suggestions?topic=tickets_orders")
    assert res.status_code == 200
    data = res.json()
    assert data["topic"] == "tickets_orders"
    assert len(data["articles"]) >= 1
    slugs = {a["slug"] for a in data["articles"]}
    assert "how-to-buy-tickets" in slugs or "how-to-find-your-qr-ticket" in slugs

    cats = client.get("/api/v1/help/categories")
    assert cats.status_code == 200
    assert len(cats.json()) >= 20

    articles = client.get("/api/v1/help/articles")
    assert len(articles.json()) >= 15
