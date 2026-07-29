"""Blog analytics — taxonomy, aggregation, trusted publish emits."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_team.service import ensure_system_admin_roles
from app.analytics.models import AnalyticsEvent
from app.analytics.taxonomy import TrackedAction, normalize_tracked_action
from app.blog.models import BlogPost
from app.blog.seed import seed_blog_content
from app.users.seed import seed_roles_and_permissions


def _register(client: TestClient, *, prefix: str) -> tuple[dict, str]:
    email = f"{prefix}-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Blog Analytics",
        },
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}, email


def test_blog_page_view_normalizes_from_path():
    assert (
        normalize_tracked_action("page_view", path="/blog")
        == TrackedAction.BLOG_INDEX_VIEW
    )
    assert (
        normalize_tracked_action("page_view", path="/blog/hello-world")
        == TrackedAction.BLOG_POST_VIEW
    )
    assert (
        normalize_tracked_action("page_view", path="/blog/category/fans")
        == TrackedAction.BLOG_CATEGORY_PAGE_VIEW
    )


def test_blog_post_view_tracks_entity_not_event_fk(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    seed_blog_content(db_session)
    db_session.commit()

    post = db_session.scalar(
        select(BlogPost).where(BlogPost.status == "published").limit(1)
    )
    assert post is not None

    tracked = client.post(
        "/api/v1/analytics/track",
        json={
            "tracked_action": TrackedAction.BLOG_POST_VIEW,
            "entity_type": "blog_post",
            "entity_id": str(post.id),
            "anonymous_id": "anon-blog-1",
            "session_id": "sess-blog-1",
            "metadata": {
                "blog_post_id": str(post.id),
                "blog_slug": post.slug,
                "path": f"/blog/{post.slug}",
            },
            "path": f"/blog/{post.slug}",
            "require_known_action": True,
        },
    )
    assert tracked.status_code == 200, tracked.text

    row = db_session.scalar(
        select(AnalyticsEvent)
        .where(AnalyticsEvent.event_name == TrackedAction.BLOG_POST_VIEW)
        .order_by(AnalyticsEvent.created_at.desc())
    )
    assert row is not None
    assert row.entity_type == "blog_post"
    assert row.entity_id == post.id
    assert row.target_event_id is None
    meta = row.event_metadata or {}
    assert "body" not in meta
    assert "prompt" not in meta
    assert meta.get("blog_slug") == post.slug


def test_admin_blog_analytics_and_publish_emit(
    client: TestClient, db_session: Session, assign_role
):
    seed_roles_and_permissions(db_session)
    ensure_system_admin_roles(db_session)
    seed_blog_content(db_session)
    db_session.commit()

    headers, email = _register(client, prefix="blog-analytics-admin")
    assign_role(email, "super_admin")

    created = client.post(
        "/api/v1/admin/blog/posts",
        headers=headers,
        json={
            "title": "Analytics Draft",
            "slug": f"analytics-draft-{uuid4().hex[:6]}",
            "excerpt": "x",
            "body": "## Hello\n\nWorld",
            "status": "draft",
        },
    )
    assert created.status_code in (200, 201), created.text
    post_id = created.json()["id"]

    published = client.post(
        f"/api/v1/admin/blog/posts/{post_id}/publish",
        headers=headers,
    )
    assert published.status_code == 200, published.text

    emit = db_session.scalar(
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.event_name == TrackedAction.BLOG_POST_PUBLISHED,
            AnalyticsEvent.entity_id == UUID(post_id),
        )
        .order_by(AnalyticsEvent.created_at.desc())
    )
    assert emit is not None
    assert emit.entity_type == "blog_post"
    meta = emit.event_metadata or {}
    assert "draft_age_hours" in meta
    assert "prompt" not in meta
    assert "body" not in meta

    summary = client.get("/api/v1/analytics/admin/blog", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert "funnel" in body
    assert "publishing" in body
    assert "ai_studio" in body
    assert "top_posts" in body

    per_post = client.get(
        f"/api/v1/analytics/admin/blog/posts/{post_id}",
        headers=headers,
    )
    assert per_post.status_code == 200, per_post.text
    assert per_post.json()["post"]["id"] == post_id
