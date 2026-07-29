"""Blog domain service — public reads + admin lifecycle."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.blog.markdown import estimate_reading_minutes, markdown_to_html
from app.blog.models import BlogAuthor, BlogCategory, BlogPost, BlogPostTag, BlogTag
from app.blog.sanitize import sanitize_html, validate_image_url
from app.blog.schemas import (
    AuthorCreate,
    CategoryCreate,
    PostCreate,
    PostUpdate,
    TagCreate,
)
from app.core.audit import write_audit_log
from app.core.http_errors import raise_not_found
from app.users.models import User
from app.users.service import user_has_permission

STATUSES = frozenset({"draft", "scheduled", "published", "archived"})


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:200] or "post"


def _require_blog_perm(user: User, *codes: str) -> None:
    if user_has_permission(user, "admin.full_access"):
        return
    if any(user_has_permission(user, c) for c in codes):
        return
    raise HTTPException(status_code=403, detail="Insufficient permission")


def apply_due_schedules(db: Session) -> None:
    now = _utcnow()
    due = db.scalars(
        select(BlogPost).where(
            BlogPost.status == "scheduled",
            BlogPost.scheduled_at.is_not(None),
            BlogPost.scheduled_at <= now,
            BlogPost.archived_at.is_(None),
        )
    ).all()
    for post in due:
        post.status = "published"
        post.published_at = post.scheduled_at or now
    if due:
        db.commit()


def render_body_html(body: str, *, content_document: dict[str, Any] | None = None) -> str:
    if content_document:
        from app.blog.document.render import document_to_html

        return document_to_html(content_document)
    return sanitize_html(markdown_to_html(body or ""))


def render_post_body_html(row: BlogPost) -> str:
    doc = getattr(row, "content_document", None)
    if doc:
        from app.blog.document.render import document_to_html

        return document_to_html(doc)
    return render_body_html(row.body or "")


def serialize_post(row: BlogPost, *, admin: bool = False, related: list[BlogPost] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": row.id,
        "title": row.title,
        "slug": row.slug,
        "excerpt": row.excerpt,
        "body": row.body,
        "body_html": render_post_body_html(row),
        "cover_url": row.cover_url,
        "status": row.status,
        "is_featured": row.is_featured,
        "reading_time_minutes": row.reading_time_minutes,
        "published_at": row.published_at,
        "scheduled_at": row.scheduled_at,
        "updated_at": row.updated_at,
        "seo_title": row.seo_title,
        "seo_description": row.seo_description,
        "canonical_url": row.canonical_url,
        "og_image_url": row.og_image_url,
        "category": row.category,
        "author": row.author if (row.author and row.author.is_active) or admin else row.author,
        "tags": list(row.tags or []),
        "related": [],
    }
    if related:
        data["related"] = [
            {
                "id": r.id,
                "title": r.title,
                "slug": r.slug,
                "excerpt": r.excerpt,
                "cover_url": r.cover_url,
                "status": r.status,
                "is_featured": r.is_featured,
                "reading_time_minutes": r.reading_time_minutes,
                "published_at": r.published_at,
                "scheduled_at": r.scheduled_at,
                "updated_at": r.updated_at,
                "category": r.category,
                "author": r.author,
                "tags": list(r.tags or []),
            }
            for r in related
        ]
    if admin:
        data["admin_notes"] = row.admin_notes
        data["created_at"] = row.created_at
        data["created_by"] = row.created_by
        data["updated_by"] = row.updated_by
        data["archived_at"] = row.archived_at
        data["studio_brief"] = row.studio_brief
        data["studio_outline"] = row.studio_outline
        data["faqs"] = row.faqs
        data["content_version"] = int(getattr(row, "content_version", None) or 1)
        data["content_document"] = getattr(row, "content_document", None)
        data["content_document_version"] = int(
            getattr(row, "content_document_version", None) or 1
        )
        data["editor_mode"] = getattr(row, "editor_mode", None)
        data["hero_settings"] = getattr(row, "hero_settings", None)
        from app.blog.document.sync import resolve_content_mode

        data["content_mode"] = resolve_content_mode(row)
        data["focus_keyword"] = row.focus_keyword
        data["secondary_keywords"] = row.secondary_keywords
        data["social_share_text"] = row.social_share_text
        data["og_title"] = row.og_title
    return data


def _post_query():
    return select(BlogPost).options(
        selectinload(BlogPost.tags),
        selectinload(BlogPost.category),
        selectinload(BlogPost.author),
    )


def list_public_posts(
    db: Session,
    *,
    category_slug: str | None = None,
    tag_slug: str | None = None,
    author_slug: str | None = None,
    featured: bool | None = None,
    q: str | None = None,
    limit: int = 50,
) -> list[BlogPost]:
    apply_due_schedules(db)
    stmt = _post_query().where(
        BlogPost.status == "published",
        BlogPost.archived_at.is_(None),
    )
    if category_slug:
        stmt = stmt.join(BlogCategory).where(BlogCategory.slug == category_slug)
    if author_slug:
        stmt = stmt.join(BlogAuthor).where(BlogAuthor.slug == author_slug)
    if tag_slug:
        stmt = (
            stmt.join(BlogPostTag, BlogPostTag.post_id == BlogPost.id)
            .join(BlogTag, BlogTag.id == BlogPostTag.tag_id)
            .where(BlogTag.slug == tag_slug)
        )
    if featured is True:
        stmt = stmt.where(BlogPost.is_featured.is_(True))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(BlogPost.title.ilike(like), BlogPost.excerpt.ilike(like))
        )
    stmt = stmt.order_by(BlogPost.published_at.desc().nullslast()).limit(min(limit, 100))
    return list(db.scalars(stmt).unique())


def get_public_post(db: Session, slug: str) -> BlogPost:
    apply_due_schedules(db)
    row = db.scalar(
        _post_query().where(
            BlogPost.slug == slug,
            BlogPost.status == "published",
            BlogPost.archived_at.is_(None),
        )
    )
    if row is None:
        raise_not_found()
    if row.published_at and _as_utc(row.published_at) > _utcnow():
        raise_not_found()
    return row


def related_posts(db: Session, post: BlogPost, *, limit: int = 3) -> list[BlogPost]:
    stmt = _post_query().where(
        BlogPost.status == "published",
        BlogPost.archived_at.is_(None),
        BlogPost.id != post.id,
    )
    if post.category_id:
        stmt = stmt.where(BlogPost.category_id == post.category_id)
    stmt = stmt.order_by(BlogPost.published_at.desc().nullslast()).limit(limit)
    rows = list(db.scalars(stmt).unique())
    if len(rows) < limit:
        extra = list(
            db.scalars(
                _post_query()
                .where(
                    BlogPost.status == "published",
                    BlogPost.archived_at.is_(None),
                    BlogPost.id != post.id,
                    BlogPost.id.notin_([r.id for r in rows] or [uuid.uuid4()]),
                )
                .order_by(BlogPost.published_at.desc().nullslast())
                .limit(limit - len(rows))
            ).unique()
        )
        rows.extend(extra)
    return rows


def list_categories(db: Session) -> list[BlogCategory]:
    return list(
        db.scalars(select(BlogCategory).order_by(BlogCategory.sort_order, BlogCategory.name))
    )


def list_tags(db: Session) -> list[BlogTag]:
    return list(db.scalars(select(BlogTag).order_by(BlogTag.name)))


def list_authors(db: Session, *, active_only: bool = True) -> list[BlogAuthor]:
    stmt = select(BlogAuthor)
    if active_only:
        stmt = stmt.where(BlogAuthor.is_active.is_(True))
    return list(db.scalars(stmt.order_by(BlogAuthor.display_name)))


def get_category_by_slug(db: Session, slug: str) -> BlogCategory:
    row = db.scalar(select(BlogCategory).where(BlogCategory.slug == slug))
    if row is None:
        raise_not_found()
    return row


def get_tag_by_slug(db: Session, slug: str) -> BlogTag:
    row = db.scalar(select(BlogTag).where(BlogTag.slug == slug))
    if row is None:
        raise_not_found()
    return row


def get_author_by_slug(db: Session, slug: str) -> BlogAuthor:
    row = db.scalar(
        select(BlogAuthor).where(BlogAuthor.slug == slug, BlogAuthor.is_active.is_(True))
    )
    if row is None:
        raise_not_found()
    return row


def slug_available(db: Session, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
    s = _slugify(slug)
    stmt = select(BlogPost.id).where(BlogPost.slug == s)
    if exclude_id:
        stmt = stmt.where(BlogPost.id != exclude_id)
    return db.scalar(stmt) is None


def list_admin_posts(
    db: Session, *, user: User, include_archived: bool = False, status_filter: str | None = None
) -> list[BlogPost]:
    _require_blog_perm(user, "admin.blog.view", "admin.blog.edit", "admin.blog.create")
    apply_due_schedules(db)
    stmt = _post_query()
    if not include_archived:
        stmt = stmt.where(BlogPost.archived_at.is_(None))
    if status_filter:
        stmt = stmt.where(BlogPost.status == status_filter)
    return list(db.scalars(stmt.order_by(BlogPost.updated_at.desc())).unique())


def get_admin_post(db: Session, *, user: User, post_id: uuid.UUID) -> BlogPost:
    _require_blog_perm(user, "admin.blog.view", "admin.blog.edit")
    row = db.scalar(_post_query().where(BlogPost.id == post_id))
    if row is None:
        raise_not_found()
    return row


def _set_tags(db: Session, post: BlogPost, tag_ids: list[uuid.UUID]) -> None:
    db.execute(delete(BlogPostTag).where(BlogPostTag.post_id == post.id))
    for tid in tag_ids:
        if db.get(BlogTag, tid) is None:
            continue
        db.add(BlogPostTag(post_id=post.id, tag_id=tid))


def create_post(db: Session, *, user: User, payload: PostCreate) -> BlogPost:
    _require_blog_perm(user, "admin.blog.create")
    if payload.client_creation_id is not None:
        existing = db.scalar(
            select(BlogPost).where(
                BlogPost.created_by == user.id,
                BlogPost.client_creation_id == payload.client_creation_id,
                BlogPost.archived_at.is_(None),
            )
        )
        if existing is not None:
            return existing

    slug = _slugify(payload.slug or payload.title)
    if not slug_available(db, slug):
        raise HTTPException(status_code=409, detail="Slug already exists")
    try:
        cover = validate_image_url(payload.cover_url)
        og = validate_image_url(payload.og_image_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    status_val = "draft"
    published_at = None
    if payload.scheduled_at and payload.scheduled_at > _utcnow():
        status_val = "scheduled"

    row = BlogPost(
        title=payload.title.strip(),
        slug=slug,
        excerpt=payload.excerpt,
        body=payload.body or "",
        cover_url=cover,
        status=status_val,
        is_featured=payload.is_featured,
        reading_time_minutes=estimate_reading_minutes(payload.body or ""),
        category_id=payload.category_id,
        author_id=payload.author_id,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        canonical_url=payload.canonical_url,
        og_image_url=og,
        admin_notes=payload.admin_notes,
        scheduled_at=payload.scheduled_at,
        published_at=published_at,
        created_by=user.id,
        client_creation_id=payload.client_creation_id,
        updated_by=user.id,
        studio_brief=payload.studio_brief,
        studio_outline=payload.studio_outline,
        faqs=payload.faqs,
        content_version=1,
        focus_keyword=payload.focus_keyword,
        secondary_keywords=payload.secondary_keywords,
        social_share_text=payload.social_share_text,
        og_title=payload.og_title,
    )
    db.add(row)
    db.flush()
    _set_tags(db, row, payload.tag_ids)
    write_audit_log(
        db,
        action="blog.post_create",
        actor_user_id=user.id,
        resource_type="blog_post",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    return get_admin_post(db, user=user, post_id=row.id)


def update_post(
    db: Session, *, user: User, post_id: uuid.UUID, payload: PostUpdate
) -> BlogPost:
    _require_blog_perm(user, "admin.blog.edit")
    row = db.get(BlogPost, post_id)
    if row is None:
        raise_not_found()
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    data = payload.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)
    # content_version is server-managed unless explicitly provided for conflict checks elsewhere
    client_version = data.pop("content_version", None)
    if "slug" in data and data["slug"]:
        slug = _slugify(data["slug"])
        if not slug_available(db, slug, exclude_id=post_id):
            raise HTTPException(status_code=409, detail="Slug already exists")
        data["slug"] = slug
    for key in ("cover_url", "og_image_url"):
        if key in data:
            try:
                data[key] = validate_image_url(data[key])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "status" in data and data["status"] not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if "body" in data and data["body"] is not None:
        data["reading_time_minutes"] = estimate_reading_minutes(data["body"])
    next_status = data.get("status", row.status)
    if next_status == "published" and row.published_at is None:
        data.setdefault("published_at", _utcnow())
        data["scheduled_at"] = None
    if next_status == "scheduled":
        scheduled = data.get("scheduled_at", row.scheduled_at)
        if scheduled is None:
            raise HTTPException(
                status_code=400, detail="scheduled_at required for scheduled posts"
            )
    meaningful = {"title", "excerpt", "body", "seo_title", "seo_description", "faqs", "studio_outline", "studio_brief"}
    bump = bool(meaningful.intersection(data.keys()))
    for key, value in data.items():
        setattr(row, key, value)
    if bump:
        row.content_version = int(row.content_version or 1) + 1
    elif client_version is not None:
        row.content_version = int(client_version)
    row.updated_by = user.id
    if tag_ids is not None:
        _set_tags(db, row, tag_ids)
    write_audit_log(
        db,
        action="blog.post_update",
        actor_user_id=user.id,
        resource_type="blog_post",
        resource_id=str(row.id),
    )
    db.commit()
    return get_admin_post(db, user=user, post_id=post_id)


def publish_post(db: Session, *, user: User, post_id: uuid.UUID) -> BlogPost:
    _require_blog_perm(user, "admin.blog.publish")
    row = db.get(BlogPost, post_id)
    if row is None or row.archived_at is not None:
        raise_not_found()
    row.status = "published"
    row.published_at = _utcnow()
    row.scheduled_at = None
    row.updated_by = user.id
    try:
        from app.blog.studio.revisions import create_revision

        create_revision(
            db,
            post=row,
            actor=user,
            source="manual",
            action_type="publish",
            summary="Published snapshot",
            commit=False,
        )
    except Exception:
        pass
    write_audit_log(
        db,
        action="blog.post_publish",
        actor_user_id=user.id,
        resource_type="blog_post",
        resource_id=str(row.id),
    )
    from app.blog.analytics_emit import emit_blog_post_published

    emit_blog_post_published(db, post=row, actor=user)
    db.commit()
    try:
        from app.core.cache_invalidation import invalidate_blog_caches

        invalidate_blog_caches(slug=row.slug)
    except Exception:
        pass
    return get_admin_post(db, user=user, post_id=post_id)


def unpublish_post(db: Session, *, user: User, post_id: uuid.UUID) -> BlogPost:
    _require_blog_perm(user, "admin.blog.publish")
    row = db.get(BlogPost, post_id)
    if row is None or row.archived_at is not None:
        raise_not_found()
    slug = row.slug
    row.status = "draft"
    row.updated_by = user.id
    write_audit_log(
        db,
        action="blog.post_unpublish",
        actor_user_id=user.id,
        resource_type="blog_post",
        resource_id=str(row.id),
    )
    from app.blog.analytics_emit import emit_blog_post_unpublished

    emit_blog_post_unpublished(db, post=row, actor=user)
    db.commit()
    try:
        from app.core.cache_invalidation import invalidate_blog_caches

        invalidate_blog_caches(slug=slug)
    except Exception:
        pass
    return get_admin_post(db, user=user, post_id=post_id)


def delete_post(db: Session, *, user: User, post_id: uuid.UUID) -> None:
    """Soft-delete via archive (prefer over hard delete)."""
    _require_blog_perm(user, "admin.blog.delete")
    row = db.get(BlogPost, post_id)
    if row is None:
        raise_not_found()
    row.status = "archived"
    row.archived_at = _utcnow()
    row.archived_by = user.id
    row.updated_by = user.id
    write_audit_log(
        db,
        action="blog.post_delete",
        actor_user_id=user.id,
        resource_type="blog_post",
        resource_id=str(row.id),
    )
    from app.blog.analytics_emit import emit_blog_post_archived

    emit_blog_post_archived(db, post=row, actor=user)
    db.commit()


def create_category(db: Session, *, user: User, payload: CategoryCreate) -> BlogCategory:
    _require_blog_perm(user, "admin.blog.edit", "admin.blog.create")
    slug = _slugify(payload.slug or payload.name)
    if db.scalar(select(BlogCategory.id).where(BlogCategory.slug == slug)):
        raise HTTPException(status_code=409, detail="Category slug exists")
    row = BlogCategory(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_tag(db: Session, *, user: User, payload: TagCreate) -> BlogTag:
    _require_blog_perm(user, "admin.blog.edit", "admin.blog.create")
    slug = _slugify(payload.slug or payload.name)
    if db.scalar(select(BlogTag.id).where(BlogTag.slug == slug)):
        raise HTTPException(status_code=409, detail="Tag slug exists")
    row = BlogTag(name=payload.name.strip(), slug=slug)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_author(db: Session, *, user: User, payload: AuthorCreate) -> BlogAuthor:
    _require_blog_perm(user, "admin.blog.edit", "admin.blog.create")
    slug = _slugify(payload.slug or payload.display_name)
    if db.scalar(select(BlogAuthor.id).where(BlogAuthor.slug == slug)):
        raise HTTPException(status_code=409, detail="Author slug exists")
    try:
        avatar = validate_image_url(payload.avatar_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = BlogAuthor(
        display_name=payload.display_name.strip(),
        slug=slug,
        bio=payload.bio,
        avatar_url=avatar,
        role_title=payload.role_title,
        user_id=payload.user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
