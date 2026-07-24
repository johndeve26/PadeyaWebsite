"""Cross-host merch marketplace discovery.

Host is required on every product; event is optional.
Public surfaces never leak private Vault/event details or buyer PII.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event
from app.hosts.models import Host, HostProfile
from app.merch.constants import (
    MARKETPLACE_PUBLIC_VISIBILITIES,
    MARKETPLACE_SORTS,
    MERCH_CATEGORY_LABELS,
    MERCH_CATEGORY_SLUGS,
    MERCH_KINDS,
    UNSAFE_EVENT_STATUSES,
    UNSAFE_HOST_STATUSES,
)
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchCategory
from app.merch.service import (
    available_variant_stock,
    serialize_catalog_product,
    slugify,
)

_RESERVED_SLUGS = frozenset(
    {
        "drops",
        "vault",
        "hosts",
        "categories",
        "marketplace",
        "health",
        "mine",
        "admin",
        "host",
        "products",
        "events",
        "item",
        "new",
        "checkout",
    }
)


def infer_marketplace_kind(product: EventMerchProduct) -> str:
    stored = (getattr(product, "marketplace_kind", None) or "").strip().lower()
    if stored in MERCH_KINDS:
        return stored
    if product.is_vault_exclusive or product.storefront_visibility == "vault_exclusive":
        return "vault_exclusive"
    if product.storefront_visibility == "post_event_drop":
        return "post_event_drop"
    if not product.is_event_linked or product.event_id is None:
        return "standalone"
    if product.requires_ticket:
        return "event_addon"
    return "event_merch"


def apply_marketplace_kind(product: EventMerchProduct, kind: str | None) -> None:
    """Align flags/visibility with an explicit marketplace kind."""
    if not kind:
        product.marketplace_kind = infer_marketplace_kind(product)
        return
    cleaned = kind.strip().lower()
    if cleaned not in MERCH_KINDS or cleaned == "bundle":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid marketplace_kind — use one of: {', '.join(k for k in MERCH_KINDS if k != 'bundle')}",
        )
    product.marketplace_kind = cleaned
    if cleaned == "standalone":
        product.is_event_linked = False
        product.event_id = None
        if product.storefront_visibility in {None, "event_only", ""}:
            product.storefront_visibility = "host_storefront"
    elif cleaned == "event_addon":
        product.is_event_linked = True
        product.requires_ticket = True
        if product.storefront_visibility in {None, ""}:
            product.storefront_visibility = "event_only"
    elif cleaned == "event_merch":
        product.is_event_linked = True
        if product.storefront_visibility in {None, ""}:
            product.storefront_visibility = "event_only"
    elif cleaned == "post_event_drop":
        product.is_event_linked = True
        product.storefront_visibility = "post_event_drop"
    elif cleaned == "vault_exclusive":
        product.is_vault_exclusive = True
        product.requires_vault_access = True
        product.storefront_visibility = "vault_exclusive"


def unique_host_product_slug(db: Session, *, host_id: uuid.UUID, base: str) -> str:
    slug = slugify(base)
    if slug in _RESERVED_SLUGS:
        slug = f"{slug}-merch"
    candidate = slug
    i = 2
    while db.scalar(
        select(EventMerchProduct.id).where(
            EventMerchProduct.host_id == host_id,
            EventMerchProduct.event_id.is_(None),
            EventMerchProduct.slug == candidate,
        )
    ):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def _public_marketplace_base_filters():
    return and_(
        EventMerchProduct.status == "active",
        EventMerchProduct.archived_at.is_(None),
        EventMerchProduct.moderation_status.in_(("clear", "flagged")),
        EventMerchProduct.marketplace_listed.is_(True),
        EventMerchProduct.storefront_visibility.in_(tuple(MARKETPLACE_PUBLIC_VISIBILITIES)),
        EventMerchProduct.storefront_visibility != "private_link",
        EventMerchProduct.storefront_visibility != "hidden",
    )


def _enrich_marketplace_row(
    db: Session,
    product: EventMerchProduct,
    *,
    host: Host | None,
    event: Event | None,
    buyer_user_id: uuid.UUID | None,
) -> dict[str, Any]:
    row = serialize_catalog_product(
        product, event=event, db=db, buyer_user_id=buyer_user_id
    )
    kind = infer_marketplace_kind(product)
    row["marketplace_kind"] = kind
    row["category"] = getattr(product, "category", None)
    row["tags"] = list(getattr(product, "tags", None) or [])
    row["marketplace_listed"] = bool(getattr(product, "marketplace_listed", True))
    row["host_id"] = product.host_id
    row["host_name"] = host.display_name if host else None
    row["host_slug"] = host.slug if host else None
    row["host_username"] = host.slug if host else None
    if event is not None:
        row["event_title"] = event.title
        row["event_slug"] = event.slug
        row["event_start_at"] = event.start_datetime
        # Privacy-safe location label only (never private venue details).
        row["event_location_label"] = getattr(event, "public_location_label", None) or getattr(
            event, "city", None
        )
    else:
        row["event_title"] = None
        row["event_slug"] = None
        row["event_start_at"] = None
        row["event_location_label"] = None

    # Context badges for cards.
    from app.merch.constants import MERCH_KIND_LABELS

    badges: list[str] = [MERCH_KIND_LABELS.get(kind, kind.replace("_", " ").title())]
    if product.status == "sold_out" or row.get("availability") == "sold_out":
        badges.append("Sold out")
    variants = product.variants or []
    total = sum(available_variant_stock(v) for v in variants if v.status == "active")
    if total > 0 and total <= int(getattr(product, "low_stock_threshold", 5) or 5):
        badges.append("Limited")
    if getattr(product, "pickup_enabled", True):
        badges.append("Pickup")
    if getattr(product, "shipping_enabled", False):
        badges.append("Delivery")
    if kind == "event_addon":
        badges.append("Available with ticket")
    row["badges"] = badges
    row["marketplace_path"] = (
        f"/merch/{product.slug}?h={host.slug}" if host else f"/merch/{product.slug}"
    )
    if kind == "post_event_drop" or product.storefront_visibility == "post_event_drop":
        from app.merch.post_event_drops import audience_from_product

        row["audience"] = audience_from_product(product)
    return row


def _load_hosts_events(
    db: Session, products: list[EventMerchProduct]
) -> tuple[dict[uuid.UUID, Host], dict[uuid.UUID, Event]]:
    host_ids = {p.host_id for p in products}
    event_ids = {p.event_id for p in products if p.event_id}
    hosts = {
        h.id: h
        for h in db.scalars(select(Host).where(Host.id.in_(host_ids))).all()
    } if host_ids else {}
    events = {
        e.id: e
        for e in db.scalars(select(Event).where(Event.id.in_(event_ids))).all()
    } if event_ids else {}
    return hosts, events


def _host_is_publicly_sellable(host: Host | None) -> bool:
    if host is None:
        return False
    return host.status not in UNSAFE_HOST_STATUSES


def _host_shop_kind_badges(products: list[EventMerchProduct]) -> list[str]:
    kinds = {infer_marketplace_kind(p) for p in products}
    badges: list[str] = []
    if "standalone" in kinds:
        badges.append("Standalone")
    if kinds & {"event_merch", "event_addon"}:
        badges.append("Event merch")
    if "vault_exclusive" in kinds:
        badges.append("Vault")
    if "post_event_drop" in kinds:
        badges.append("Drops")
    return badges


def _event_is_publicly_listable(event: Event | None) -> bool:
    if event is None:
        return True  # standalone
    if event.status in UNSAFE_EVENT_STATUSES:
        return False
    return event.status in {"published", "completed", "live"}


def list_marketplace_products(
    db: Session,
    *,
    buyer_user_id: uuid.UUID | None = None,
    q: str | None = None,
    host: str | None = None,
    event: str | None = None,
    category: str | None = None,
    merch_kind: str | None = None,
    fulfillment_type: str | None = None,
    availability: str | None = None,
    city: str | None = None,
    vault_only: bool = False,
    drops_only: bool = False,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    sort: str = "featured",
    limit: int = 48,
    offset: int = 0,
) -> dict[str, Any]:
    sort_key = (sort or "featured").strip().lower()
    if sort_key not in MARKETPLACE_SORTS:
        sort_key = "featured"
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    stmt = (
        select(EventMerchProduct)
        .options(selectinload(EventMerchProduct.variants))
        .where(_public_marketplace_base_filters())
    )

    if q:
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(EventMerchProduct.name).like(needle),
                func.lower(func.coalesce(EventMerchProduct.description, "")).like(needle),
                func.lower(func.coalesce(EventMerchProduct.short_description, "")).like(needle),
            )
        )
    if category:
        cat = category.strip().lower()
        if cat in MERCH_CATEGORY_SLUGS:
            stmt = stmt.where(EventMerchProduct.category == cat)
    if merch_kind:
        kind = merch_kind.strip().lower()
        if kind in MERCH_KINDS and kind != "bundle":
            stmt = stmt.where(EventMerchProduct.marketplace_kind == kind)
    if vault_only:
        stmt = stmt.where(
            or_(
                EventMerchProduct.is_vault_exclusive.is_(True),
                EventMerchProduct.storefront_visibility == "vault_exclusive",
                EventMerchProduct.marketplace_kind == "vault_exclusive",
            )
        )
    if drops_only:
        stmt = stmt.where(
            or_(
                EventMerchProduct.storefront_visibility == "post_event_drop",
                EventMerchProduct.marketplace_kind == "post_event_drop",
            )
        )
    if fulfillment_type:
        ft = fulfillment_type.strip().lower()
        if ft in {"pickup", "manual"}:
            stmt = stmt.where(EventMerchProduct.pickup_enabled.is_(True))
        elif ft in {"delivery", "shipping"}:
            stmt = stmt.where(EventMerchProduct.shipping_enabled.is_(True))
        elif ft == "digital":
            stmt = stmt.where(EventMerchProduct.print_on_demand_enabled.is_(True))
    if price_min is not None:
        stmt = stmt.where(EventMerchProduct.base_price >= price_min)
    if price_max is not None:
        stmt = stmt.where(EventMerchProduct.base_price <= price_max)

    if host:
        host_needle = host.strip().lstrip("@").lower()
        host_ids = list(
            db.scalars(
                select(Host.id).where(
                    or_(
                        func.lower(Host.slug) == host_needle,
                        func.lower(Host.display_name).like(f"%{host_needle}%"),
                    )
                )
            ).all()
        )
        if not host_ids:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        stmt = stmt.where(EventMerchProduct.host_id.in_(host_ids))

    if event or city:
        event_stmt = select(Event.id)
        if event:
            ev_needle = event.strip().lower()
            event_stmt = event_stmt.where(
                or_(
                    func.lower(Event.slug) == ev_needle,
                    func.lower(Event.title).like(f"%{ev_needle}%"),
                )
            )
        if city:
            city_needle = f"%{city.strip().lower()}%"
            # Prefer city / venue public fields when present.
            city_cols = []
            for attr in ("city", "location_label", "venue_name"):
                if hasattr(Event, attr):
                    city_cols.append(func.lower(func.coalesce(getattr(Event, attr), "")).like(city_needle))
            if city_cols:
                event_stmt = event_stmt.where(or_(*city_cols))
        event_ids = list(db.scalars(event_stmt).all())
        if not event_ids:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        stmt = stmt.where(EventMerchProduct.event_id.in_(event_ids))

    if sort_key == "newest":
        stmt = stmt.order_by(EventMerchProduct.created_at.desc())
    elif sort_key == "price_asc":
        stmt = stmt.order_by(EventMerchProduct.base_price.asc(), EventMerchProduct.created_at.desc())
    elif sort_key == "price_desc":
        stmt = stmt.order_by(EventMerchProduct.base_price.desc(), EventMerchProduct.created_at.desc())
    elif sort_key == "popular":
        # Approximate popularity via sold variant quantity.
        sold = (
            select(
                EventMerchVariant.product_id.label("pid"),
                func.coalesce(func.sum(EventMerchVariant.sold_quantity), 0).label("sold"),
            )
            .group_by(EventMerchVariant.product_id)
            .subquery()
        )
        stmt = (
            stmt.outerjoin(sold, sold.c.pid == EventMerchProduct.id)
            .order_by(func.coalesce(sold.c.sold, 0).desc(), EventMerchProduct.is_featured.desc())
        )
    else:
        stmt = stmt.order_by(
            EventMerchProduct.is_featured.desc(),
            EventMerchProduct.created_at.desc(),
        )

    # Fetch a window then filter host/event safety in Python (status joins stay simple).
    rows = list(db.scalars(stmt.offset(offset).limit(limit + 40)).all())
    hosts, events = _load_hosts_events(db, rows)
    items: list[dict[str, Any]] = []
    for product in rows:
        host_row = hosts.get(product.host_id)
        event_row = events.get(product.event_id) if product.event_id else None
        if not _host_is_publicly_sellable(host_row):
            continue
        if product.event_id and not _event_is_publicly_listable(event_row):
            continue
        # Vault exclusives: always include as safe teasers (serializer strips secrets).
        enriched = _enrich_marketplace_row(
            db,
            product,
            host=host_row,
            event=event_row,
            buyer_user_id=buyer_user_id,
        )
        if availability:
            avail = availability.strip().lower()
            if avail == "sold_out" and enriched.get("availability") != "sold_out":
                continue
            if avail in {"available", "in_stock", "purchasable"} and enriched.get(
                "availability"
            ) != "purchasable":
                continue
            if avail == "coming_soon" and enriched.get("availability") != "coming_soon":
                continue
        items.append(enriched)
        if len(items) >= limit:
            break

    return {
        "items": items,
        "total": offset + len(items),  # approximate window total
        "limit": limit,
        "offset": offset,
        "sort": sort_key,
    }


def get_marketplace_homepage(
    db: Session, *, buyer_user_id: uuid.UUID | None = None
) -> dict[str, Any]:
    featured = list_marketplace_products(
        db, buyer_user_id=buyer_user_id, sort="featured", limit=12
    )["items"]
    event_merch = list_marketplace_products(
        db, buyer_user_id=buyer_user_id, merch_kind="event_merch", sort="newest", limit=12
    )["items"]
    # Also include add-ons in event rail.
    addons = list_marketplace_products(
        db, buyer_user_id=buyer_user_id, merch_kind="event_addon", sort="newest", limit=8
    )["items"]
    event_rail = (event_merch + addons)[:12]
    drops = list_marketplace_products(
        db, buyer_user_id=buyer_user_id, drops_only=True, sort="newest", limit=12
    )["items"]
    vault = list_marketplace_products(
        db, buyer_user_id=buyer_user_id, vault_only=True, sort="featured", limit=12
    )["items"]
    hosts = list_marketplace_host_shops(db, limit=12)
    categories = list_marketplace_categories(db)
    return {
        "featured": featured,
        "event_merch": event_rail,
        "host_shops": hosts,
        "drops": drops,
        "vault_exclusives": vault,
        "categories": categories,
        "empty": not any([featured, event_rail, hosts, drops, vault]),
    }


def list_marketplace_drops(
    db: Session, *, buyer_user_id: uuid.UUID | None = None, limit: int = 48
) -> dict[str, Any]:
    result = list_marketplace_products(
        db, buyer_user_id=buyer_user_id, drops_only=True, sort="newest", limit=limit
    )
    return result


def list_marketplace_vault(
    db: Session, *, buyer_user_id: uuid.UUID | None = None, limit: int = 48
) -> dict[str, Any]:
    """Vault exclusives as safe teasers — locked details never exposed."""
    return list_marketplace_products(
        db, buyer_user_id=buyer_user_id, vault_only=True, sort="featured", limit=limit
    )


def list_marketplace_host_shops(db: Session, *, limit: int = 24) -> list[dict[str, Any]]:
    """Hosts with at least one active, marketplace-listed public merch product."""
    limit = max(1, min(limit, 60))
    stmt = (
        select(
            Host.id,
            Host.display_name,
            Host.slug,
            HostProfile.avatar_url,
            func.count(EventMerchProduct.id).label("merch_count"),
        )
        .join(EventMerchProduct, EventMerchProduct.host_id == Host.id)
        .outerjoin(HostProfile, HostProfile.host_id == Host.id)
        .where(
            Host.status.notin_(tuple(UNSAFE_HOST_STATUSES)),
            _public_marketplace_base_filters(),
        )
        .group_by(Host.id, Host.display_name, Host.slug, HostProfile.avatar_url)
        .having(func.count(EventMerchProduct.id) > 0)
        .order_by(func.count(EventMerchProduct.id).desc())
        .limit(limit)
    )
    shops: list[dict[str, Any]] = []
    for host_id, display_name, slug, avatar_url, merch_count in db.execute(stmt).all():
        catalog = list(
            db.scalars(
                select(EventMerchProduct)
                .options(selectinload(EventMerchProduct.variants))
                .where(
                    EventMerchProduct.host_id == host_id,
                    _public_marketplace_base_filters(),
                )
                .order_by(EventMerchProduct.created_at.desc())
            ).all()
        )
        host = db.get(Host, host_id)
        events = {
            e.id: e
            for e in db.scalars(
                select(Event).where(
                    Event.id.in_({p.event_id for p in catalog if p.event_id})
                )
            ).all()
        }
        latest = catalog[:3]
        latest_rows = [
            _enrich_marketplace_row(
                db,
                p,
                host=host,
                event=events.get(p.event_id) if p.event_id else None,
                buyer_user_id=None,
            )
            for p in latest
        ]
        shops.append(
            {
                "host_id": host_id,
                "host_name": display_name,
                "host_slug": slug,
                "host_username": slug,
                "host_avatar_url": avatar_url,
                "merch_count": int(merch_count),
                "shop_badges": _host_shop_kind_badges(catalog),
                "latest_products": latest_rows,
                "shop_path": f"/merch/hosts/{slug}",
                "storefront_path": f"/u/{slug}/merch",
            }
        )
    return shops


def get_marketplace_host_shop(
    db: Session,
    *,
    username: str,
    buyer_user_id: uuid.UUID | None = None,
    product_type: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    """Public marketplace host shop — listed merch without legacy storefront gate."""
    slug = username.strip().lstrip("@").lower()
    host = db.scalar(
        select(Host)
        .where(func.lower(Host.slug) == slug)
        .options(selectinload(Host.profile))
    )
    if host is None or not _host_is_publicly_sellable(host):
        raise HTTPException(status_code=404, detail="Host shop not found")

    profile = host.profile
    if profile is None:
        profile = db.scalar(select(HostProfile).where(HostProfile.host_id == host.id))

    rows = list(
        db.scalars(
            select(EventMerchProduct)
            .options(selectinload(EventMerchProduct.variants))
            .where(
                EventMerchProduct.host_id == host.id,
                _public_marketplace_base_filters(),
            )
            .order_by(
                EventMerchProduct.is_featured.desc(),
                EventMerchProduct.created_at.desc(),
            )
        ).all()
    )
    events = {
        e.id: e
        for e in db.scalars(
            select(Event).where(
                Event.id.in_({p.event_id for p in rows if p.event_id})
            )
        ).all()
    }
    products: list[dict[str, Any]] = []
    events_meta: dict[str, dict[str, Any]] = {}
    types: set[str] = set()
    for product in rows:
        event_row = events.get(product.event_id) if product.event_id else None
        if product.event_id and not _event_is_publicly_listable(event_row):
            continue
        enriched = _enrich_marketplace_row(
            db,
            product,
            host=host,
            event=event_row,
            buyer_user_id=buyer_user_id,
        )
        products.append(enriched)
        if enriched.get("product_type"):
            types.add(str(enriched["product_type"]))
        ev_slug = enriched.get("event_slug")
        if ev_slug and not enriched.get("event_is_private"):
            events_meta[str(ev_slug)] = {
                "event_id": enriched.get("event_id"),
                "event_slug": ev_slug,
                "event_title": enriched.get("event_title"),
            }

    type_filter = (product_type or "").strip()
    if type_filter:
        products = [r for r in products if (r.get("product_type") or "") == type_filter]
    kind_filter = (kind or "").strip().lower()
    if kind_filter in {"post_event", "post_event_drop", "drop"}:
        products = [
            r
            for r in products
            if r.get("marketplace_kind") == "post_event_drop"
            or r.get("is_post_event_drop")
        ]
    elif kind_filter in {"vault", "vault_exclusive"}:
        products = [
            r
            for r in products
            if r.get("marketplace_kind") == "vault_exclusive"
            or r.get("is_vault_exclusive")
        ]
    elif kind_filter in {"host_storefront", "evergreen", "merch_only", "standalone"}:
        products = [
            r
            for r in products
            if r.get("marketplace_kind") in {"standalone", "event_merch", "event_addon"}
            and not r.get("is_post_event_drop")
            and not r.get("is_vault_exclusive")
        ]

    title = (
        (profile.merch_storefront_title if profile else None)
        or f"{host.display_name} merch"
    )
    description = (
        (profile.merch_storefront_description if profile else None)
        or "Official merch from this Pàdéyá host — standalone, event, drops, and Vault teasers."
    )
    host_slug = host.slug

    return {
        "host_id": host.id,
        "host_name": host.display_name,
        "host_slug": host_slug,
        "host_username": host_slug,
        "host_avatar_url": profile.avatar_url if profile else None,
        "storefront_title": title,
        "storefront_description": description,
        "storefront_enabled": bool(profile.merch_storefront_enabled if profile else False),
        "products": products,
        "product_count": len(products),
        "shop_path": f"/merch/hosts/{host_slug}",
        "storefront_path": f"/u/{host_slug}/merch",
        "empty": not products,
        "empty_message": "This host has not added merch yet.",
        "filters": {
            "events": list(events_meta.values()),
            "product_types": sorted(types),
            "availabilities": ["purchasable", "coming_soon", "locked", "sold_out"],
            "kinds": ["standalone", "event_merch", "post_event_drop", "vault_exclusive"],
        },
    }


def get_marketplace_product_by_slug(
    db: Session,
    *,
    slug: str,
    host_slug: str | None = None,
    buyer_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    cleaned = slugify(slug)
    if cleaned in _RESERVED_SLUGS:
        raise HTTPException(status_code=404, detail="Merch not found")

    stmt = (
        select(EventMerchProduct)
        .options(selectinload(EventMerchProduct.variants))
        .where(
            EventMerchProduct.slug == cleaned,
            EventMerchProduct.status == "active",
            EventMerchProduct.archived_at.is_(None),
            EventMerchProduct.moderation_status.in_(("clear", "flagged")),
            EventMerchProduct.storefront_visibility != "hidden",
            EventMerchProduct.storefront_visibility != "private_link",
        )
    )
    if host_slug:
        host = db.scalar(
            select(Host).where(func.lower(Host.slug) == host_slug.strip().lstrip("@").lower())
        )
        if host is None:
            raise HTTPException(status_code=404, detail="Merch not found")
        stmt = stmt.where(EventMerchProduct.host_id == host.id)

    products = list(db.scalars(stmt.order_by(EventMerchProduct.created_at.desc()).limit(5)).all())
    if not products:
        raise HTTPException(status_code=404, detail="Merch not found")

    # Prefer marketplace-listed / featured when slug collides.
    product = next(
        (p for p in products if getattr(p, "marketplace_listed", True) and p.is_featured),
        products[0],
    )
    host = db.get(Host, product.host_id)
    if not _host_is_publicly_sellable(host):
        raise HTTPException(status_code=404, detail="Merch not found")
    event = db.get(Event, product.event_id) if product.event_id else None
    if product.event_id and not _event_is_publicly_listable(event):
        raise HTTPException(status_code=404, detail="Merch not found")

    row = _enrich_marketplace_row(
        db, product, host=host, event=event, buyer_user_id=buyer_user_id
    )

    # More by host (standalone context).
    more = []
    if host is not None:
        siblings = list(
            db.scalars(
                select(EventMerchProduct)
                .options(selectinload(EventMerchProduct.variants))
                .where(
                    EventMerchProduct.host_id == host.id,
                    EventMerchProduct.id != product.id,
                    _public_marketplace_base_filters(),
                )
                .order_by(EventMerchProduct.created_at.desc())
                .limit(6)
            ).all()
        )
        more = [
            _enrich_marketplace_row(
                db, s, host=host, event=None, buyer_user_id=buyer_user_id
            )
            for s in siblings
        ]

    row["more_by_host"] = more
    row["host_shop_path"] = f"/merch/hosts/{host.slug}" if host else None
    row["host_public_path"] = f"/u/{host.slug}" if host else None
    row["indexable"] = bool(
        getattr(product, "marketplace_listed", True)
        and product.storefront_visibility
        not in {"vault_exclusive", "private_link", "hidden", "event_only"}
        and not product.is_vault_exclusive
    )
    return row


def list_marketplace_categories(db: Session) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(MerchCategory)
            .where(MerchCategory.status == "active", MerchCategory.archived_at.is_(None))
            .order_by(MerchCategory.sort_order.asc(), MerchCategory.name.asc())
        ).all()
    )
    if rows:
        return [
            {
                "id": r.id,
                "slug": r.slug,
                "name": r.name,
                "description": r.description,
                "sort_order": r.sort_order,
            }
            for r in rows
        ]
    # Fallback to constants when table empty (pre-migrate / tests).
    return [
        {
            "id": None,
            "slug": slug,
            "name": MERCH_CATEGORY_LABELS[slug],
            "description": None,
            "sort_order": i * 10,
        }
        for i, slug in enumerate(MERCH_CATEGORY_SLUGS)
    ]


def get_event_merch_by_slug(
    db: Session,
    *,
    event_slug: str,
    buyer_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    from app.merch.service import get_public_catalog

    event = db.scalar(select(Event).where(func.lower(Event.slug) == event_slug.strip().lower()))
    if event is None or event.status in UNSAFE_EVENT_STATUSES:
        raise HTTPException(status_code=404, detail="Event not found")
    catalog = get_public_catalog(
        db, event_id=event.id, buyer_user_id=buyer_user_id
    )
    host = db.get(Host, event.host_id)
    items = []
    for row in catalog:
        # Attach marketplace kind hints when possible.
        product = db.get(EventMerchProduct, row["id"])
        if product is None:
            items.append(row)
            continue
        items.append(
            _enrich_marketplace_row(
                db, product, host=host, event=event, buyer_user_id=buyer_user_id
            )
        )
    return {
        "event_id": event.id,
        "event_slug": event.slug,
        "event_title": event.title,
        "host_name": host.display_name if host else None,
        "host_slug": host.slug if host else None,
        "items": items,
        "empty": not items,
    }


def admin_list_categories(db: Session) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(MerchCategory).order_by(
                MerchCategory.sort_order.asc(), MerchCategory.name.asc()
            )
        ).all()
    )
    return [
        {
            "id": r.id,
            "slug": r.slug,
            "name": r.name,
            "description": r.description,
            "sort_order": r.sort_order,
            "status": r.status,
            "archived_at": r.archived_at,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


def admin_upsert_category(
    db: Session,
    *,
    category_id: uuid.UUID | None = None,
    slug: str,
    name: str,
    description: str | None = None,
    sort_order: int = 0,
    status: str = "active",
) -> dict[str, Any]:
    cleaned_slug = slugify(slug)
    cleaned_name = name.strip()
    if not cleaned_slug or not cleaned_name:
        raise HTTPException(status_code=400, detail="slug and name are required")
    if status not in {"active", "hidden", "archived"}:
        raise HTTPException(status_code=400, detail="Invalid category status")

    row: MerchCategory | None = None
    if category_id is not None:
        row = db.get(MerchCategory, category_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Category not found")
    else:
        existing = db.scalar(select(MerchCategory).where(MerchCategory.slug == cleaned_slug))
        if existing is not None:
            row = existing
        else:
            row = MerchCategory(slug=cleaned_slug)
            db.add(row)

    row.slug = cleaned_slug
    row.name = cleaned_name
    row.description = (description or "").strip() or None
    row.sort_order = int(sort_order)
    row.status = status
    if status == "archived":
        row.archived_at = datetime.now(UTC)
    elif row.archived_at is not None and status == "active":
        row.archived_at = None
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "sort_order": row.sort_order,
        "status": row.status,
        "archived_at": row.archived_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
