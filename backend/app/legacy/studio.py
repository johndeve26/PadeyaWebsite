"""Legacy Content Studio — page settings, blocks, featured items."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host
from app.hosts.schemas import HostProfileUpdate
from app.hosts.service import require_user_host, slugify, update_host_profile
from app.legacy.constants import (
    BLOCK_TYPES,
    DEFAULT_CONTENT_BLOCKS,
    FEATURED_ITEM_TYPES,
    FEATURED_PLACEMENTS,
)
from app.legacy.models import (
    HostContactSettings,
    HostLegacyContentBlock,
    HostLegacyFeaturedItem,
    HostLegacyPage,
    HostSocialLink,
)
from app.memories.models import EventMemory
from app.reviews.models import VerifiedReview
from app.sponsorships.models import HostSponsorshipSettings, SponsorshipSlot
from app.users.models import User
from app.vault.models import VaultItem
from app.vault.service import serialize_item


def ensure_legacy_page(db: Session, host_id: UUID) -> HostLegacyPage:
    page = db.scalar(select(HostLegacyPage).where(HostLegacyPage.host_id == host_id))
    if page is None:
        page = HostLegacyPage(host_id=host_id)
        db.add(page)
        db.flush()
    ensure_default_blocks(db, host_id)
    ensure_contact_settings(db, host_id)
    return page


def ensure_contact_settings(db: Session, host_id: UUID) -> HostContactSettings:
    row = db.scalar(
        select(HostContactSettings).where(HostContactSettings.host_id == host_id)
    )
    if row is None:
        row = HostContactSettings(host_id=host_id, preference="none")
        db.add(row)
        db.flush()
    return row


def ensure_default_blocks(db: Session, host_id: UUID) -> list[HostLegacyContentBlock]:
    existing = list(
        db.scalars(
            select(HostLegacyContentBlock)
            .where(HostLegacyContentBlock.host_id == host_id)
            .order_by(HostLegacyContentBlock.sort_order.asc())
        ).all()
    )
    if existing:
        return existing

    created: list[HostLegacyContentBlock] = []
    for spec in DEFAULT_CONTENT_BLOCKS:
        block = HostLegacyContentBlock(host_id=host_id, **spec)
        db.add(block)
        created.append(block)
    db.flush()
    return created


def _serialize_block(block: HostLegacyContentBlock) -> dict[str, Any]:
    return {
        "id": block.id,
        "host_id": block.host_id,
        "block_type": block.block_type,
        "title_override": block.title_override,
        "description_override": block.description_override,
        "is_visible": block.is_visible,
        "sort_order": block.sort_order,
        "layout_style": block.layout_style,
        "source_type": block.source_type,
        "item_limit": block.item_limit,
        "config": block.config,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
    }


def _serialize_social(link: HostSocialLink) -> dict[str, Any]:
    return {
        "id": link.id,
        "host_id": link.host_id,
        "platform": link.platform,
        "url": link.url,
        "label": link.label,
        "sort_order": link.sort_order,
        "is_visible": link.is_visible,
        "created_at": link.created_at,
    }


def _serialize_contact(row: HostContactSettings, *, public: bool) -> dict[str, Any]:
    data = {
        "preference": row.preference,
        "show_contact_form": row.show_contact_form,
        "preferred_channel": row.preferred_channel,
        "note": row.note,
    }
    if not public or row.preference in {"email", "email_and_form"}:
        data["public_email"] = row.public_email
    else:
        data["public_email"] = None
    if not public:
        data["id"] = row.id
        data["host_id"] = row.host_id
        data["created_at"] = row.created_at
        data["updated_at"] = row.updated_at
    return data


def _serialize_featured(item: HostLegacyFeaturedItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "host_id": item.host_id,
        "item_type": item.item_type,
        "item_id": item.item_id,
        "placement": item.placement,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
    }


def _serialize_page_settings(page: HostLegacyPage) -> dict[str, Any]:
    return {
        "tagline": page.tagline,
        "primary_category_slug": page.primary_category_slug,
        "host_type_slug": page.host_type_slug,
        "service_areas": page.service_areas or [],
        "sponsorship_available": page.sponsorship_available,
        "sponsorship_note": page.sponsorship_note,
        "primary_cta_label": page.primary_cta_label,
        "primary_cta_type": page.primary_cta_type,
        "primary_cta_value": page.primary_cta_value,
        "secondary_cta_label": page.secondary_cta_label,
        "secondary_cta_type": page.secondary_cta_type,
        "secondary_cta_value": page.secondary_cta_value,
    }


def list_blocks(db: Session, host_id: UUID) -> list[dict[str, Any]]:
    ensure_default_blocks(db, host_id)
    rows = db.scalars(
        select(HostLegacyContentBlock)
        .where(HostLegacyContentBlock.host_id == host_id)
        .order_by(HostLegacyContentBlock.sort_order.asc())
    ).all()
    return [_serialize_block(r) for r in rows]


def get_block_for_host(
    db: Session, *, host_id: UUID, block_id: UUID
) -> HostLegacyContentBlock:
    block = db.get(HostLegacyContentBlock, block_id)
    if block is None or block.host_id != host_id:
        raise HTTPException(status_code=404, detail="Content block not found")
    return block


def create_block(
    db: Session,
    *,
    user: User,
    payload: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    host = require_user_host(db, user)
    ensure_legacy_page(db, host.id)
    block_type = payload.get("block_type")
    if block_type not in BLOCK_TYPES:
        raise HTTPException(status_code=400, detail="Invalid block_type")

    max_order = db.scalar(
        select(HostLegacyContentBlock.sort_order)
        .where(HostLegacyContentBlock.host_id == host.id)
        .order_by(HostLegacyContentBlock.sort_order.desc())
        .limit(1)
    )
    block = HostLegacyContentBlock(
        host_id=host.id,
        block_type=block_type,
        title_override=payload.get("title_override"),
        description_override=payload.get("description_override"),
        is_visible=bool(payload.get("is_visible", True)),
        sort_order=int(payload.get("sort_order", (max_order or 0) + 1)),
        layout_style=payload.get("layout_style") or "default",
        source_type=payload.get("source_type") or "automatic",
        item_limit=payload.get("item_limit"),
        config=payload.get("config"),
    )
    db.add(block)
    write_audit_log(
        db,
        action="legacy.block_create",
        actor_user_id=user.id,
        resource_type="host_legacy_content_block",
        resource_id=str(block.id),
        details={"block_type": block_type},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(block)
    return _serialize_block(block)


def update_block(
    db: Session,
    *,
    user: User,
    block_id: UUID,
    payload: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    host = require_user_host(db, user)
    block = get_block_for_host(db, host_id=host.id, block_id=block_id)
    for key in (
        "title_override",
        "description_override",
        "is_visible",
        "layout_style",
        "source_type",
        "item_limit",
        "config",
        "sort_order",
    ):
        if key in payload:
            setattr(block, key, payload[key])
    if "block_type" in payload and payload["block_type"] in BLOCK_TYPES:
        block.block_type = payload["block_type"]
    block.updated_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="legacy.block_update",
        actor_user_id=user.id,
        resource_type="host_legacy_content_block",
        resource_id=str(block.id),
        details=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(block)
    return _serialize_block(block)


def toggle_block(
    db: Session,
    *,
    user: User,
    block_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    host = require_user_host(db, user)
    block = get_block_for_host(db, host_id=host.id, block_id=block_id)
    block.is_visible = not block.is_visible
    block.updated_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="legacy.block_toggle",
        actor_user_id=user.id,
        resource_type="host_legacy_content_block",
        resource_id=str(block.id),
        details={"is_visible": block.is_visible, "block_type": block.block_type},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(block)
    return _serialize_block(block)


def reorder_blocks(
    db: Session,
    *,
    user: User,
    ordered_ids: list[UUID],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> list[dict[str, Any]]:
    host = require_user_host(db, user)
    ensure_default_blocks(db, host.id)
    blocks = {
        b.id: b
        for b in db.scalars(
            select(HostLegacyContentBlock).where(HostLegacyContentBlock.host_id == host.id)
        ).all()
    }
    if set(ordered_ids) != set(blocks.keys()):
        raise HTTPException(
            status_code=400,
            detail="Reorder payload must include every content block id exactly once",
        )
    for index, block_id in enumerate(ordered_ids):
        blocks[block_id].sort_order = index
        blocks[block_id].updated_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="legacy.block_reorder",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host.id),
        details={"ordered_ids": [str(i) for i in ordered_ids]},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return list_blocks(db, host.id)


def delete_block(
    db: Session,
    *,
    user: User,
    block_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    host = require_user_host(db, user)
    block = get_block_for_host(db, host_id=host.id, block_id=block_id)
    # Soft end-of-life: hide + archive flag in config rather than hard delete core defaults
    if block.block_type in {
        "about",
        "upcoming_events",
        "past_events",
        "verified_reviews",
        "vault_preview",
    }:
        block.is_visible = False
        cfg = dict(block.config or {})
        cfg["archived"] = True
        block.config = cfg
        block.updated_at = datetime.now(UTC)
        action = "legacy.block_archive"
    else:
        db.delete(block)
        action = "legacy.block_delete"
    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        resource_type="host_legacy_content_block",
        resource_id=str(block_id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()


def list_featured(db: Session, host_id: UUID) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(HostLegacyFeaturedItem)
        .where(HostLegacyFeaturedItem.host_id == host_id)
        .order_by(
            HostLegacyFeaturedItem.placement.asc(),
            HostLegacyFeaturedItem.sort_order.asc(),
        )
    ).all()
    return [_serialize_featured(r) for r in rows]


def _assert_item_belongs_to_host(
    db: Session, *, host_id: UUID, item_type: str, item_id: UUID
) -> None:
    if item_type == "event":
        row = db.get(Event, item_id)
        if row is None or row.host_id != host_id:
            raise HTTPException(status_code=400, detail="Event not found for this host")
    elif item_type == "review":
        row = db.get(VerifiedReview, item_id)
        if row is None or row.host_id != host_id or row.status != "visible":
            raise HTTPException(status_code=400, detail="Review not available to feature")
    elif item_type == "vault_item":
        row = db.get(VaultItem, item_id)
        if row is None or row.host_id != host_id:
            raise HTTPException(status_code=400, detail="Vault item not found for this host")
    elif item_type == "memory":
        row = db.get(EventMemory, item_id)
        if row is None or row.host_id != host_id:
            raise HTTPException(status_code=400, detail="Memory not found for this host")
    elif item_type == "sponsor_slot":
        row = db.get(SponsorshipSlot, item_id)
        if row is None or row.host_id != host_id:
            raise HTTPException(status_code=400, detail="Sponsor slot not found for this host")
    elif item_type == "media":
        return
    else:
        raise HTTPException(status_code=400, detail="Invalid item_type")


def upsert_featured(
    db: Session,
    *,
    user: User,
    payload: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    host = require_user_host(db, user)
    ensure_legacy_page(db, host.id)
    item_type = payload.get("item_type")
    placement = payload.get("placement")
    item_id = payload.get("item_id")
    if item_type not in FEATURED_ITEM_TYPES:
        raise HTTPException(status_code=400, detail="Invalid item_type")
    if placement not in FEATURED_PLACEMENTS:
        raise HTTPException(status_code=400, detail="Invalid placement")
    if item_id is None:
        raise HTTPException(status_code=400, detail="item_id is required")

    _assert_item_belongs_to_host(
        db, host_id=host.id, item_type=item_type, item_id=item_id
    )

    # Single featured slot for primary placements
    if placement.startswith("featured_"):
        existing = db.scalars(
            select(HostLegacyFeaturedItem).where(
                HostLegacyFeaturedItem.host_id == host.id,
                HostLegacyFeaturedItem.placement == placement,
            )
        ).all()
        for row in existing:
            db.delete(row)

    featured = HostLegacyFeaturedItem(
        host_id=host.id,
        item_type=item_type,
        item_id=item_id,
        placement=placement,
        sort_order=int(payload.get("sort_order") or 0),
    )
    db.add(featured)
    write_audit_log(
        db,
        action="legacy.featured_upsert",
        actor_user_id=user.id,
        resource_type="host_legacy_featured_item",
        resource_id=str(featured.id),
        details={"item_type": item_type, "placement": placement},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(featured)
    return _serialize_featured(featured)


def clear_featured_placement(
    db: Session,
    *,
    user: User,
    placement: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    host = require_user_host(db, user)
    rows = db.scalars(
        select(HostLegacyFeaturedItem).where(
            HostLegacyFeaturedItem.host_id == host.id,
            HostLegacyFeaturedItem.placement == placement,
        )
    ).all()
    for row in rows:
        db.delete(row)
    write_audit_log(
        db,
        action="legacy.featured_clear",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host.id),
        details={"placement": placement},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()


def replace_social_links(
    db: Session,
    *,
    host_id: UUID,
    links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing = db.scalars(
        select(HostSocialLink).where(HostSocialLink.host_id == host_id)
    ).all()
    for row in existing:
        db.delete(row)
    created: list[HostSocialLink] = []
    for index, link in enumerate(links):
        url = (link.get("url") or "").strip()
        platform = (link.get("platform") or "").strip().lower()
        if not url or not platform:
            continue
        row = HostSocialLink(
            host_id=host_id,
            platform=platform[:64],
            url=url[:500],
            label=(link.get("label") or None),
            sort_order=int(link.get("sort_order", index)),
            is_visible=bool(link.get("is_visible", True)),
        )
        db.add(row)
        created.append(row)
    db.flush()

    # Keep host_profiles.social_links in sync for older consumers
    host = db.get(Host, host_id)
    if host and host.profile is not None:
        merged = dict(host.profile.social_links or {})
        # Preserve niche_positioning
        niche = merged.get("niche_positioning")
        platform_map = {
            r.platform: r.url for r in created if r.is_visible
        }
        merged = {**platform_map}
        if niche:
            merged["niche_positioning"] = niche
        host.profile.social_links = merged or None
    return [_serialize_social(r) for r in created]


def update_contact_settings(
    db: Session,
    *,
    host_id: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = ensure_contact_settings(db, host_id)
    for key in (
        "preference",
        "public_email",
        "show_contact_form",
        "preferred_channel",
        "note",
    ):
        if key in payload:
            setattr(row, key, payload[key])
    row.updated_at = datetime.now(UTC)
    db.flush()
    return _serialize_contact(row, public=False)


def update_legacy_studio(
    db: Session,
    *,
    user: User,
    payload: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    host = require_user_host(db, user)
    page = ensure_legacy_page(db, host.id)

    profile_keys = {
        "display_name",
        "bio",
        "website",
        "city",
        "state",
        "country",
        "avatar_url",
        "cover_url",
        "host_type_slugs",
        "category_slugs",
        "audience_slugs",
        "primary_city_slug",
        "service_area_slugs",
        "niche_positioning",
    }
    profile_data = {k: payload[k] for k in profile_keys if k in payload}
    if profile_data:
        update_host_profile(
            db,
            user=user,
            payload=HostProfileUpdate.model_validate(profile_data),
        )
        # update_host_profile commits; re-bind host/page
        host = require_user_host(db, user)
        page = ensure_legacy_page(db, host.id)

    if "username" in payload and payload["username"]:
        new_slug = slugify(str(payload["username"]))
        if new_slug != host.slug:
            taken = db.scalar(
                select(Host.id).where(Host.slug == new_slug, Host.id != host.id)
            )
            if taken:
                raise HTTPException(status_code=409, detail="Username already taken")
            host.slug = new_slug

    page_keys = (
        "tagline",
        "primary_category_slug",
        "host_type_slug",
        "service_areas",
        "sponsorship_available",
        "sponsorship_note",
        "primary_cta_label",
        "primary_cta_type",
        "primary_cta_value",
        "secondary_cta_label",
        "secondary_cta_type",
        "secondary_cta_value",
    )
    for key in page_keys:
        if key in payload:
            setattr(page, key, payload[key])
    page.updated_at = datetime.now(UTC)

    if "social_links" in payload:
        links = payload["social_links"]
        if isinstance(links, dict):
            links = [
                {"platform": key, "url": value, "sort_order": index}
                for index, (key, value) in enumerate(links.items())
                if key != "niche_positioning" and isinstance(value, str)
            ]
        if isinstance(links, list):
            replace_social_links(db, host_id=host.id, links=links)

    if "contact" in payload and isinstance(payload["contact"], dict):
        update_contact_settings(db, host_id=host.id, payload=payload["contact"])

    write_audit_log(
        db,
        action="legacy.studio_update",
        actor_user_id=user.id,
        resource_type="host_legacy_page",
        resource_id=str(page.id),
        details={k: payload[k] for k in payload if k != "social_links"},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_host_legacy_studio(db, user)


def get_host_legacy_studio(db: Session, user: User) -> dict[str, Any]:
    host = require_user_host(db, user)
    return assemble_legacy_payload(db, host=host, public_only=False, user=user)


def get_public_legacy_by_username(
    db: Session, username: str, *, user: User | None = None
) -> dict[str, Any]:
    host = db.scalar(
        select(Host)
        .where(Host.slug == username.lower())
        .options(selectinload(Host.profile), selectinload(Host.verifications))
    )
    if host is None or host.status != "active":
        from app.core.http_errors import raise_not_found

        raise_not_found()
    return assemble_legacy_payload(db, host=host, public_only=True, user=user)


def _vault_item_is_publicly_previewable(item: VaultItem) -> bool:
    """Published, not removed/hidden — safe to teaser on Legacy."""
    if item.status != "published":
        return False
    if item.moderation_status == "removed":
        return False
    if item.access_rule and item.access_rule.access_type == "admin_hidden":
        return False
    return True


def _load_vault_items_by_ids(
    db: Session, *, host_id: UUID, item_ids: list[UUID]
) -> list[VaultItem]:
    """Load published Vault items in the given order (skips missing/invalid)."""
    if not item_ids:
        return []
    rows = db.scalars(
        select(VaultItem)
        .where(VaultItem.host_id == host_id, VaultItem.id.in_(item_ids))
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
    ).all()
    by_id = {row.id: row for row in rows}
    ordered: list[VaultItem] = []
    for item_id in item_ids:
        item = by_id.get(item_id)
        if item is not None and _vault_item_is_publicly_previewable(item):
            ordered.append(item)
    return ordered


def _vault_preview_cards(
    db: Session,
    *,
    host: Host,
    limit: int,
    featured_ids: list[UUID],
    source_type: str = "automatic",
    vault_item_ids: list[UUID] | None = None,
) -> list[dict[str, Any]]:
    """Build teaser-only Vault cards for Legacy. Never includes locked body/media."""
    featured_ids = list(featured_ids or [])
    featured_set = set(featured_ids)
    items: list[VaultItem] = []

    if source_type == "manual":
        ordered_ids = list(vault_item_ids or [])
        # Featured placement always surfaces first when configured
        for fid in reversed(featured_ids):
            if fid in ordered_ids:
                ordered_ids = [fid] + [i for i in ordered_ids if i != fid]
            else:
                ordered_ids.insert(0, fid)
        items = _load_vault_items_by_ids(db, host_id=host.id, item_ids=ordered_ids)
    else:
        if featured_ids:
            items.extend(
                _load_vault_items_by_ids(db, host_id=host.id, item_ids=featured_ids)
            )
        if len(items) < limit:
            rows = db.scalars(
                select(VaultItem)
                .where(
                    VaultItem.host_id == host.id,
                    VaultItem.status == "published",
                    VaultItem.moderation_status.in_(["none", "approved", "flagged"]),
                )
                .options(
                    selectinload(VaultItem.media), selectinload(VaultItem.access_rule)
                )
                .order_by(VaultItem.created_at.desc())
                .limit(limit)
            ).all()
            seen = {i.id for i in items}
            for row in rows:
                if row.id in seen or not _vault_item_is_publicly_previewable(row):
                    continue
                items.append(row)
                if len(items) >= limit:
                    break

    cards: list[dict[str, Any]] = []
    for item in items[:limit]:
        # Serialize as anonymous viewer so owner/entitled sessions never leak unlock state
        serialized = serialize_item(db, item, user=None, include_locked=False)
        access_type = (
            item.access_rule.access_type if item.access_rule else None
        )
        cards.append(
            {
                "id": serialized["id"],
                "title": serialized["title"],
                "slug": serialized["slug"],
                "cover_url": serialized["cover_url"],
                "preview_text": serialized["preview_text"],
                # Legacy Vault Preview is always a locked teaser surface
                "locked": True,
                "has_access": False,
                "featured": item.id in featured_set,
                "access_type": access_type,
                "content_type": serialized["content_type"],
                "price": serialized["price"],
                "currency": serialized["currency"],
                "share_path": f"/u/{host.slug}/vault/{serialized['slug']}",
            }
        )
    return cards


def _sponsor_preview(db: Session, *, host_id: UUID, limit: int) -> list[dict[str, Any]]:
    settings = db.scalar(
        select(HostSponsorshipSettings).where(HostSponsorshipSettings.host_id == host_id)
    )
    slots = db.scalars(
        select(SponsorshipSlot)
        .where(
            SponsorshipSlot.host_id == host_id,
            SponsorshipSlot.status == "published",
            SponsorshipSlot.moderation_status.in_(["none", "approved"]),
        )
        .order_by(SponsorshipSlot.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "price": s.price,
            "currency": s.currency,
            "slot_type": s.slot_type,
            "accepting_sponsors": bool(settings.accepting_sponsors) if settings else False,
        }
        for s in slots
    ]


def assemble_legacy_payload(
    db: Session,
    *,
    host: Host,
    public_only: bool,
    user: User | None = None,
) -> dict[str, Any]:
    """Assemble public or host-studio Legacy payload with content blocks."""
    from app.legacy.service import build_legacy_page

    # Reuse existing aggregation for events/reviews/memories/stats
    base = build_legacy_page(db, slug=host.slug)
    page = ensure_legacy_page(db, host.id)
    contact = ensure_contact_settings(db, host.id)
    blocks = list_blocks(db, host.id)
    featured = list_featured(db, host.id)
    social = [
        _serialize_social(r)
        for r in db.scalars(
            select(HostSocialLink)
            .where(HostSocialLink.host_id == host.id)
            .order_by(HostSocialLink.sort_order.asc())
        ).all()
        if (r.is_visible or not public_only)
    ]

    featured_by_placement: dict[str, list[UUID]] = {}
    for item in featured:
        featured_by_placement.setdefault(item["placement"], []).append(item["item_id"])

    all_blocks = blocks
    if public_only:
        blocks = [
            b
            for b in all_blocks
            if b["is_visible"] and not (b.get("config") or {}).get("archived")
        ]

    visible_types = {b["block_type"] for b in blocks}
    reviews_hidden = "verified_reviews" not in visible_types

    # Apply per-block limits / featured ordering for list sections
    for block in blocks:
        limit = block.get("item_limit")
        btype = block["block_type"]
        if btype == "upcoming_events" and limit:
            featured_ids = featured_by_placement.get("featured_upcoming_event", [])
            events = list(base["upcoming_events"])
            if featured_ids and block.get("source_type") in {"manual", "automatic"}:
                featured_events = [e for e in events if e["id"] in featured_ids]
                rest = [e for e in events if e["id"] not in featured_ids]
                events = featured_events + rest
            base["upcoming_events"] = events[: int(limit)]
        elif btype == "past_events" and limit:
            featured_ids = featured_by_placement.get("featured_past_event", [])
            events = list(base["past_events"])
            if featured_ids:
                featured_events = [e for e in events if e["id"] in featured_ids]
                rest = [e for e in events if e["id"] not in featured_ids]
                events = featured_events + rest
            base["past_events"] = events[: int(limit)]
        elif btype == "event_memories" and limit:
            memories = list(base.get("event_memories") or [])
            featured_ids = featured_by_placement.get("featured_memory", [])
            if featured_ids:
                featured_m = [m for m in memories if m["id"] in featured_ids]
                rest = [m for m in memories if m["id"] not in featured_ids]
                memories = featured_m + rest
            base["event_memories"] = memories[: int(limit)]
        elif btype == "verified_reviews" and limit:
            reviews = list(base["reviews"])
            featured_ids = set(featured_by_placement.get("featured_review", []))
            if featured_ids:
                def _rid(r: Any) -> UUID:
                    return r["id"] if isinstance(r, dict) else r.id

                featured_r = [r for r in reviews if _rid(r) in featured_ids]
                rest = [r for r in reviews if _rid(r) not in featured_ids]
                reviews = featured_r + rest
            # Never filter by rating — hosts cannot hide negative reviews via limits alone
            base["reviews"] = reviews[: int(limit)]

    vault_limit = 3
    vault_source = "automatic"
    vault_item_ids: list[UUID] = []
    for block in blocks:
        if block["block_type"] != "vault_preview":
            continue
        if block.get("item_limit"):
            vault_limit = int(block["item_limit"])
        vault_source = block.get("source_type") or "automatic"
        raw_ids = (block.get("config") or {}).get("vault_item_ids") or []
        for raw in raw_ids:
            try:
                vault_item_ids.append(UUID(str(raw)))
            except (TypeError, ValueError):
                continue
        break

    vault_preview = _vault_preview_cards(
        db,
        host=host,
        limit=vault_limit,
        featured_ids=featured_by_placement.get("featured_vault_item", []),
        source_type=vault_source,
        vault_item_ids=vault_item_ids,
    )

    sponsor_limit = 3
    for block in blocks:
        if block["block_type"] == "sponsor_packages" and block.get("item_limit"):
            sponsor_limit = int(block["item_limit"])
            break
    sponsor_packages = _sponsor_preview(db, host_id=host.id, limit=sponsor_limit)

    settings = _serialize_page_settings(page)
    sponsor_settings = db.scalar(
        select(HostSponsorshipSettings).where(HostSponsorshipSettings.host_id == host.id)
    )
    if (
        sponsor_settings is not None
        and page.sponsorship_available is False
        and sponsor_settings.accepting_sponsors
    ):
        settings["sponsorship_available"] = True

    if public_only:
        if "upcoming_events" not in visible_types:
            base["upcoming_events"] = []
        if "past_events" not in visible_types:
            base["past_events"] = []
        if "event_memories" not in visible_types:
            base["event_memories"] = []
        if "verified_reviews" not in visible_types:
            base["reviews"] = []
        if "vault_preview" not in visible_types:
            vault_preview = []
        if "sponsor_packages" not in visible_types:
            sponsor_packages = []
        if "about" not in visible_types:
            base["about"] = None

    return {
        **base,
        "tagline": page.tagline,
        "settings": settings,
        "content_blocks": blocks,
        "featured_items": (
            featured
            if not public_only
            else [
                {
                    "item_type": f["item_type"],
                    "item_id": f["item_id"],
                    "placement": f["placement"],
                    "sort_order": f["sort_order"],
                }
                for f in featured
            ]
        ),
        "social_links": social,
        "contact": _serialize_contact(contact, public=public_only),
        "vault_preview": vault_preview,
        "sponsor_packages": sponsor_packages,
        "reviews_block_hidden": reviews_hidden and public_only,
        "trust_note": (
            "Verified reviews remain on Pàdéyá even when a host hides the Reviews block."
            if reviews_hidden and public_only
            else None
        ),
    }
