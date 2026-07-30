"""Marketplace taxonomy image upload and visual settings."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.cache_invalidation import invalidate_taxonomy_caches
from app.core.media import get_public_media_storage
from app.core.media_folders import taxonomy_public_folder
from app.taxonomy.image_constants import (
    PUBLIC_IMAGE_FIELD_NAMES,
    assert_approved_public_media_url,
    assert_image_capable_kind,
    assert_image_role,
    clamp_focal,
    normalize_alt,
)
from app.taxonomy.models import Location, TaxonomyCategory
from app.taxonomy.schemas import TaxonomyVisualUpdate
from app.taxonomy.service import require_taxonomy_admin
from app.users.models import User


def _focal_float(value: Any) -> float:
    try:
        return float(value if value is not None else 0.5)
    except (TypeError, ValueError):
        return 0.5


def public_image_payload(row: TaxonomyCategory | Location) -> dict[str, Any]:
    primary_url = getattr(row, "primary_image_url", None)
    hero_url = getattr(row, "hero_image_url", None)
    primary_alt = getattr(row, "primary_image_alt", None)
    hero_alt = getattr(row, "hero_image_alt", None)
    fx = _focal_float(getattr(row, "primary_image_focal_x", 0.5))
    fy = _focal_float(getattr(row, "primary_image_focal_y", 0.5))
    hfx = _focal_float(getattr(row, "hero_image_focal_x", 0.5))
    hfy = _focal_float(getattr(row, "hero_image_focal_y", 0.5))
    return {
        "primary_image_url": primary_url,
        "primary_image_alt": primary_alt,
        "primary_image_focal_x": fx,
        "primary_image_focal_y": fy,
        "hero_image_url": hero_url,
        "hero_image_alt": hero_alt,
        "hero_image_focal_x": hfx,
        "hero_image_focal_y": hfy,
        # Card convenience: primary only (hero is hub-specific)
        "image_url": primary_url,
        "image_alt": primary_alt or getattr(row, "name", None),
        "image_focal_x": fx,
        "image_focal_y": fy,
    }


def enrich_category_public(row: TaxonomyCategory, *, usage_count: int | None = None) -> dict[str, Any]:
    from app.taxonomy.schemas import CategoryPublic

    base = CategoryPublic.model_validate(row).model_dump()
    base.update(public_image_payload(row))
    if usage_count is not None:
        base["usage_count"] = usage_count
    return base


def enrich_location_public(row: Location) -> dict[str, Any]:
    from app.taxonomy.schemas import LocationPublic

    base = LocationPublic.model_validate(row).model_dump()
    base.update(public_image_payload(row))
    return base


def _load_term(
    db: Session, *, kind: str, term_id: uuid.UUID
) -> tuple[str, TaxonomyCategory | Location]:
    kind = assert_image_capable_kind(kind)
    if kind == "category":
        row = db.get(TaxonomyCategory, term_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return kind, row
    row = db.get(Location, term_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    if row.kind != kind:
        raise HTTPException(
            status_code=400,
            detail=f"Location kind is '{row.kind}', expected '{kind}'",
        )
    return kind, row


def upload_taxonomy_media(
    db: Session,
    *,
    user: User,
    kind: str,
    term_id: uuid.UUID,
    image_role: str,
    data: bytes,
    filename: str,
    content_type: str,
    alt: str | None = None,
    apply: bool = True,
) -> dict[str, Any]:
    """Store a unique public object and optionally apply it to the term."""
    require_taxonomy_admin(user)
    kind, row = _load_term(db, kind=kind, term_id=term_id)
    if isinstance(row, TaxonomyCategory) and row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    if isinstance(row, Location) and not row.is_active:
        raise HTTPException(status_code=400, detail="Restore before updating")
    role = assert_image_role(image_role)
    folder = taxonomy_public_folder(kind, term_id, role)
    storage = get_public_media_storage()
    try:
        stored = storage.store_bytes(
            data=data,
            filename=filename,
            content_type=content_type,
            folder=folder,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if apply:
        alt_norm = normalize_alt(alt)
        if role == "hero":
            row.hero_image_url = stored.url
            if alt_norm is not None:
                row.hero_image_alt = alt_norm
            action = "taxonomy.hero_image_upload"
        else:
            row.primary_image_url = stored.url
            if alt_norm is not None:
                row.primary_image_alt = alt_norm
            action = "taxonomy.primary_image_upload"
        write_audit_log(
            db,
            action=action,
            actor_user_id=user.id,
            resource_type=f"taxonomy_{kind}",
            resource_id=str(term_id),
            details={"image_role": role, "url": stored.url},
        )
        db.commit()
        db.refresh(row)
        invalidate_taxonomy_caches()

    return {
        "url": stored.url,
        "key": stored.key,
        "kind": kind,
        "term_id": term_id,
        "image_role": role,
    }


def update_term_visuals(
    db: Session,
    *,
    user: User,
    kind: str,
    term_id: uuid.UUID,
    payload: TaxonomyVisualUpdate,
) -> TaxonomyCategory | Location:
    require_taxonomy_admin(user)
    kind, row = _load_term(db, kind=kind, term_id=term_id)
    if isinstance(row, TaxonomyCategory) and row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore before updating")
    if isinstance(row, Location) and not row.is_active:
        raise HTTPException(status_code=400, detail="Restore before updating")

    data = payload.model_dump(exclude_unset=True)
    clear_primary = bool(data.pop("clear_primary", False))
    clear_hero = bool(data.pop("clear_hero", False))
    changes: dict[str, Any] = {}

    if clear_primary:
        row.primary_image_url = None
        row.primary_image_alt = None
        row.primary_image_focal_x = Decimal("0.500")
        row.primary_image_focal_y = Decimal("0.500")
        changes["clear_primary"] = True
    if clear_hero:
        row.hero_image_url = None
        row.hero_image_alt = None
        row.hero_image_focal_x = Decimal("0.500")
        row.hero_image_focal_y = Decimal("0.500")
        changes["clear_hero"] = True

    for field in PUBLIC_IMAGE_FIELD_NAMES:
        if field not in data:
            continue
        value = data[field]
        if field.endswith("_url"):
            value = assert_approved_public_media_url(value, allow_null=True)
        elif field.endswith("_alt"):
            value = normalize_alt(value)
        elif "focal" in field:
            value = clamp_focal(value)
        setattr(row, field, value)
        changes[field] = value

    if not changes:
        raise HTTPException(status_code=400, detail="No visual fields to update")

    write_audit_log(
        db,
        action="taxonomy.visuals_update",
        actor_user_id=user.id,
        resource_type=f"taxonomy_{kind}",
        resource_id=str(term_id),
        details={"fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(row)
    invalidate_taxonomy_caches()
    return row
