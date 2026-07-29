"""Trusted analytics emitters for blog editorial + AI Studio (no content/prompts)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.taxonomy import TrackedAction
from app.analytics.trusted import track_server_event
from app.blog.models import BlogPost
from app.users.models import User

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _draft_age_hours(post: BlogPost, *, published_at: datetime | None = None) -> float | None:
    created = _as_utc(post.created_at)
    published = _as_utc(published_at or post.published_at)
    if created is None or published is None:
        return None
    seconds = (published - created).total_seconds()
    if seconds < 0:
        return None
    return round(seconds / 3600.0, 2)


def _duration_bucket(duration_ms: int | None) -> str | None:
    if duration_ms is None:
        return None
    if duration_ms < 1000:
        return "under_1s"
    if duration_ms < 5000:
        return "1_5s"
    if duration_ms < 15000:
        return "5_15s"
    if duration_ms < 60000:
        return "15_60s"
    return "over_60s"


def emit_blog_post_published(
    db: Session,
    *,
    post: BlogPost,
    actor: User | None,
) -> None:
    try:
        draft_age = _draft_age_hours(post)
        track_server_event(
            db,
            event_name=TrackedAction.BLOG_POST_PUBLISHED,
            user_id=actor.id if actor else None,
            entity_type="blog_post",
            entity_id=post.id,
            request_id=f"trusted:blog_post_published:{post.id}:{post.published_at}",
            metadata={
                "blog_post_id": str(post.id),
                "blog_slug": (post.slug or "")[:160] or None,
                "post_status": "published",
                "draft_age_hours": draft_age,
                "traffic_segment": "editorial",
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("blog publish analytics failed post=%s", post.id)


def emit_blog_post_unpublished(
    db: Session,
    *,
    post: BlogPost,
    actor: User | None,
) -> None:
    try:
        track_server_event(
            db,
            event_name=TrackedAction.BLOG_POST_UNPUBLISHED,
            user_id=actor.id if actor else None,
            entity_type="blog_post",
            entity_id=post.id,
            request_id=f"trusted:blog_post_unpublished:{post.id}:{uuid.uuid4().hex[:8]}",
            metadata={
                "blog_post_id": str(post.id),
                "blog_slug": (post.slug or "")[:160] or None,
                "post_status": post.status,
                "traffic_segment": "editorial",
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("blog unpublish analytics failed post=%s", post.id)


def emit_blog_post_archived(
    db: Session,
    *,
    post: BlogPost,
    actor: User | None,
) -> None:
    try:
        track_server_event(
            db,
            event_name=TrackedAction.BLOG_POST_ARCHIVED,
            user_id=actor.id if actor else None,
            entity_type="blog_post",
            entity_id=post.id,
            request_id=f"trusted:blog_post_archived:{post.id}:{uuid.uuid4().hex[:8]}",
            metadata={
                "blog_post_id": str(post.id),
                "blog_slug": (post.slug or "")[:160] or None,
                "post_status": "archived",
                "traffic_segment": "editorial",
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("blog archive analytics failed post=%s", post.id)


def emit_blog_ai_operation(
    db: Session,
    *,
    post_id: uuid.UUID | None,
    actor: User | None,
    operation: str,
    feature_key: str | None,
    success: bool,
    duration_ms: int | None,
    client_request_id: str | None = None,
) -> None:
    """Emit AI Studio usage — never includes prompts or article text."""
    try:
        rid = client_request_id or uuid.uuid4().hex
        track_server_event(
            db,
            event_name=TrackedAction.BLOG_AI_OPERATION,
            user_id=actor.id if actor else None,
            entity_type="blog_post" if post_id else None,
            entity_id=post_id,
            request_id=f"trusted:blog_ai_operation:{rid}:{operation}"[:64],
            metadata={
                "blog_post_id": str(post_id) if post_id else None,
                "ai_operation": (operation or "")[:64] or None,
                "feature_key": (feature_key or "")[:120] or None,
                "success": bool(success),
                "duration_bucket": _duration_bucket(duration_ms),
                "traffic_segment": "editorial",
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("blog AI analytics failed op=%s", operation)


def emit_blog_comment_created(
    db: Session,
    *,
    post_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    depth: int,
    comment_id: uuid.UUID,
) -> None:
    try:
        track_server_event(
            db,
            event_name=TrackedAction.BLOG_COMMENT_CREATED,
            user_id=actor_user_id,
            entity_type="blog_post",
            entity_id=post_id,
            request_id=f"trusted:blog_comment_created:{comment_id}",
            metadata={
                "blog_post_id": str(post_id),
                "comment_depth": int(depth),
                "traffic_segment": "public",
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("blog comment analytics failed post=%s", post_id)
