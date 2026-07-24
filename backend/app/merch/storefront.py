"""Host merch-only storefront — event-native, not a marketplace."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event
from app.hosts.models import Host, HostProfile
from app.merch.access import buyer_eligible_for_product, product_is_drop_live, public_teaser_fields
from app.merch.constants import (
    HOST_STOREFRONT_VISIBILITIES,
    UNSAFE_EVENT_STATUSES,
    UNSAFE_HOST_STATUSES,
)
from app.merch.models import EventMerchProduct
from app.merch.privacy import public_pickup_fields
from app.merch.service import serialize_variant
from app.merch.size_charts import get_public_chart
from app.users.models import User

_STOREFRONT_PRODUCT_VIS = frozenset(
    {"host_storefront", "post_event_drop", "vault_exclusive"}
)
_PRIVATE_EVENT_VIS = frozenset({"unlisted", "password_protected"})
_PRIVATE_EVENT_TYPES = frozenset({"private", "invite_only", "secret_location"})


def _resolve_host(db: Session, username: str) -> Host:
    slug = username.strip().lstrip("@").lower()
    host = db.scalar(
        select(Host)
        .where(Host.slug == slug)
        .options(selectinload(Host.profile))
    )
    if host is None or host.status in UNSAFE_HOST_STATUSES:
        raise HTTPException(status_code=404, detail="Host storefront not found")
    return host


def _ensure_profile(host: Host) -> HostProfile:
    if host.profile is None:
        host.profile = HostProfile(host_id=host.id)
    return host.profile


def _is_owner(host: Host, viewer: User | None) -> bool:
    return viewer is not None and viewer.id == host.user_id


def _storefront_publicly_reachable(profile: HostProfile) -> bool:
    if not profile.merch_storefront_enabled:
        return False
    return profile.merch_storefront_visibility in {"public", "unlisted"}


def _assert_storefront_access(
    host: Host,
    *,
    viewer: User | None = None,
) -> tuple[HostProfile, bool]:
    """Return (profile, is_preview). Hidden/disabled → 404 for non-owners."""
    profile = _ensure_profile(host)
    owner = _is_owner(host, viewer)
    if _storefront_publicly_reachable(profile):
        return profile, False
    if owner:
        return profile, True
    raise HTTPException(status_code=404, detail="Host storefront not found")


def _event_is_private(event: Event | None) -> bool:
    if event is None:
        return False
    visibility = getattr(event, "visibility", None) or "listed"
    event_type = getattr(event, "event_type", None) or "public"
    if visibility in _PRIVATE_EVENT_VIS:
        return True
    if event_type in _PRIVATE_EVENT_TYPES:
        return True
    return False


def _public_event_fields(event: Event | None) -> dict:
    if event is None:
        return {"event_title": None, "event_slug": None, "event_is_private": False}
    if event.status in UNSAFE_EVENT_STATUSES:
        return {"event_title": None, "event_slug": None, "event_is_private": True}
    if _event_is_private(event):
        return {
            "event_title": None,
            "event_slug": None,
            "event_is_private": True,
        }
    return {
        "event_title": event.title,
        "event_slug": event.slug,
        "event_is_private": False,
    }


def serialize_storefront_product(
    db: Session,
    product: EventMerchProduct,
    *,
    buyer_user_id: uuid.UUID | None = None,
) -> dict:
    from app.merch.reviews import list_product_reviews

    eligible, reason = buyer_eligible_for_product(
        db, product=product, buyer_user_id=buyer_user_id
    )
    teaser = public_teaser_fields(product, eligible=eligible)
    locked = bool(teaser.get("access_locked") or teaser.get("teaser_only"))
    event = db.get(Event, product.event_id) if product.event_id else None
    pickup = (
        public_pickup_fields(product, event)
        if product.pickup_enabled and not locked
        else {
            "pickup_location_label": None,
            "pickup_time_window": None,
            "pickup_instructions": None,
            "fulfillment_notes": None,
        }
    )
    variants = []
    for v in product.variants or []:
        if v.archived_at is not None or v.status in {"archived", "paused"}:
            continue
        data = serialize_variant(product, v)
        if locked:
            # Don't expose exact stock or SKUs for locked vault / drop teasers
            data["available_quantity"] = None
            data["inventory_count"] = None
            data["stock_quantity"] = None
            data["sku"] = None
        variants.append(data)

    description = product.description
    short_description = product.short_description
    gallery_urls: list[str] = list(product.gallery_urls or [])
    size_chart = None
    reviews = {"average_rating": None, "review_count": 0}

    if locked and (product.is_vault_exclusive or product.requires_vault_access):
        description = product.short_description or "Exclusive merch for Vault members."
        short_description = description
        gallery_urls = []
        # Teaser card image only — no size chart / review bodies for locked Vault.
        size_chart = None
    else:
        if teaser.get("teaser_only") and product.is_vault_exclusive:
            description = product.short_description or "Exclusive merch for Vault members."
        reviews = list_product_reviews(db, product_id=product.id)
        size_chart = get_public_chart(db, product.size_chart_id)

    drop_live = product_is_drop_live(product)
    availability = "purchasable"
    if not drop_live:
        availability = "coming_soon"
    elif locked:
        availability = "locked"
    elif not variants and not product.print_on_demand_enabled:
        availability = "unavailable"
    elif variants and all(
        (v.get("available_quantity") or 0) <= 0
        for v in variants
        if v.get("available_quantity") is not None
    ):
        if not product.print_on_demand_enabled:
            availability = "sold_out"

    teaser_flags = {
        "access_locked": teaser.get("access_locked", False),
        "teaser_only": teaser.get("teaser_only", False),
        "access_label": teaser.get("access_label"),
        "access_requirements": teaser.get("access_requirements") or [],
        "unlock_hint": teaser.get("unlock_hint"),
    }

    return {
        "id": product.id,
        "event_id": None if _event_is_private(event) else product.event_id,
        "host_id": product.host_id,
        "name": product.name,
        "slug": product.slug,
        "description": description,
        "short_description": short_description,
        "product_type": product.product_type,
        "base_price": product.base_price,
        "currency": product.currency,
        "image_url": product.image_url,
        "cover_image_url": product.image_url,
        "gallery_urls": gallery_urls,
        "status": product.status,
        "is_featured": product.is_featured,
        "storefront_visibility": product.storefront_visibility,
        "is_event_linked": product.is_event_linked,
        "is_merch_only": not product.is_event_linked or bool(product.is_merch_only_enabled),
        "is_vault_exclusive": product.is_vault_exclusive,
        "requires_vault_access": bool(
            product.requires_vault_access or product.is_vault_exclusive
        ),
        "required_access_type": product.required_access_type,
        # Eligible buyers may deep-link; locked teasers omit Vault item ids
        "required_vault_item_id": (
            None if locked else product.required_vault_item_id
        ),
        "is_sponsor_branded": product.is_sponsor_branded,
        "sponsor_brand_name": product.sponsor_brand_name if product.is_sponsor_branded else None,
        "sponsor_logo_url": product.sponsor_logo_url if product.is_sponsor_branded else None,
        "sponsor_description": (
            None
            if locked
            else (product.sponsor_description if product.is_sponsor_branded else None)
        ),
        "pickup_enabled": product.pickup_enabled and not locked,
        "shipping_enabled": product.shipping_enabled and not locked,
        "print_on_demand_enabled": product.print_on_demand_enabled,
        "post_event_drop_at": product.post_event_drop_at,
        "is_drop_live": drop_live,
        "is_post_event_drop": product.storefront_visibility == "post_event_drop",
        "access_eligible": eligible,
        "access_reason": reason if not eligible else None,
        "availability": availability,
        **teaser_flags,
        **pickup,
        "variants": (
            []
            if locked and (product.is_vault_exclusive or product.requires_vault_access)
            else variants
        ),
        "size_chart": size_chart,
        "average_rating": reviews["average_rating"],
        "review_count": reviews["review_count"],
        **_public_event_fields(event),
        # Never: private venue street when hidden; never shipping address
    }


def _product_on_storefront(product: EventMerchProduct) -> bool:
    if product.status != "active":
        return False
    if product.archived_at is not None:
        return False
    mod = getattr(product, "moderation_status", None) or "clear"
    if mod in {"hidden", "removed"}:
        return False
    if product.storefront_visibility == "hidden":
        return False
    if product.storefront_visibility in _STOREFRONT_PRODUCT_VIS:
        return True
    # Merch-only evergreen products opted into the host shop
    if not product.is_event_linked and product.storefront_visibility == "host_storefront":
        return True
    return False


def _sales_window_open(product: EventMerchProduct, *, now: datetime) -> bool:
    if product.sales_start_at and now < product.sales_start_at:
        # Upcoming drops still show as teasers when post_event_drop
        if product.storefront_visibility == "post_event_drop":
            return True
        return False
    if product.sales_end_at and now > product.sales_end_at:
        return False
    return True


def get_host_storefront(
    db: Session,
    *,
    username: str,
    buyer_user_id: uuid.UUID | None = None,
    viewer: User | None = None,
    event: str | None = None,
    product_type: str | None = None,
    availability: str | None = None,
    kind: str | None = None,
) -> dict:
    host = _resolve_host(db, username)
    profile, is_preview = _assert_storefront_access(host, viewer=viewer)
    now = datetime.now(UTC)
    stmt = (
        select(EventMerchProduct)
        .where(
            EventMerchProduct.host_id == host.id,
            EventMerchProduct.status == "active",
            EventMerchProduct.archived_at.is_(None),
            EventMerchProduct.moderation_status.notin_(("hidden", "removed")),
            or_(
                EventMerchProduct.storefront_visibility.in_(
                    ("host_storefront", "post_event_drop", "vault_exclusive")
                ),
                and_(
                    EventMerchProduct.is_event_linked.is_(False),
                    EventMerchProduct.storefront_visibility == "host_storefront",
                ),
            ),
        )
        .options(selectinload(EventMerchProduct.variants))
        .order_by(
            EventMerchProduct.is_featured.desc(),
            EventMerchProduct.created_at.desc(),
        )
    )
    products = list(db.scalars(stmt))
    catalog = []
    for p in products:
        if not _product_on_storefront(p):
            continue
        if not _sales_window_open(p, now=now):
            continue
        row = serialize_storefront_product(db, p, buyer_user_id=buyer_user_id)
        catalog.append(row)

    events_meta: dict[str, dict] = {}
    types: set[str] = set()
    for r in catalog:
        if r.get("product_type"):
            types.add(str(r["product_type"]))
        slug = r.get("event_slug")
        if slug and not r.get("event_is_private"):
            events_meta[str(slug)] = {
                "event_id": r.get("event_id"),
                "event_slug": slug,
                "event_title": r.get("event_title"),
            }

    # Filters (after filter metadata so option lists stay complete)
    event_filter = (event or "").strip()
    if event_filter:
        if event_filter.lower() in {"none", "merch-only", "merch_only"}:
            catalog = [
                r for r in catalog if not r.get("event_id") and not r.get("event_slug")
            ]
        else:
            catalog = [
                r
                for r in catalog
                if str(r.get("event_id") or "") == event_filter
                or (r.get("event_slug") or "") == event_filter
            ]
    type_filter = (product_type or "").strip()
    if type_filter:
        catalog = [r for r in catalog if (r.get("product_type") or "") == type_filter]
    avail_filter = (availability or "").strip().lower()
    if avail_filter and avail_filter != "all":
        catalog = [r for r in catalog if (r.get("availability") or "") == avail_filter]
    kind_filter = (kind or "").strip().lower()
    if kind_filter in {"post_event", "post_event_drop", "drop"}:
        catalog = [r for r in catalog if r.get("is_post_event_drop")]
    elif kind_filter in {"vault", "vault_exclusive"}:
        catalog = [r for r in catalog if r.get("is_vault_exclusive")]
    elif kind_filter in {"host_storefront", "evergreen", "merch_only"}:
        catalog = [
            r
            for r in catalog
            if not r.get("is_post_event_drop") and not r.get("is_vault_exclusive")
        ]

    title = profile.merch_storefront_title or f"{host.display_name} merch"
    description = (
        profile.merch_storefront_description
        or "Event merch from this host on Pàdéyá — pickup, drops, and exclusives."
    )

    return {
        "host_id": host.id,
        "host_name": host.display_name,
        "host_slug": host.slug,
        "host_avatar_url": profile.avatar_url,
        "legacy_path": f"/@{host.slug}",
        "legacy_url": f"/u/{host.slug}",
        "storefront_enabled": profile.merch_storefront_enabled,
        "storefront_title": title,
        "storefront_description": description,
        "storefront_visibility": profile.merch_storefront_visibility,
        "is_listed": (
            profile.merch_storefront_enabled
            and profile.merch_storefront_visibility == "public"
        ),
        "is_preview": is_preview,
        "products": catalog,
        "product_count": len(catalog),
        "filters": {
            "events": list(events_meta.values()),
            "product_types": sorted(types),
            "availabilities": ["purchasable", "coming_soon", "locked", "sold_out"],
            "kinds": ["host_storefront", "post_event_drop", "vault_exclusive"],
        },
    }


def get_storefront_product(
    db: Session,
    *,
    username: str,
    product_id: uuid.UUID,
    buyer_user_id: uuid.UUID | None = None,
    viewer: User | None = None,
) -> dict:
    host = _resolve_host(db, username)
    _assert_storefront_access(host, viewer=viewer)
    product = db.scalar(
        select(EventMerchProduct)
        .where(
            EventMerchProduct.id == product_id,
            EventMerchProduct.host_id == host.id,
        )
        .options(selectinload(EventMerchProduct.variants))
    )
    if product is None or not _product_on_storefront(product):
        raise HTTPException(status_code=404, detail="Product not found")
    now = datetime.now(UTC)
    if not _sales_window_open(product, now=now):
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_storefront_product(db, product, buyer_user_id=buyer_user_id)


def get_host_storefront_settings(db: Session, *, host: Host) -> dict:
    profile = _ensure_profile(host)
    return {
        "enabled": profile.merch_storefront_enabled,
        "title": profile.merch_storefront_title,
        "description": profile.merch_storefront_description,
        "visibility": profile.merch_storefront_visibility,
        "public_path": f"/@{host.slug}/merch",
        "legacy_path": f"/@{host.slug}",
    }


def update_host_storefront_settings(
    db: Session,
    *,
    host: Host,
    enabled: bool | None = None,
    title: str | None = None,
    description: str | None = None,
    visibility: str | None = None,
) -> dict:
    profile = _ensure_profile(host)
    if enabled is not None:
        profile.merch_storefront_enabled = bool(enabled)
    if title is not None:
        cleaned = title.strip()
        profile.merch_storefront_title = cleaned[:160] or None
    if description is not None:
        cleaned = description.strip()
        profile.merch_storefront_description = cleaned[:500] or None
    if visibility is not None:
        vis = visibility.strip().lower()
        if vis not in HOST_STOREFRONT_VISIBILITIES:
            raise HTTPException(
                status_code=400,
                detail=f"visibility must be one of: {', '.join(HOST_STOREFRONT_VISIBILITIES)}",
            )
        profile.merch_storefront_visibility = vis
    db.add(profile)
    db.flush()
    return get_host_storefront_settings(db, host=host)
