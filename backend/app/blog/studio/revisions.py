"""Blog post revision snapshots for AI Studio / manual checkpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blog.models import BlogPost, BlogRevision
from app.core.http_errors import raise_not_found
from app.users.models import User


def create_revision(
    db: Session,
    *,
    post: BlogPost,
    actor: User | None,
    source: str = "manual",
    action_type: str = "checkpoint",
    provider: str | None = None,
    model_name: str | None = None,
    summary: str | None = None,
    commit: bool = False,
) -> BlogRevision:
    """Snapshot current post fields. Never store secrets/prompts."""
    rev = BlogRevision(
        post_id=post.id,
        title=post.title,
        excerpt=post.excerpt,
        body=post.body or "",
        seo_title=post.seo_title,
        seo_description=post.seo_description,
        faqs=post.faqs,
        studio_outline=post.studio_outline,
        studio_brief=post.studio_brief,
        content_version=int(post.content_version or 1),
        actor_user_id=actor.id if actor else None,
        source=source,
        action_type=action_type,
        provider=provider,
        model_name=model_name,
        summary=(summary or "")[:500] or None,
    )
    db.add(rev)
    db.flush()
    if commit:
        db.commit()
        db.refresh(rev)
    return rev


def list_revisions(
    db: Session, *, post_id: uuid.UUID, limit: int = 50
) -> list[BlogRevision]:
    return list(
        db.scalars(
            select(BlogRevision)
            .where(BlogRevision.post_id == post_id)
            .order_by(BlogRevision.created_at.desc())
            .limit(limit)
        ).all()
    )


def get_revision(
    db: Session, *, post_id: uuid.UUID, revision_id: uuid.UUID
) -> BlogRevision:
    row = db.scalar(
        select(BlogRevision).where(
            BlogRevision.id == revision_id,
            BlogRevision.post_id == post_id,
        )
    )
    if row is None:
        raise_not_found()
    return row


def restore_revision(
    db: Session,
    *,
    user: User,
    post_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> BlogPost:
    post = db.get(BlogPost, post_id)
    if post is None or post.archived_at is not None:
        raise_not_found()
    rev = get_revision(db, post_id=post_id, revision_id=revision_id)
    # Checkpoint current state before restore
    create_revision(
        db,
        post=post,
        actor=user,
        source="manual",
        action_type="pre_restore",
        summary=f"Checkpoint before restoring {revision_id}",
        commit=False,
    )
    post.title = rev.title
    post.excerpt = rev.excerpt
    post.body = rev.body or ""
    post.seo_title = rev.seo_title
    post.seo_description = rev.seo_description
    post.faqs = rev.faqs
    post.studio_outline = rev.studio_outline
    post.studio_brief = rev.studio_brief
    post.content_version = int(post.content_version or 1) + 1
    post.updated_by = user.id
    create_revision(
        db,
        post=post,
        actor=user,
        source="manual",
        action_type="restore",
        summary=f"Restored revision {revision_id}",
        commit=False,
    )
    db.commit()
    db.refresh(post)
    return post


def serialize_revision(row: BlogRevision) -> dict[str, Any]:
    return {
        "id": row.id,
        "post_id": row.post_id,
        "title": row.title,
        "excerpt": row.excerpt,
        "body": row.body,
        "seo_title": row.seo_title,
        "seo_description": row.seo_description,
        "faqs": row.faqs,
        "studio_outline": row.studio_outline,
        "studio_brief": row.studio_brief,
        "content_version": row.content_version,
        "actor_user_id": row.actor_user_id,
        "source": row.source,
        "action_type": row.action_type,
        "provider": row.provider,
        "model_name": row.model_name,
        "summary": row.summary,
        "created_at": row.created_at,
    }


def assert_version_match(post: BlogPost, expected: int) -> None:
    current = int(post.content_version or 1)
    if current != expected:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "content_version conflict",
                "expected_content_version": expected,
                "current_content_version": current,
            },
        )
