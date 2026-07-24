"""Build and scrub blog CMS context for admin AI writing assists."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.context_scrubber import scrub_context, scrub_value
from app.users.models import User
from app.users.service import user_has_permission

BLOG_STUDIO_SAFE_KEYS = frozenset(
    {
        "title",
        "excerpt",
        "body",
        "category",
        "existing_tags",
        "catalog_categories",
        "catalog_tags",
        "audience",
        "goal",
        "notes",
        "existing_slug",
        "existing_seo_title",
        "existing_seo_description",
    }
)


def assert_blog_ai_permission(user: User) -> None:
    if not (
        user_has_permission(user, "ai.use_platform")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="AI permission required")
    if not (
        user_has_permission(user, "admin.blog.edit")
        or user_has_permission(user, "admin.blog.create")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Blog edit permission required")


def _catalog_lists(db: Session) -> tuple[str, str]:
    from app.blog.service import list_categories, list_tags

    cats = list_categories(db)
    tags = list_tags(db)
    cat_text = ", ".join(f"{c.slug} ({c.name})" for c in cats) or "none"
    tag_text = ", ".join(f"{t.slug} ({t.name})" for t in tags) or "none"
    return cat_text, tag_text


def build_blog_studio_context(
    db: Session,
    *,
    user: User,
    blog_post_id: UUID | None,
    extra: dict[str, object] | None,
    notes: str = "",
) -> tuple[dict[str, str], list[str]]:
    """Scrub client draft fields; optionally enrich from an existing post."""
    assert_blog_ai_permission(user)
    client = extra or {}

    title = str(client.get("title") or "")
    excerpt = str(client.get("excerpt") or "")
    body = str(client.get("body") or "")
    category = str(client.get("category") or client.get("existing_category") or "")
    existing_tags = str(client.get("existing_tags") or "")
    audience = str(client.get("audience") or "")
    goal = str(client.get("goal") or "")
    existing_slug = str(client.get("existing_slug") or "")
    existing_seo_title = str(client.get("existing_seo_title") or "")
    existing_seo_description = str(client.get("existing_seo_description") or "")

    if blog_post_id is not None:
        from app.blog.service import get_admin_post

        post = get_admin_post(db, user=user, post_id=blog_post_id)
        title = title or (post.title or "")
        excerpt = excerpt or (post.excerpt or "")
        body = body or (post.body or "")
        if not category and post.category is not None:
            category = post.category.name or post.category.slug or ""
        if not existing_tags and post.tags:
            existing_tags = ", ".join(
                t.name for t in post.tags if getattr(t, "name", None)
            )
        existing_slug = existing_slug or (post.slug or "")
        existing_seo_title = existing_seo_title or (post.seo_title or "")
        existing_seo_description = existing_seo_description or (
            post.seo_description or ""
        )

    cat_catalog, tag_catalog = _catalog_lists(db)
    raw = {
        "title": scrub_value(title, max_len=200),
        "excerpt": scrub_value(excerpt, max_len=500),
        "body": scrub_value(body, max_len=8000),
        "category": scrub_value(category, max_len=120),
        "existing_tags": scrub_value(existing_tags, max_len=400),
        "catalog_categories": cat_catalog,
        "catalog_tags": tag_catalog,
        "audience": scrub_value(audience, max_len=160),
        "goal": scrub_value(goal, max_len=240),
        "notes": scrub_value(notes or str(client.get("notes") or ""), max_len=500),
        "existing_slug": scrub_value(existing_slug, max_len=220),
        "existing_seo_title": scrub_value(existing_seo_title, max_len=200),
        "existing_seo_description": scrub_value(
            existing_seo_description, max_len=400
        ),
    }
    scrubbed, redactions = scrub_context(raw, allowlist=BLOG_STUDIO_SAFE_KEYS)
    return scrubbed, redactions
