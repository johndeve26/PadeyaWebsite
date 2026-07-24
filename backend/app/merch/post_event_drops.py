"""Host post-event merch drops — create/list/patch + live notifications."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import Event
from app.merch.access import buyer_eligible_for_product, product_is_drop_live
from app.merch.constants import ACCESS_TYPES, PRODUCT_STATUSES, STOREFRONT_VISIBILITIES
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.merch.service import (
    can_manage_event_merch,
    serialize_product,
    unique_product_slug,
)
from app.tickets.models import Ticket
from app.users.models import User
from app.vault.models import VaultPurchase

DROP_AUDIENCES = (
    "public",
    "ticket_buyers",
    "checked_in",
    "vip",
    "vault_members",
)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def event_allows_post_event_drop(event: Event, *, now: datetime | None = None) -> bool:
    """Completed events, or published events whose end time has passed."""
    current = now or datetime.now(UTC)
    if event.status == "completed":
        return True
    if event.status != "published":
        return False
    end = _aware(event.end_datetime)
    return end is not None and current >= end


def audience_from_product(product: EventMerchProduct) -> str:
    if product.requires_vault_access or product.is_vault_exclusive:
        return "vault_members"
    if product.requires_vip or product.required_access_type == "vip_ticket_holder":
        return "vip"
    if product.requires_check_in or product.required_access_type == "checked_in_attendee":
        return "checked_in"
    if product.requires_ticket or product.required_access_type == "ticket_holder":
        return "ticket_buyers"
    return "public"


def apply_audience_flags(product: EventMerchProduct, audience: str) -> None:
    if audience not in DROP_AUDIENCES:
        raise HTTPException(
            status_code=400,
            detail=f"audience must be one of: {', '.join(DROP_AUDIENCES)}",
        )
    product.requires_ticket = False
    product.requires_check_in = False
    product.requires_vip = False
    product.requires_vault_access = False
    product.is_vault_exclusive = False
    product.required_access_type = None

    if audience == "ticket_buyers":
        product.requires_ticket = True
        product.required_access_type = "ticket_holder"
    elif audience == "checked_in":
        product.requires_ticket = True
        product.requires_check_in = True
        product.required_access_type = "checked_in_attendee"
    elif audience == "vip":
        product.requires_ticket = True
        product.requires_vip = True
        product.required_access_type = "vip_ticket_holder"
    elif audience == "vault_members":
        product.requires_vault_access = True
        product.is_vault_exclusive = True
        product.required_access_type = "paid_vault_member"


def _serialize_drop(product: EventMerchProduct, *, event_title: str | None = None) -> dict:
    row = serialize_product(product, event_title=event_title)
    row.update(
        {
            "storefront_visibility": product.storefront_visibility,
            "post_event_drop_at": product.post_event_drop_at,
            "is_post_event_drop": product.storefront_visibility == "post_event_drop",
            "is_drop_live": product_is_drop_live(product),
            "is_event_linked": product.is_event_linked,
            "requires_ticket": bool(product.requires_ticket),
            "requires_check_in": bool(product.requires_check_in),
            "requires_vip": bool(product.requires_vip),
            "requires_vault_access": bool(product.requires_vault_access),
            "is_vault_exclusive": bool(product.is_vault_exclusive),
            "required_access_type": product.required_access_type,
            "audience": audience_from_product(product),
            "drop_live_notified_at": product.drop_live_notified_at,
            "drop_description": product.short_description or product.description,
        }
    )
    return row


def list_post_event_drops(
    db: Session, *, user: User, event_id: uuid.UUID
) -> list[dict]:
    if not can_manage_event_merch(db, user, event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage merch for this event")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    rows = db.scalars(
        select(EventMerchProduct)
        .where(
            EventMerchProduct.event_id == event_id,
            EventMerchProduct.storefront_visibility == "post_event_drop",
            EventMerchProduct.archived_at.is_(None),
        )
        .options(selectinload(EventMerchProduct.variants))
        .order_by(EventMerchProduct.created_at.desc())
    ).all()
    return [_serialize_drop(p, event_title=event.title) for p in rows]


def create_post_event_drop(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    name: str,
    base_price: Decimal,
    audience: str = "public",
    drop_description: str | None = None,
    post_event_drop_at: datetime | None = None,
    currency: str = "NGN",
    product_type: str | None = "souvenir",
    image_url: str | None = None,
    status: str = "draft",
    inventory_count: int = 0,
    variant_label: str = "Default",
) -> dict:
    if not can_manage_event_merch(db, user, event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage merch for this event")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event_allows_post_event_drop(event):
        raise HTTPException(
            status_code=400,
            detail="Post-event drops can only be created for completed or ended events",
        )
    if status not in PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid product status")
    if "post_event_drop" not in STOREFRONT_VISIBILITIES:
        raise HTTPException(status_code=500, detail="Invalid storefront visibility config")

    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="name is required")
    desc = (drop_description or "").strip() or None
    drop_at = _aware(post_event_drop_at) or datetime.now(UTC)

    product = EventMerchProduct(
        event_id=event.id,
        host_id=event.host_id,
        name=cleaned_name,
        slug=unique_product_slug(db, event_id=event.id, base=cleaned_name),
        description=desc,
        short_description=(desc[:280] if desc else None),
        product_type=product_type or "souvenir",
        base_price=base_price,
        currency=(currency or "NGN").upper(),
        image_url=(image_url or "").strip() or None,
        status=status,
        show_on_event_page=True,
        is_featured=False,
        is_event_linked=True,
        storefront_visibility="post_event_drop",
        post_event_drop_at=drop_at,
        pickup_enabled=True,
        shipping_enabled=True,
        print_on_demand_enabled=False,
        moderation_status="clear",
    )
    apply_audience_flags(product, audience)
    db.add(product)
    db.flush()
    db.add(
        EventMerchVariant(
            product_id=product.id,
            label=(variant_label or "Default").strip() or "Default",
            inventory_count=max(0, int(inventory_count)),
            reserved_quantity=0,
            sold_quantity=0,
            status="active",
        )
    )
    write_audit_log(
        db,
        action="merch.post_event_drop_create",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details={
            "event_id": str(event.id),
            "audience": audience,
            "status": status,
        },
    )
    db.commit()
    loaded = db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product.id)
        .options(selectinload(EventMerchProduct.variants))
    )
    assert loaded is not None
    # Notify immediately when activating a drop that is already live.
    if loaded.status == "active" and product_is_drop_live(loaded):
        notify_post_event_drop_live(db, product_id=loaded.id, limit=200)
        db.refresh(loaded)
    return _serialize_drop(loaded, event_title=event.title)


def patch_post_event_drop(
    db: Session,
    *,
    user: User,
    product_id: uuid.UUID,
    name: str | None = None,
    drop_description: str | None = None,
    audience: str | None = None,
    post_event_drop_at: datetime | None = None,
    status: str | None = None,
    base_price: Decimal | None = None,
    image_url: str | None = None,
) -> dict:
    product = db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product_id)
        .options(selectinload(EventMerchProduct.variants))
    )
    if product is None or product.archived_at is not None:
        raise HTTPException(status_code=404, detail="Drop not found")
    if product.storefront_visibility != "post_event_drop":
        raise HTTPException(status_code=400, detail="Product is not a post-event drop")
    if product.event_id is None or not can_manage_event_merch(db, user, product.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to manage this drop")

    previous_status = product.status
    was_live = product_is_drop_live(product)

    if name is not None:
        cleaned = name.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="name is required")
        product.name = cleaned
    if drop_description is not None:
        desc = drop_description.strip() or None
        product.description = desc
        product.short_description = desc[:280] if desc else None
    if audience is not None:
        apply_audience_flags(product, audience)
    if post_event_drop_at is not None:
        product.post_event_drop_at = _aware(post_event_drop_at)
        # Reschedule clears prior notify stamp so a later go-live can notify again.
        if not product_is_drop_live(product):
            product.drop_live_notified_at = None
    if status is not None:
        if status not in PRODUCT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid product status")
        product.status = status
    if base_price is not None:
        product.base_price = base_price
    if image_url is not None:
        product.image_url = image_url.strip() or None

    if product.required_access_type and product.required_access_type not in ACCESS_TYPES:
        raise HTTPException(status_code=400, detail="Invalid required_access_type")

    write_audit_log(
        db,
        action="merch.post_event_drop_update",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details={"status": product.status, "audience": audience_from_product(product)},
    )
    db.commit()
    db.refresh(product)

    became_active = previous_status != "active" and product.status == "active"
    became_live = not was_live and product_is_drop_live(product)
    if product.status == "active" and (became_active or became_live):
        if product_is_drop_live(product) and product.drop_live_notified_at is None:
            notify_post_event_drop_live(db, product_id=product.id, limit=200)
            db.refresh(product)

    event = db.get(Event, product.event_id) if product.event_id else None
    return _serialize_drop(product, event_title=event.title if event else None)


def _eligible_buyer_ids_for_drop(
    db: Session, *, product: EventMerchProduct, limit: int = 200
) -> list[uuid.UUID]:
    """Candidates to notify — ticket holders / vault buyers; never PII in notify path."""
    audience = audience_from_product(product)
    event_id = product.event_id
    ids: list[uuid.UUID] = []

    if audience == "vault_members":
        from app.vault.models import VaultItem

        host_items = select(VaultItem.id).where(VaultItem.host_id == product.host_id)
        rows = db.scalars(
            select(VaultPurchase.user_id)
            .where(
                VaultPurchase.status == "paid",
                VaultPurchase.vault_item_id.in_(host_items),
            )
            .distinct()
            .limit(limit)
        ).all()
        ids = list(rows)
    elif event_id is not None:
        statuses = ["checked_in"] if audience == "checked_in" else ["active", "checked_in"]
        q = (
            select(Ticket.buyer_user_id)
            .where(
                Ticket.event_id == event_id,
                Ticket.status.in_(statuses),
                Ticket.buyer_user_id.is_not(None),
            )
            .distinct()
            .limit(limit)
        )
        if audience == "vip":
            from app.events.models import TicketType

            q = q.join(TicketType, TicketType.id == Ticket.ticket_type_id).where(
                TicketType.type.in_(("vip", "vvip"))
            )
        ids = list(db.scalars(q).all())
    else:
        return []

    # Public drops: ticket holders of the event (recap audience), already in ids when event_id set.
    # Filter through eligibility so wrong audience never gets a "you can access" ping.
    eligible: list[uuid.UUID] = []
    for uid in ids:
        if uid is None:
            continue
        ok, _reason = buyer_eligible_for_product(
            db, product=product, buyer_user_id=uid, has_ticket_cover=False
        )
        if ok:
            eligible.append(uid)
        if len(eligible) >= limit:
            break
    return eligible


def notify_post_event_drop_live(
    db: Session, *, product_id: uuid.UUID, limit: int = 200
) -> int:
    """Idempotent: notify eligible buyers once when a drop goes live. No PII/payment."""
    product = db.get(EventMerchProduct, product_id)
    if product is None:
        return 0
    if product.storefront_visibility != "post_event_drop":
        return 0
    if product.status != "active" or product.archived_at is not None:
        return 0
    if not product_is_drop_live(product):
        return 0
    if product.drop_live_notified_at is not None:
        return 0

    try:
        from app.admin_notifications.settings_service import get_or_create_setting

        setting = get_or_create_setting(db, "merch.post_event_drop_live")
        if not setting.enabled:
            product.drop_live_notified_at = datetime.now(UTC)
            db.add(product)
            db.commit()
            return 0
    except Exception:  # noqa: BLE001
        pass

    from app.merch.notifications import notify_buyers_post_event_drop_live

    event = db.get(Event, product.event_id) if product.event_id else None
    event_title = event.title if event else "your event"
    buyer_ids = _eligible_buyer_ids_for_drop(db, product=product, limit=limit)
    audience = audience_from_product(product)
    sent = notify_buyers_post_event_drop_live(
        db,
        product=product,
        buyer_user_ids=buyer_ids,
        event_title=event_title,
        audience=audience,
    )
    product.drop_live_notified_at = datetime.now(UTC)
    db.add(product)
    db.commit()
    return sent


def notify_due_post_event_drops(db: Session, *, limit: int = 20) -> int:
    """Job: activate notifications for drops whose schedule has passed."""
    now = datetime.now(UTC)
    rows = list(
        db.scalars(
            select(EventMerchProduct)
            .where(
                EventMerchProduct.storefront_visibility == "post_event_drop",
                EventMerchProduct.status == "active",
                EventMerchProduct.archived_at.is_(None),
                EventMerchProduct.drop_live_notified_at.is_(None),
                EventMerchProduct.post_event_drop_at.is_not(None),
                EventMerchProduct.post_event_drop_at <= now,
            )
            .order_by(EventMerchProduct.post_event_drop_at.asc())
            .limit(limit)
        )
    )
    total = 0
    for product in rows:
        total += notify_post_event_drop_live(db, product_id=product.id, limit=200)
    return total


def list_buyer_eligible_drops(
    db: Session, *, buyer_user_id: uuid.UUID, limit: int = 40
) -> list[dict]:
    """Drops the signed-in buyer can purchase now (dashboard / event surfaces)."""
    from app.merch.storefront import serialize_storefront_product

    now = datetime.now(UTC)
    rows = list(
        db.scalars(
            select(EventMerchProduct)
            .where(
                EventMerchProduct.storefront_visibility == "post_event_drop",
                EventMerchProduct.status == "active",
                EventMerchProduct.archived_at.is_(None),
                EventMerchProduct.moderation_status.notin_(("hidden", "removed")),
            )
            .options(selectinload(EventMerchProduct.variants))
            .order_by(EventMerchProduct.post_event_drop_at.desc().nullslast())
            .limit(limit * 3)
        )
    )
    out: list[dict] = []
    for product in rows:
        if not product_is_drop_live(product, now=now):
            continue
        ok, _reason = buyer_eligible_for_product(
            db, product=product, buyer_user_id=buyer_user_id
        )
        if not ok:
            continue
        out.append(serialize_storefront_product(db, product, buyer_user_id=buyer_user_id))
        if len(out) >= limit:
            break
    return out
