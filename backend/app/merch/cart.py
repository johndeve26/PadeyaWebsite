"""Abandoned cart recovery — never invents paid state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event
from app.hosts.models import Host
from app.merch.access import product_is_drop_live
from app.merch.constants import UNSAFE_EVENT_STATUSES
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchCart, MerchCartItem
from app.merch.service import _sales_window_open, available_variant_stock, effective_variant_price
from app.users.models import User


def _abandon_after_hours(db: Session | None = None) -> int:
    from app.runtime_settings import get_runtime_setting

    return int(
        get_runtime_setting("merch_cart_abandon_after_hours", db=db) or 24
    )


def _expire_after_days(db: Session | None = None) -> int:
    from app.runtime_settings import get_runtime_setting

    return int(get_runtime_setting("merch_cart_expire_after_days", db=db) or 14)


def _recovery_min_gap_hours(db: Session | None = None) -> int:
    from app.runtime_settings import get_runtime_setting

    return int(
        get_runtime_setting("merch_cart_recovery_min_gap_hours", db=db) or 72
    )


def serialize_cart(cart: MerchCart, *, db: Session | None = None) -> dict:
    event_slug: str | None = None
    host_slug: str | None = None
    if cart.event_id and db is not None:
        event = db.get(Event, cart.event_id)
        event_slug = event.slug if event else None
    if cart.host_id and db is not None:
        host = db.get(Host, cart.host_id)
        host_slug = host.slug if host else None
    if event_slug:
        resume_path = f"/events/{event_slug}/checkout"
    elif host_slug:
        resume_path = f"/merch/hosts/{host_slug}/checkout"
    else:
        resume_path = "/dashboard/cart"
    return {
        "id": cart.id,
        "status": cart.status,
        "event_id": cart.event_id,
        "event_slug": event_slug,
        "host_id": cart.host_id,
        "host_slug": host_slug,
        "last_activity_at": cart.last_activity_at,
        "recovery_sent_at": cart.recovery_sent_at,
        "order_id": cart.order_id,
        "resume_path": resume_path,
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "variant_id": i.variant_id,
                "quantity": i.quantity,
                "unit_price_snapshot": i.unit_price_snapshot,
                "product_name_snapshot": i.product_name_snapshot,
                "variant_label_snapshot": i.variant_label_snapshot,
            }
            for i in (cart.items or [])
        ],
        # Never mark paid from cart; no address/payment/buyer private data
    }


def get_or_create_cart(
    db: Session,
    *,
    user: User | None,
    anonymous_id: str | None = None,
    event_id: uuid.UUID | None = None,
    host_id: uuid.UUID | None = None,
) -> MerchCart:
    stmt = (
        select(MerchCart)
        .where(MerchCart.status.in_(("active", "abandoned")))
        .options(selectinload(MerchCart.items))
    )
    if user is not None:
        stmt = stmt.where(MerchCart.buyer_user_id == user.id)
    elif anonymous_id:
        stmt = stmt.where(MerchCart.anonymous_id == anonymous_id)
    else:
        raise HTTPException(status_code=400, detail="Login or anonymous_id required")
    cart = db.scalar(stmt.order_by(MerchCart.updated_at.desc()))
    if cart is None:
        cart = MerchCart(
            buyer_user_id=user.id if user else None,
            anonymous_id=anonymous_id if user is None else None,
            event_id=event_id,
            host_id=host_id,
            status="active",
            last_activity_at=datetime.now(UTC),
        )
        db.add(cart)
        db.flush()
    elif cart.status == "abandoned":
        # Resume shopping — clear one-shot recovery latch for new activity
        cart.status = "active"
        cart.recovery_sent_at = None
        from app.analytics.trusted import emit_merch_abandoned_cart_recovered

        emit_merch_abandoned_cart_recovered(
            db,
            cart_id=cart.id,
            event_id=cart.event_id,
            host_id=cart.host_id,
            buyer_user_id=cart.buyer_user_id,
            method="reactivated",
        )
    return cart


def add_cart_item(
    db: Session,
    *,
    user: User | None,
    variant_id: uuid.UUID,
    quantity: int,
    anonymous_id: str | None = None,
) -> dict:
    variant = db.get(EventMerchVariant, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    product = db.get(EventMerchProduct, variant.product_id)
    if product is None or product.status != "active":
        raise HTTPException(status_code=400, detail="Product not available")
    if available_variant_stock(variant) < quantity:
        raise HTTPException(status_code=409, detail="Not enough stock")
    cart = get_or_create_cart(
        db,
        user=user,
        anonymous_id=anonymous_id,
        event_id=product.event_id,
        host_id=product.host_id,
    )
    existing = next((i for i in cart.items if i.variant_id == variant_id), None)
    unit = effective_variant_price(product, variant)
    if existing:
        new_qty = existing.quantity + quantity
        if available_variant_stock(variant) < new_qty:
            raise HTTPException(status_code=409, detail="Not enough stock")
        existing.quantity = new_qty
        existing.unit_price_snapshot = unit
    else:
        db.add(
            MerchCartItem(
                cart_id=cart.id,
                product_id=product.id,
                variant_id=variant.id,
                quantity=quantity,
                unit_price_snapshot=unit,
                product_name_snapshot=product.name,
                variant_label_snapshot=variant.label,
            )
        )
    cart.last_activity_at = datetime.now(UTC)
    cart.host_id = product.host_id
    cart.event_id = product.event_id
    db.commit()
    db.refresh(cart)
    return serialize_cart(cart, db=db)


def set_cart_item_quantity(
    db: Session, *, user: User, item_id: uuid.UUID, quantity: int
) -> dict:
    """Set a cart line to an exact quantity (not additive like add_cart_item)."""
    cart = db.scalar(
        select(MerchCart)
        .where(
            MerchCart.buyer_user_id == user.id,
            MerchCart.status.in_(("active", "abandoned")),
        )
        .options(selectinload(MerchCart.items))
    )
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    variant = db.get(EventMerchVariant, item.variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    if available_variant_stock(variant) < quantity:
        raise HTTPException(status_code=409, detail="Not enough stock")
    item.quantity = quantity
    cart.last_activity_at = datetime.now(UTC)
    if cart.status == "abandoned":
        cart.status = "active"
        cart.recovery_sent_at = None
    db.commit()
    db.refresh(cart)
    return serialize_cart(cart, db=db)


def get_buyer_cart(db: Session, *, user: User) -> dict | None:
    cart = db.scalar(
        select(MerchCart)
        .where(
            MerchCart.buyer_user_id == user.id,
            MerchCart.status.in_(("active", "abandoned")),
        )
        .options(selectinload(MerchCart.items))
        .order_by(MerchCart.updated_at.desc())
    )
    if cart is None:
        return None
    return serialize_cart(cart, db=db)


def remove_cart_item(
    db: Session, *, user: User, item_id: uuid.UUID
) -> dict | None:
    cart = db.scalar(
        select(MerchCart)
        .where(
            MerchCart.buyer_user_id == user.id,
            MerchCart.status.in_(("active", "abandoned")),
        )
        .options(selectinload(MerchCart.items))
    )
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    cart.last_activity_at = datetime.now(UTC)
    if cart.status == "abandoned":
        cart.status = "active"
        cart.recovery_sent_at = None
        from app.analytics.trusted import emit_merch_abandoned_cart_recovered

        emit_merch_abandoned_cart_recovered(
            db,
            cart_id=cart.id,
            event_id=cart.event_id,
            host_id=cart.host_id,
            buyer_user_id=cart.buyer_user_id,
            method="reactivated",
        )
    db.commit()
    db.refresh(cart)
    return serialize_cart(cart, db=db)


def mark_cart_converted(db: Session, *, user_id: uuid.UUID, order_id: uuid.UUID) -> None:
    """Link cart to a paid order. Call only after verified payment webhook."""
    cart = db.scalar(
        select(MerchCart).where(
            MerchCart.buyer_user_id == user_id,
            MerchCart.status.in_(("active", "abandoned")),
        )
    )
    if cart is None:
        return
    was_abandoned = cart.status == "abandoned"
    cart.status = "converted"
    cart.order_id = order_id
    db.flush()
    if was_abandoned:
        from app.analytics.trusted import emit_merch_abandoned_cart_recovered

        emit_merch_abandoned_cart_recovered(
            db,
            cart_id=cart.id,
            event_id=cart.event_id,
            host_id=cart.host_id,
            buyer_user_id=cart.buyer_user_id,
            order_id=order_id,
            method="converted",
        )


def _line_is_recoverable(
    db: Session,
    *,
    item: MerchCartItem,
    now: datetime,
) -> bool:
    variant = db.get(EventMerchVariant, item.variant_id)
    product = db.get(EventMerchProduct, item.product_id)
    if variant is None or product is None:
        return False
    if product.status != "active" or getattr(product, "archived_at", None) is not None:
        return False
    mod = getattr(product, "moderation_status", None) or "clear"
    if mod in {"hidden", "removed"}:
        return False
    if variant.status != "active" or getattr(variant, "archived_at", None) is not None:
        return False
    if available_variant_stock(variant) < int(item.quantity or 0):
        return False
    if not _sales_window_open(product, now=now):
        return False
    if not product_is_drop_live(product, now=now):
        return False

    eid = product.event_id
    if eid is None:
        return True  # evergreen / host storefront merch
    event = db.get(Event, eid)
    if event is None:
        return False
    if event.status != "published" or event.status in UNSAFE_EVENT_STATUSES:
        return False
    end = event.end_datetime
    if end is None:
        return True
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    if now <= end:
        return True
    # Event ended — only post-event drop or an explicit open sales window
    if product.storefront_visibility == "post_event_drop":
        return True
    sales_end = getattr(product, "sales_end_at", None)
    if sales_end is not None:
        if sales_end.tzinfo is None:
            sales_end = sales_end.replace(tzinfo=UTC)
        return now <= sales_end
    return False


def _user_recovery_rate_limited(
    db: Session, *, user_id: uuid.UUID, now: datetime
) -> bool:
    from app.messaging.models import InAppNotification

    gap = timedelta(hours=_recovery_min_gap_hours(db))
    last = db.scalar(
        select(InAppNotification.created_at)
        .where(
            InAppNotification.user_id == user_id,
            InAppNotification.kind == "merch.cart_reminder",
        )
        .order_by(InAppNotification.created_at.desc())
        .limit(1)
    )
    if last is None:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return (now - last) < gap


def _buyer_accepts_reminders(db: Session, *, user_id: uuid.UUID) -> bool:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return False
    if getattr(user, "deactivated_at", None) is not None:
        return False
    return True


def recover_abandoned_carts(db: Session, *, limit: int = 50) -> int:
    """Idempotent job: mark abandoned + send one in-app reminder. No payment invention."""
    now = datetime.now(UTC)
    abandon_before = now - timedelta(hours=_abandon_after_hours(db))
    expire_before = now - timedelta(days=_expire_after_days(db))
    sent = 0
    host_summary: dict[uuid.UUID, int] = {}

    stale = list(
        db.scalars(
            select(MerchCart)
            .where(
                MerchCart.status == "active",
                MerchCart.last_activity_at < abandon_before,
            )
            .options(selectinload(MerchCart.items))
            .limit(limit)
        )
    )
    for cart in stale:
        cart.status = "abandoned"
        from app.analytics.trusted import emit_merch_abandoned_cart_created

        emit_merch_abandoned_cart_created(
            db,
            cart_id=cart.id,
            event_id=cart.event_id,
            host_id=cart.host_id,
            buyer_user_id=cart.buyer_user_id,
            merch_item_count=len(cart.items or []),
        )

    abandoned = list(
        db.scalars(
            select(MerchCart)
            .where(
                MerchCart.status == "abandoned",
                MerchCart.recovery_sent_at.is_(None),
                MerchCart.buyer_user_id.is_not(None),
            )
            .options(selectinload(MerchCart.items))
            .limit(limit)
        )
    )
    from app.merch.notifications import (
        notify_buyer_cart_reminder,
        notify_host_abandoned_cart_summary,
    )

    for cart in abandoned:
        if not cart.items:
            cart.status = "expired"
            continue
        if not _buyer_accepts_reminders(db, user_id=cart.buyer_user_id):
            continue
        if _user_recovery_rate_limited(db, user_id=cart.buyer_user_id, now=now):
            continue

        sellable = False
        for item in cart.items:
            if _line_is_recoverable(db, item=item, now=now):
                sellable = True
                break
        if not sellable:
            cart.status = "expired"
            continue

        notified = notify_buyer_cart_reminder(db, cart=cart)
        if not notified:
            # Muted / declined — leave recovery_sent_at unset until prefs allow or expire
            continue
        cart.recovery_sent_at = now
        sent += 1
        if cart.host_id is not None:
            host_summary[cart.host_id] = host_summary.get(cart.host_id, 0) + 1

    for host_id, count in host_summary.items():
        notify_host_abandoned_cart_summary(db, host_id=host_id, cart_count=count)

    expired = list(
        db.scalars(
            select(MerchCart)
            .where(
                MerchCart.status.in_(("active", "abandoned")),
                MerchCart.last_activity_at < expire_before,
            )
            .limit(limit)
        )
    )
    for cart in expired:
        cart.status = "expired"

    db.commit()
    return sent
