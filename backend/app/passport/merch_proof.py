"""Safe merch proof aggregates for Fan Passport and Host Legacy.

Never include spend amounts, order IDs, payment refs, emails, or buyer identities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import Event, EventCategory
from app.hosts.models import Host
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchFulfillment
from app.passport.constants import (
    CULTURE_FEST_CATEGORY_SLUGS,
    CULTURE_FEST_COLLECTOR_THRESHOLD,
    FOUNDER_MODE_CATEGORY_SLUGS,
    MERCH_COLLECTOR_THRESHOLD,
)


def _active_fulfillments(db: Session, *, user_id: UUID | None = None, host_id: UUID | None = None):
    stmt = select(MerchFulfillment).where(MerchFulfillment.status != "cancelled")
    if user_id is not None:
        stmt = stmt.where(MerchFulfillment.buyer_user_id == user_id)
    if host_id is not None:
        stmt = stmt.where(MerchFulfillment.host_id == host_id)
    return list(db.scalars(stmt))


def _product_context(
    db: Session, fulfillments: list[MerchFulfillment]
) -> list[tuple[MerchFulfillment, EventMerchProduct, Event | None, EventCategory | None, Host | None]]:
    if not fulfillments:
        return []
    variant_ids = {f.merch_variant_id for f in fulfillments}
    variants = {
        v.id: v
        for v in db.scalars(select(EventMerchVariant).where(EventMerchVariant.id.in_(variant_ids)))
    }
    product_ids = {v.product_id for v in variants.values()}
    products = {
        p.id: p
        for p in db.scalars(select(EventMerchProduct).where(EventMerchProduct.id.in_(product_ids)))
    } if product_ids else {}
    event_ids = {f.event_id for f in fulfillments if f.event_id} | {
        p.event_id for p in products.values() if p.event_id
    }
    events = {
        e.id: e for e in db.scalars(select(Event).where(Event.id.in_(event_ids)))
    } if event_ids else {}
    category_ids = {e.category_id for e in events.values() if e.category_id}
    categories = {
        c.id: c
        for c in db.scalars(select(EventCategory).where(EventCategory.id.in_(category_ids)))
    } if category_ids else {}
    host_ids = {f.host_id for f in fulfillments}
    hosts = {
        h.id: h for h in db.scalars(select(Host).where(Host.id.in_(host_ids)))
    } if host_ids else {}

    out = []
    for f in fulfillments:
        variant = variants.get(f.merch_variant_id)
        if variant is None:
            continue
        product = products.get(variant.product_id)
        if product is None:
            continue
        event = events.get(f.event_id or product.event_id) if (f.event_id or product.event_id) else None
        cat = categories.get(event.category_id) if event and event.category_id else None
        host = hosts.get(f.host_id)
        out.append((f, product, event, cat, host))
    return out


def _is_culture_fest_event(event: Event | None, category: EventCategory | None) -> bool:
    """Culture/fest scoped — category art-culture, or title/slug with 'culture'.

    Bare 'fest' alone is not enough (avoids matching generic slugs like merch-fest).
    """
    if category and category.slug in CULTURE_FEST_CATEGORY_SLUGS:
        return True
    if event is None:
        return False
    blob = f"{event.slug or ''} {event.title or ''}".lower()
    return "culture" in blob


def _is_founder_mode_context(
    *,
    product: EventMerchProduct,
    event: Event | None,
    category: EventCategory | None,
    host: Host | None,
) -> bool:
    name = (product.name or "").lower()
    if "founder" in name:
        return True
    if host and (host.slug or "").lower() in {"techconnectafrica", "tech-connect-africa"}:
        return True
    if category and category.slug in FOUNDER_MODE_CATEGORY_SLUGS:
        if event is not None:
            blob = f"{event.slug or ''} {event.title or ''}".lower()
            if "founder" in blob or "tech" in blob or "connect" in blob:
                return True
        # Tech/business category merch still counts for founder-mode gear
        return category.slug in FOUNDER_MODE_CATEGORY_SLUGS
    if event is not None:
        blob = f"{event.slug or ''} {event.title or ''}".lower()
        return "founder" in blob
    return False


def evaluate_merch_badge_flags(db: Session, user_id: UUID) -> dict[str, bool]:
    """Deterministic merch criteria — paid fulfillments only; never spend amounts."""
    rows = _product_context(db, _active_fulfillments(db, user_id=user_id))
    product_ids: set[UUID] = set()
    culture_products: set[UUID] = set()
    vip_pack = False
    drop_supporter = False
    vault_merch = False
    sponsor_merch = False
    founder_gear = False

    for _f, product, event, cat, host in rows:
        product_ids.add(product.id)
        if product.product_type == "vip_pack":
            vip_pack = True
        if product.storefront_visibility == "post_event_drop" or product.post_event_drop_at:
            drop_supporter = True
        if product.is_vault_exclusive:
            vault_merch = True
        if product.is_sponsor_branded:
            sponsor_merch = True
        if _is_culture_fest_event(event, cat):
            culture_products.add(product.id)
        if _is_founder_mode_context(product=product, event=event, category=cat, host=host):
            founder_gear = True

    return {
        "first_merch_buy": len(rows) >= 1,
        "merch_collector": len(product_ids) >= MERCH_COLLECTOR_THRESHOLD,
        "vip_pack_owner": vip_pack,
        "event_drop_supporter": drop_supporter,
        "vault_merch_member": vault_merch,
        "sponsor_drop_supporter": sponsor_merch,
        "culture_fest_collector": len(culture_products) >= CULTURE_FEST_COLLECTOR_THRESHOLD,
        "founder_mode_gear": founder_gear,
    }


def fan_merch_proof_counts(db: Session, user_id: UUID) -> dict[str, int]:
    """Count-only merch proof for a fan — never amounts or order refs."""
    rows = _product_context(db, _active_fulfillments(db, user_id=user_id))
    drop_event_ids: set[UUID] = set()
    host_ids: set[UUID] = set()
    product_ids: set[UUID] = set()
    for f, product, event, _cat, _host in rows:
        product_ids.add(product.id)
        host_ids.add(f.host_id)
        if product.storefront_visibility == "post_event_drop" or product.post_event_drop_at:
            if event is not None:
                drop_event_ids.add(event.id)
            elif f.event_id:
                drop_event_ids.add(f.event_id)
    return {
        "paid_items": len(rows),
        "distinct_products": len(product_ids),
        "hosts_collected_from": len(host_ids),
        "event_drops_supported": len(drop_event_ids),
    }


def fan_merch_proof_summaries(db: Session, user_id: UUID) -> list[str]:
    """Safe Fan Passport copy — counts only, never spend."""
    counts = fan_merch_proof_counts(db, user_id)
    out: list[str] = []
    drops = counts["event_drops_supported"]
    hosts = counts["hosts_collected_from"]
    products = counts["distinct_products"]
    if drops:
        out.append(
            f"Supported {drops} event merch drop{'s' if drops != 1 else ''}"
        )
    if hosts:
        out.append(
            f"Collected merch from {hosts} host{'s' if hosts != 1 else ''}"
        )
    if products and not out:
        out.append(
            f"Collected {products} merch product{'s' if products != 1 else ''}"
        )
    return out


def host_merch_proof_counts(db: Session, host_id: UUID) -> dict[str, int]:
    """Host Legacy aggregates — item/fan counts only, no buyer identities."""
    items_sold = int(
        db.scalar(
            select(func.coalesce(func.sum(MerchFulfillment.quantity), 0)).where(
                MerchFulfillment.host_id == host_id,
                MerchFulfillment.status != "cancelled",
            )
        )
        or 0
    )
    fans = int(
        db.scalar(
            select(func.count(func.distinct(MerchFulfillment.buyer_user_id))).where(
                MerchFulfillment.host_id == host_id,
                MerchFulfillment.status != "cancelled",
            )
        )
        or 0
    )
    return {"merch_items_sold": items_sold, "fans_collected_merch": fans}


def host_merch_proof_summaries(db: Session, host_id: UUID) -> list[str]:
    """Safe Host Legacy proof lines — no buyer list or order data."""
    counts = host_merch_proof_counts(db, host_id)
    items = counts["merch_items_sold"]
    fans = counts["fans_collected_merch"]
    out: list[str] = []
    if items:
        out.append(f"{items} merch item{'s' if items != 1 else ''} sold")
    if fans:
        out.append(
            f"{fans} fan{'s' if fans != 1 else ''} collected event merch"
        )
    return out
