"""CMS content lifecycle services."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cms.models import CmsBlogPost, CmsBrowseTile, CmsFaq, CmsHomepageBanner
from app.cms.schemas import (
    BROWSE_RAILS,
    BannerCreate,
    BannerUpdate,
    BlogPostCreate,
    BlogPostUpdate,
    BrowseTileCreate,
    BrowseTileUpdate,
    FaqCreate,
    FaqUpdate,
)
from app.core.audit import write_audit_log
from app.users.models import User
from app.users.service import user_has_permission


def _require_cms_admin(user: User) -> None:
    if not user_has_permission(user, "admin.full_access"):
        raise HTTPException(status_code=403, detail="Insufficient permission")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "post"


# --- Blog ---


def list_public_posts(db: Session) -> list[CmsBlogPost]:
    return list(
        db.scalars(
            select(CmsBlogPost)
            .where(
                CmsBlogPost.status == "published",
                CmsBlogPost.archived_at.is_(None),
            )
            .order_by(CmsBlogPost.published_at.desc())
        )
    )


def list_admin_posts(
    db: Session, *, user: User, include_archived: bool = False
) -> list[CmsBlogPost]:
    _require_cms_admin(user)
    q = select(CmsBlogPost)
    if not include_archived:
        q = q.where(CmsBlogPost.archived_at.is_(None))
    return list(db.scalars(q.order_by(CmsBlogPost.updated_at.desc())))


def get_public_post(db: Session, slug: str) -> CmsBlogPost:
    row = db.scalar(
        select(CmsBlogPost).where(
            CmsBlogPost.slug == slug,
            CmsBlogPost.status == "published",
            CmsBlogPost.archived_at.is_(None),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return row


def create_post(db: Session, *, user: User, payload: BlogPostCreate) -> CmsBlogPost:
    _require_cms_admin(user)
    slug = payload.slug or _slugify(payload.title)
    if db.scalar(select(CmsBlogPost.id).where(CmsBlogPost.slug == slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")
    row = CmsBlogPost(
        title=payload.title.strip(),
        slug=slug,
        excerpt=payload.excerpt,
        body=payload.body,
        cover_url=payload.cover_url,
        status="draft",
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cms.blog_create",
        actor_user_id=user.id,
        resource_type="cms_blog_post",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def update_post(
    db: Session, *, user: User, post_id: uuid.UUID, payload: BlogPostUpdate
) -> CmsBlogPost:
    _require_cms_admin(user)
    row = db.get(CmsBlogPost, post_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        clash = db.scalar(
            select(CmsBlogPost.id).where(
                CmsBlogPost.slug == data["slug"], CmsBlogPost.id != post_id
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Slug already exists")
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.blog_update",
        actor_user_id=user.id,
        resource_type="cms_blog_post",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def publish_post(db: Session, *, user: User, post_id: uuid.UUID) -> CmsBlogPost:
    _require_cms_admin(user)
    row = db.get(CmsBlogPost, post_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=404, detail="Post not found")
    row.status = "published"
    row.published_at = datetime.now(UTC)
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.blog_publish",
        actor_user_id=user.id,
        resource_type="cms_blog_post",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def archive_post(db: Session, *, user: User, post_id: uuid.UUID) -> CmsBlogPost:
    _require_cms_admin(user)
    row = db.get(CmsBlogPost, post_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    row.status = "archived"
    row.archived_at = datetime.now(UTC)
    row.archived_by = user.id
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.blog_archive",
        actor_user_id=user.id,
        resource_type="cms_blog_post",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_post(db: Session, *, user: User, post_id: uuid.UUID) -> CmsBlogPost:
    _require_cms_admin(user)
    row = db.get(CmsBlogPost, post_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")
    row.status = "draft"
    row.archived_at = None
    row.archived_by = None
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.blog_restore",
        actor_user_id=user.id,
        resource_type="cms_blog_post",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def delete_cms_blocked() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Hard delete blocked; use POST .../archive",
    )


# --- FAQs ---


def list_public_faqs(db: Session) -> list[CmsFaq]:
    return list(
        db.scalars(
            select(CmsFaq)
            .where(CmsFaq.status == "published", CmsFaq.archived_at.is_(None))
            .order_by(CmsFaq.sort_order.asc(), CmsFaq.created_at.asc())
        )
    )


def list_admin_faqs(
    db: Session, *, user: User, include_archived: bool = False
) -> list[CmsFaq]:
    _require_cms_admin(user)
    q = select(CmsFaq)
    if not include_archived:
        q = q.where(CmsFaq.archived_at.is_(None))
    return list(db.scalars(q.order_by(CmsFaq.sort_order.asc())))


def create_faq(db: Session, *, user: User, payload: FaqCreate) -> CmsFaq:
    _require_cms_admin(user)
    row = CmsFaq(
        question=payload.question.strip(),
        answer=payload.answer,
        category=payload.category,
        sort_order=payload.sort_order,
        status="draft",
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cms.faq_create",
        actor_user_id=user.id,
        resource_type="cms_faq",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def update_faq(
    db: Session, *, user: User, faq_id: uuid.UUID, payload: FaqUpdate
) -> CmsFaq:
    _require_cms_admin(user)
    row = db.get(CmsFaq, faq_id)
    if row is None:
        raise HTTPException(status_code=404, detail="FAQ not found")
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.faq_update",
        actor_user_id=user.id,
        resource_type="cms_faq",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def publish_faq(db: Session, *, user: User, faq_id: uuid.UUID) -> CmsFaq:
    _require_cms_admin(user)
    row = db.get(CmsFaq, faq_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=404, detail="FAQ not found")
    row.status = "published"
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.faq_publish",
        actor_user_id=user.id,
        resource_type="cms_faq",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    try:
        from app.core.cache_invalidation import invalidate_cms_caches

        invalidate_cms_caches()
    except Exception:
        pass
    return row


def archive_faq(db: Session, *, user: User, faq_id: uuid.UUID) -> CmsFaq:
    _require_cms_admin(user)
    row = db.get(CmsFaq, faq_id)
    if row is None:
        raise HTTPException(status_code=404, detail="FAQ not found")
    row.status = "archived"
    row.archived_at = datetime.now(UTC)
    row.archived_by = user.id
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.faq_archive",
        actor_user_id=user.id,
        resource_type="cms_faq",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_faq(db: Session, *, user: User, faq_id: uuid.UUID) -> CmsFaq:
    _require_cms_admin(user)
    row = db.get(CmsFaq, faq_id)
    if row is None:
        raise HTTPException(status_code=404, detail="FAQ not found")
    row.status = "draft"
    row.archived_at = None
    row.archived_by = None
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.faq_restore",
        actor_user_id=user.id,
        resource_type="cms_faq",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


# --- Banners ---


def list_public_banners(db: Session) -> list[CmsHomepageBanner]:
    return list(
        db.scalars(
            select(CmsHomepageBanner)
            .where(
                CmsHomepageBanner.status == "published",
                CmsHomepageBanner.archived_at.is_(None),
            )
            .order_by(CmsHomepageBanner.sort_order.asc())
        )
    )


def list_admin_banners(
    db: Session, *, user: User, include_archived: bool = False
) -> list[CmsHomepageBanner]:
    _require_cms_admin(user)
    q = select(CmsHomepageBanner)
    if not include_archived:
        q = q.where(CmsHomepageBanner.archived_at.is_(None))
    return list(db.scalars(q.order_by(CmsHomepageBanner.sort_order.asc())))


def create_banner(db: Session, *, user: User, payload: BannerCreate) -> CmsHomepageBanner:
    _require_cms_admin(user)
    row = CmsHomepageBanner(
        title=payload.title.strip(),
        subtitle=payload.subtitle,
        image_url=payload.image_url,
        cta_label=payload.cta_label,
        cta_href=payload.cta_href,
        sort_order=payload.sort_order,
        status="draft",
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cms.banner_create",
        actor_user_id=user.id,
        resource_type="cms_homepage_banner",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def update_banner(
    db: Session, *, user: User, banner_id: uuid.UUID, payload: BannerUpdate
) -> CmsHomepageBanner:
    _require_cms_admin(user)
    row = db.get(CmsHomepageBanner, banner_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Banner not found")
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.banner_update",
        actor_user_id=user.id,
        resource_type="cms_homepage_banner",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def publish_banner(db: Session, *, user: User, banner_id: uuid.UUID) -> CmsHomepageBanner:
    _require_cms_admin(user)
    row = db.get(CmsHomepageBanner, banner_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=404, detail="Banner not found")
    row.status = "published"
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.banner_publish",
        actor_user_id=user.id,
        resource_type="cms_homepage_banner",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def archive_banner(db: Session, *, user: User, banner_id: uuid.UUID) -> CmsHomepageBanner:
    _require_cms_admin(user)
    row = db.get(CmsHomepageBanner, banner_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Banner not found")
    row.status = "archived"
    row.archived_at = datetime.now(UTC)
    row.archived_by = user.id
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.banner_archive",
        actor_user_id=user.id,
        resource_type="cms_homepage_banner",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_banner(db: Session, *, user: User, banner_id: uuid.UUID) -> CmsHomepageBanner:
    _require_cms_admin(user)
    row = db.get(CmsHomepageBanner, banner_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Banner not found")
    row.status = "draft"
    row.archived_at = None
    row.archived_by = None
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.banner_restore",
        actor_user_id=user.id,
        resource_type="cms_homepage_banner",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


# --- Browse tiles ---


DEFAULT_BROWSE_TILES: list[dict[str, str | int]] = [
    # interest
    {"rail": "interest", "label": "Nightlife & parties", "hint": "Detty · club nights", "href": "/events/c/nightlife", "image_url": "/brand/browse/nightlife.svg", "sort_order": 0},
    {"rail": "interest", "label": "Concerts & live shows", "hint": "Afrobeats · stages", "href": "/events/c/music", "image_url": "/brand/browse/music.svg", "sort_order": 1},
    {"rail": "interest", "label": "Comedy", "hint": "Open mics · headliners", "href": "/events/c/comedy", "image_url": "/brand/browse/comedy.svg", "sort_order": 2},
    {"rail": "interest", "label": "Tech & business", "hint": "Mixers · demos", "href": "/events/c/tech", "image_url": "/brand/browse/tech.svg", "sort_order": 3},
    {"rail": "interest", "label": "Gospel & worship", "hint": "Faith nights", "href": "/events/c/gospel", "image_url": "/brand/browse/gospel.svg", "sort_order": 4},
    {"rail": "interest", "label": "Campus events", "hint": "Student energy", "href": "/events/c/campus", "image_url": "/brand/browse/campus.svg", "sort_order": 5},
    {"rail": "interest", "label": "Food & lifestyle", "hint": "Tastings · pop-ups", "href": "/events/c/food-drink", "image_url": "/brand/browse/food-drink.svg", "sort_order": 6},
    {"rail": "interest", "label": "Sports & culture", "hint": "Games · galleries", "href": "/events/c/arts-culture", "image_url": "/brand/browse/arts-culture.svg", "sort_order": 7},
    # city
    {"rail": "city", "label": "Lagos", "hint": "Island · mainland", "href": "/events/city/lagos", "image_url": "/brand/browse/city-lagos.svg", "sort_order": 0},
    {"rail": "city", "label": "Abuja", "hint": "Capital nights", "href": "/events/city/abuja", "image_url": "/brand/browse/city-abuja.svg", "sort_order": 1},
    {"rail": "city", "label": "Ibadan", "hint": "Ancient city pulse", "href": "/events/city/ibadan", "image_url": "/brand/browse/city-ibadan.svg", "sort_order": 2},
    {"rail": "city", "label": "Akure", "hint": "Ondo energy", "href": "/events/city/akure", "image_url": "/brand/browse/city-akure.svg", "sort_order": 3},
    {"rail": "city", "label": "Port Harcourt", "hint": "Garden city", "href": "/events/city/port-harcourt", "image_url": "/brand/browse/city-port-harcourt.svg", "sort_order": 4},
    {"rail": "city", "label": "Enugu", "hint": "Coal city culture", "href": "/events/city/enugu", "image_url": "/brand/browse/city-enugu.svg", "sort_order": 5},
    # price
    {"rail": "price", "label": "Free", "hint": "No ticket cost", "href": "/events/free", "image_url": "/brand/browse/price-free.svg", "sort_order": 0},
    {"rail": "price", "label": "Under ₦5,000", "hint": "Easy entry", "href": "/events/under/5000", "image_url": "/brand/browse/price-5k.svg", "sort_order": 1},
    {"rail": "price", "label": "Under ₦10,000", "hint": "Mid-range nights", "href": "/events/under/10000", "image_url": "/brand/browse/price-10k.svg", "sort_order": 2},
    {"rail": "price", "label": "Under ₦25,000", "hint": "Premium seats", "href": "/events/under/25000", "image_url": "/brand/browse/price-25k.svg", "sort_order": 3},
    {"rail": "price", "label": "VIP nights", "hint": "Tables & tiers", "href": "/events/vip", "image_url": "/brand/browse/price-vip.svg", "sort_order": 4},
    # when
    {"rail": "when", "label": "This weekend", "hint": "Fri–Sun picks", "href": "/events/this-weekend", "image_url": "/brand/browse/when-weekend.svg", "sort_order": 0},
    {"rail": "when", "label": "In person", "hint": "Show up live", "href": "/events/in-person", "image_url": "/brand/browse/when-person.svg", "sort_order": 1},
    {"rail": "when", "label": "Online", "hint": "From anywhere", "href": "/events/online", "image_url": "/brand/browse/when-online.svg", "sort_order": 2},
    {"rail": "when", "label": "Hybrid", "hint": "Both ways in", "href": "/events/hybrid", "image_url": "/brand/browse/when-hybrid.svg", "sort_order": 3},
]


def _validate_rail(rail: str) -> str:
    value = rail.strip().lower()
    if value not in BROWSE_RAILS:
        raise HTTPException(
            status_code=400,
            detail=f"rail must be one of: {', '.join(sorted(BROWSE_RAILS))}",
        )
    return value


def list_public_browse_tiles(db: Session) -> list[CmsBrowseTile]:
    return list(
        db.scalars(
            select(CmsBrowseTile)
            .where(
                CmsBrowseTile.status == "published",
                CmsBrowseTile.archived_at.is_(None),
            )
            .order_by(CmsBrowseTile.rail.asc(), CmsBrowseTile.sort_order.asc())
        )
    )


def list_admin_browse_tiles(
    db: Session, *, user: User, include_archived: bool = False
) -> list[CmsBrowseTile]:
    _require_cms_admin(user)
    q = select(CmsBrowseTile)
    if not include_archived:
        q = q.where(CmsBrowseTile.archived_at.is_(None))
    return list(
        db.scalars(q.order_by(CmsBrowseTile.rail.asc(), CmsBrowseTile.sort_order.asc()))
    )


def create_browse_tile(
    db: Session, *, user: User, payload: BrowseTileCreate
) -> CmsBrowseTile:
    _require_cms_admin(user)
    row = CmsBrowseTile(
        rail=_validate_rail(payload.rail),
        label=payload.label.strip(),
        hint=payload.hint.strip() if payload.hint else None,
        href=payload.href.strip(),
        image_url=payload.image_url.strip(),
        sort_order=payload.sort_order,
        status="draft",
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cms.browse_tile_create",
        actor_user_id=user.id,
        resource_type="cms_browse_tile",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def update_browse_tile(
    db: Session, *, user: User, tile_id: uuid.UUID, payload: BrowseTileUpdate
) -> CmsBrowseTile:
    _require_cms_admin(user)
    row = db.get(CmsBrowseTile, tile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Browse tile not found")
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    data = payload.model_dump(exclude_unset=True)
    if "rail" in data and data["rail"] is not None:
        data["rail"] = _validate_rail(data["rail"])
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(row, key, value)
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.browse_tile_update",
        actor_user_id=user.id,
        resource_type="cms_browse_tile",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def publish_browse_tile(
    db: Session, *, user: User, tile_id: uuid.UUID
) -> CmsBrowseTile:
    _require_cms_admin(user)
    row = db.get(CmsBrowseTile, tile_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=404, detail="Browse tile not found")
    row.status = "published"
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.browse_tile_publish",
        actor_user_id=user.id,
        resource_type="cms_browse_tile",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def archive_browse_tile(
    db: Session, *, user: User, tile_id: uuid.UUID
) -> CmsBrowseTile:
    _require_cms_admin(user)
    row = db.get(CmsBrowseTile, tile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Browse tile not found")
    row.status = "archived"
    row.archived_at = datetime.now(UTC)
    row.archived_by = user.id
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.browse_tile_archive",
        actor_user_id=user.id,
        resource_type="cms_browse_tile",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_browse_tile(
    db: Session, *, user: User, tile_id: uuid.UUID
) -> CmsBrowseTile:
    _require_cms_admin(user)
    row = db.get(CmsBrowseTile, tile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Browse tile not found")
    row.status = "draft"
    row.archived_at = None
    row.archived_by = None
    row.updated_by = user.id
    write_audit_log(
        db,
        action="cms.browse_tile_restore",
        actor_user_id=user.id,
        resource_type="cms_browse_tile",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def seed_default_browse_tiles(db: Session, *, actor_user_id: uuid.UUID | None = None) -> int:
    """Idempotent seed of default homepage browse tiles (published).

    When tiles already exist, syncs hrefs for matching rail+label defaults
    (keeps CMS copy current for price hubs, etc.).
    """
    existing = db.scalar(select(CmsBrowseTile.id).limit(1))
    if existing is not None:
        updated = 0
        for item in DEFAULT_BROWSE_TILES:
            row = db.scalar(
                select(CmsBrowseTile).where(
                    CmsBrowseTile.rail == str(item["rail"]),
                    CmsBrowseTile.label == str(item["label"]),
                    CmsBrowseTile.archived_at.is_(None),
                )
            )
            if row is None:
                continue
            new_href = str(item["href"])
            if row.href != new_href:
                row.href = new_href
                row.updated_by = actor_user_id
                updated += 1
        if updated:
            db.commit()
        return updated
    for item in DEFAULT_BROWSE_TILES:
        db.add(
            CmsBrowseTile(
                rail=str(item["rail"]),
                label=str(item["label"]),
                hint=str(item["hint"]) if item.get("hint") else None,
                href=str(item["href"]),
                image_url=str(item["image_url"]),
                sort_order=int(item["sort_order"]),
                status="published",
                created_by=actor_user_id,
                updated_by=actor_user_id,
            )
        )
    db.commit()
    return len(DEFAULT_BROWSE_TILES)
