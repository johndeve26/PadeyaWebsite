"""Blog taxonomy lifecycle — categories, tags, post types, media roles."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blog.models import (
    BlogCategory,
    BlogMediaRole,
    BlogPost,
    BlogPostTag,
    BlogPostType,
    BlogTag,
    BlogTaxonomySlugRedirect,
)
from app.blog.taxonomy_constants import (
    CONTENT_TYPE_TO_KEY,
    REQUIRED_MEDIA_ROLE_KEYS,
    SAFE_STORAGE_FOLDERS,
    SYSTEM_MEDIA_ROLES,
    SYSTEM_POST_TYPES,
)
from app.core.audit import write_audit_log
from app.core.cache_invalidation import invalidate_blog_caches
from app.core.http_errors import raise_not_found
from app.core.media import get_public_media_storage
from app.core.media_folders import blog_public_folder
from app.users.models import User
from app.users.service import user_has_permission

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
_FOLDER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,78}$")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _slugify(value: str, *, max_len: int = 140) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:max_len] or "term"


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def require_taxonomy_manage(user: User) -> None:
    if user_has_permission(user, "admin.full_access"):
        return
    if user_has_permission(user, "admin.blog.taxonomy.manage"):
        return
    raise HTTPException(status_code=403, detail="Insufficient permission")


def require_taxonomy_view(user: User) -> None:
    if user_has_permission(user, "admin.full_access"):
        return
    if any(
        user_has_permission(user, c)
        for c in (
            "admin.blog.view",
            "admin.blog.edit",
            "admin.blog.taxonomy.manage",
            "admin.blog.create",
        )
    ):
        return
    raise HTTPException(status_code=403, detail="Insufficient permission")


def _is_active(row: Any) -> bool:
    archived = getattr(row, "archived_at", None)
    active = getattr(row, "is_active", True)
    return bool(active) and archived is None


def _bump_redirect(
    db: Session,
    *,
    resource_type: str,
    resource_id: uuid.UUID,
    old_slug: str,
    new_slug: str,
) -> None:
    if old_slug == new_slug:
        return
    # Collapse chains: any redirect pointing at old_slug should point at new_slug
    db.execute(
        update(BlogTaxonomySlugRedirect)
        .where(
            BlogTaxonomySlugRedirect.resource_type == resource_type,
            BlogTaxonomySlugRedirect.new_slug == old_slug,
        )
        .values(new_slug=new_slug)
    )
    existing = db.scalar(
        select(BlogTaxonomySlugRedirect).where(
            BlogTaxonomySlugRedirect.resource_type == resource_type,
            BlogTaxonomySlugRedirect.old_slug == old_slug,
        )
    )
    if existing:
        existing.new_slug = new_slug
        existing.resource_id = resource_id
    else:
        db.add(
            BlogTaxonomySlugRedirect(
                resource_type=resource_type,
                old_slug=old_slug,
                new_slug=new_slug,
                resource_id=resource_id,
            )
        )
    # Never redirect a current live slug to itself as old
    db.execute(
        update(BlogTaxonomySlugRedirect)
        .where(
            BlogTaxonomySlugRedirect.resource_type == resource_type,
            BlogTaxonomySlugRedirect.old_slug == new_slug,
        )
        .values(new_slug=new_slug)
    )
    stale = db.scalar(
        select(BlogTaxonomySlugRedirect).where(
            BlogTaxonomySlugRedirect.resource_type == resource_type,
            BlogTaxonomySlugRedirect.old_slug == new_slug,
        )
    )
    if stale and stale.new_slug == new_slug:
        db.delete(stale)


def resolve_slug_redirect(
    db: Session, *, resource_type: str, slug: str
) -> str | None:
    row = db.scalar(
        select(BlogTaxonomySlugRedirect).where(
            BlogTaxonomySlugRedirect.resource_type == resource_type,
            BlogTaxonomySlugRedirect.old_slug == slug,
        )
    )
    return row.new_slug if row else None


# ---------------------------------------------------------------------------
# Usage counts (batch)
# ---------------------------------------------------------------------------


def category_usage_map(db: Session, ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, int]:
    stmt = (
        select(BlogPost.category_id, func.count())
        .where(BlogPost.category_id.is_not(None))
        .group_by(BlogPost.category_id)
    )
    if ids is not None:
        stmt = stmt.where(BlogPost.category_id.in_(ids))
    return {cid: int(n) for cid, n in db.execute(stmt).all() if cid}


def tag_usage_map(db: Session, ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, int]:
    stmt = (
        select(BlogPostTag.tag_id, func.count())
        .group_by(BlogPostTag.tag_id)
    )
    if ids is not None:
        stmt = stmt.where(BlogPostTag.tag_id.in_(ids))
    return {tid: int(n) for tid, n in db.execute(stmt).all()}


def post_type_usage_map(
    db: Session, ids: list[uuid.UUID] | None = None
) -> dict[uuid.UUID, int]:
    stmt = (
        select(BlogPost.post_type_id, func.count())
        .where(BlogPost.post_type_id.is_not(None))
        .group_by(BlogPost.post_type_id)
    )
    if ids is not None:
        stmt = stmt.where(BlogPost.post_type_id.in_(ids))
    return {pid: int(n) for pid, n in db.execute(stmt).all() if pid}


def media_role_usage_map(db: Session) -> dict[str, int]:
    """Approximate usage by measurable blog media references."""
    cover_n = int(
        db.scalar(
            select(func.count()).select_from(BlogPost).where(BlogPost.cover_url.is_not(None))
        )
        or 0
    )
    og_n = int(
        db.scalar(
            select(func.count())
            .select_from(BlogPost)
            .where(BlogPost.og_image_url.is_not(None))
        )
        or 0
    )
    # Inline / gallery: scan content_document for image blocks with role_key or type
    inline_n = 0
    gallery_n = 0
    social_n = 0
    teaser_n = 0
    docs = db.scalars(
        select(BlogPost.content_document).where(BlogPost.content_document.is_not(None))
    ).all()
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        for block in doc.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            btype = (block.get("type") or "").strip().lower()
            props = block.get("props") if isinstance(block.get("props"), dict) else {}
            role = (props.get("media_role_key") or "").strip().lower()
            if btype == "image_gallery" or role == "gallery":
                gallery_n += 1
            elif btype == "image" or role == "inline":
                inline_n += 1
            if role == "social_share":
                social_n += 1
            if role == "teaser":
                teaser_n += 1
    return {
        "cover": cover_n,
        "og": og_n,
        "inline": inline_n,
        "gallery": gallery_n,
        "social_share": social_n,
        "teaser": teaser_n,
    }


def serialize_category(row: BlogCategory, *, usage: int = 0) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "description": row.description,
        "sort_order": row.sort_order,
        "is_active": _is_active(row),
        "archived_at": row.archived_at,
        "seo_title": row.seo_title,
        "seo_description": row.seo_description,
        "usage_count": usage,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def serialize_tag(row: BlogTag, *, usage: int = 0) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "description": row.description,
        "sort_order": row.sort_order,
        "is_active": _is_active(row),
        "archived_at": row.archived_at,
        "usage_count": usage,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def serialize_post_type(row: BlogPostType, *, usage: int = 0) -> dict[str, Any]:
    return {
        "id": row.id,
        "key": row.key,
        "name": row.name,
        "slug": row.slug,
        "description": row.description,
        "sort_order": row.sort_order,
        "is_system": row.is_system,
        "is_active": _is_active(row),
        "archived_at": row.archived_at,
        "usage_count": usage,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def serialize_media_role(row: BlogMediaRole, *, usage: int = 0) -> dict[str, Any]:
    required = bool(row.is_required) or row.key in REQUIRED_MEDIA_ROLE_KEYS
    return {
        "id": row.id,
        "key": row.key,
        "name": row.name,
        "description": row.description,
        "sort_order": row.sort_order,
        "is_system": row.is_system,
        "is_required": required,
        "required_system_role": required,
        "storage_folder": row.storage_folder,
        "allowed_contexts": list(row.allowed_contexts or []),
        "is_active": _is_active(row),
        "archived_at": row.archived_at,
        "usage_count": usage,
        "display_usage_count": usage,
        "usage_count_is_approximate": row.key
        in {"inline", "gallery", "social_share", "teaser"},
        "can_archive": (not required) and _is_active(row),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


# ---------------------------------------------------------------------------
# List helpers
# ---------------------------------------------------------------------------


def list_categories(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[BlogCategory]:
    stmt = select(BlogCategory)
    if active_only:
        stmt = stmt.where(BlogCategory.is_active.is_(True), BlogCategory.archived_at.is_(None))
    elif not include_archived:
        stmt = stmt.where(BlogCategory.archived_at.is_(None))
    return list(
        db.scalars(stmt.order_by(BlogCategory.sort_order, BlogCategory.name)).all()
    )


def list_tags(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[BlogTag]:
    stmt = select(BlogTag)
    if active_only:
        stmt = stmt.where(BlogTag.is_active.is_(True), BlogTag.archived_at.is_(None))
    elif not include_archived:
        stmt = stmt.where(BlogTag.archived_at.is_(None))
    return list(db.scalars(stmt.order_by(BlogTag.sort_order, BlogTag.name)).all())


def list_post_types(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[BlogPostType]:
    stmt = select(BlogPostType)
    if active_only:
        stmt = stmt.where(
            BlogPostType.is_active.is_(True), BlogPostType.archived_at.is_(None)
        )
    elif not include_archived:
        stmt = stmt.where(BlogPostType.archived_at.is_(None))
    return list(
        db.scalars(stmt.order_by(BlogPostType.sort_order, BlogPostType.name)).all()
    )


def list_media_roles(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[BlogMediaRole]:
    stmt = select(BlogMediaRole)
    if active_only:
        stmt = stmt.where(
            BlogMediaRole.is_active.is_(True), BlogMediaRole.archived_at.is_(None)
        )
    elif not include_archived:
        stmt = stmt.where(BlogMediaRole.archived_at.is_(None))
    return list(
        db.scalars(stmt.order_by(BlogMediaRole.sort_order, BlogMediaRole.name)).all()
    )


def get_category_by_slug(db: Session, slug: str) -> BlogCategory:
    row = db.scalar(select(BlogCategory).where(BlogCategory.slug == slug))
    if row is None:
        redirected = resolve_slug_redirect(db, resource_type="category", slug=slug)
        if redirected:
            row = db.scalar(select(BlogCategory).where(BlogCategory.slug == redirected))
    if row is None or not _is_active(row):
        # Archived categories stay resolvable for redirect targets of existing posts
        # but public hubs should 404 for archived-only terms without published use.
        if row is None:
            raise_not_found()
    return row


def get_tag_by_slug(db: Session, slug: str) -> BlogTag:
    row = db.scalar(select(BlogTag).where(BlogTag.slug == slug))
    if row is None:
        redirected = resolve_slug_redirect(db, resource_type="tag", slug=slug)
        if redirected:
            row = db.scalar(select(BlogTag).where(BlogTag.slug == redirected))
    if row is None:
        raise_not_found()
    return row


def get_post_type(db: Session, post_type_id: uuid.UUID) -> BlogPostType:
    row = db.get(BlogPostType, post_type_id)
    if row is None:
        raise_not_found()
    return row


def get_media_role_by_key(db: Session, key: str) -> BlogMediaRole | None:
    return db.scalar(select(BlogMediaRole).where(BlogMediaRole.key == key))


# ---------------------------------------------------------------------------
# Assignment validation
# ---------------------------------------------------------------------------


def assert_assignable_category(
    db: Session,
    category_id: uuid.UUID | None,
    *,
    previous_id: uuid.UUID | None = None,
) -> None:
    if category_id is None:
        return
    row = db.get(BlogCategory, category_id)
    if row is None:
        raise HTTPException(status_code=400, detail="Unknown category")
    if not _is_active(row) and category_id != previous_id:
        raise HTTPException(status_code=400, detail="Cannot assign archived category")


def assert_assignable_tags(
    db: Session,
    tag_ids: list[uuid.UUID],
    *,
    previous_ids: set[uuid.UUID] | None = None,
) -> list[uuid.UUID]:
    prev = previous_ids or set()
    seen: set[uuid.UUID] = set()
    out: list[uuid.UUID] = []
    for tid in tag_ids:
        if tid in seen:
            continue
        seen.add(tid)
        row = db.get(BlogTag, tid)
        if row is None:
            raise HTTPException(status_code=400, detail="Unknown tag")
        if not _is_active(row) and tid not in prev:
            raise HTTPException(status_code=400, detail="Cannot assign archived tag")
        out.append(tid)
    return out


def assert_assignable_post_type(
    db: Session,
    post_type_id: uuid.UUID | None,
    *,
    previous_id: uuid.UUID | None = None,
) -> None:
    if post_type_id is None:
        return
    row = db.get(BlogPostType, post_type_id)
    if row is None:
        raise HTTPException(status_code=400, detail="Unknown post type")
    if not _is_active(row) and post_type_id != previous_id:
        raise HTTPException(status_code=400, detail="Cannot assign archived post type")


# ---------------------------------------------------------------------------
# Categories CRUD
# ---------------------------------------------------------------------------


def create_category(
    db: Session,
    *,
    user: User,
    name: str,
    slug: str | None = None,
    description: str | None = None,
    sort_order: int = 0,
    seo_title: str | None = None,
    seo_description: str | None = None,
) -> BlogCategory:
    require_taxonomy_manage(user)
    clean_name = name.strip()
    if len(clean_name) < 2:
        raise HTTPException(status_code=400, detail="Name too short")
    final_slug = _slugify(slug or clean_name)
    if db.scalar(select(BlogCategory.id).where(BlogCategory.slug == final_slug)):
        raise HTTPException(status_code=409, detail="Category slug exists")
    # normalized name uniqueness among active
    for existing in list_categories(db, include_archived=True):
        if _normalize_name(existing.name) == _normalize_name(clean_name) and _is_active(
            existing
        ):
            raise HTTPException(status_code=409, detail="Category name exists")
    row = BlogCategory(
        name=clean_name,
        slug=final_slug,
        description=description,
        sort_order=sort_order,
        seo_title=seo_title,
        seo_description=seo_description,
        is_active=True,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category slug exists") from exc
    write_audit_log(
        db,
        action="blog.category_create",
        actor_user_id=user.id,
        resource_type="blog_category",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def update_category(
    db: Session,
    *,
    user: User,
    category_id: uuid.UUID,
    name: str | None = None,
    slug: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    seo_title: str | None = None,
    seo_description: str | None = None,
    confirm_slug_change: bool = False,
) -> BlogCategory:
    require_taxonomy_manage(user)
    row = db.get(BlogCategory, category_id)
    if row is None:
        raise_not_found()
    if name is not None:
        clean = name.strip()
        if len(clean) < 2:
            raise HTTPException(status_code=400, detail="Name too short")
        for existing in list_categories(db, include_archived=True):
            if (
                existing.id != row.id
                and _normalize_name(existing.name) == _normalize_name(clean)
                and _is_active(existing)
            ):
                raise HTTPException(status_code=409, detail="Category name exists")
        row.name = clean
    if slug is not None:
        new_slug = _slugify(slug)
        if new_slug != row.slug:
            if not confirm_slug_change:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Changing a category slug breaks public URLs. "
                        "Pass confirm_slug_change=true to create a redirect."
                    ),
                )
            clash = db.scalar(
                select(BlogCategory.id).where(
                    BlogCategory.slug == new_slug, BlogCategory.id != row.id
                )
            )
            if clash:
                raise HTTPException(status_code=409, detail="Category slug exists")
            _bump_redirect(
                db,
                resource_type="category",
                resource_id=row.id,
                old_slug=row.slug,
                new_slug=new_slug,
            )
            row.slug = new_slug
    if description is not None:
        row.description = description
    if sort_order is not None:
        row.sort_order = sort_order
    if seo_title is not None:
        row.seo_title = seo_title
    if seo_description is not None:
        row.seo_description = seo_description
    write_audit_log(
        db,
        action="blog.category_update",
        actor_user_id=user.id,
        resource_type="blog_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def archive_category(db: Session, *, user: User, category_id: uuid.UUID) -> BlogCategory:
    require_taxonomy_manage(user)
    row = db.get(BlogCategory, category_id)
    if row is None:
        raise_not_found()
    row.is_active = False
    row.archived_at = _utcnow()
    write_audit_log(
        db,
        action="blog.category_archive",
        actor_user_id=user.id,
        resource_type="blog_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def restore_category(db: Session, *, user: User, category_id: uuid.UUID) -> BlogCategory:
    require_taxonomy_manage(user)
    row = db.get(BlogCategory, category_id)
    if row is None:
        raise_not_found()
    row.is_active = True
    row.archived_at = None
    write_audit_log(
        db,
        action="blog.category_restore",
        actor_user_id=user.id,
        resource_type="blog_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def reorder_categories(
    db: Session, *, user: User, ordered_ids: list[uuid.UUID]
) -> list[BlogCategory]:
    require_taxonomy_manage(user)
    for i, cid in enumerate(ordered_ids):
        row = db.get(BlogCategory, cid)
        if row is None:
            raise HTTPException(status_code=400, detail=f"Unknown category {cid}")
        row.sort_order = i * 10
    write_audit_log(
        db,
        action="blog.category_reorder",
        actor_user_id=user.id,
        resource_type="blog_category",
        resource_id="batch",
        details={"count": len(ordered_ids)},
    )
    db.commit()
    invalidate_blog_caches()
    return list_categories(db, include_archived=True)


# ---------------------------------------------------------------------------
# Tags CRUD
# ---------------------------------------------------------------------------


def create_tag(
    db: Session,
    *,
    user: User,
    name: str,
    slug: str | None = None,
    description: str | None = None,
    sort_order: int = 0,
) -> BlogTag:
    require_taxonomy_manage(user)
    clean_name = name.strip()
    if len(clean_name) < 2:
        raise HTTPException(status_code=400, detail="Name too short")
    final_slug = _slugify(slug or clean_name, max_len=100)
    if db.scalar(select(BlogTag.id).where(BlogTag.slug == final_slug)):
        raise HTTPException(status_code=409, detail="Tag slug exists")
    for existing in list_tags(db, include_archived=True):
        if _normalize_name(existing.name) == _normalize_name(clean_name) and _is_active(
            existing
        ):
            raise HTTPException(status_code=409, detail="Tag name exists")
    row = BlogTag(
        name=clean_name,
        slug=final_slug,
        description=description,
        sort_order=sort_order,
        is_active=True,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tag slug exists") from exc
    write_audit_log(
        db,
        action="blog.tag_create",
        actor_user_id=user.id,
        resource_type="blog_tag",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def update_tag(
    db: Session,
    *,
    user: User,
    tag_id: uuid.UUID,
    name: str | None = None,
    slug: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    confirm_slug_change: bool = False,
) -> BlogTag:
    require_taxonomy_manage(user)
    row = db.get(BlogTag, tag_id)
    if row is None:
        raise_not_found()
    if name is not None:
        clean = name.strip()
        if len(clean) < 2:
            raise HTTPException(status_code=400, detail="Name too short")
        for existing in list_tags(db, include_archived=True):
            if (
                existing.id != row.id
                and _normalize_name(existing.name) == _normalize_name(clean)
                and _is_active(existing)
            ):
                raise HTTPException(status_code=409, detail="Tag name exists")
        row.name = clean
    if slug is not None:
        new_slug = _slugify(slug, max_len=100)
        if new_slug != row.slug:
            if not confirm_slug_change:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Changing a tag slug breaks public URLs. "
                        "Pass confirm_slug_change=true to create a redirect."
                    ),
                )
            clash = db.scalar(
                select(BlogTag.id).where(BlogTag.slug == new_slug, BlogTag.id != row.id)
            )
            if clash:
                raise HTTPException(status_code=409, detail="Tag slug exists")
            _bump_redirect(
                db,
                resource_type="tag",
                resource_id=row.id,
                old_slug=row.slug,
                new_slug=new_slug,
            )
            row.slug = new_slug
    if description is not None:
        row.description = description
    if sort_order is not None:
        row.sort_order = sort_order
    write_audit_log(
        db,
        action="blog.tag_update",
        actor_user_id=user.id,
        resource_type="blog_tag",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def archive_tag(db: Session, *, user: User, tag_id: uuid.UUID) -> BlogTag:
    require_taxonomy_manage(user)
    row = db.get(BlogTag, tag_id)
    if row is None:
        raise_not_found()
    row.is_active = False
    row.archived_at = _utcnow()
    write_audit_log(
        db,
        action="blog.tag_archive",
        actor_user_id=user.id,
        resource_type="blog_tag",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def restore_tag(db: Session, *, user: User, tag_id: uuid.UUID) -> BlogTag:
    require_taxonomy_manage(user)
    row = db.get(BlogTag, tag_id)
    if row is None:
        raise_not_found()
    row.is_active = True
    row.archived_at = None
    write_audit_log(
        db,
        action="blog.tag_restore",
        actor_user_id=user.id,
        resource_type="blog_tag",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def reorder_tags(
    db: Session, *, user: User, ordered_ids: list[uuid.UUID]
) -> list[BlogTag]:
    require_taxonomy_manage(user)
    for i, tid in enumerate(ordered_ids):
        row = db.get(BlogTag, tid)
        if row is None:
            raise HTTPException(status_code=400, detail=f"Unknown tag {tid}")
        row.sort_order = i * 10
    write_audit_log(
        db,
        action="blog.tag_reorder",
        actor_user_id=user.id,
        resource_type="blog_tag",
        resource_id="batch",
    )
    db.commit()
    invalidate_blog_caches()
    return list_tags(db, include_archived=True)


# ---------------------------------------------------------------------------
# Post types CRUD
# ---------------------------------------------------------------------------


def create_post_type(
    db: Session,
    *,
    user: User,
    name: str,
    key: str | None = None,
    slug: str | None = None,
    description: str | None = None,
    sort_order: int = 0,
) -> BlogPostType:
    require_taxonomy_manage(user)
    clean_name = name.strip()
    if len(clean_name) < 2:
        raise HTTPException(status_code=400, detail="Name too short")
    final_key = (key or _slugify(clean_name, max_len=64).replace("-", "_")).strip().lower()
    if not _KEY_RE.match(final_key):
        raise HTTPException(
            status_code=400,
            detail="Invalid key; use lowercase letters, numbers, underscores",
        )
    if db.scalar(select(BlogPostType.id).where(BlogPostType.key == final_key)):
        raise HTTPException(status_code=409, detail="Post type key exists")
    final_slug = _slugify(slug or clean_name)
    if db.scalar(select(BlogPostType.id).where(BlogPostType.slug == final_slug)):
        raise HTTPException(status_code=409, detail="Post type slug exists")
    row = BlogPostType(
        key=final_key,
        name=clean_name,
        slug=final_slug,
        description=description,
        sort_order=sort_order,
        is_system=False,
        is_active=True,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Post type key or slug exists") from exc
    write_audit_log(
        db,
        action="blog.post_type_create",
        actor_user_id=user.id,
        resource_type="blog_post_type",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def update_post_type(
    db: Session,
    *,
    user: User,
    post_type_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    slug: str | None = None,
) -> BlogPostType:
    require_taxonomy_manage(user)
    row = db.get(BlogPostType, post_type_id)
    if row is None:
        raise_not_found()
    if name is not None:
        clean = name.strip()
        if len(clean) < 2:
            raise HTTPException(status_code=400, detail="Name too short")
        row.name = clean
    if description is not None:
        row.description = description
    if sort_order is not None:
        row.sort_order = sort_order
    if slug is not None and not row.is_system:
        new_slug = _slugify(slug)
        clash = db.scalar(
            select(BlogPostType.id).where(
                BlogPostType.slug == new_slug, BlogPostType.id != row.id
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Post type slug exists")
        row.slug = new_slug
    write_audit_log(
        db,
        action="blog.post_type_update",
        actor_user_id=user.id,
        resource_type="blog_post_type",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def archive_post_type(
    db: Session, *, user: User, post_type_id: uuid.UUID
) -> BlogPostType:
    require_taxonomy_manage(user)
    row = db.get(BlogPostType, post_type_id)
    if row is None:
        raise_not_found()
    row.is_active = False
    row.archived_at = _utcnow()
    write_audit_log(
        db,
        action="blog.post_type_archive",
        actor_user_id=user.id,
        resource_type="blog_post_type",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def restore_post_type(
    db: Session, *, user: User, post_type_id: uuid.UUID
) -> BlogPostType:
    require_taxonomy_manage(user)
    row = db.get(BlogPostType, post_type_id)
    if row is None:
        raise_not_found()
    row.is_active = True
    row.archived_at = None
    write_audit_log(
        db,
        action="blog.post_type_restore",
        actor_user_id=user.id,
        resource_type="blog_post_type",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def reorder_post_types(
    db: Session, *, user: User, ordered_ids: list[uuid.UUID]
) -> list[BlogPostType]:
    require_taxonomy_manage(user)
    for i, pid in enumerate(ordered_ids):
        row = db.get(BlogPostType, pid)
        if row is None:
            raise HTTPException(status_code=400, detail=f"Unknown post type {pid}")
        row.sort_order = i * 10
    write_audit_log(
        db,
        action="blog.post_type_reorder",
        actor_user_id=user.id,
        resource_type="blog_post_type",
        resource_id="batch",
    )
    db.commit()
    invalidate_blog_caches()
    return list_post_types(db, include_archived=True)


# ---------------------------------------------------------------------------
# Media roles CRUD
# ---------------------------------------------------------------------------


def create_media_role(
    db: Session,
    *,
    user: User,
    name: str,
    key: str,
    description: str | None = None,
    sort_order: int = 0,
    storage_folder: str = "content",
    allowed_contexts: list[str] | None = None,
) -> BlogMediaRole:
    require_taxonomy_manage(user)
    clean_name = name.strip()
    final_key = key.strip().lower()
    if not _KEY_RE.match(final_key):
        raise HTTPException(
            status_code=400,
            detail="Invalid key; use lowercase letters, numbers, underscores",
        )
    if db.scalar(select(BlogMediaRole.id).where(BlogMediaRole.key == final_key)):
        raise HTTPException(status_code=409, detail="Media role key exists")
    folder = (storage_folder or "content").strip().lower()
    if folder not in SAFE_STORAGE_FOLDERS or not _FOLDER_RE.match(folder):
        raise HTTPException(status_code=400, detail="Unsafe or invalid storage_folder")
    if ".." in folder or "/" in folder or "\\" in folder:
        raise HTTPException(status_code=400, detail="Unsafe storage_folder")
    row = BlogMediaRole(
        key=final_key,
        name=clean_name,
        description=description,
        sort_order=sort_order,
        storage_folder=folder,
        allowed_contexts=allowed_contexts or [final_key],
        is_system=False,
        is_required=False,
        is_active=True,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Media role key exists") from exc
    write_audit_log(
        db,
        action="blog.media_role_create",
        actor_user_id=user.id,
        resource_type="blog_media_role",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def update_media_role(
    db: Session,
    *,
    user: User,
    role_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    allowed_contexts: list[str] | None = None,
) -> BlogMediaRole:
    require_taxonomy_manage(user)
    row = db.get(BlogMediaRole, role_id)
    if row is None:
        raise_not_found()
    # System keys and storage_folder are immutable via this path
    if name is not None:
        row.name = name.strip()
    if description is not None:
        row.description = description
    if sort_order is not None:
        row.sort_order = sort_order
    if allowed_contexts is not None and not row.is_system:
        row.allowed_contexts = allowed_contexts
    write_audit_log(
        db,
        action="blog.media_role_update",
        actor_user_id=user.id,
        resource_type="blog_media_role",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def archive_media_role(
    db: Session, *, user: User, role_id: uuid.UUID
) -> BlogMediaRole:
    require_taxonomy_manage(user)
    row = db.get(BlogMediaRole, role_id)
    if row is None:
        raise_not_found()
    if row.is_required or row.key in REQUIRED_MEDIA_ROLE_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"Required system media role '{row.key}' cannot be archived",
        )
    row.is_active = False
    row.archived_at = _utcnow()
    write_audit_log(
        db,
        action="blog.media_role_archive",
        actor_user_id=user.id,
        resource_type="blog_media_role",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def restore_media_role(
    db: Session, *, user: User, role_id: uuid.UUID
) -> BlogMediaRole:
    require_taxonomy_manage(user)
    row = db.get(BlogMediaRole, role_id)
    if row is None:
        raise_not_found()
    row.is_active = True
    row.archived_at = None
    write_audit_log(
        db,
        action="blog.media_role_restore",
        actor_user_id=user.id,
        resource_type="blog_media_role",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_blog_caches()
    return row


def reorder_media_roles(
    db: Session, *, user: User, ordered_ids: list[uuid.UUID]
) -> list[BlogMediaRole]:
    require_taxonomy_manage(user)
    for i, rid in enumerate(ordered_ids):
        row = db.get(BlogMediaRole, rid)
        if row is None:
            raise HTTPException(status_code=400, detail=f"Unknown media role {rid}")
        row.sort_order = i * 10
    write_audit_log(
        db,
        action="blog.media_role_reorder",
        actor_user_id=user.id,
        resource_type="blog_media_role",
        resource_id="batch",
    )
    db.commit()
    invalidate_blog_caches()
    return list_media_roles(db, include_archived=True)


def resolve_upload_folder(db: Session, role_key: str) -> tuple[BlogMediaRole, str]:
    key = (role_key or "inline").strip().lower()
    role = get_media_role_by_key(db, key)
    if role is None or not _is_active(role):
        # Required roles fall back to active system defaults
        fallback_key = key if key in REQUIRED_MEDIA_ROLE_KEYS else "inline"
        role = get_media_role_by_key(db, fallback_key)
        if role is None or not _is_active(role):
            raise HTTPException(
                status_code=400,
                detail=f"Unknown or archived media role '{role_key}'",
            )
    folder_leaf = (
        role.storage_folder if role.storage_folder in SAFE_STORAGE_FOLDERS else "content"
    )
    return role, blog_public_folder(folder_leaf)


def upload_blog_media(
    db: Session,
    *,
    user: User,
    data: bytes,
    filename: str,
    content_type: str,
    role_key: str = "inline",
) -> dict[str, Any]:
    """Store a public blog image under the role's storage folder."""
    if not any(
        user_has_permission(user, c)
        for c in (
            "admin.full_access",
            "admin.blog.edit",
            "admin.blog.create",
            "admin.blog.taxonomy.manage",
        )
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    role, folder = resolve_upload_folder(db, (role_key or "inline").strip().lower())
    _ = folder
    _ = filename
    from app.public_media.processor import PublicMediaProcessingError
    from app.public_media.roles import MediaRole
    from app.public_media.service import (
        process_and_store_public_media,
        public_media_response,
    )

    media_role = {
        "cover": MediaRole.BLOG_COVER,
        "og": MediaRole.SOCIAL_OG,
        "inline": MediaRole.BLOG_INLINE,
        "content": MediaRole.BLOG_INLINE,
    }.get(role.key, MediaRole.BLOG_INLINE)

    try:
        payload = process_and_store_public_media(
            db,
            data=data,
            declared_content_type=content_type,
            role=media_role,
            created_by_user_id=user.id,
            owner_type="blog",
            owner_id=None,
            store_source=True,
        )
    except PublicMediaProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    public = public_media_response(payload)
    display_url = public.get("display_url") or public.get("url")
    if not display_url:
        raise HTTPException(status_code=400, detail="Failed to process image")
    db.commit()
    return {
        "url": display_url,
        "thumbnail_url": public.get("thumbnail_url"),
        "card_url": public.get("card_url"),
        "display_url": display_url,
        "full_url": public.get("full_url"),
        "og_url": public.get("og_url"),
        "media": public,
        "key": None,
        "media_role_key": role.key,
        "media_role_id": str(role.id),
    }


# ---------------------------------------------------------------------------
# Seed + content-type migration
# ---------------------------------------------------------------------------


def ensure_system_post_types(db: Session) -> int:
    created = 0
    by_key = {r.key: r for r in db.scalars(select(BlogPostType)).all()}
    for key, name, desc, sort in SYSTEM_POST_TYPES:
        if key in by_key:
            row = by_key[key]
            row.is_system = True
            if not row.name:
                row.name = name
            continue
        slug = _slugify(name)
        # avoid slug clash
        if db.scalar(select(BlogPostType.id).where(BlogPostType.slug == slug)):
            slug = f"{slug}-{key}"
        db.add(
            BlogPostType(
                key=key,
                name=name,
                slug=slug,
                description=desc,
                sort_order=sort,
                is_system=True,
                is_active=True,
            )
        )
        created += 1
    if created:
        db.flush()
    return created


def ensure_system_media_roles(db: Session) -> int:
    created = 0
    by_key = {r.key: r for r in db.scalars(select(BlogMediaRole)).all()}
    for key, name, desc, sort, folder, required, contexts in SYSTEM_MEDIA_ROLES:
        if key in by_key:
            row = by_key[key]
            row.is_system = True
            row.is_required = required
            row.storage_folder = folder
            continue
        db.add(
            BlogMediaRole(
                key=key,
                name=name,
                description=desc,
                sort_order=sort,
                storage_folder=folder,
                allowed_contexts=contexts,
                is_system=True,
                is_required=required,
                is_active=True,
            )
        )
        created += 1
    if created:
        db.flush()
    return created


def migrate_studio_content_types(db: Session) -> dict[str, Any]:
    """Map studio_brief.content_type → post_type_id. Idempotent."""
    ensure_system_post_types(db)
    by_key = {r.key: r for r in db.scalars(select(BlogPostType)).all()}
    report: dict[str, Any] = {
        "mapped": 0,
        "unmapped": [],
        "custom_created": [],
        "already_set": 0,
    }
    posts = db.scalars(select(BlogPost)).all()
    for post in posts:
        if post.post_type_id is not None:
            report["already_set"] += 1
            continue
        brief = post.studio_brief if isinstance(post.studio_brief, dict) else {}
        raw = brief.get("content_type")
        if not raw or not isinstance(raw, str):
            continue
        value = raw.strip()
        key = CONTENT_TYPE_TO_KEY.get(value)
        if key is None:
            # try normalize
            norm = _slugify(value, max_len=64).replace("-", "_")
            key = CONTENT_TYPE_TO_KEY.get(norm)
            if key is None and norm in by_key:
                key = norm
        if key and key in by_key:
            post.post_type_id = by_key[key].id
            report["mapped"] += 1
            continue
        # create custom non-system term for unique unmapped display values
        custom_key = _slugify(value, max_len=64).replace("-", "_") or "custom"
        if not _KEY_RE.match(custom_key):
            custom_key = f"custom_{uuid.uuid4().hex[:8]}"
        if custom_key not in by_key:
            # avoid key clash
            base = custom_key
            i = 1
            while custom_key in by_key:
                custom_key = f"{base}_{i}"
                i += 1
            slug = _slugify(value)
            if db.scalar(select(BlogPostType.id).where(BlogPostType.slug == slug)):
                slug = f"{slug}-{custom_key}"
            row = BlogPostType(
                key=custom_key,
                name=value[:120],
                slug=slug,
                description="Migrated from historical studio content_type",
                sort_order=900,
                is_system=False,
                is_active=True,
            )
            db.add(row)
            db.flush()
            by_key[custom_key] = row
            report["custom_created"].append({"key": custom_key, "name": value})
        post.post_type_id = by_key[custom_key].id
        report["mapped"] += 1
        report["unmapped"].append({"post_id": str(post.id), "content_type": value, "mapped_to": custom_key})
    db.flush()
    return report
