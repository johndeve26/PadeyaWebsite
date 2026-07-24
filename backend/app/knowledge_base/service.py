"""Knowledge Base domain service."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.blog.markdown import estimate_reading_minutes, markdown_to_html
from app.core.audit import write_audit_log
from app.core.http_errors import raise_not_found
from app.knowledge_base.models import (
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    KnowledgeBaseFeedback,
    KnowledgeBaseSearchLog,
    KnowledgeBaseTag,
)
from app.knowledge_base.sanitize import sanitize_html, validate_image_url
from app.knowledge_base.schemas import ArticleCreate, ArticleUpdate, CategoryCreate, CategoryUpdate
from app.knowledge_base.video import parse_video_url
from app.users.models import User
from app.users.service import user_has_permission

STATUSES = frozenset({"draft", "scheduled", "published", "archived"})
CONTENT_TYPES = frozenset(
    {"text", "how_to", "video", "faq", "troubleshooting", "policy", "update"}
)
DIFFICULTIES = frozenset({"beginner", "intermediate", "advanced"})
AUDIENCES = frozenset(
    {"fan", "host", "admin", "ambassador", "sponsor", "visitor"}
)
SENSITIVE_QUERY = re.compile(
    r"(@|\.com\b|\.net\b|password|token|bearer|ssn|\d{10,})",
    re.I,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:200] or "article"


def _require_perm(user: User, *codes: str) -> None:
    if user_has_permission(user, "admin.full_access"):
        return
    if any(user_has_permission(user, c) for c in codes):
        return
    raise HTTPException(status_code=403, detail="Insufficient permission")


def apply_due_schedules(db: Session) -> None:
    now = _utcnow()
    due = db.scalars(
        select(KnowledgeBaseArticle).where(
            KnowledgeBaseArticle.status == "scheduled",
            KnowledgeBaseArticle.scheduled_at.is_not(None),
            KnowledgeBaseArticle.scheduled_at <= now,
            KnowledgeBaseArticle.archived_at.is_(None),
        )
    ).all()
    for row in due:
        row.status = "published"
        row.published_at = row.scheduled_at or now
    if due:
        db.commit()


def render_body_html(body: str) -> str:
    return sanitize_html(markdown_to_html(body or ""))


def serialize_article(
    row: KnowledgeBaseArticle,
    *,
    admin: bool = False,
    related: list[KnowledgeBaseArticle] | None = None,
) -> dict[str, Any]:
    video = {}
    try:
        video = parse_video_url(row.video_url)
    except ValueError:
        video = {}
    cat = None
    if row.category and row.category.archived_at is None:
        cat = {
            "id": row.category.id,
            "name": row.category.name,
            "slug": row.category.slug,
            "description": row.category.description,
            "group_key": row.category.group_key,
            "sort_order": row.category.sort_order,
            "icon_key": row.category.icon_key,
            "article_count": 0,
        }
    data: dict[str, Any] = {
        "id": row.id,
        "title": row.title,
        "slug": row.slug,
        "excerpt": row.excerpt,
        "body": row.body if admin else "",
        "body_html": render_body_html(row.body),
        "content_type": row.content_type,
        "difficulty": row.difficulty,
        "audiences": list(row.audiences or []),
        "cover_url": row.cover_url,
        "video_url": video.get("video_url") or row.video_url,
        "video_provider": video.get("provider") or row.video_provider,
        "video_thumbnail_url": video.get("thumbnail_url")
        or row.video_thumbnail_url,
        "video_embed_url": video.get("embed_url"),
        "status": row.status,
        "is_featured": row.is_featured,
        "featured_sort": row.featured_sort,
        "reading_time_minutes": row.reading_time_minutes,
        "helpful_count": row.helpful_count,
        "not_helpful_count": row.not_helpful_count,
        "view_count": row.view_count,
        "published_at": row.published_at,
        "scheduled_at": row.scheduled_at if admin else None,
        "updated_at": row.updated_at,
        "seo_title": row.seo_title,
        "seo_description": row.seo_description,
        "category": cat,
        "tags": [
            {"id": t.id, "name": t.name, "slug": t.slug} for t in (row.tags or [])
        ],
        "related": [],
        "related_article_ids": list(row.related_article_ids or []) if admin else [],
        "created_by": row.created_by if admin else None,
        "updated_by": row.updated_by if admin else None,
        "archived_at": row.archived_at if admin else None,
        "created_at": row.created_at if admin else None,
    }
    if related:
        data["related"] = [
            serialize_article(r, admin=False) for r in related if r.id != row.id
        ]
    if not admin:
        data.pop("body", None)
        data["body"] = ""
    return data


def list_categories(db: Session, *, include_archived: bool = False) -> list[dict[str, Any]]:
    q = select(KnowledgeBaseCategory).order_by(
        KnowledgeBaseCategory.sort_order, KnowledgeBaseCategory.name
    )
    if not include_archived:
        q = q.where(KnowledgeBaseCategory.archived_at.is_(None))
    rows = db.scalars(q).all()
    counts = dict(
        db.execute(
            select(
                KnowledgeBaseArticle.category_id,
                func.count(KnowledgeBaseArticle.id),
            )
            .where(
                KnowledgeBaseArticle.status == "published",
                KnowledgeBaseArticle.archived_at.is_(None),
            )
            .group_by(KnowledgeBaseArticle.category_id)
        ).all()
    )
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "name": r.name,
                "slug": r.slug,
                "description": r.description,
                "group_key": r.group_key,
                "sort_order": r.sort_order,
                "icon_key": r.icon_key,
                "article_count": int(counts.get(r.id, 0)),
            }
        )
    return out


def get_category_by_slug(db: Session, slug: str) -> KnowledgeBaseCategory:
    row = db.scalar(
        select(KnowledgeBaseCategory).where(
            KnowledgeBaseCategory.slug == slug,
            KnowledgeBaseCategory.archived_at.is_(None),
        )
    )
    if row is None:
        raise_not_found("Category not found")
    return row


def _public_query(db: Session):
    apply_due_schedules(db)
    return (
        select(KnowledgeBaseArticle)
        .options(
            selectinload(KnowledgeBaseArticle.tags),
            selectinload(KnowledgeBaseArticle.category),
        )
        .where(
            KnowledgeBaseArticle.status == "published",
            KnowledgeBaseArticle.archived_at.is_(None),
        )
    )


def list_public_articles(
    db: Session,
    *,
    category_slug: str | None = None,
    tag_slug: str | None = None,
    audience: str | None = None,
    featured: bool | None = None,
    popular: bool = False,
    q: str | None = None,
    limit: int = 50,
    user_id: UUID | None = None,
) -> list[KnowledgeBaseArticle]:
    stmt = _public_query(db)
    if category_slug:
        cat = get_category_by_slug(db, category_slug)
        stmt = stmt.where(KnowledgeBaseArticle.category_id == cat.id)
    if tag_slug:
        stmt = stmt.join(KnowledgeBaseArticle.tags).where(
            KnowledgeBaseTag.slug == tag_slug
        )
    if audience:
        # Portable JSON array membership (SQLite tests + Postgres)
        stmt = stmt.where(
            cast(KnowledgeBaseArticle.audiences, String).like(f'%"{audience}"%')
        )
    if featured is True:
        stmt = stmt.where(KnowledgeBaseArticle.is_featured.is_(True))
    query = (q or "").strip()[:120]
    if query:
        safe = query.lower()
        if not SENSITIVE_QUERY.search(safe):
            like = f"%{safe}%"
            stmt = (
                stmt.outerjoin(KnowledgeBaseArticle.category)
                .outerjoin(KnowledgeBaseArticle.tags)
                .where(
                    or_(
                        func.lower(KnowledgeBaseArticle.title).like(like),
                        func.lower(KnowledgeBaseArticle.excerpt).like(like),
                        func.lower(KnowledgeBaseArticle.body).like(like),
                        func.lower(KnowledgeBaseCategory.name).like(like),
                        func.lower(KnowledgeBaseCategory.slug).like(like),
                        func.lower(KnowledgeBaseTag.name).like(like),
                        func.lower(KnowledgeBaseTag.slug).like(like),
                    )
                )
            )
    if popular:
        stmt = stmt.order_by(
            KnowledgeBaseArticle.view_count.desc(),
            KnowledgeBaseArticle.helpful_count.desc(),
        )
    elif featured is True:
        stmt = stmt.order_by(
            KnowledgeBaseArticle.featured_sort,
            KnowledgeBaseArticle.published_at.desc(),
        )
    else:
        stmt = stmt.order_by(KnowledgeBaseArticle.published_at.desc())
    rows = list(db.scalars(stmt.limit(limit)).unique().all())
    if query and not SENSITIVE_QUERY.search(query.lower()):
        db.add(
            KnowledgeBaseSearchLog(
                query=query.lower()[:120],
                result_count=len(rows),
                audience=audience,
                user_id=user_id,
            )
        )
        db.commit()
    return rows


def get_public_article(db: Session, slug: str) -> KnowledgeBaseArticle:
    apply_due_schedules(db)
    row = db.scalar(
        _public_query(db).where(KnowledgeBaseArticle.slug == slug)
    )
    if row is None:
        raise_not_found("Article not found")
    row.view_count = int(row.view_count or 0) + 1
    db.commit()
    db.refresh(row)
    return row


def related_articles(
    db: Session, row: KnowledgeBaseArticle, *, limit: int = 4
) -> list[KnowledgeBaseArticle]:
    ids = [UUID(str(x)) for x in (row.related_article_ids or []) if x]
    found: list[KnowledgeBaseArticle] = []
    if ids:
        found = list(
            db.scalars(
                _public_query(db).where(KnowledgeBaseArticle.id.in_(ids)).limit(limit)
            ).unique().all()
        )
    if len(found) >= limit:
        return found[:limit]
    extra = list(
        db.scalars(
            _public_query(db)
            .where(
                KnowledgeBaseArticle.id != row.id,
                KnowledgeBaseArticle.category_id == row.category_id,
            )
            .order_by(KnowledgeBaseArticle.view_count.desc())
            .limit(limit)
        ).unique().all()
    )
    seen = {a.id for a in found}
    for a in extra:
        if a.id not in seen:
            found.append(a)
            seen.add(a.id)
        if len(found) >= limit:
            break
    return found[:limit]


def submit_feedback(
    db: Session,
    *,
    article_id: UUID,
    is_helpful: bool,
    comment: str | None,
    user_id: UUID | None,
) -> dict[str, Any]:
    row = db.get(KnowledgeBaseArticle, article_id)
    if row is None or row.status != "published" or row.archived_at is not None:
        raise_not_found("Article not found")
    cleaned = (comment or "").strip()[:500] or None
    db.add(
        KnowledgeBaseFeedback(
            article_id=row.id,
            is_helpful=is_helpful,
            user_id=user_id,
            comment=cleaned,
        )
    )
    if is_helpful:
        row.helpful_count = int(row.helpful_count or 0) + 1
    else:
        row.not_helpful_count = int(row.not_helpful_count or 0) + 1
    db.commit()
    return {
        "article_id": row.id,
        "helpful_count": row.helpful_count,
        "not_helpful_count": row.not_helpful_count,
    }


def _ensure_tags(db: Session, slugs: list[str]) -> list[KnowledgeBaseTag]:
    tags: list[KnowledgeBaseTag] = []
    for raw in slugs:
        slug = _slugify(raw)
        if not slug:
            continue
        tag = db.scalar(select(KnowledgeBaseTag).where(KnowledgeBaseTag.slug == slug))
        if tag is None:
            tag = KnowledgeBaseTag(name=raw.strip()[:80] or slug, slug=slug)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def _apply_video(row: KnowledgeBaseArticle, url: str | None) -> None:
    if url is None:
        return
    if url.strip() == "":
        row.video_url = None
        row.video_provider = None
        row.video_thumbnail_url = None
        return
    try:
        parsed = parse_video_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row.video_url = parsed["video_url"]
    row.video_provider = parsed["provider"]
    row.video_thumbnail_url = parsed.get("thumbnail_url")


def create_article(
    db: Session, *, payload: ArticleCreate, actor: User
) -> KnowledgeBaseArticle:
    _require_perm(actor, "admin.knowledge_base.create")
    status = payload.status if payload.status in STATUSES else "draft"
    if status == "published":
        _require_perm(actor, "admin.knowledge_base.publish")
    slug = _slugify(payload.slug or payload.title)
    if db.scalar(select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.slug == slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")
    if payload.cover_url:
        validate_image_url(payload.cover_url)
    audiences = [a for a in payload.audiences if a in AUDIENCES] or ["visitor"]
    content_type = payload.content_type if payload.content_type in CONTENT_TYPES else "text"
    difficulty = payload.difficulty if payload.difficulty in DIFFICULTIES else "beginner"
    row = KnowledgeBaseArticle(
        title=payload.title.strip(),
        slug=slug,
        excerpt=(payload.excerpt or "").strip() or None,
        body=payload.body or "",
        content_type=content_type,
        difficulty=difficulty,
        audiences=audiences,
        cover_url=payload.cover_url,
        category_id=payload.category_id,
        is_featured=payload.is_featured,
        featured_sort=payload.featured_sort,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        related_article_ids=[str(x) for x in payload.related_article_ids],
        status=status,
        scheduled_at=payload.scheduled_at,
        reading_time_minutes=estimate_reading_minutes(payload.body or ""),
        created_by=actor.id,
        updated_by=actor.id,
    )
    if status == "published":
        row.published_at = _utcnow()
    _apply_video(row, payload.video_url)
    db.add(row)
    db.flush()
    tags = _ensure_tags(db, payload.tag_slugs)
    row.tags = tags
    write_audit_log(
        db,
        action="kb.article.create",
        actor_user_id=actor.id,
        resource_type="knowledge_base_article",
        resource_id=str(row.id),
        details={"slug": row.slug, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return row


def update_article(
    db: Session, *, article_id: UUID, payload: ArticleUpdate, actor: User
) -> KnowledgeBaseArticle:
    _require_perm(actor, "admin.knowledge_base.edit")
    row = db.get(KnowledgeBaseArticle, article_id)
    if row is None:
        raise_not_found("Article not found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] == "published" and row.status != "published":
        _require_perm(actor, "admin.knowledge_base.publish")
    if "slug" in data and data["slug"]:
        slug = _slugify(data["slug"])
        clash = db.scalar(
            select(KnowledgeBaseArticle).where(
                KnowledgeBaseArticle.slug == slug,
                KnowledgeBaseArticle.id != row.id,
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Slug already exists")
        row.slug = slug
        data.pop("slug")
    if "cover_url" in data and data["cover_url"]:
        validate_image_url(data["cover_url"])
    if "video_url" in data:
        _apply_video(row, data.pop("video_url"))
    if "tag_slugs" in data:
        row.tags = _ensure_tags(db, data.pop("tag_slugs") or [])
    if "audiences" in data and data["audiences"] is not None:
        data["audiences"] = [a for a in data["audiences"] if a in AUDIENCES] or [
            "visitor"
        ]
    if "related_article_ids" in data and data["related_article_ids"] is not None:
        data["related_article_ids"] = [str(x) for x in data["related_article_ids"]]
    if "content_type" in data and data["content_type"] not in CONTENT_TYPES:
        data.pop("content_type")
    if "difficulty" in data and data["difficulty"] not in DIFFICULTIES:
        data.pop("difficulty")
    if "status" in data and data["status"] not in STATUSES:
        data.pop("status")
    if "body" in data and data["body"] is not None:
        row.reading_time_minutes = estimate_reading_minutes(data["body"])
    for key, val in data.items():
        setattr(row, key, val)
    if row.status == "published" and row.published_at is None:
        row.published_at = _utcnow()
    row.updated_by = actor.id
    write_audit_log(
        db,
        action="kb.article.update",
        actor_user_id=actor.id,
        resource_type="knowledge_base_article",
        resource_id=str(row.id),
        details={"slug": row.slug, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return row


def publish_article(db: Session, *, article_id: UUID, actor: User) -> KnowledgeBaseArticle:
    _require_perm(actor, "admin.knowledge_base.publish")
    row = db.get(KnowledgeBaseArticle, article_id)
    if row is None:
        raise_not_found("Article not found")
    row.status = "published"
    row.published_at = row.published_at or _utcnow()
    row.archived_at = None
    row.archived_by = None
    row.updated_by = actor.id
    write_audit_log(
        db,
        action="kb.article.publish",
        actor_user_id=actor.id,
        resource_type="knowledge_base_article",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    try:
        from app.core.cache_invalidation import invalidate_help_caches

        invalidate_help_caches(slug=row.slug)
    except Exception:
        pass
    return row


def archive_article(db: Session, *, article_id: UUID, actor: User) -> KnowledgeBaseArticle:
    _require_perm(actor, "admin.knowledge_base.archive")
    row = db.get(KnowledgeBaseArticle, article_id)
    if row is None:
        raise_not_found("Article not found")
    row.status = "archived"
    row.archived_at = _utcnow()
    row.archived_by = actor.id
    row.updated_by = actor.id
    write_audit_log(
        db,
        action="kb.article.archive",
        actor_user_id=actor.id,
        resource_type="knowledge_base_article",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    try:
        from app.core.cache_invalidation import invalidate_help_caches

        invalidate_help_caches(slug=row.slug)
    except Exception:
        pass
    return row


def delete_article(db: Session, *, article_id: UUID, actor: User) -> None:
    _require_perm(actor, "admin.knowledge_base.archive")
    row = db.get(KnowledgeBaseArticle, article_id)
    if row is None:
        raise_not_found("Article not found")
    # Soft-delete via archive
    archive_article(db, article_id=article_id, actor=actor)


def list_admin_articles(
    db: Session,
    *,
    status: str | None = None,
    q: str | None = None,
    limit: int = 100,
) -> list[KnowledgeBaseArticle]:
    stmt = (
        select(KnowledgeBaseArticle)
        .options(
            selectinload(KnowledgeBaseArticle.tags),
            selectinload(KnowledgeBaseArticle.category),
        )
        .order_by(KnowledgeBaseArticle.updated_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(KnowledgeBaseArticle.status == status)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(KnowledgeBaseArticle.title).like(like))
    return list(db.scalars(stmt).unique().all())


def get_admin_article(db: Session, article_id: UUID) -> KnowledgeBaseArticle:
    row = db.scalar(
        select(KnowledgeBaseArticle)
        .options(
            selectinload(KnowledgeBaseArticle.tags),
            selectinload(KnowledgeBaseArticle.category),
        )
        .where(KnowledgeBaseArticle.id == article_id)
    )
    if row is None:
        raise_not_found("Article not found")
    return row


def create_category(
    db: Session, *, payload: CategoryCreate, actor: User
) -> KnowledgeBaseCategory:
    _require_perm(actor, "admin.knowledge_base.manage_categories")
    slug = _slugify(payload.slug or payload.name)
    if db.scalar(select(KnowledgeBaseCategory).where(KnowledgeBaseCategory.slug == slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")
    row = KnowledgeBaseCategory(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        group_key=payload.group_key or "general",
        sort_order=payload.sort_order,
        icon_key=payload.icon_key,
    )
    db.add(row)
    write_audit_log(
        db,
        action="kb.category.create",
        actor_user_id=actor.id,
        resource_type="knowledge_base_category",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    return row


def update_category(
    db: Session, *, category_id: UUID, payload: CategoryUpdate, actor: User
) -> KnowledgeBaseCategory:
    _require_perm(actor, "admin.knowledge_base.manage_categories")
    row = db.get(KnowledgeBaseCategory, category_id)
    if row is None:
        raise_not_found("Category not found")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        data["slug"] = _slugify(data["slug"])
    for key, val in data.items():
        setattr(row, key, val)
    write_audit_log(
        db,
        action="kb.category.update",
        actor_user_id=actor.id,
        resource_type="knowledge_base_category",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    return row


def unpublish_article(
    db: Session, *, article_id: UUID, actor: User
) -> KnowledgeBaseArticle:
    _require_perm(actor, "admin.knowledge_base.publish")
    row = db.get(KnowledgeBaseArticle, article_id)
    if row is None:
        raise_not_found("Article not found")
    row.status = "draft"
    row.updated_by = actor.id
    write_audit_log(
        db,
        action="kb.article.unpublish",
        actor_user_id=actor.id,
        resource_type="knowledge_base_article",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    return row


def suggestions_for_topic(
    db: Session, *, topic: str, limit: int = 5
) -> list[KnowledgeBaseArticle]:
    """Match Help articles for a Support Center topic."""
    from app.knowledge_base.topic_suggestions import TOPIC_HINTS

    apply_due_schedules(db)
    hints = TOPIC_HINTS.get(topic) or TOPIC_HINTS.get("other") or {}
    found: list[KnowledgeBaseArticle] = []
    seen: set[UUID] = set()

    slugs = list(hints.get("slugs") or [])
    if slugs:
        for row in db.scalars(
            _public_query(db).where(KnowledgeBaseArticle.slug.in_(slugs))
        ).unique().all():
            if row.id not in seen:
                found.append(row)
                seen.add(row.id)

    cat_slugs = list(hints.get("category_slugs") or [])
    if cat_slugs and len(found) < limit:
        cats = list(
            db.scalars(
                select(KnowledgeBaseCategory).where(
                    KnowledgeBaseCategory.slug.in_(cat_slugs),
                    KnowledgeBaseCategory.archived_at.is_(None),
                )
            ).all()
        )
        cat_ids = [c.id for c in cats]
        if cat_ids:
            for row in db.scalars(
                _public_query(db)
                .where(KnowledgeBaseArticle.category_id.in_(cat_ids))
                .order_by(KnowledgeBaseArticle.view_count.desc())
                .limit(limit * 2)
            ).unique().all():
                if row.id not in seen:
                    found.append(row)
                    seen.add(row.id)
                if len(found) >= limit:
                    break

    keywords = list(hints.get("keywords") or [])
    for kw in keywords:
        if len(found) >= limit:
            break
        for row in list_public_articles(db, q=kw, limit=limit):
            if row.id not in seen:
                found.append(row)
                seen.add(row.id)
            if len(found) >= limit:
                break

    by_slug = {a.slug: a for a in found}
    ordered: list[KnowledgeBaseArticle] = []
    for slug in slugs:
        if slug in by_slug:
            ordered.append(by_slug.pop(slug))
    ordered.extend(a for a in found if a.slug not in {x.slug for x in ordered})
    return ordered[:limit]


def list_feedback(
    db: Session, *, article_id: UUID | None = None, limit: int = 100
) -> list[dict]:
    stmt = (
        select(KnowledgeBaseFeedback)
        .order_by(KnowledgeBaseFeedback.created_at.desc())
        .limit(limit)
    )
    if article_id:
        stmt = stmt.where(KnowledgeBaseFeedback.article_id == article_id)
    rows = list(db.scalars(stmt).all())
    return [
        {
            "id": r.id,
            "article_id": r.article_id,
            "is_helpful": r.is_helpful,
            "comment": r.comment,
            "user_id": r.user_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def list_search_terms(db: Session, *, limit: int = 50) -> list[dict]:
    """Aggregated safe search terms for admin insights."""
    stmt = (
        select(
            KnowledgeBaseSearchLog.query,
            func.count(KnowledgeBaseSearchLog.id).label("hits"),
            func.avg(KnowledgeBaseSearchLog.result_count).label("avg_results"),
            func.max(KnowledgeBaseSearchLog.created_at).label("last_seen"),
        )
        .group_by(KnowledgeBaseSearchLog.query)
        .order_by(func.count(KnowledgeBaseSearchLog.id).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "query": r.query,
            "hits": int(r.hits or 0),
            "avg_results": float(r.avg_results or 0),
            "last_seen": r.last_seen,
        }
        for r in rows
    ]
