"""Catalog CRUD and serialization for event merch."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.checkins.permissions import can_scan_event, is_event_staff
from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.team_access import (
    require_host_event_permission,
    require_host_for_permission,
)
from app.merch.constants import (
    ACCESS_TYPES,
    PRODUCT_STATUSES,
    PRODUCT_TYPES,
    STOREFRONT_VISIBILITIES,
    VARIANT_STATUSES,
)
from app.merch.content_safety import assert_public_merch_copy_safe
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.merch.privacy import public_pickup_fields
from app.merch.schemas import (
    MerchProductCreate,
    MerchProductUpdate,
    MerchVariantCreate,
    MerchVariantUpdate,
)
from app.users.models import User
from app.users.service import user_has_permission, user_has_role
from app.vault.models import VaultItem

_ACCESS_TYPE_SET = frozenset(ACCESS_TYPES)


def _normalize_access_type(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    if cleaned not in _ACCESS_TYPE_SET:
        raise HTTPException(
            status_code=400,
            detail=f"required_access_type must be one of: {', '.join(ACCESS_TYPES)}",
        )
    return cleaned


def _resolve_host_vault_item(
    db: Session, *, host_id: uuid.UUID, vault_item_id: uuid.UUID | None
) -> uuid.UUID | None:
    if vault_item_id is None:
        return None
    item = db.get(VaultItem, vault_item_id)
    if item is None or item.host_id != host_id:
        raise HTTPException(status_code=400, detail="Invalid Vault item for this host")
    return item.id


def _apply_vault_access_fields(
    product: EventMerchProduct,
    *,
    db: Session,
    is_vault_exclusive: bool | None = None,
    requires_vault_access: bool | None = None,
    required_vault_item_id: uuid.UUID | None | object = ...,
    required_access_type: str | None | object = ...,
    requires_check_in: bool | None = None,
    storefront_visibility: str | None = None,
    post_event_drop_at: datetime | None | object = ...,
) -> None:
    """Keep is_vault_exclusive / requires_vault_access aligned; validate access fields."""
    if is_vault_exclusive is not None:
        product.is_vault_exclusive = bool(is_vault_exclusive)
    if requires_vault_access is not None:
        product.requires_vault_access = bool(requires_vault_access)
    # Consistency: exclusive implies vault access gate.
    if product.is_vault_exclusive:
        product.requires_vault_access = True
    elif is_vault_exclusive is False:
        product.requires_vault_access = False

    if required_access_type is not ...:
        product.required_access_type = _normalize_access_type(
            required_access_type if isinstance(required_access_type, str) or required_access_type is None else None
        )

    if required_vault_item_id is not ...:
        product.required_vault_item_id = _resolve_host_vault_item(
            db,
            host_id=product.host_id,
            vault_item_id=required_vault_item_id
            if isinstance(required_vault_item_id, uuid.UUID) or required_vault_item_id is None
            else None,
        )

    if requires_check_in is not None:
        product.requires_check_in = bool(requires_check_in)
        if product.requires_check_in and product.required_access_type is None:
            # Soft default — checked-in gate without forcing vault exclusive.
            pass

    if storefront_visibility is not None:
        vis = storefront_visibility.strip().lower()
        if vis not in STOREFRONT_VISIBILITIES:
            raise HTTPException(
                status_code=400,
                detail=(
                    "storefront_visibility must be one of: "
                    f"{', '.join(STOREFRONT_VISIBILITIES)}"
                ),
            )
        product.storefront_visibility = vis
    elif product.is_vault_exclusive and product.storefront_visibility == "event_only":
        product.storefront_visibility = "vault_exclusive"

    if post_event_drop_at is not ...:
        product.post_event_drop_at = (
            post_event_drop_at if isinstance(post_event_drop_at, datetime) or post_event_drop_at is None else None
        )


def _normalize_product_type(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "tshirt": "t_shirt",
        "tee": "t_shirt",
        "facemask": "face_mask",
        "mask": "face_mask",
        "totebag": "tote_bag",
        "vip": "vip_pack",
        "vippack": "vip_pack",
    }
    cleaned = aliases.get(cleaned, cleaned)
    if cleaned not in PRODUCT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid product_type — use one of: {', '.join(PRODUCT_TYPES)}",
        )
    return cleaned


def available_variant_stock(variant: EventMerchVariant) -> int:
    """Units free to reserve (inventory minus open checkout holds)."""
    reserved = int(getattr(variant, "reserved_quantity", 0) or 0)
    return max(0, int(variant.inventory_count) - reserved)


def sync_variant_sold_out(variant: EventMerchVariant) -> bool:
    """Keep sold_out status in sync. Returns True if status newly became sold_out."""
    if variant.status == "archived":
        return False
    if available_variant_stock(variant) <= 0 and int(variant.inventory_count) <= 0:
        if variant.status == "active":
            variant.status = "sold_out"
            return True
    elif variant.status == "sold_out" and available_variant_stock(variant) > 0:
        variant.status = "active"
    return False


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "merch"


def unique_product_slug(db: Session, *, event_id: uuid.UUID, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    i = 2
    while db.scalar(
        select(EventMerchProduct.id).where(
            EventMerchProduct.event_id == event_id,
            EventMerchProduct.slug == candidate,
        )
    ):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def _require_event_for_host(db: Session, *, host_id: uuid.UUID, event_id: uuid.UUID) -> Event:
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def can_manage_event_merch(
    db: Session,
    user: User,
    event_id: uuid.UUID | None,
    *,
    permission: str | tuple[str, ...] = (
        "merch.create",
        "merch.edit",
        "merch.manage_inventory",
        "merch.manage_discounts",
        "merch.manage_bundles",
        "merch.manage_shipping",
    ),
) -> bool:
    """Host owner or team member with merch catalog permission on the event.

    When event_id is None (standalone host merch), falls back to host-wide permission.
    """
    if event_id is None:
        return False
    if user_has_role(user, "super_admin") or user_has_permission(user, "admin.full_access"):
        return True
    from app.teams.permissions import has_event_permission, is_host_owner

    event = db.get(Event, event_id)
    if event is None:
        return False
    if is_host_owner(db, user.id, event.host_id):
        return True
    keys = (permission,) if isinstance(permission, str) else tuple(permission)
    return any(
        has_event_permission(db, user.id, event.host_id, event_id, key)
        for key in keys
    )


def can_manage_host_merch(
    db: Session,
    user: User,
    host_id: uuid.UUID,
    *,
    permission: str | tuple[str, ...] = (
        "merch.create",
        "merch.edit",
        "merch.manage_inventory",
    ),
) -> bool:
    """Host owner or team member with host-wide merch permission (standalone shop)."""
    if user_has_role(user, "super_admin") or user_has_permission(user, "admin.full_access"):
        return True
    from app.hosts.team_access import require_host_for_permission
    from app.teams.permissions import is_host_owner

    if is_host_owner(db, user.id, host_id):
        return True
    keys = (permission,) if isinstance(permission, str) else tuple(permission)
    for key in keys:
        try:
            require_host_for_permission(
                db, user=user, host_id=host_id, permission=key
            )
            return True
        except Exception:
            continue
    return False


def can_manage_product_merch(
    db: Session,
    user: User,
    product: EventMerchProduct,
    *,
    permission: str | tuple[str, ...] = "merch.edit",
) -> bool:
    if product.event_id is not None:
        return can_manage_event_merch(
            db, user, product.event_id, permission=permission
        )
    return can_manage_host_merch(
        db, user, product.host_id, permission=permission
    )


def _host_wide_merch_desk(db: Session, user: User, event_id: uuid.UUID) -> bool:
    from app.events.models import Event
    from app.teams.permissions import can_scan_merch_pickup, has_event_permission

    event = db.get(Event, event_id)
    if event is None:
        return False
    if can_scan_merch_pickup(
        db,
        user_id=user.id,
        host_profile_id=event.host_id,
        event_id=event_id,
    ):
        return True
    return has_event_permission(
        db,
        user_id=user.id,
        host_profile_id=event.host_id,
        event_id=event_id,
        permission="merch.view",
    )


def _assigned_to_event_desk(db: Session, user: User, event_id: uuid.UUID) -> bool:
    """Staff may access desk via host-wide team perm, scan auth, or event assignment."""
    if _host_wide_merch_desk(db, user, event_id):
        return True
    if can_scan_event(db, user, event_id):
        return True
    return is_event_staff(db, user_id=user.id, event_id=event_id)


def can_view_event_merch_fulfillments(
    db: Session, user: User, event_id: uuid.UUID
) -> bool:
    """Host owner, host-wide team desk, or staff with merch view/fulfill + desk access."""
    if can_manage_event_merch(db, user, event_id):
        return True
    if _host_wide_merch_desk(db, user, event_id):
        return True
    if not (
        user_has_permission(user, "merch.view_fulfillment")
        or user_has_permission(user, "merch.fulfill")
    ):
        return False
    return _assigned_to_event_desk(db, user, event_id)


def can_fulfill_event_merch(db: Session, user: User, event_id: uuid.UUID) -> bool:
    """Confirm pickup / desk notes — never grants catalog edit.

    Allow:
    - host owner with ``merch.manage_own`` (catalog owner)
    - hybrid merch desk (``merch.scan_pickup_qr`` / ``merch.mark_picked_up``
      via host team or ``merch_pickup`` / ``event_ops`` staff)
    - global RBAC ``merch.fulfill`` when assigned to the event desk
      (legacy ``host_staff`` + check-in staff assignment)
    """
    if can_manage_event_merch(db, user, event_id):
        return True
    from app.events.models import Event
    from app.teams.permissions import can_scan_merch_pickup, has_event_permission

    event = db.get(Event, event_id)
    if event is None:
        return False
    if can_scan_merch_pickup(
        db,
        user_id=user.id,
        host_profile_id=event.host_id,
        event_id=event_id,
    ):
        return True
    # Team desk: fulfill without catalog create/edit/inventory.
    if any(
        has_event_permission(db, user.id, event.host_id, event_id, key)
        for key in (
            "merch.mark_picked_up",
            "merch.fulfill_orders",
            "merch.scan_pickup_qr",
        )
    ):
        return True
    # RBAC desk role (host_staff): merch.fulfill without merch.manage_own / host ownership.
    if user_has_permission(user, "merch.fulfill") and _assigned_to_event_desk(
        db, user, event_id
    ):
        return True
    return False


def can_reveal_shipping_address(db: Session, user: User, event_id: uuid.UUID) -> bool:
    """Full decrypted shipping address — owner or ``merch.manage_shipping`` only."""
    if can_manage_event_merch(db, user, event_id):
        return True
    from app.events.models import Event
    from app.teams.permissions import has_event_permission

    event = db.get(Event, event_id)
    if event is None:
        return False
    return has_event_permission(
        db,
        user.id,
        event.host_id,
        event_id,
        "merch.manage_shipping",
    )


def effective_variant_price(product: EventMerchProduct, variant: EventMerchVariant) -> Decimal:
    if variant.price is not None:
        return Decimal(variant.price)
    return Decimal(product.base_price)


def serialize_variant(product: EventMerchProduct, variant: EventMerchVariant) -> dict:
    reserved = int(getattr(variant, "reserved_quantity", 0) or 0)
    sold = int(getattr(variant, "sold_quantity", 0) or 0)
    return {
        "id": variant.id,
        "product_id": variant.product_id,
        "label": variant.label,
        "name": variant.label,  # plan alias
        "sku": variant.sku,
        "size": variant.size,
        "color": variant.color,
        "option_1_name": getattr(variant, "option_1_name", None),
        "option_1_value": getattr(variant, "option_1_value", None),
        "option_2_name": getattr(variant, "option_2_name", None),
        "option_2_value": getattr(variant, "option_2_value", None),
        "price": variant.price,
        "price_override": variant.price,  # plan alias
        "effective_price": effective_variant_price(product, variant),
        "inventory_count": variant.inventory_count,
        "stock_quantity": variant.inventory_count,  # plan alias (available unsold)
        "reserved_quantity": reserved,
        "sold_quantity": sold,
        "available_quantity": available_variant_stock(variant),
        "status": variant.status,
        "print_on_demand_variant_ref": getattr(
            variant, "print_on_demand_variant_ref", None
        ),
        "archived_at": variant.archived_at,
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
    }


def serialize_product(
    product: EventMerchProduct, *, event_title: str | None = None
) -> dict:
    variants = [serialize_variant(product, v) for v in (product.variants or [])]
    return {
        "id": product.id,
        "event_id": product.event_id,
        "host_id": product.host_id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "short_description": getattr(product, "short_description", None),
        "product_type": getattr(product, "product_type", None),
        "base_price": product.base_price,
        "currency": product.currency,
        "image_url": product.image_url,
        "cover_image_url": product.image_url,  # plan alias
        "gallery_urls": getattr(product, "gallery_urls", None) or [],
        "status": product.status,
        "sales_start_at": getattr(product, "sales_start_at", None),
        "sales_end_at": getattr(product, "sales_end_at", None),
        "pickup_instructions": product.pickup_instructions,
        "pickup_location_label": getattr(product, "pickup_location_label", None),
        "pickup_time_window": getattr(product, "pickup_time_window", None),
        "fulfillment_notes": getattr(product, "fulfillment_notes", None),
        "show_on_event_page": bool(getattr(product, "show_on_event_page", True)),
        "is_featured": bool(getattr(product, "is_featured", False)),
        "requires_ticket": bool(getattr(product, "requires_ticket", False)),
        "pickup_enabled": bool(getattr(product, "pickup_enabled", True)),
        "shipping_enabled": bool(getattr(product, "shipping_enabled", False)),
        "print_on_demand_enabled": bool(
            getattr(product, "print_on_demand_enabled", False)
        ),
        "max_per_order": product.max_per_order,
        "max_per_buyer": getattr(product, "max_per_buyer", None),
        "restock_on_refund": product.restock_on_refund,
        "size_chart_id": getattr(product, "size_chart_id", None),
        "moderation_status": getattr(product, "moderation_status", None) or "clear",
        "moderation_note": getattr(product, "moderation_note", None),
        "moderated_at": getattr(product, "moderated_at", None),
        "archived_at": product.archived_at,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "variants": variants,
        "variant_count": len([v for v in variants if v["status"] != "archived"]),
        "total_inventory": sum(
            v["available_quantity"] for v in variants if v["status"] != "archived"
        ),
        "sold_count": sum(int(v["sold_quantity"] or 0) for v in variants),
        "price_min": min((v["effective_price"] for v in variants), default=product.base_price),
        "price_max": max((v["effective_price"] for v in variants), default=product.base_price),
        "event_title": event_title,
        "is_sponsor_branded": bool(getattr(product, "is_sponsor_branded", False)),
        "sponsor_id": getattr(product, "sponsor_id", None),
        "sponsor_brand_name": getattr(product, "sponsor_brand_name", None),
        "sponsor_logo_url": getattr(product, "sponsor_logo_url", None),
        "sponsor_description": getattr(product, "sponsor_description", None),
        "sponsor_split_type": getattr(product, "sponsor_split_type", None),
        "sponsor_split_value": getattr(product, "sponsor_split_value", None),
        "is_vault_exclusive": bool(getattr(product, "is_vault_exclusive", False)),
        "requires_vault_access": bool(
            getattr(product, "requires_vault_access", False)
            or getattr(product, "is_vault_exclusive", False)
        ),
        "required_vault_item_id": getattr(product, "required_vault_item_id", None),
        "required_access_type": getattr(product, "required_access_type", None),
        "requires_check_in": bool(getattr(product, "requires_check_in", False)),
        "requires_vip": bool(getattr(product, "requires_vip", False)),
        "is_event_linked": bool(getattr(product, "is_event_linked", True)),
        "storefront_visibility": getattr(product, "storefront_visibility", None)
        or "event_only",
        "post_event_drop_at": getattr(product, "post_event_drop_at", None),
        "is_post_event_drop": getattr(product, "storefront_visibility", None)
        == "post_event_drop",
        "marketplace_kind": getattr(product, "marketplace_kind", None),
        "category": getattr(product, "category", None),
        "tags": list(getattr(product, "tags", None) or []),
        "marketplace_listed": bool(getattr(product, "marketplace_listed", True)),
    }


def _sales_window_open(product: EventMerchProduct, *, now: datetime | None = None) -> bool:
    moment = now or datetime.now(UTC)
    start = getattr(product, "sales_start_at", None)
    end = getattr(product, "sales_end_at", None)
    if start is not None and moment < start:
        return False
    if end is not None and moment > end:
        return False
    return True


def serialize_catalog_product(
    product: EventMerchProduct,
    *,
    event: Event | None = None,
    db: Session | None = None,
    buyer_user_id: uuid.UUID | None = None,
) -> dict:
    from app.merch.access import (
        buyer_eligible_for_product,
        product_is_drop_live,
        product_requires_vault_gate,
        public_teaser_fields,
    )

    eligible = True
    reason: str | None = None
    if db is not None:
        eligible, reason = buyer_eligible_for_product(
            db, product=product, buyer_user_id=buyer_user_id
        )
    teaser = public_teaser_fields(product, eligible=eligible)
    locked = bool(teaser.get("access_locked") or teaser.get("teaser_only"))
    vault_locked = locked and product_requires_vault_gate(product)

    drop_live = product_is_drop_live(product)
    is_drop = product.storefront_visibility == "post_event_drop"
    sellable = []
    if not vault_locked:
        sellable = [
            serialize_variant(product, v)
            for v in (product.variants or [])
            if v.status == "active"
            and v.archived_at is None
            and available_variant_stock(v) > 0
        ]
        # Upcoming post-event drops still surface as teasers.
        if not sellable and is_drop and not drop_live:
            sellable = [
                serialize_variant(product, v)
                for v in (product.variants or [])
                if v.status == "active" and v.archived_at is None
            ]
            for row in sellable:
                row["available_quantity"] = None
                row["inventory_count"] = None
                row["stock_quantity"] = None
                row["sku"] = None
    pickup = (
        public_pickup_fields(product, event)
        if not vault_locked
        else {
            "pickup_location_label": None,
            "pickup_time_window": None,
            "pickup_instructions": None,
            "fulfillment_notes": None,
        }
    )
    size_chart = None
    if db is not None and not vault_locked:
        from app.merch.size_charts import get_public_chart

        size_chart = get_public_chart(db, getattr(product, "size_chart_id", None))

    description = product.description
    short_description = getattr(product, "short_description", None)
    gallery_urls = list(getattr(product, "gallery_urls", None) or [])
    if vault_locked:
        description = short_description or "Exclusive merch for Vault members."
        short_description = description
        gallery_urls = []

    availability = "purchasable"
    if not drop_live:
        availability = "coming_soon"
    elif locked:
        availability = "locked"
    elif not sellable and not product.print_on_demand_enabled:
        availability = "sold_out"

    return {
        "id": product.id,
        "event_id": product.event_id,
        "name": product.name,
        "slug": product.slug,
        "description": description,
        "short_description": short_description,
        "product_type": getattr(product, "product_type", None),
        "base_price": product.base_price,
        "currency": product.currency,
        "image_url": product.image_url,
        "cover_image_url": product.image_url,
        "gallery_urls": gallery_urls,
        "show_on_event_page": bool(getattr(product, "show_on_event_page", True)),
        "is_featured": bool(getattr(product, "is_featured", False)),
        "requires_ticket": bool(getattr(product, "requires_ticket", False)),
        "requires_check_in": bool(getattr(product, "requires_check_in", False)),
        "requires_vip": bool(getattr(product, "requires_vip", False)),
        "pickup_enabled": bool(getattr(product, "pickup_enabled", True)) and not vault_locked,
        "shipping_enabled": bool(getattr(product, "shipping_enabled", False))
        and not vault_locked,
        "pickup_location_label": pickup["pickup_location_label"],
        "pickup_time_window": pickup["pickup_time_window"],
        "pickup_instructions": pickup["pickup_instructions"],
        "max_per_order": product.max_per_order,
        "max_per_buyer": getattr(product, "max_per_buyer", None),
        "is_sponsor_branded": bool(getattr(product, "is_sponsor_branded", False)),
        "sponsor_brand_name": (
            getattr(product, "sponsor_brand_name", None)
            if getattr(product, "is_sponsor_branded", False)
            else None
        ),
        "sponsor_logo_url": (
            getattr(product, "sponsor_logo_url", None)
            if getattr(product, "is_sponsor_branded", False)
            else None
        ),
        "sponsor_description": (
            None
            if vault_locked
            else (
                getattr(product, "sponsor_description", None)
                if getattr(product, "is_sponsor_branded", False)
                else None
            )
        ),
        "is_vault_exclusive": bool(getattr(product, "is_vault_exclusive", False)),
        "requires_vault_access": bool(
            getattr(product, "requires_vault_access", False)
            or getattr(product, "is_vault_exclusive", False)
        ),
        "required_access_type": getattr(product, "required_access_type", None),
        "required_vault_item_id": None if vault_locked else product.required_vault_item_id,
        "storefront_visibility": product.storefront_visibility,
        "is_event_linked": bool(product.is_event_linked),
        "is_post_event_drop": is_drop,
        "post_event_drop_at": product.post_event_drop_at,
        "access_eligible": eligible,
        "access_reason": reason if not eligible else None,
        "access_locked": teaser.get("access_locked", False),
        "teaser_only": teaser.get("teaser_only", False),
        "access_label": teaser.get("access_label"),
        "access_requirements": teaser.get("access_requirements") or [],
        "unlock_hint": teaser.get("unlock_hint"),
        "availability": availability,
        "is_drop_live": drop_live,
        "variants": sellable,
        "size_chart": size_chart,
    }


def _load_product(db: Session, product_id: uuid.UUID) -> EventMerchProduct | None:
    return db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product_id)
        .options(selectinload(EventMerchProduct.variants))
    )


def list_host_products(db: Session, *, user: User, event_id: uuid.UUID) -> list[dict]:
    if not can_manage_event_merch(db, user, event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage merch for this event")
    event = db.get(Event, event_id)
    title = event.title if event else None
    rows = db.scalars(
        select(EventMerchProduct)
        .where(
            EventMerchProduct.event_id == event_id,
            EventMerchProduct.archived_at.is_(None),
        )
        .options(selectinload(EventMerchProduct.variants))
        .order_by(EventMerchProduct.created_at.desc())
    ).all()
    return [serialize_product(p, event_title=title) for p in rows]


def list_all_host_products(db: Session, *, user: User) -> list[dict]:
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=None,
        permission=(
            "merch.view",
            "merch.create",
            "merch.edit",
            "merch.manage_inventory",
        ),
    )
    rows = db.scalars(
        select(EventMerchProduct)
        .where(
            EventMerchProduct.host_id == host.id,
            EventMerchProduct.archived_at.is_(None),
        )
        .options(selectinload(EventMerchProduct.variants))
        .order_by(EventMerchProduct.created_at.desc())
    ).all()
    event_ids = {p.event_id for p in rows}
    titles: dict[uuid.UUID, str] = {}
    if event_ids:
        for event in db.scalars(select(Event).where(Event.id.in_(event_ids))).all():
            titles[event.id] = event.title
    return [
        serialize_product(p, event_title=titles.get(p.event_id)) for p in rows
    ]


def get_host_product(db: Session, *, user: User, product_id: uuid.UUID) -> dict:
    product = _load_product(db, product_id)
    if product is None or product.archived_at is not None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_manage_event_merch(db, user, product.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage this product")
    event = db.get(Event, product.event_id)
    return serialize_product(product, event_title=event.title if event else None)


def get_public_catalog_by_slug(
    db: Session,
    *,
    event_slug: str,
    buyer_user_id: uuid.UUID | None = None,
) -> list[dict]:
    event = db.scalar(select(Event).where(Event.slug == event_slug))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return get_public_catalog(
        db, event_id=event.id, buyer_user_id=buyer_user_id
    )


def get_public_catalog_product_by_slug(
    db: Session,
    *,
    event_slug: str,
    product_slug: str,
    buyer_user_id: uuid.UUID | None = None,
) -> dict:
    catalog = get_public_catalog_by_slug(
        db, event_slug=event_slug, buyer_user_id=buyer_user_id
    )
    for row in catalog:
        if row.get("slug") == product_slug or str(row.get("id")) == product_slug:
            return row
    raise HTTPException(status_code=404, detail="Product not found")


def get_public_catalog(
    db: Session,
    *,
    event_id: uuid.UUID,
    buyer_user_id: uuid.UUID | None = None,
) -> list[dict]:
    from app.hosts.models import Host
    from app.merch.access import product_is_drop_live, product_requires_vault_gate
    from app.merch.constants import UNSAFE_EVENT_STATUSES, UNSAFE_HOST_STATUSES

    event = db.get(Event, event_id)
    # Completed events keep a catalog surface for post-event drops.
    if event is None or event.status not in {"published", "completed"}:
        raise HTTPException(status_code=404, detail="Event not found")
    host = db.get(Host, event.host_id)
    if host is not None and host.status in UNSAFE_HOST_STATUSES:
        return []
    if event.status in UNSAFE_EVENT_STATUSES:
        return []

    rows = db.scalars(
        select(EventMerchProduct)
        .where(
            EventMerchProduct.event_id == event_id,
            EventMerchProduct.status == "active",
            EventMerchProduct.archived_at.is_(None),
            EventMerchProduct.moderation_status.in_(("clear", "flagged")),
        )
        .options(selectinload(EventMerchProduct.variants))
        .order_by(
            EventMerchProduct.is_featured.desc(),
            EventMerchProduct.name.asc(),
        )
    ).all()
    catalog = []
    for product in rows:
        # Flagged stays visible until admin hides; hidden/removed never public.
        if getattr(product, "moderation_status", "clear") in {"hidden", "removed"}:
            continue
        is_drop = product.storefront_visibility == "post_event_drop"
        if not _sales_window_open(product):
            if not (is_drop and not product_is_drop_live(product)):
                continue
        row = serialize_catalog_product(
            product, event=event, db=db, buyer_user_id=buyer_user_id
        )
        # Locked Vault / scheduled drop teasers stay visible without sellable variants.
        if row["variants"] or product_requires_vault_gate(product) or is_drop:
            catalog.append(row)
    return catalog


def create_product(
    db: Session, *, user: User, event_id: uuid.UUID, payload: MerchProductCreate
) -> dict:
    from app.users.restrictions import assert_can_manage_merch

    assert_can_manage_merch(db, user)

    host, event = require_host_event_permission(
        db, user=user, event_id=event_id, permission="merch.create"
    )
    if payload.status not in PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid product status")

    name = payload.name.strip()
    description = (payload.description or "").strip() or None
    short_description = (payload.short_description or "").strip() or None
    pickup_instructions = (payload.pickup_instructions or "").strip() or None
    pickup_location_label = (payload.pickup_location_label or "").strip() or None
    pickup_time_window = (payload.pickup_time_window or "").strip() or None
    sponsor_brand_name = (payload.sponsor_brand_name or "").strip() or None
    sponsor_logo_url = (payload.sponsor_logo_url or "").strip() or None
    sponsor_description = (payload.sponsor_description or "").strip() or None
    # Public-facing copy only — desk notes stay host-private and are not filtered here.
    assert_public_merch_copy_safe(
        name=name,
        description=description,
        short_description=short_description,
        pickup_instructions=pickup_instructions,
        pickup_location_label=pickup_location_label,
        pickup_time_window=pickup_time_window,
        sponsor_brand_name=sponsor_brand_name,
        sponsor_description=sponsor_description,
    )

    from app.merch.size_charts import require_host_chart

    size_chart_id = None
    if payload.size_chart_id is not None:
        size_chart_id = require_host_chart(
            db, host_id=host.id, chart_id=payload.size_chart_id
        ).id

    cover = (payload.cover_image_url or payload.image_url or "").strip() or None
    branded = bool(payload.is_sponsor_branded)
    product = EventMerchProduct(
        event_id=event.id,
        host_id=host.id,
        name=name,
        slug=unique_product_slug(db, event_id=event.id, base=payload.name),
        description=description,
        short_description=short_description,
        product_type=_normalize_product_type(payload.product_type),
        base_price=payload.base_price,
        currency=(payload.currency or "NGN").upper(),
        image_url=cover,
        gallery_urls=list(payload.gallery_urls or []) or None,
        status=payload.status,
        sales_start_at=payload.sales_start_at,
        sales_end_at=payload.sales_end_at,
        pickup_instructions=pickup_instructions,
        pickup_location_label=pickup_location_label,
        pickup_time_window=pickup_time_window,
        fulfillment_notes=(payload.fulfillment_notes or "").strip() or None,
        show_on_event_page=bool(payload.show_on_event_page),
        is_featured=bool(payload.is_featured),
        requires_ticket=bool(payload.requires_ticket),
        pickup_enabled=bool(payload.pickup_enabled),
        shipping_enabled=bool(payload.shipping_enabled),
        print_on_demand_enabled=bool(payload.print_on_demand_enabled),
        max_per_order=payload.max_per_order,
        max_per_buyer=payload.max_per_buyer,
        restock_on_refund=payload.restock_on_refund,
        size_chart_id=size_chart_id,
        is_sponsor_branded=branded,
        sponsor_id=payload.sponsor_id if branded else None,
        sponsor_brand_name=sponsor_brand_name if branded else None,
        sponsor_logo_url=sponsor_logo_url if branded else None,
        sponsor_description=sponsor_description if branded else None,
        sponsor_split_type=payload.sponsor_split_type if branded else None,
        sponsor_split_value=payload.sponsor_split_value if branded else None,
    )
    _apply_vault_access_fields(
        product,
        db=db,
        is_vault_exclusive=bool(payload.is_vault_exclusive),
        requires_vault_access=bool(
            payload.requires_vault_access or payload.is_vault_exclusive
        ),
        required_vault_item_id=payload.required_vault_item_id,
        required_access_type=payload.required_access_type,
        requires_check_in=bool(payload.requires_check_in),
        storefront_visibility=payload.storefront_visibility,
        post_event_drop_at=payload.post_event_drop_at,
    )
    db.add(product)
    db.flush()

    variants = payload.variants or [
        MerchVariantCreate(label="Default", inventory_count=0, status="active")
    ]
    for v in variants:
        if v.status not in VARIANT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid variant status")
        stock = v.stock_quantity if v.stock_quantity is not None else v.inventory_count
        label = (v.name or v.label or "").strip()
        db.add(
            EventMerchVariant(
                product_id=product.id,
                label=label,
                sku=(v.sku or "").strip() or None,
                size=(v.size or "").strip() or None,
                color=(v.color or "").strip() or None,
                option_1_name=(v.option_1_name or "").strip() or None,
                option_1_value=(v.option_1_value or "").strip() or None,
                option_2_name=(v.option_2_name or "").strip() or None,
                option_2_value=(v.option_2_value or "").strip() or None,
                price=v.price_override if v.price_override is not None else v.price,
                inventory_count=stock,
                reserved_quantity=0,
                sold_quantity=0,
                status=v.status,
            )
        )

    write_audit_log(
        db,
        action="merch.product_create",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details={"event_id": str(event.id), "name": product.name, "status": product.status},
    )
    from app.analytics.trusted import emit_host_merch_product_created

    emit_host_merch_product_created(
        db,
        event_id=event.id,
        host_id=host.id,
        actor_user_id=user.id,
        merch_product_id=product.id,
        product_status=product.status,
    )
    if (
        product.status == "active"
        and getattr(product, "storefront_visibility", None) != "post_event_drop"
    ):
        try:
            from app.admin_notifications.orchestrator import dispatch_typed

            dispatch_typed(
                db,
                type_key="merch.listing_published",
                context={
                    "host_id": str(host.id),
                    "event_id": str(event.id),
                    "context_id": str(product.id),
                    "product_name": product.name,
                    "host_name": host.display_name,
                    "event_title": event.title,
                },
                title=f"New merch from {host.display_name}",
                body=(product.name or "A new listing is live on Pàdéyá.")[:240],
                link_path=(
                    f"/events/{event.slug}/merch"
                    if event.slug
                    else "/dashboard/merchandise"
                ),
                dedupe_key=f"merch.listing_published:{product.id}",
            )
        except Exception:  # noqa: BLE001
            pass
    db.commit()
    loaded = _load_product(db, product.id)
    assert loaded is not None
    return serialize_product(loaded)


def create_standalone_product(
    db: Session, *, user: User, payload: MerchProductCreate
) -> dict:
    """Create host shop merch without an event (standalone marketplace listing)."""
    from app.hosts.team_access import require_host_for_permission
    from app.merch.marketplace import apply_marketplace_kind, unique_host_product_slug
    from app.users.restrictions import assert_can_manage_merch

    assert_can_manage_merch(db, user)
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="merch.create"
    )
    if payload.status not in PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid product status")

    name = payload.name.strip()
    description = (payload.description or "").strip() or None
    short_description = (payload.short_description or "").strip() or None
    pickup_instructions = (payload.pickup_instructions or "").strip() or None
    pickup_location_label = (payload.pickup_location_label or "").strip() or None
    pickup_time_window = (payload.pickup_time_window or "").strip() or None
    sponsor_brand_name = (payload.sponsor_brand_name or "").strip() or None
    sponsor_logo_url = (payload.sponsor_logo_url or "").strip() or None
    sponsor_description = (payload.sponsor_description or "").strip() or None
    assert_public_merch_copy_safe(
        name=name,
        description=description,
        short_description=short_description,
        pickup_instructions=pickup_instructions,
        pickup_location_label=pickup_location_label,
        pickup_time_window=pickup_time_window,
        sponsor_brand_name=sponsor_brand_name,
        sponsor_description=sponsor_description,
    )

    from app.merch.size_charts import require_host_chart

    size_chart_id = None
    if payload.size_chart_id is not None:
        size_chart_id = require_host_chart(
            db, host_id=host.id, chart_id=payload.size_chart_id
        ).id

    cover = (payload.cover_image_url or payload.image_url or "").strip() or None
    branded = bool(payload.is_sponsor_branded)
    kind = getattr(payload, "marketplace_kind", None) or "standalone"
    category = getattr(payload, "category", None)
    tags = getattr(payload, "tags", None)

    product = EventMerchProduct(
        event_id=None,
        host_id=host.id,
        name=name,
        slug=unique_host_product_slug(db, host_id=host.id, base=payload.name),
        description=description,
        short_description=short_description,
        product_type=_normalize_product_type(payload.product_type),
        base_price=payload.base_price,
        currency=(payload.currency or "NGN").upper(),
        image_url=cover,
        gallery_urls=list(payload.gallery_urls or []) or None,
        status=payload.status,
        sales_start_at=payload.sales_start_at,
        sales_end_at=payload.sales_end_at,
        pickup_instructions=pickup_instructions,
        pickup_location_label=pickup_location_label,
        pickup_time_window=pickup_time_window,
        fulfillment_notes=(payload.fulfillment_notes or "").strip() or None,
        show_on_event_page=False,
        is_featured=bool(payload.is_featured),
        requires_ticket=False,
        pickup_enabled=bool(payload.pickup_enabled),
        shipping_enabled=bool(payload.shipping_enabled),
        print_on_demand_enabled=bool(payload.print_on_demand_enabled),
        max_per_order=payload.max_per_order,
        max_per_buyer=payload.max_per_buyer,
        restock_on_refund=payload.restock_on_refund,
        size_chart_id=size_chart_id,
        is_sponsor_branded=branded,
        sponsor_id=payload.sponsor_id if branded else None,
        sponsor_brand_name=sponsor_brand_name if branded else None,
        sponsor_logo_url=sponsor_logo_url if branded else None,
        sponsor_description=sponsor_description if branded else None,
        sponsor_split_type=payload.sponsor_split_type if branded else None,
        sponsor_split_value=payload.sponsor_split_value if branded else None,
        is_event_linked=False,
        is_merch_only_enabled=True,
        storefront_visibility=payload.storefront_visibility or "host_storefront",
        category=(str(category).strip().lower() if category else None),
        tags=list(tags) if tags else None,
        marketplace_listed=bool(getattr(payload, "marketplace_listed", True)),
    )
    apply_marketplace_kind(product, kind)
    _apply_vault_access_fields(
        product,
        db=db,
        is_vault_exclusive=bool(payload.is_vault_exclusive),
        requires_vault_access=bool(
            payload.requires_vault_access or payload.is_vault_exclusive
        ),
        required_vault_item_id=payload.required_vault_item_id,
        required_access_type=payload.required_access_type,
        requires_check_in=bool(payload.requires_check_in),
        storefront_visibility=product.storefront_visibility,
        post_event_drop_at=payload.post_event_drop_at,
    )
    db.add(product)
    db.flush()

    variants = payload.variants or [
        MerchVariantCreate(label="Default", inventory_count=0, status="active")
    ]
    for v in variants:
        if v.status not in VARIANT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid variant status")
        stock = v.stock_quantity if v.stock_quantity is not None else v.inventory_count
        label = (v.name or v.label or "").strip()
        db.add(
            EventMerchVariant(
                product_id=product.id,
                label=label,
                sku=(v.sku or "").strip() or None,
                size=(v.size or "").strip() or None,
                color=(v.color or "").strip() or None,
                option_1_name=(v.option_1_name or "").strip() or None,
                option_1_value=(v.option_1_value or "").strip() or None,
                option_2_name=(v.option_2_name or "").strip() or None,
                option_2_value=(v.option_2_value or "").strip() or None,
                price=v.price_override if v.price_override is not None else v.price,
                inventory_count=stock,
                reserved_quantity=0,
                sold_quantity=0,
                status=v.status,
            )
        )

    write_audit_log(
        db,
        action="merch.product_create",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details={
            "event_id": None,
            "host_id": str(host.id),
            "name": product.name,
            "status": product.status,
            "marketplace_kind": product.marketplace_kind,
            "standalone": True,
        },
    )
    if product.status == "active":
        try:
            from app.admin_notifications.orchestrator import dispatch_typed

            dispatch_typed(
                db,
                type_key="merch.listing_published",
                context={
                    "host_id": str(host.id),
                    "event_id": None,
                    "context_id": str(product.id),
                    "product_name": product.name,
                    "host_name": host.display_name,
                },
                title=f"New merch from {host.display_name}",
                body=(product.name or "A new listing is live on Pàdéyá.")[:240],
                link_path=f"/merch/{product.slug}",
                dedupe_key=f"merch.listing_published:{product.id}",
            )
        except Exception:  # noqa: BLE001
            pass
    db.commit()
    loaded = _load_product(db, product.id)
    assert loaded is not None
    return serialize_product(loaded)


def update_product(
    db: Session, *, user: User, product_id: uuid.UUID, payload: MerchProductUpdate
) -> dict:
    product = _load_product(db, product_id)
    if product is None or product.archived_at is not None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_manage_product_merch(
        db, user, product, permission="merch.edit"
    ):
        raise HTTPException(status_code=403, detail="Not allowed to manage this product")

    previous_status = product.status
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid product status")

    next_name = data["name"].strip() if data.get("name") else product.name
    next_description = (
        (data["description"] or "").strip() or None
        if "description" in data
        else product.description
    )
    next_short = (
        (data["short_description"] or "").strip() or None
        if "short_description" in data
        else getattr(product, "short_description", None)
    )
    next_pickup_instructions = (
        (data["pickup_instructions"] or "").strip() or None
        if "pickup_instructions" in data
        else product.pickup_instructions
    )
    next_pickup_label = (
        (data["pickup_location_label"] or "").strip() or None
        if "pickup_location_label" in data
        else getattr(product, "pickup_location_label", None)
    )
    next_pickup_window = (
        (data["pickup_time_window"] or "").strip() or None
        if "pickup_time_window" in data
        else getattr(product, "pickup_time_window", None)
    )
    next_sponsor_brand = (
        (data["sponsor_brand_name"] or "").strip() or None
        if "sponsor_brand_name" in data
        else getattr(product, "sponsor_brand_name", None)
    )
    next_sponsor_desc = (
        (data["sponsor_description"] or "").strip() or None
        if "sponsor_description" in data
        else getattr(product, "sponsor_description", None)
    )
    assert_public_merch_copy_safe(
        name=next_name,
        description=next_description,
        short_description=next_short,
        pickup_instructions=next_pickup_instructions,
        pickup_location_label=next_pickup_label,
        pickup_time_window=next_pickup_window,
        sponsor_brand_name=next_sponsor_brand,
        sponsor_description=next_sponsor_desc,
    )

    if "name" in data and data["name"]:
        product.name = next_name
    if "description" in data:
        product.description = next_description
    if "short_description" in data:
        product.short_description = next_short
    if "product_type" in data:
        product.product_type = _normalize_product_type(data["product_type"])
    if "base_price" in data and data["base_price"] is not None:
        product.base_price = data["base_price"]
    if "currency" in data and data["currency"]:
        product.currency = data["currency"].upper()
    if "cover_image_url" in data:
        product.image_url = (data["cover_image_url"] or "").strip() or None
    elif "image_url" in data:
        product.image_url = (data["image_url"] or "").strip() or None
    if "gallery_urls" in data:
        product.gallery_urls = list(data["gallery_urls"] or []) or None
    if "status" in data and data["status"]:
        next_status = data["status"]
        mod = getattr(product, "moderation_status", None) or "clear"
        if next_status == "active" and mod in {"hidden", "removed"}:
            raise HTTPException(
                status_code=400,
                detail=(
                    "This listing is hidden by Pàdéyá moderation and cannot be "
                    "reactivated until an admin restores it."
                ),
            )
        product.status = next_status
    if "sales_start_at" in data:
        product.sales_start_at = data["sales_start_at"]
    if "sales_end_at" in data:
        product.sales_end_at = data["sales_end_at"]
    if "pickup_instructions" in data:
        product.pickup_instructions = next_pickup_instructions
    if "pickup_location_label" in data:
        product.pickup_location_label = next_pickup_label
    if "pickup_time_window" in data:
        product.pickup_time_window = next_pickup_window
    if "fulfillment_notes" in data:
        product.fulfillment_notes = (data["fulfillment_notes"] or "").strip() or None
    if "show_on_event_page" in data and data["show_on_event_page"] is not None:
        product.show_on_event_page = bool(data["show_on_event_page"])
    if "is_featured" in data and data["is_featured"] is not None:
        product.is_featured = bool(data["is_featured"])
    if "requires_ticket" in data and data["requires_ticket"] is not None:
        product.requires_ticket = bool(data["requires_ticket"])
    if "pickup_enabled" in data and data["pickup_enabled"] is not None:
        product.pickup_enabled = bool(data["pickup_enabled"])
    if "shipping_enabled" in data and data["shipping_enabled"] is not None:
        product.shipping_enabled = bool(data["shipping_enabled"])
    if "print_on_demand_enabled" in data and data["print_on_demand_enabled"] is not None:
        product.print_on_demand_enabled = bool(data["print_on_demand_enabled"])
    if (
        not product.pickup_enabled
        and not product.shipping_enabled
        and not product.print_on_demand_enabled
    ):
        raise HTTPException(
            status_code=400,
            detail="Enable pickup, shipping, and/or print on demand",
        )
    if "max_per_order" in data:
        product.max_per_order = data["max_per_order"]
    if "max_per_buyer" in data:
        product.max_per_buyer = data["max_per_buyer"]
    if "restock_on_refund" in data and data["restock_on_refund"] is not None:
        product.restock_on_refund = data["restock_on_refund"]
    if "size_chart_id" in data:
        chart_id = data["size_chart_id"]
        if chart_id is None:
            product.size_chart_id = None
        else:
            from app.merch.size_charts import require_host_chart

            product.size_chart_id = require_host_chart(
                db, host_id=product.host_id, chart_id=chart_id
            ).id

    sponsor_keys = {
        "is_sponsor_branded",
        "sponsor_id",
        "sponsor_brand_name",
        "sponsor_logo_url",
        "sponsor_description",
        "sponsor_split_type",
        "sponsor_split_value",
    }
    if sponsor_keys & data.keys():
        branded = (
            bool(data["is_sponsor_branded"])
            if "is_sponsor_branded" in data
            else bool(product.is_sponsor_branded)
        )
        product.is_sponsor_branded = branded
        if not branded:
            product.sponsor_id = None
            product.sponsor_brand_name = None
            product.sponsor_logo_url = None
            product.sponsor_description = None
            product.sponsor_split_type = None
            product.sponsor_split_value = None
        else:
            if "sponsor_id" in data:
                product.sponsor_id = data["sponsor_id"]
            if "sponsor_brand_name" in data:
                product.sponsor_brand_name = next_sponsor_brand
            elif not product.sponsor_brand_name:
                raise HTTPException(
                    status_code=400,
                    detail="sponsor_brand_name is required for sponsor-branded merch",
                )
            if "sponsor_logo_url" in data:
                product.sponsor_logo_url = (
                    (data["sponsor_logo_url"] or "").strip() or None
                )
            if "sponsor_description" in data:
                product.sponsor_description = next_sponsor_desc
            if "sponsor_split_type" in data:
                product.sponsor_split_type = data["sponsor_split_type"]
            if "sponsor_split_value" in data:
                product.sponsor_split_value = data["sponsor_split_value"]
            if product.sponsor_split_type and product.sponsor_split_value is None:
                raise HTTPException(
                    status_code=400,
                    detail="sponsor_split_value is required when sponsor_split_type is set",
                )

    vault_keys = {
        "is_vault_exclusive",
        "requires_vault_access",
        "required_vault_item_id",
        "required_access_type",
        "requires_check_in",
        "storefront_visibility",
        "post_event_drop_at",
    }
    if vault_keys & data.keys():
        _apply_vault_access_fields(
            product,
            db=db,
            is_vault_exclusive=data.get("is_vault_exclusive"),
            requires_vault_access=data.get("requires_vault_access"),
            required_vault_item_id=(
                data["required_vault_item_id"]
                if "required_vault_item_id" in data
                else ...
            ),
            required_access_type=(
                data["required_access_type"]
                if "required_access_type" in data
                else ...
            ),
            requires_check_in=data.get("requires_check_in"),
            storefront_visibility=data.get("storefront_visibility"),
            post_event_drop_at=(
                data["post_event_drop_at"] if "post_event_drop_at" in data else ...
            ),
        )

    audit_details = {
        key: (str(value) if isinstance(value, Decimal) else value)
        for key, value in data.items()
    }
    write_audit_log(
        db,
        action="merch.product_update",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details=audit_details,
    )
    from app.analytics.trusted import (
        emit_host_merch_product_paused,
        emit_host_merch_product_updated,
    )

    emit_host_merch_product_updated(
        db,
        event_id=product.event_id or product.host_id,  # standalone: no event
        host_id=product.host_id,
        actor_user_id=user.id,
        merch_product_id=product.id,
        product_status=product.status,
    )
    if previous_status != "paused" and product.status == "paused":
        emit_host_merch_product_paused(
            db,
            event_id=product.event_id or product.host_id,
            host_id=product.host_id,
            actor_user_id=user.id,
            merch_product_id=product.id,
        )
    db.commit()
    loaded = _load_product(db, product.id)
    assert loaded is not None
    return serialize_product(loaded)


def archive_product(db: Session, *, user: User, product_id: uuid.UUID) -> dict:
    product = _load_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_manage_product_merch(db, user, product):
        raise HTTPException(status_code=403, detail="Not allowed to manage this product")
    if product.archived_at is not None:
        return serialize_product(product)

    now = datetime.now(UTC)
    product.status = "archived"
    product.archived_at = now
    for variant in product.variants or []:
        variant.status = "archived"
        variant.archived_at = now

    write_audit_log(
        db,
        action="merch.product_archive",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details={"event_id": str(product.event_id)},
    )
    db.commit()
    loaded = _load_product(db, product.id)
    assert loaded is not None
    return serialize_product(loaded)


def duplicate_product(db: Session, *, user: User, product_id: uuid.UUID) -> dict:
    source = _load_product(db, product_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_manage_event_merch(db, user, source.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage this product")

    event = db.get(Event, source.event_id)
    title = event.title if event else None
    clone = EventMerchProduct(
        event_id=source.event_id,
        host_id=source.host_id,
        name=f"{source.name} (copy)",
        slug=unique_product_slug(db, event_id=source.event_id, base=f"{source.name}-copy"),
        description=source.description,
        short_description=source.short_description,
        product_type=source.product_type,
        base_price=source.base_price,
        currency=source.currency,
        image_url=source.image_url,
        gallery_urls=list(source.gallery_urls or []) or None,
        status="draft",
        sales_start_at=source.sales_start_at,
        sales_end_at=source.sales_end_at,
        pickup_instructions=source.pickup_instructions,
        pickup_location_label=getattr(source, "pickup_location_label", None),
        pickup_time_window=getattr(source, "pickup_time_window", None),
        fulfillment_notes=getattr(source, "fulfillment_notes", None),
        show_on_event_page=bool(getattr(source, "show_on_event_page", True)),
        is_featured=False,
        requires_ticket=bool(getattr(source, "requires_ticket", False)),
        max_per_order=source.max_per_order,
        max_per_buyer=getattr(source, "max_per_buyer", None),
        restock_on_refund=source.restock_on_refund,
        moderation_status="clear",
        is_sponsor_branded=bool(getattr(source, "is_sponsor_branded", False)),
        sponsor_id=getattr(source, "sponsor_id", None),
        sponsor_brand_name=getattr(source, "sponsor_brand_name", None),
        sponsor_logo_url=getattr(source, "sponsor_logo_url", None),
        sponsor_description=getattr(source, "sponsor_description", None),
        sponsor_split_type=getattr(source, "sponsor_split_type", None),
        sponsor_split_value=getattr(source, "sponsor_split_value", None),
        pickup_enabled=bool(getattr(source, "pickup_enabled", True)),
        shipping_enabled=bool(getattr(source, "shipping_enabled", False)),
        size_chart_id=getattr(source, "size_chart_id", None),
    )
    db.add(clone)
    db.flush()
    for variant in source.variants or []:
        if variant.archived_at is not None:
            continue
        db.add(
            EventMerchVariant(
                product_id=clone.id,
                label=variant.label,
                sku=variant.sku,
                size=variant.size,
                color=variant.color,
                option_1_name=getattr(variant, "option_1_name", None),
                option_1_value=getattr(variant, "option_1_value", None),
                option_2_name=getattr(variant, "option_2_name", None),
                option_2_value=getattr(variant, "option_2_value", None),
                price=variant.price,
                inventory_count=variant.inventory_count,
                reserved_quantity=0,
                sold_quantity=0,
                status="active" if variant.status != "archived" else "archived",
            )
        )
    write_audit_log(
        db,
        action="merch.product_duplicate",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(clone.id),
        details={"source_product_id": str(source.id)},
    )
    db.commit()
    loaded = _load_product(db, clone.id)
    assert loaded is not None
    return serialize_product(loaded, event_title=title)


def get_host_event_merch_stats(db: Session, *, user: User, event_id: uuid.UUID) -> dict:
    """Host studio metrics — merch revenue totals only, no payment secrets."""
    from app.merch.constants import ITEM_KIND_MERCH
    from app.merch.models import MerchFulfillment
    from app.payments.models import Order, OrderItem

    if not can_manage_event_merch(db, user, event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage merch for this event")

    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    products = list(
        db.scalars(
            select(EventMerchProduct)
            .where(
                EventMerchProduct.event_id == event_id,
                EventMerchProduct.archived_at.is_(None),
            )
            .options(selectinload(EventMerchProduct.variants))
        ).all()
    )
    active_products = sum(1 for p in products if p.status == "active")
    sold_out_variants = 0
    for product in products:
        for variant in product.variants or []:
            if variant.archived_at is not None:
                continue
            if variant.status == "sold_out" or (
                variant.status == "active" and available_variant_stock(variant) <= 0
            ):
                sold_out_variants += 1

    revenue = db.scalar(
        select(func.coalesce(func.sum(OrderItem.line_total), 0)).where(
            OrderItem.item_kind == ITEM_KIND_MERCH,
            OrderItem.order_id.in_(
                select(Order.id).where(
                    Order.event_id == event_id,
                    Order.status == "paid",
                )
            ),
        )
    )
    items_sold = db.scalar(
        select(func.coalesce(func.sum(OrderItem.quantity), 0)).where(
            OrderItem.item_kind == ITEM_KIND_MERCH,
            OrderItem.order_id.in_(
                select(Order.id).where(
                    Order.event_id == event_id,
                    Order.status == "paid",
                )
            ),
        )
    )
    pending_pickup = db.scalar(
        select(func.count())
        .select_from(MerchFulfillment)
        .where(
            MerchFulfillment.event_id == event_id,
            MerchFulfillment.status.in_(("awaiting_pickup", "collect_at_stand")),
        )
    ) or 0
    picked_up = db.scalar(
        select(func.count())
        .select_from(MerchFulfillment)
        .where(
            MerchFulfillment.event_id == event_id,
            MerchFulfillment.status == "fulfilled",
        )
    ) or 0

    sales_status = "no_merch"
    if products:
        if active_products == 0:
            sales_status = "paused"
        elif any(
            p.status == "active" and _sales_window_open(p) for p in products
        ):
            sales_status = "selling"
        else:
            sales_status = "closed"

    return {
        "event_id": event_id,
        "event_title": event.title,
        "sales_status": sales_status,
        "currency": "NGN",
        "total_merch_revenue": Decimal(revenue or 0),
        "items_sold": int(items_sold or 0),
        "pending_pickup": int(pending_pickup),
        "picked_up": int(picked_up),
        "active_products": active_products,
        "sold_out_variants": sold_out_variants,
        "product_count": len(products),
        # Intentionally omit payment IDs, Paystack refs, buyer emails, gateway payloads.
    }


def create_variant(
    db: Session, *, user: User, product_id: uuid.UUID, payload: MerchVariantCreate
) -> dict:
    product = _load_product(db, product_id)
    if product is None or product.archived_at is not None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_manage_event_merch(db, user, product.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage this product")
    if payload.status not in VARIANT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid variant status")

    stock = (
        payload.stock_quantity
        if payload.stock_quantity is not None
        else payload.inventory_count
    )
    label = (payload.name or payload.label or "").strip()
    variant = EventMerchVariant(
        product_id=product.id,
        label=label,
        sku=(payload.sku or "").strip() or None,
        size=(payload.size or "").strip() or None,
        color=(payload.color or "").strip() or None,
        option_1_name=(payload.option_1_name or "").strip() or None,
        option_1_value=(payload.option_1_value or "").strip() or None,
        option_2_name=(payload.option_2_name or "").strip() or None,
        option_2_value=(payload.option_2_value or "").strip() or None,
        price=(
            payload.price_override
            if payload.price_override is not None
            else payload.price
        ),
        inventory_count=stock,
        reserved_quantity=0,
        sold_quantity=0,
        status=payload.status,
        print_on_demand_variant_ref=(
            (payload.print_on_demand_variant_ref or "").strip() or None
        ),
    )
    db.add(variant)
    write_audit_log(
        db,
        action="merch.variant_create",
        actor_user_id=user.id,
        resource_type="event_merch_variant",
        resource_id=str(variant.id),
        details={"product_id": str(product.id), "label": variant.label},
    )
    db.commit()
    db.refresh(variant)
    return serialize_variant(product, variant)


def update_variant(
    db: Session, *, user: User, variant_id: uuid.UUID, payload: MerchVariantUpdate
) -> dict:
    variant = db.get(EventMerchVariant, variant_id)
    if variant is None or variant.archived_at is not None:
        raise HTTPException(status_code=404, detail="Variant not found")
    product = _load_product(db, variant.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_manage_event_merch(db, user, product.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage this product")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in VARIANT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid variant status")
    if "name" in data and data["name"]:
        variant.label = data["name"].strip()
    elif "label" in data and data["label"]:
        variant.label = data["label"].strip()
    for field in (
        "sku",
        "size",
        "color",
        "option_1_name",
        "option_1_value",
        "option_2_name",
        "option_2_value",
        "print_on_demand_variant_ref",
    ):
        if field in data:
            value = data[field]
            setattr(variant, field, (value or "").strip() or None)
    if "price_override" in data:
        variant.price = data["price_override"]
    elif "price" in data:
        variant.price = data["price"]
    inventory_changed = (
        ("stock_quantity" in data and data["stock_quantity"] is not None)
        or ("inventory_count" in data and data["inventory_count"] is not None)
    )
    previous_available = available_variant_stock(variant) if inventory_changed else None
    if "stock_quantity" in data and data["stock_quantity"] is not None:
        variant.inventory_count = data["stock_quantity"]
    elif "inventory_count" in data and data["inventory_count"] is not None:
        variant.inventory_count = data["inventory_count"]
    if "status" in data and data["status"]:
        variant.status = data["status"]
    sync_variant_sold_out(variant)

    if inventory_changed:
        from app.merch.stock_alerts import evaluate_variant_stock_alerts

        evaluate_variant_stock_alerts(
            db,
            product=product,
            variant=variant,
            previous_available=previous_available,
        )

    write_audit_log(
        db,
        action="merch.variant_update",
        actor_user_id=user.id,
        resource_type="event_merch_variant",
        resource_id=str(variant.id),
        details=data,
    )
    db.commit()
    db.refresh(variant)
    return serialize_variant(product, variant)


def archive_variant(db: Session, *, user: User, variant_id: uuid.UUID) -> dict:
    variant = db.get(EventMerchVariant, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    product = _load_product(db, variant.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_manage_event_merch(db, user, product.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage this product")
    if variant.archived_at is None:
        variant.status = "archived"
        variant.archived_at = datetime.now(UTC)
        write_audit_log(
            db,
            action="merch.variant_archive",
            actor_user_id=user.id,
            resource_type="event_merch_variant",
            resource_id=str(variant.id),
            details={"product_id": str(product.id)},
        )
        db.commit()
        db.refresh(variant)
    return serialize_variant(product, variant)


def assert_event_host_sellable(db: Session, *, event: Event) -> None:
    """Block checkout when the event or host cannot sell merch.

    Completed events remain sellable for post-event drops / merch-only recovery
    (ticket sales stay gated separately in create_order).
    """
    from app.hosts.models import Host
    from app.merch.constants import UNSAFE_EVENT_STATUSES, UNSAFE_HOST_STATUSES

    if event.status in UNSAFE_EVENT_STATUSES or event.status not in {
        "published",
        "completed",
    }:
        raise HTTPException(status_code=400, detail="Event is not available for purchase")
    host = db.get(Host, event.host_id)
    if host is None or host.status in UNSAFE_HOST_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Merch is unavailable for this event right now",
        )


def buyer_has_active_event_ticket(
    db: Session, *, buyer_user_id: uuid.UUID, event_id: uuid.UUID
) -> bool:
    """True when the buyer already holds an active ticket for this event."""
    from app.tickets.models import Ticket

    ticket_id = db.scalar(
        select(Ticket.id)
        .where(
            Ticket.buyer_user_id == buyer_user_id,
            Ticket.event_id == event_id,
            Ticket.status == "active",
        )
        .limit(1)
    )
    return ticket_id is not None


def buyer_prior_product_quantity(
    db: Session,
    *,
    buyer_user_id: uuid.UUID,
    product_id: uuid.UUID,
) -> int:
    """Paid fulfillments + pending cart holds for this product (max_per_buyer)."""
    from app.merch.models import MerchFulfillment
    from app.payments.models import Order, OrderItem

    paid = db.scalar(
        select(func.coalesce(func.sum(MerchFulfillment.quantity), 0)).where(
            MerchFulfillment.buyer_user_id == buyer_user_id,
            MerchFulfillment.status != "cancelled",
            MerchFulfillment.merch_variant_id.in_(
                select(EventMerchVariant.id).where(
                    EventMerchVariant.product_id == product_id
                )
            ),
        )
    )
    pending = db.scalar(
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.buyer_user_id == buyer_user_id,
            Order.status == "pending",
            OrderItem.merch_product_id == product_id,
            OrderItem.item_kind == "merch",
        )
    )
    return int(paid or 0) + int(pending or 0)


def load_sellable_variant(
    db: Session,
    *,
    event_id: uuid.UUID,
    variant_id: uuid.UUID,
    for_update: bool = False,
    buyer_user_id: uuid.UUID | None = None,
) -> tuple[EventMerchProduct, EventMerchVariant]:
    stmt = (
        select(EventMerchVariant)
        .where(EventMerchVariant.id == variant_id)
        .options(selectinload(EventMerchVariant.product))
    )
    if for_update:
        stmt = stmt.with_for_update()
    variant = db.scalar(stmt)
    if variant is None or variant.archived_at is not None:
        raise HTTPException(status_code=400, detail="Invalid merch variant")
    product = variant.product
    if product is None:
        product = db.get(EventMerchProduct, variant.product_id)
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=400, detail="Event is not available for purchase")
    if product is None or product.status != "active" or product.archived_at is not None:
        raise HTTPException(status_code=400, detail="Merch product unavailable for this event")
    # Event-linked products must match; evergreen storefront merch must share host.
    event_ok = product.event_id == event_id
    evergreen_ok = (not product.is_event_linked) and product.host_id == event.host_id
    if not event_ok and not evergreen_ok:
        raise HTTPException(status_code=400, detail="Merch product unavailable for this event")
    mod = getattr(product, "moderation_status", None) or "clear"
    if mod in {"hidden", "removed"}:
        raise HTTPException(status_code=400, detail="Merch product unavailable for this event")
    assert_event_host_sellable(db, event=event)
    if not _sales_window_open(product):
        raise HTTPException(status_code=400, detail="Merch sales window is closed")
    from app.merch.access import assert_buyer_can_purchase, product_is_drop_live

    if not product_is_drop_live(product):
        raise HTTPException(status_code=400, detail="Post-event merch drop is not available yet")
    if buyer_user_id is not None:
        assert_buyer_can_purchase(db, product=product, buyer_user_id=buyer_user_id)
    if variant.status == "sold_out" or available_variant_stock(variant) <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough inventory for {product.name} ({variant.label})",
        )
    if variant.status != "active":
        raise HTTPException(status_code=400, detail=f"Variant {variant.label} is unavailable")
    return product, variant


def load_sellable_host_variant(
    db: Session,
    *,
    host_id: uuid.UUID,
    variant_id: uuid.UUID,
    for_update: bool = False,
    buyer_user_id: uuid.UUID | None = None,
) -> tuple[EventMerchProduct, EventMerchVariant]:
    """Sell standalone / host-storefront merch without an event checkout context."""
    from app.hosts.models import Host
    from app.merch.constants import UNSAFE_HOST_STATUSES

    stmt = (
        select(EventMerchVariant)
        .where(EventMerchVariant.id == variant_id)
        .options(selectinload(EventMerchVariant.product))
    )
    if for_update:
        stmt = stmt.with_for_update()
    variant = db.scalar(stmt)
    if variant is None or variant.archived_at is not None:
        raise HTTPException(status_code=400, detail="Invalid merch variant")
    product = variant.product or db.get(EventMerchProduct, variant.product_id)
    host = db.get(Host, host_id)
    if host is None or host.status in UNSAFE_HOST_STATUSES:
        raise HTTPException(status_code=400, detail="Host shop is not available")
    if product is None or product.status != "active" or product.archived_at is not None:
        raise HTTPException(status_code=400, detail="Merch product unavailable")
    if product.host_id != host_id:
        raise HTTPException(status_code=400, detail="Merch product unavailable for this host")
    if product.is_event_linked and product.event_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Event merch must be purchased from the event checkout",
        )
    mod = getattr(product, "moderation_status", None) or "clear"
    if mod in {"hidden", "removed"}:
        raise HTTPException(status_code=400, detail="Merch product unavailable")
    if not _sales_window_open(product):
        raise HTTPException(status_code=400, detail="Merch sales window is closed")
    from app.merch.access import assert_buyer_can_purchase, product_is_drop_live

    if not product_is_drop_live(product):
        raise HTTPException(status_code=400, detail="Post-event merch drop is not available yet")
    if buyer_user_id is not None:
        assert_buyer_can_purchase(db, product=product, buyer_user_id=buyer_user_id)
    if variant.status == "sold_out" or available_variant_stock(variant) <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough inventory for {product.name} ({variant.label})",
        )
    if variant.status != "active":
        raise HTTPException(status_code=400, detail=f"Variant {variant.label} is unavailable")
    return product, variant


def assert_variant_quantity_ok(
    *,
    product: EventMerchProduct,
    variant: EventMerchVariant,
    quantity: int,
    product_order_quantity: int | None = None,
) -> None:
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid merch quantity")
    order_qty = product_order_quantity if product_order_quantity is not None else quantity
    if product.max_per_order is not None and order_qty > product.max_per_order:
        raise HTTPException(
            status_code=400,
            detail=f"Quantity for {product.name} cannot exceed {product.max_per_order}",
        )
    if available_variant_stock(variant) < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough inventory for {product.name} ({variant.label})",
        )


def reserve_variant_quantity(variant: EventMerchVariant, quantity: int) -> None:
    """Hold stock for a pending checkout. Caller validates product limits first."""
    if available_variant_stock(variant) < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough inventory for {variant.label}",
        )
    variant.reserved_quantity = int(variant.reserved_quantity or 0) + quantity


def release_variant_reservation(variant: EventMerchVariant, quantity: int) -> None:
    variant.reserved_quantity = max(0, int(variant.reserved_quantity or 0) - quantity)


def commit_variant_sale(variant: EventMerchVariant, quantity: int) -> bool:
    """Move reserved units into sold after verified payment.

    Returns True if the variant newly became sold out.
    """
    release_variant_reservation(variant, quantity)
    if variant.inventory_count < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough inventory for {variant.label}",
        )
    variant.inventory_count -= quantity
    variant.sold_quantity = int(variant.sold_quantity or 0) + quantity
    return sync_variant_sold_out(variant)


def restock_variant_on_refund(variant: EventMerchVariant, quantity: int) -> None:
    variant.inventory_count += quantity
    variant.sold_quantity = max(0, int(variant.sold_quantity or 0) - quantity)
    sync_variant_sold_out(variant)
