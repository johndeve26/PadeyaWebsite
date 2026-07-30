"""Taxonomy vocabulary lifecycle and seed helpers."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.cache_invalidation import invalidate_taxonomy_caches
from app.events.constants import DEFAULT_CATEGORIES
from app.taxonomy.image_constants import (
    PUBLIC_IMAGE_FIELD_NAMES,
    assert_approved_public_media_url,
    clamp_focal,
    normalize_alt,
)
from app.events.models import Event, EventCategory
from app.taxonomy.constants import (
    DEFAULT_AUDIENCE_TYPES,
    DEFAULT_HOST_TYPES,
    DEFAULT_LOCATIONS,
    DEFAULT_TAGS,
    DEFAULT_VENUE_TYPES,
    DEFAULT_VIBES,
    LEGACY_LOCATION_SLUG_RENAMES,
    LOCATION_PARENT_KIND,
)
from app.taxonomy.models import (
    EventTaxonomyLink,
    HostLocationLink,
    HostTaxonomyLink,
    HostType,
    Location,
    TaxonomyAudienceType,
    TaxonomyCategory,
    TaxonomySubcategory,
    TaxonomyTag,
    TaxonomyVibe,
    VenueType,
)
from app.taxonomy.schemas import (
    CategoryCreate,
    CategoryUpdate,
    LocationCreate,
    LocationUpdate,
    SubcategoryCreate,
    SubcategoryUpdate,
    VocabCreate,
    VocabUpdate,
)
from app.users.models import User
from app.users.service import user_has_permission

_ADMIN_PERMS = ("admin.full_access", "events.approve")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def require_taxonomy_admin(user: User) -> None:
    if not any(user_has_permission(user, code) for code in _ADMIN_PERMS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permission",
        )


def category_usage_count(db: Session, category: TaxonomyCategory) -> int:
    """Count events linked via primary_category, legacy category slug, or links."""
    legacy = db.scalar(
        select(EventCategory.id).where(EventCategory.slug == category.slug)
    )
    conditions = [Event.primary_category_id == category.id]
    if legacy is not None:
        conditions.append(Event.category_id == legacy)
    event_ids = set(db.scalars(select(Event.id).where(or_(*conditions))).all())
    linked = set(
        db.scalars(
            select(EventTaxonomyLink.event_id).where(
                EventTaxonomyLink.link_type.in_(("category", "primary_category")),
                EventTaxonomyLink.taxonomy_id == category.id,
            )
        ).all()
    )
    return len(event_ids | linked)


def list_categories(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[TaxonomyCategory]:
    q = select(TaxonomyCategory)
    if active_only:
        q = q.where(
            TaxonomyCategory.is_active.is_(True),
            TaxonomyCategory.archived_at.is_(None),
        )
    elif not include_archived:
        q = q.where(TaxonomyCategory.archived_at.is_(None))
    return list(
        db.scalars(q.order_by(TaxonomyCategory.sort_order, TaxonomyCategory.name)).all()
    )


def create_category(
    db: Session, *, user: User, payload: CategoryCreate
) -> TaxonomyCategory:
    require_taxonomy_admin(user)
    slug = payload.slug or slugify(payload.name)
    if db.scalar(select(TaxonomyCategory.id).where(TaxonomyCategory.slug == slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")
    row = TaxonomyCategory(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        sort_order=payload.sort_order,
        featured=payload.featured,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="taxonomy.category_create",
        actor_user_id=user.id,
        resource_type="taxonomy_category",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    invalidate_taxonomy_caches()
    return row


def update_category(
    db: Session, *, user: User, category_id: uuid.UUID, payload: CategoryUpdate
) -> TaxonomyCategory:
    require_taxonomy_admin(user)
    row = db.get(TaxonomyCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        clash = db.scalar(
            select(TaxonomyCategory.id).where(
                TaxonomyCategory.slug == data["slug"],
                TaxonomyCategory.id != category_id,
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Slug already exists")
    for key, value in data.items():
        if key == "name" and isinstance(value, str):
            value = value.strip()
        if key in PUBLIC_IMAGE_FIELD_NAMES:
            if key.endswith("_url"):
                value = assert_approved_public_media_url(value, allow_null=True)
            elif key.endswith("_alt"):
                value = normalize_alt(value)
            elif "focal" in key:
                value = clamp_focal(value)
        setattr(row, key, value)
    write_audit_log(
        db,
        action="taxonomy.category_update",
        actor_user_id=user.id,
        resource_type="taxonomy_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_taxonomy_caches()
    return row


def archive_category(
    db: Session, *, user: User, category_id: uuid.UUID
) -> TaxonomyCategory:
    require_taxonomy_admin(user)
    row = db.get(TaxonomyCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")
    row.is_active = False
    row.archived_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="taxonomy.category_archive",
        actor_user_id=user.id,
        resource_type="taxonomy_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_category(
    db: Session, *, user: User, category_id: uuid.UUID
) -> TaxonomyCategory:
    require_taxonomy_admin(user)
    row = db.get(TaxonomyCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")
    row.archived_at = None
    row.is_active = True
    write_audit_log(
        db,
        action="taxonomy.category_restore",
        actor_user_id=user.id,
        resource_type="taxonomy_category",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def list_subcategories(
    db: Session,
    *,
    category_id: uuid.UUID,
    include_archived: bool = False,
    active_only: bool = False,
) -> list[TaxonomySubcategory]:
    q = select(TaxonomySubcategory).where(
        TaxonomySubcategory.category_id == category_id
    )
    if active_only:
        q = q.where(
            TaxonomySubcategory.is_active.is_(True),
            TaxonomySubcategory.archived_at.is_(None),
        )
    elif not include_archived:
        q = q.where(TaxonomySubcategory.archived_at.is_(None))
    return list(
        db.scalars(
            q.order_by(TaxonomySubcategory.sort_order, TaxonomySubcategory.name)
        ).all()
    )


def create_subcategory(
    db: Session,
    *,
    user: User,
    category_id: uuid.UUID,
    payload: SubcategoryCreate,
) -> TaxonomySubcategory:
    require_taxonomy_admin(user)
    parent = db.get(TaxonomyCategory, category_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Category not found")
    slug = payload.slug or slugify(payload.name)
    exists = db.scalar(
        select(TaxonomySubcategory.id).where(
            TaxonomySubcategory.category_id == category_id,
            TaxonomySubcategory.slug == slug,
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="Slug already exists in category")
    row = TaxonomySubcategory(
        category_id=category_id,
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        sort_order=payload.sort_order,
        featured=payload.featured,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="taxonomy.subcategory_create",
        actor_user_id=user.id,
        resource_type="taxonomy_subcategory",
        resource_id=str(row.id),
        details={"slug": row.slug, "category_id": str(category_id)},
    )
    db.commit()
    db.refresh(row)
    return row


def update_subcategory(
    db: Session,
    *,
    user: User,
    subcategory_id: uuid.UUID,
    payload: SubcategoryUpdate,
) -> TaxonomySubcategory:
    require_taxonomy_admin(user)
    row = db.get(TaxonomySubcategory, subcategory_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        conflict = db.scalar(
            select(TaxonomySubcategory.id).where(
                TaxonomySubcategory.category_id == row.category_id,
                TaxonomySubcategory.slug == data["slug"],
                TaxonomySubcategory.id != subcategory_id,
            )
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Slug already exists in category")
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(
        db,
        action="taxonomy.subcategory_update",
        actor_user_id=user.id,
        resource_type="taxonomy_subcategory",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def archive_subcategory(
    db: Session, *, user: User, subcategory_id: uuid.UUID
) -> TaxonomySubcategory:
    require_taxonomy_admin(user)
    row = db.get(TaxonomySubcategory, subcategory_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    row.is_active = False
    row.archived_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="taxonomy.subcategory_archive",
        actor_user_id=user.id,
        resource_type="taxonomy_subcategory",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_subcategory(
    db: Session, *, user: User, subcategory_id: uuid.UUID
) -> TaxonomySubcategory:
    require_taxonomy_admin(user)
    row = db.get(TaxonomySubcategory, subcategory_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    row.archived_at = None
    row.is_active = True
    write_audit_log(
        db,
        action="taxonomy.subcategory_restore",
        actor_user_id=user.id,
        resource_type="taxonomy_subcategory",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def _list_vocab(
    db: Session,
    model: type[Any],
    *,
    include_archived: bool = False,
    active_only: bool = False,
) -> list[Any]:
    q = select(model)
    if active_only:
        q = q.where(model.is_active.is_(True), model.archived_at.is_(None))
    elif not include_archived:
        q = q.where(model.archived_at.is_(None))
    return list(db.scalars(q.order_by(model.sort_order, model.name)).all())


def _create_vocab(
    db: Session,
    *,
    user: User,
    model: type[Any],
    payload: VocabCreate,
    resource_type: str,
    action: str,
) -> Any:
    require_taxonomy_admin(user)
    slug = payload.slug or slugify(payload.name)
    if db.scalar(select(model.id).where(model.slug == slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")
    row = model(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        sort_order=payload.sort_order,
        featured=payload.featured,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        resource_type=resource_type,
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    return row


def _update_vocab(
    db: Session,
    *,
    user: User,
    model: type[Any],
    row_id: uuid.UUID,
    payload: VocabUpdate,
    resource_type: str,
    action: str,
    not_found: str,
) -> Any:
    require_taxonomy_admin(user)
    row = db.get(model, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail=not_found)
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        clash = db.scalar(
            select(model.id).where(model.slug == data["slug"], model.id != row_id)
        )
        if clash:
            raise HTTPException(status_code=409, detail="Slug already exists")
    for key, value in data.items():
        if key == "name" and isinstance(value, str):
            value = value.strip()
        setattr(row, key, value)
    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        resource_type=resource_type,
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def _archive_vocab(
    db: Session,
    *,
    user: User,
    model: type[Any],
    row_id: uuid.UUID,
    resource_type: str,
    action: str,
    not_found: str,
) -> Any:
    require_taxonomy_admin(user)
    row = db.get(model, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail=not_found)
    row.is_active = False
    row.archived_at = datetime.now(UTC)
    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        resource_type=resource_type,
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def _restore_vocab(
    db: Session,
    *,
    user: User,
    model: type[Any],
    row_id: uuid.UUID,
    resource_type: str,
    action: str,
    not_found: str,
) -> Any:
    require_taxonomy_admin(user)
    row = db.get(model, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail=not_found)
    row.archived_at = None
    row.is_active = True
    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        resource_type=resource_type,
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def list_tags(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[TaxonomyTag]:
    return _list_vocab(
        db, TaxonomyTag, include_archived=include_archived, active_only=active_only
    )


def create_tag(db: Session, *, user: User, payload: VocabCreate) -> TaxonomyTag:
    return _create_vocab(
        db,
        user=user,
        model=TaxonomyTag,
        payload=payload,
        resource_type="taxonomy_tag",
        action="taxonomy.tag_create",
    )


def update_tag(
    db: Session, *, user: User, tag_id: uuid.UUID, payload: VocabUpdate
) -> TaxonomyTag:
    return _update_vocab(
        db,
        user=user,
        model=TaxonomyTag,
        row_id=tag_id,
        payload=payload,
        resource_type="taxonomy_tag",
        action="taxonomy.tag_update",
        not_found="Tag not found",
    )


def archive_tag(db: Session, *, user: User, tag_id: uuid.UUID) -> TaxonomyTag:
    return _archive_vocab(
        db,
        user=user,
        model=TaxonomyTag,
        row_id=tag_id,
        resource_type="taxonomy_tag",
        action="taxonomy.tag_archive",
        not_found="Tag not found",
    )


def restore_tag(db: Session, *, user: User, tag_id: uuid.UUID) -> TaxonomyTag:
    return _restore_vocab(
        db,
        user=user,
        model=TaxonomyTag,
        row_id=tag_id,
        resource_type="taxonomy_tag",
        action="taxonomy.tag_restore",
        not_found="Tag not found",
    )


def list_host_types(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[HostType]:
    return _list_vocab(
        db, HostType, include_archived=include_archived, active_only=active_only
    )


def create_host_type(db: Session, *, user: User, payload: VocabCreate) -> HostType:
    return _create_vocab(
        db,
        user=user,
        model=HostType,
        payload=payload,
        resource_type="host_type",
        action="taxonomy.host_type_create",
    )


def update_host_type(
    db: Session, *, user: User, type_id: uuid.UUID, payload: VocabUpdate
) -> HostType:
    return _update_vocab(
        db,
        user=user,
        model=HostType,
        row_id=type_id,
        payload=payload,
        resource_type="host_type",
        action="taxonomy.host_type_update",
        not_found="Host type not found",
    )


def archive_host_type(db: Session, *, user: User, type_id: uuid.UUID) -> HostType:
    return _archive_vocab(
        db,
        user=user,
        model=HostType,
        row_id=type_id,
        resource_type="host_type",
        action="taxonomy.host_type_archive",
        not_found="Host type not found",
    )


def restore_host_type(db: Session, *, user: User, type_id: uuid.UUID) -> HostType:
    return _restore_vocab(
        db,
        user=user,
        model=HostType,
        row_id=type_id,
        resource_type="host_type",
        action="taxonomy.host_type_restore",
        not_found="Host type not found",
    )


def list_venue_types(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[VenueType]:
    return _list_vocab(
        db, VenueType, include_archived=include_archived, active_only=active_only
    )


def create_venue_type(db: Session, *, user: User, payload: VocabCreate) -> VenueType:
    return _create_vocab(
        db,
        user=user,
        model=VenueType,
        payload=payload,
        resource_type="venue_type",
        action="taxonomy.venue_type_create",
    )


def update_venue_type(
    db: Session, *, user: User, type_id: uuid.UUID, payload: VocabUpdate
) -> VenueType:
    return _update_vocab(
        db,
        user=user,
        model=VenueType,
        row_id=type_id,
        payload=payload,
        resource_type="venue_type",
        action="taxonomy.venue_type_update",
        not_found="Venue type not found",
    )


def archive_venue_type(db: Session, *, user: User, type_id: uuid.UUID) -> VenueType:
    return _archive_vocab(
        db,
        user=user,
        model=VenueType,
        row_id=type_id,
        resource_type="venue_type",
        action="taxonomy.venue_type_archive",
        not_found="Venue type not found",
    )


def restore_venue_type(db: Session, *, user: User, type_id: uuid.UUID) -> VenueType:
    return _restore_vocab(
        db,
        user=user,
        model=VenueType,
        row_id=type_id,
        resource_type="venue_type",
        action="taxonomy.venue_type_restore",
        not_found="Venue type not found",
    )


def suggest_venue_type(db: Session, *, user: User, name: str) -> VenueType:
    """Create (or reuse) an active venue type for all hosts to pick."""
    host = _require_host_suggester(db, user, label="venue type")

    clean = " ".join(name.strip().split())
    if len(clean) < 2:
        raise HTTPException(status_code=400, detail="Venue type name is too short")

    existing_same = db.scalar(
        select(VenueType).where(func.lower(VenueType.name) == clean.lower())
    )
    if existing_same is not None:
        if not existing_same.is_active or existing_same.archived_at is not None:
            existing_same.is_active = True
            existing_same.archived_at = None
            db.commit()
            db.refresh(existing_same)
        return existing_same

    base_slug = slugify(clean)
    slug = base_slug
    clash = db.scalar(select(VenueType).where(VenueType.slug == slug))
    if clash is not None:
        if clash.name.strip().lower() == clean.lower():
            if not clash.is_active or clash.archived_at is not None:
                clash.is_active = True
                clash.archived_at = None
                db.commit()
                db.refresh(clash)
            return clash
        for i in range(2, 50):
            candidate = f"{base_slug}-{i}"
            if (
                db.scalar(select(VenueType.id).where(VenueType.slug == candidate))
                is None
            ):
                slug = candidate
                break
        else:
            raise HTTPException(
                status_code=409, detail="Could not create a unique venue type slug"
            )

    row = VenueType(
        name=clean,
        slug=slug,
        description="Host-suggested venue type",
        sort_order=1000,
        featured=False,
        is_active=True,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="taxonomy.venue_type_suggest",
        actor_user_id=user.id,
        resource_type="venue_type",
        resource_id=str(row.id),
        details={
            "slug": row.slug,
            "name": row.name,
            "host_id": str(host.id) if host else None,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def list_locations(
    db: Session,
    *,
    active_only: bool = False,
    include_inactive: bool = False,
    kind: str | None = None,
    parent_id: uuid.UUID | None = None,
) -> list[Location]:
    q = select(Location)
    if active_only or not include_inactive:
        q = q.where(Location.is_active.is_(True))
    if kind:
        q = q.where(Location.kind == kind.strip().lower())
    if parent_id is not None:
        q = q.where(Location.parent_id == parent_id)
    return list(db.scalars(q.order_by(Location.kind, Location.name)).all())


def get_location_by_kind_slug(
    db: Session, *, kind: str, slug: str, active_only: bool = True
) -> Location | None:
    q = select(Location).where(
        Location.kind == kind.strip().lower(),
        Location.slug == slug.strip().lower(),
    )
    if active_only:
        q = q.where(Location.is_active.is_(True))
    return db.scalar(q)


def location_ancestors(db: Session, location: Location) -> list[Location]:
    """Root-first ancestor chain (country → … → parent), excluding self."""
    chain: list[Location] = []
    seen: set[uuid.UUID] = set()
    current = location
    while current.parent_id and current.parent_id not in seen:
        seen.add(current.parent_id)
        parent = db.get(Location, current.parent_id)
        if parent is None:
            break
        chain.append(parent)
        current = parent
    chain.reverse()
    return chain


def location_children(
    db: Session, location: Location, *, active_only: bool = True
) -> list[Location]:
    return list_locations(
        db,
        active_only=active_only,
        include_inactive=not active_only,
        parent_id=location.id,
    )


def descendant_location_ids(db: Session, location: Location) -> set[uuid.UUID]:
    """Self + all descendant location IDs (BFS)."""
    ids: set[uuid.UUID] = {location.id}
    frontier = [location.id]
    while frontier:
        parent_ids = frontier
        frontier = []
        children = list(
            db.scalars(select(Location).where(Location.parent_id.in_(parent_ids))).all()
        )
        for child in children:
            if child.id not in ids:
                ids.add(child.id)
                frontier.append(child.id)
    return ids


def location_siblings(
    db: Session, location: Location, *, active_only: bool = True
) -> list[Location]:
    """Other locations under the same parent (or root peers when parent is null)."""
    q = select(Location).where(
        Location.kind == location.kind,
        Location.id != location.id,
    )
    if active_only:
        q = q.where(Location.is_active.is_(True))
    if location.parent_id is None:
        q = q.where(Location.parent_id.is_(None))
    else:
        q = q.where(Location.parent_id == location.parent_id)
    return list(db.scalars(q.order_by(Location.name)).all())


def resolve_location_detail(
    db: Session, *, kind: str, slug: str
) -> tuple[Location, list[Location], list[Location], list[Location]] | None:
    row = get_location_by_kind_slug(db, kind=kind, slug=slug, active_only=True)
    if row is None:
        return None
    return (
        row,
        location_ancestors(db, row),
        location_children(db, row),
        location_siblings(db, row),
    )


def restore_location(db: Session, *, user: User, location_id: uuid.UUID) -> Location:
    require_taxonomy_admin(user)
    row = db.get(Location, location_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    row.is_active = True
    write_audit_log(
        db,
        action="taxonomy.location_restore",
        actor_user_id=user.id,
        resource_type="location",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def hard_delete_blocked(resource: str = "taxonomy term") -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail=f"Hard delete blocked for {resource}; use POST .../archive",
    )


def list_vibes(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[TaxonomyVibe]:
    return _list_vocab(
        db, TaxonomyVibe, include_archived=include_archived, active_only=active_only
    )


def list_audience_types(
    db: Session, *, include_archived: bool = False, active_only: bool = False
) -> list[TaxonomyAudienceType]:
    return _list_vocab(
        db,
        TaxonomyAudienceType,
        include_archived=include_archived,
        active_only=active_only,
    )


def get_host_taxonomy(db: Session, host_id: uuid.UUID) -> dict[str, Any]:
    links = list(
        db.scalars(
            select(HostTaxonomyLink).where(HostTaxonomyLink.host_id == host_id)
        ).all()
    )
    loc_links = list(
        db.scalars(
            select(HostLocationLink).where(HostLocationLink.host_id == host_id)
        ).all()
    )
    loc_ids = [link.location_id for link in loc_links]
    locations = {
        loc.id: loc
        for loc in db.scalars(select(Location).where(Location.id.in_(loc_ids))).all()
    } if loc_ids else {}

    host_types = [l.taxonomy_slug for l in links if l.link_type == "host_type"]
    categories = [l.taxonomy_slug for l in links if l.link_type == "category"]
    audiences = [l.taxonomy_slug for l in links if l.link_type == "audience"]
    primary_city = ""
    service_areas: list[str] = []
    for link in loc_links:
        loc = locations.get(link.location_id)
        if loc is None:
            continue
        if link.is_primary and loc.kind == "city":
            primary_city = loc.slug
        elif loc.kind == "area":
            service_areas.append(loc.slug)
    return {
        "host_type_slugs": host_types,
        "category_slugs": categories,
        "audience_slugs": audiences,
        "primary_city_slug": primary_city or None,
        "service_area_slugs": service_areas,
    }


def sync_host_taxonomy(
    db: Session,
    *,
    host_id: uuid.UUID,
    host_type_slugs: list[str] | None = None,
    category_slugs: list[str] | None = None,
    audience_slugs: list[str] | None = None,
    primary_city_slug: str | None = None,
    service_area_slugs: list[str] | None = None,
) -> None:
    """Replace host taxonomy / location links for provided fields."""

    def _replace_vocab_links(
        link_type: str, slugs: list[str], model: type[Any]
    ) -> None:
        existing = list(
            db.scalars(
                select(HostTaxonomyLink).where(
                    HostTaxonomyLink.host_id == host_id,
                    HostTaxonomyLink.link_type == link_type,
                )
            ).all()
        )
        for row in existing:
            db.delete(row)
        db.flush()
        for slug in slugs:
            term = db.scalar(
                select(model).where(model.slug == slug, model.is_active.is_(True))
            )
            if term is None:
                raise HTTPException(
                    status_code=400, detail=f"Unknown or inactive {link_type}: {slug}"
                )
            db.add(
                HostTaxonomyLink(
                    host_id=host_id,
                    link_type=link_type,
                    taxonomy_id=term.id,
                    taxonomy_slug=term.slug,
                )
            )

    if host_type_slugs is not None:
        _replace_vocab_links("host_type", host_type_slugs, HostType)
    if category_slugs is not None:
        _replace_vocab_links("category", category_slugs, TaxonomyCategory)
    if audience_slugs is not None:
        _replace_vocab_links("audience", audience_slugs, TaxonomyAudienceType)

    if primary_city_slug is not None or service_area_slugs is not None:
        existing_locs = list(
            db.scalars(
                select(HostLocationLink).where(HostLocationLink.host_id == host_id)
            ).all()
        )
        for row in existing_locs:
            db.delete(row)
        db.flush()
        if primary_city_slug:
            city = db.scalar(
                select(Location).where(
                    Location.slug == primary_city_slug,
                    Location.kind == "city",
                    Location.is_active.is_(True),
                )
            )
            if city is None:
                raise HTTPException(
                    status_code=400, detail=f"Unknown city: {primary_city_slug}"
                )
            db.add(
                HostLocationLink(
                    host_id=host_id, location_id=city.id, is_primary=True
                )
            )
        for slug in service_area_slugs or []:
            area = db.scalar(
                select(Location).where(
                    Location.slug == slug,
                    Location.kind == "area",
                    Location.is_active.is_(True),
                )
            )
            if area is None:
                raise HTTPException(status_code=400, detail=f"Unknown area: {slug}")
            db.add(
                HostLocationLink(
                    host_id=host_id, location_id=area.id, is_primary=False
                )
            )


def create_location(
    db: Session, *, user: User, payload: LocationCreate
) -> Location:
    require_taxonomy_admin(user)
    slug = payload.slug or slugify(payload.name)
    existing = db.scalar(
        select(Location.id).where(Location.kind == payload.kind, Location.slug == slug)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Location already exists")
    row = Location(
        kind=payload.kind.strip().lower(),
        name=payload.name.strip(),
        slug=slug,
        parent_id=payload.parent_id,
        state_code=payload.state_code,
        country_code=payload.country_code,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="taxonomy.location_create",
        actor_user_id=user.id,
        resource_type="location",
        resource_id=str(row.id),
        details={"slug": row.slug, "kind": row.kind},
    )
    db.commit()
    db.refresh(row)
    return row


def _require_host_suggester(db: Session, user: User, *, label: str):
    from app.hosts.service import get_host_by_user_id

    host = get_host_by_user_id(db, user.id)
    if host is None and not user_has_permission(user, "admin.full_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Host account required to suggest a {label}",
        )
    return host


def _unique_location_slug(
    db: Session, *, kind: str, base_slug: str, parent: Location
) -> str:
    slug = base_slug
    clash = db.scalar(
        select(Location).where(Location.kind == kind, Location.slug == slug)
    )
    if clash is None:
        return slug
    if clash.parent_id == parent.id:
        return slug  # caller reuses existing row
    slug = f"{parent.slug}-{base_slug}"
    clash = db.scalar(
        select(Location).where(Location.kind == kind, Location.slug == slug)
    )
    if clash is None:
        return slug
    if clash.parent_id == parent.id:
        return slug
    for i in range(2, 50):
        candidate = f"{slug}-{i}"
        if (
            db.scalar(
                select(Location.id).where(
                    Location.kind == kind, Location.slug == candidate
                )
            )
            is None
        ):
            return candidate
    raise HTTPException(
        status_code=409, detail=f"Could not create a unique {kind} slug"
    )


def _suggest_child_location(
    db: Session,
    *,
    user: User,
    parent_id: uuid.UUID,
    parent_kind: str,
    child_kind: str,
    name: str,
    missing_parent_detail: str,
) -> Location:
    """Create (or reuse) an active child location under a parent for all hosts."""
    host = _require_host_suggester(db, user, label=child_kind)

    parent = db.get(Location, parent_id)
    if parent is None or parent.kind != parent_kind or not parent.is_active:
        raise HTTPException(status_code=400, detail=missing_parent_detail)

    clean = " ".join(name.strip().split())
    if len(clean) < 2:
        raise HTTPException(
            status_code=400, detail=f"{child_kind.capitalize()} name is too short"
        )

    existing_same = db.scalar(
        select(Location).where(
            Location.kind == child_kind,
            Location.parent_id == parent.id,
            func.lower(Location.name) == clean.lower(),
        )
    )
    if existing_same is not None:
        if not existing_same.is_active:
            existing_same.is_active = True
            db.commit()
            db.refresh(existing_same)
        return existing_same

    base_slug = slugify(clean)
    slug = _unique_location_slug(
        db, kind=child_kind, base_slug=base_slug, parent=parent
    )
    existing_slug = db.scalar(
        select(Location).where(Location.kind == child_kind, Location.slug == slug)
    )
    if existing_slug is not None and existing_slug.parent_id == parent.id:
        if not existing_slug.is_active:
            existing_slug.is_active = True
            db.commit()
            db.refresh(existing_slug)
        return existing_slug

    row = Location(
        kind=child_kind,
        name=clean,
        slug=slug,
        parent_id=parent.id,
        state_code=parent.state_code,
        country_code=parent.country_code,
        is_active=True,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action=f"taxonomy.{child_kind}_suggest",
        actor_user_id=user.id,
        resource_type="location",
        resource_id=str(row.id),
        details={
            "slug": row.slug,
            "kind": child_kind,
            "parent_id": str(parent.id),
            "parent_slug": parent.slug,
            "parent_kind": parent.kind,
            "host_id": str(host.id) if host else None,
            "name": row.name,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def suggest_area(
    db: Session,
    *,
    user: User,
    city_id: uuid.UUID,
    name: str,
) -> Location:
    """Create (or reuse) an active area under a city for all hosts to pick."""
    return _suggest_child_location(
        db,
        user=user,
        parent_id=city_id,
        parent_kind="city",
        child_kind="area",
        name=name,
        missing_parent_detail="Select a valid city first",
    )


def suggest_city(
    db: Session,
    *,
    user: User,
    state_id: uuid.UUID,
    name: str,
) -> Location:
    """Create (or reuse) an active city under a state for all hosts to pick."""
    return _suggest_child_location(
        db,
        user=user,
        parent_id=state_id,
        parent_kind="state",
        child_kind="city",
        name=name,
        missing_parent_detail="Select a valid state first",
    )


def update_location(
    db: Session, *, user: User, location_id: uuid.UUID, payload: LocationUpdate
) -> Location:
    require_taxonomy_admin(user)
    row = db.get(Location, location_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    data = payload.model_dump(exclude_unset=True)
    if "kind" in data and data["kind"]:
        data["kind"] = data["kind"].strip().lower()
    if "name" in data and isinstance(data["name"], str):
        data["name"] = data["name"].strip()
    if "seo_index_mode" in data and data["seo_index_mode"] is not None:
        mode = str(data["seo_index_mode"]).strip().lower()
        if mode not in ("auto", "force_index", "force_noindex"):
            raise HTTPException(
                status_code=422,
                detail="seo_index_mode must be auto, force_index, or force_noindex",
            )
        data["seo_index_mode"] = mode
    if "seo_title" in data and isinstance(data["seo_title"], str):
        data["seo_title"] = data["seo_title"].strip() or None
    if "seo_description" in data and isinstance(data["seo_description"], str):
        data["seo_description"] = data["seo_description"].strip() or None
    if "intro_content" in data and isinstance(data["intro_content"], str):
        data["intro_content"] = data["intro_content"].strip() or None
    kind = data.get("kind", row.kind)
    slug = data.get("slug", row.slug)
    if slug:
        clash = db.scalar(
            select(Location.id).where(
                Location.kind == kind,
                Location.slug == slug,
                Location.id != location_id,
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Location already exists")
    for key, value in data.items():
        if key in PUBLIC_IMAGE_FIELD_NAMES:
            if key.endswith("_url"):
                value = assert_approved_public_media_url(value, allow_null=True)
            elif key.endswith("_alt"):
                value = normalize_alt(value)
            elif "focal" in key:
                value = clamp_focal(value)
        setattr(row, key, value)
    write_audit_log(
        db,
        action="taxonomy.location_update",
        actor_user_id=user.id,
        resource_type="location",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    invalidate_taxonomy_caches()
    return row


def archive_location(db: Session, *, user: User, location_id: uuid.UUID) -> Location:
    require_taxonomy_admin(user)
    row = db.get(Location, location_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    row.is_active = False
    write_audit_log(
        db,
        action="taxonomy.location_archive",
        actor_user_id=user.id,
        resource_type="location",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def _upsert_vocab_rows(
    db: Session,
    model: type[Any],
    rows: list[tuple[str, str, str]],
) -> None:
    for i, (name, slug, description) in enumerate(rows):
        existing = db.scalar(select(model).where(model.slug == slug))
        if existing is None:
            db.add(
                model(
                    name=name,
                    slug=slug,
                    description=description,
                    sort_order=i,
                    featured=False,
                    is_active=True,
                )
            )
        else:
            existing.name = name
            existing.description = description
            existing.sort_order = i
            if existing.archived_at is None:
                existing.is_active = True


def seed_taxonomy_vocab(db: Session) -> dict[str, int]:
    """Upsert categories (dual-write from event_categories), tags, vibes, etc."""
    # Prefer copying legacy event_categories when taxonomy_categories is empty.
    existing_count = db.scalar(select(func.count()).select_from(TaxonomyCategory)) or 0
    if existing_count == 0:
        legacy = list(db.scalars(select(EventCategory).order_by(EventCategory.name)).all())
        if legacy:
            for i, cat in enumerate(legacy):
                db.add(
                    TaxonomyCategory(
                        name=cat.name,
                        slug=cat.slug,
                        description=cat.description,
                        sort_order=i,
                        featured=False,
                        is_active=bool(cat.is_active),
                    )
                )
            db.flush()

    # Always upsert DEFAULT_CATEGORIES (and any missing legacy slugs).
    _upsert_vocab_rows(db, TaxonomyCategory, DEFAULT_CATEGORIES)
    _upsert_vocab_rows(db, TaxonomyTag, DEFAULT_TAGS)
    _upsert_vocab_rows(db, TaxonomyVibe, DEFAULT_VIBES)
    _upsert_vocab_rows(db, TaxonomyAudienceType, DEFAULT_AUDIENCE_TYPES)
    _upsert_vocab_rows(db, HostType, DEFAULT_HOST_TYPES)
    _upsert_vocab_rows(db, VenueType, DEFAULT_VENUE_TYPES)

    for kind, old_slug, new_slug in LEGACY_LOCATION_SLUG_RENAMES:
        legacy = db.scalar(
            select(Location).where(Location.kind == kind, Location.slug == old_slug)
        )
        if legacy is None:
            continue
        clash = db.scalar(
            select(Location).where(Location.kind == kind, Location.slug == new_slug)
        )
        if clash is None:
            legacy.slug = new_slug
        db.flush()

    kind_slug_to_id: dict[str, uuid.UUID] = {}
    for kind, name, slug, parent_slug, state_code, country_code in DEFAULT_LOCATIONS:
        existing = db.scalar(
            select(Location).where(Location.kind == kind, Location.slug == slug)
        )
        parent_id = None
        if parent_slug:
            parent_kind = LOCATION_PARENT_KIND.get(kind)
            if parent_kind:
                parent_id = kind_slug_to_id.get(f"{parent_kind}:{parent_slug}")
                if parent_id is None:
                    parent = db.scalar(
                        select(Location).where(
                            Location.kind == parent_kind,
                            Location.slug == parent_slug,
                        )
                    )
                    parent_id = parent.id if parent else None
        if existing is None:
            row = Location(
                kind=kind,
                name=name,
                slug=slug,
                parent_id=parent_id,
                state_code=state_code,
                country_code=country_code,
                is_active=True,
            )
            db.add(row)
            db.flush()
            kind_slug_to_id[f"{kind}:{slug}"] = row.id
        else:
            existing.name = name
            if parent_id is not None:
                existing.parent_id = parent_id
            existing.state_code = state_code
            existing.country_code = country_code
            existing.is_active = True
            kind_slug_to_id[f"{kind}:{slug}"] = existing.id

    db.commit()
    return {
        "categories": db.scalar(select(func.count()).select_from(TaxonomyCategory)) or 0,
        "tags": db.scalar(select(func.count()).select_from(TaxonomyTag)) or 0,
        "vibes": db.scalar(select(func.count()).select_from(TaxonomyVibe)) or 0,
        "audience_types": db.scalar(select(func.count()).select_from(TaxonomyAudienceType))
        or 0,
        "host_types": db.scalar(select(func.count()).select_from(HostType)) or 0,
        "venue_types": db.scalar(select(func.count()).select_from(VenueType)) or 0,
        "locations": db.scalar(select(func.count()).select_from(Location)) or 0,
    }
