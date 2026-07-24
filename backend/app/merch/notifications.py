"""Merch buyer/host notifications — no payment secrets or private contact in bodies."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.service import enqueue_template
from app.events.models import Event
from app.hosts.models import Host
from app.merch.cart import serialize_cart
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchFulfillment
from app.messaging.models import InAppNotification
from app.payments.models import Order
from app.users.models import User

LOW_STOCK_THRESHOLD = 5


def _has_notification(
    db: Session,
    *,
    user_id,
    kind: str,
    title: str,
) -> bool:
    return (
        db.scalar(
            select(InAppNotification.id).where(
                InAppNotification.user_id == user_id,
                InAppNotification.kind == kind,
                InAppNotification.title == title,
            )
        )
        is not None
    )


def _add_in_app(
    db: Session,
    *,
    user_id,
    kind: str,
    title: str,
    body: str,
    link_path: str,
) -> None:
    if _has_notification(db, user_id=user_id, kind=kind, title=title):
        return
    from app.notifications.service import notify_user

    notify_user(
        db,
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        link_path=link_path,
        send_push=True,
    )


def notify_buyer_merch_paid(
    db: Session,
    *,
    order: Order,
    fulfillments: list[MerchFulfillment],
) -> None:
    """After verified payment: buyer confirmed + host sale notice."""
    if not fulfillments:
        return

    event = db.get(Event, order.event_id)
    event_title = event.title if event else "your event"
    item_bits = ", ".join(
        f"{f.quantity}× {f.product_name_snapshot}" for f in fulfillments[:4]
    )
    if len(fulfillments) > 4:
        item_bits += ", …"

    title = "Your merch order is confirmed."
    body = (
        f"Your merch for {event_title} is confirmed: {item_bits}. "
        "Pickup details are in Merchandise."
    )
    _add_in_app(
        db,
        user_id=order.buyer_user_id,
        kind="merch.confirmed",
        title=title,
        body=body,
        link_path="/dashboard/merchandise",
    )

    # Keep legacy kind for older clients / tests that look for merch.paid
    _add_in_app(
        db,
        user_id=order.buyer_user_id,
        kind="merch.paid",
        title=title,
        body=body,
        link_path="/dashboard/merchandise",
    )

    enqueue_template(
        db,
        template="merch_order_confirmed",
        to=order.buyer_email,
        recipient_user_id=order.buyer_user_id,
        dedupe_key=f"order:{order.id}:merch_order_confirmed",
        context={
            "buyer_name": order.buyer_name,
            "event_title": event_title,
            "item_summary": item_bits,
        },
    )

    notify_host_merch_sale(db, order=order, fulfillments=fulfillments)
    from app.email.admin_triggers import admin_notify_merch_sale_paid
    from app.hosts.models import Host

    host = db.get(Host, fulfillments[0].host_id)
    admin_notify_merch_sale_paid(
        db,
        order_id=order.id,
        order_reference=order.reference,
        product_title=fulfillments[0].product_name_snapshot,
        host_name=host.display_name if host else "Host",
        buyer_name=order.buyer_name or "Buyer",
        quantity=sum(int(f.quantity or 0) for f in fulfillments),
        amount=order.total_amount,
        currency=order.currency or "NGN",
        fulfillment_type=fulfillments[0].fulfillment_method or "pickup",
    )
    # Low/sold-out/restock alerts are opened via evaluate_variant_stock_alerts
    # during paid merch finalize — avoid duplicate one-shot low_stock notifies.


def notify_host_merch_sale(
    db: Session,
    *,
    order: Order,
    fulfillments: list[MerchFulfillment],
) -> None:
    if not fulfillments:
        return
    host = db.get(Host, fulfillments[0].host_id)
    if host is None:
        return
    event = db.get(Event, order.event_id)
    event_title = event.title if event else "your event"
    count = sum(int(f.quantity or 0) for f in fulfillments)
    title = "New merch sale"
    body = f"You sold {count} merch item(s) for {event_title}."
    _add_in_app(
        db,
        user_id=host.user_id,
        kind="merch.host_sale",
        title=title,
        body=body,
        link_path=f"/host/events/{order.event_id}/merchandise/orders",
    )
    host_user = db.get(User, host.user_id)
    if host_user and host_user.email:
        enqueue_template(
            db,
            template="host_merch_sale",
            to=host_user.email,
            recipient_user_id=host_user.id,
            dedupe_key=f"order:{order.id}:host_merch_sale",
            context={
                "event_title": event_title,
                "item_count": count,
            },
        )


def notify_buyer_merch_ready(
    db: Session,
    *,
    fulfillment: MerchFulfillment,
) -> None:
    event = db.get(Event, fulfillment.event_id)
    event_title = event.title if event else "the event"
    title = "Your merch pickup code is ready."
    body = (
        f"{fulfillment.product_name_snapshot} for {event_title} is ready "
        "at the merch stand on Pàdéyá."
    )
    _add_in_app(
        db,
        user_id=fulfillment.buyer_user_id,
        kind="merch.ready_for_pickup",
        title=title,
        body=body,
        link_path="/dashboard/merchandise",
    )
    buyer = db.get(User, fulfillment.buyer_user_id)
    if buyer and buyer.email:
        short = (fulfillment.pickup_code or "")[:8]
        enqueue_template(
            db,
            template="merch_pickup_ready",
            to=buyer.email,
            recipient_user_id=buyer.id,
            dedupe_key=f"fulfillment:{fulfillment.id}:merch_pickup_ready",
            context={
                "product_name": fulfillment.product_name_snapshot,
                "event_title": event_title,
                "pickup_code_short": short,
            },
        )


def notify_buyer_merch_picked_up(
    db: Session,
    *,
    fulfillment: MerchFulfillment,
) -> None:
    event = db.get(Event, fulfillment.event_id)
    event_title = event.title if event else "the event"
    title = "Merch picked up"
    body = (
        f"{fulfillment.product_name_snapshot} for {event_title} was marked picked up."
    )
    _add_in_app(
        db,
        user_id=fulfillment.buyer_user_id,
        kind="merch.picked_up",
        title=title,
        body=body,
        link_path="/dashboard/merchandise",
    )
    buyer = db.get(User, fulfillment.buyer_user_id)
    if buyer and buyer.email:
        enqueue_template(
            db,
            template="merch_picked_up",
            to=buyer.email,
            recipient_user_id=buyer.id,
            dedupe_key=f"fulfillment:{fulfillment.id}:merch_picked_up",
            context={
                "product_name": fulfillment.product_name_snapshot,
                "event_title": event_title,
            },
        )


def notify_host_merch_pickup(
    db: Session,
    *,
    fulfillment: MerchFulfillment,
) -> None:
    host = db.get(Host, fulfillment.host_id)
    if host is None:
        return
    event = db.get(Event, fulfillment.event_id)
    event_title = event.title if event else "your event"
    title = "Merch collected"
    body = (
        f"{fulfillment.product_name_snapshot} for {event_title} was marked picked up."
    )
    _add_in_app(
        db,
        user_id=host.user_id,
        kind="merch.host_pickup",
        title=title,
        body=body,
        link_path=f"/host/events/{fulfillment.event_id}/merchandise/fulfillment",
    )


def notify_buyer_merch_refunded(
    db: Session,
    *,
    order: Order,
    fulfillments: list[MerchFulfillment],
) -> None:
    if not fulfillments:
        return
    event = db.get(Event, order.event_id)
    event_title = event.title if event else "your event"
    title = "Merch order refunded"
    body = f"Merch for {event_title} was cancelled after a refund."
    _add_in_app(
        db,
        user_id=order.buyer_user_id,
        kind="merch.refunded",
        title=title,
        body=body,
        link_path="/dashboard/merchandise",
    )
    if order.buyer_email:
        enqueue_template(
            db,
            template="merch_refund_update",
            to=order.buyer_email,
            recipient_user_id=order.buyer_user_id,
            dedupe_key=f"order:{order.id}:merch_refund_update",
            context={
                "event_title": event_title,
                "refund_status": "refunded",
            },
        )


def _stock_alert_title(
    alert_type: str,
    *,
    product: EventMerchProduct,
    variant: EventMerchVariant,
) -> str:
    if alert_type == "low_stock":
        return f"Low stock: {product.name}"
    if alert_type == "sold_out":
        label = (variant.label or "").strip()
        name = f"{product.name} {label}".strip() if label else product.name
        return f"Sold out: {name}"
    if alert_type == "restocked":
        return f"Restocked: {product.name}"
    if alert_type == "high_reserve":
        return f"High reserve: {product.name}"
    if alert_type == "pre_event_risk":
        return f"Pre-event stock risk: {product.name}"
    return f"Stock alert: {product.name}"


def notify_host_stock_alerts(
    db: Session,
    *,
    product: EventMerchProduct,
    variant: EventMerchVariant,
    alerts: list,
) -> None:
    """In-app stock alerts — product/event names only; no payment/address data."""
    host = db.get(Host, product.host_id)
    if host is None:
        return
    for alert in alerts:
        alert_type = getattr(alert, "alert_type", "") or "low_stock"
        kind_map = {
            "low_stock": "merch.low_stock",
            "sold_out": "merch.sold_out",
            "restocked": "merch.restocked",
            "high_reserve": "merch.stock_risk",
            "pre_event_risk": "merch.stock_risk",
        }
        kind = kind_map.get(alert_type, "merch.low_stock")
        title = _stock_alert_title(alert_type, product=product, variant=variant)
        body = f"{product.name} ({variant.label}) — stock alert on Pàdéyá."
        link = "/host/merchandise/stock-alerts"
        _add_in_app(
            db,
            user_id=host.user_id,
            kind=kind,
            title=title,
            body=body,
            link_path=link,
        )


def notify_buyer_cart_reminder(db: Session, *, cart) -> bool:
    """Abandoned cart reminder — product names only; never address/phone/payment secrets.

    Returns True when an in-app reminder was created (or already existed for this cart).
    Email is opt-in only (host marketing consent; default off).
    """
    if not cart.buyer_user_id or not cart.items:
        return False
    buyer = db.get(User, cart.buyer_user_id)
    if buyer is None or not buyer.is_active or buyer.deactivated_at is not None:
        return False

    names = ", ".join(
        (i.product_name_snapshot or "Merch").strip() for i in cart.items[:3]
    )
    if len(cart.items) > 3:
        names += ", …"
    title = "Still interested in your Pàdéyá merch?"
    body = f"Your event merch is still waiting: {names}."
    # Hard privacy: never put email, phone, address, or payment data in the body
    forbidden = (
        getattr(buyer, "email", None),
        getattr(buyer, "full_name", None),
    )
    for bit in forbidden:
        if bit and str(bit) in body:
            body = "Your event merch is still waiting."

    _add_in_app(
        db,
        user_id=cart.buyer_user_id,
        kind="merch.cart_reminder",
        title=title,
        body=body[:240],
        link_path=serialize_cart(cart, db=db)["resume_path"],
    )

    # Marketing email: platform email_marketing pref (defaults off) + host opt-in.
    if cart.host_id is not None and buyer.email:
        from app.crm.models import HostFollower

        opted_in = db.scalar(
            select(HostFollower.id).where(
                HostFollower.host_id == cart.host_id,
                HostFollower.user_id == cart.buyer_user_id,
                HostFollower.marketing_opt_in.is_(True),
            )
        )
        if opted_in is not None:
            enqueue_template(
                db,
                template="merch_cart_reminder",
                to=buyer.email,
                recipient_user_id=buyer.id,
                dedupe_key=f"cart:{cart.id}:merch_cart_reminder",
                context={},
            )
    return True


def notify_host_abandoned_cart_summary(
    db: Session, *, host_id, cart_count: int
) -> None:
    """Optional host digest — counts only; no buyer names, emails, or phones."""
    if cart_count < 1:
        return
    host = db.get(Host, host_id)
    if host is None:
        return
    from datetime import UTC, datetime

    day = datetime.now(UTC).date().isoformat()
    title = f"Abandoned merch carts · {day}"
    body = (
        f"{cart_count} shopper(s) left Pàdéyá merch in their cart. "
        "No buyer contact details are shared here."
    )
    _add_in_app(
        db,
        user_id=host.user_id,
        kind="merch.host_cart_summary",
        title=title,
        body=body[:240],
        link_path="/host/merchandise",
    )


def notify_buyer_merch_shipped(
    db: Session,
    *,
    fulfillment: MerchFulfillment,
) -> None:
    title = "Merch shipped"
    body = (
        f"{fulfillment.product_name_snapshot} is on the way"
        + (
            f" (tracking {fulfillment.tracking_number})."
            if fulfillment.tracking_number
            else "."
        )
    )
    _add_in_app(
        db,
        user_id=fulfillment.buyer_user_id,
        kind="merch.shipped",
        title=title,
        body=body,
        link_path="/dashboard/merchandise",
    )
    buyer = db.get(User, fulfillment.buyer_user_id)
    if buyer and buyer.email:
        enqueue_template(
            db,
            template="merch_shipping_update",
            to=buyer.email,
            recipient_user_id=buyer.id,
            dedupe_key=f"fulfillment:{fulfillment.id}:merch_shipped",
            context={
                "product_name": fulfillment.product_name_snapshot,
                "shipping_status": "shipped",
                "tracking_number": fulfillment.tracking_number or "",
            },
        )


def notify_buyer_merch_delivered(
    db: Session,
    *,
    fulfillment: MerchFulfillment,
) -> None:
    title = "Merch delivered"
    body = f"{fulfillment.product_name_snapshot} was marked delivered."
    _add_in_app(
        db,
        user_id=fulfillment.buyer_user_id,
        kind="merch.delivered",
        title=title,
        body=body,
        link_path="/dashboard/merchandise",
    )
    buyer = db.get(User, fulfillment.buyer_user_id)
    if buyer and buyer.email:
        enqueue_template(
            db,
            template="merch_shipping_update",
            to=buyer.email,
            recipient_user_id=buyer.id,
            dedupe_key=f"fulfillment:{fulfillment.id}:merch_delivered",
            context={
                "product_name": fulfillment.product_name_snapshot,
                "shipping_status": "delivered",
                "tracking_number": "",
            },
        )


def notify_host_merch_sold_out(
    db: Session,
    *,
    product: EventMerchProduct,
    variant: EventMerchVariant,
) -> None:
    host = db.get(Host, product.host_id)
    if host is None:
        return
    title = _stock_alert_title("sold_out", product=product, variant=variant)
    body = f"{product.name} ({variant.label}) is sold out."
    _add_in_app(
        db,
        user_id=host.user_id,
        kind="merch.sold_out",
        title=title,
        body=body,
        link_path="/host/merchandise/stock-alerts",
    )


def notify_host_review_received(
    db: Session,
    *,
    review: object,
) -> None:
    host_id = getattr(review, "host_id", None)
    product_id = getattr(review, "product_id", None)
    review_id = getattr(review, "id", None)
    if host_id is None:
        return
    host = db.get(Host, host_id)
    product = db.get(EventMerchProduct, product_id) if product_id else None
    if host is None:
        return
    name = product.name if product else "your merch"
    # Unique title so each verified review notifies (dedupe is by kind+title).
    title = (
        f"New merch review · {name}"
        if review_id is None
        else f"New merch review · {name} ({str(review_id)[:8]})"
    )
    _add_in_app(
        db,
        user_id=host.user_id,
        kind="merch.review_received",
        title=title,
        body=f"A buyer reviewed {name}.",
        link_path="/host/merchandise/reviews",
    )
    host_user = db.get(User, host.user_id)
    if host_user and host_user.email:
        enqueue_template(
            db,
            template="host_new_review",
            to=host_user.email,
            recipient_user_id=host_user.id,
            dedupe_key=f"merch_review:{review_id}:host_new_review",
            context={"subject_label": name},
        )


def maybe_notify_buyer_vault_merch_unlocked(
    db: Session,
    *,
    user_id,
    host_id,
    vault_item_id=None,
) -> None:
    """Cheap notify when a buyer becomes eligible for Vault-exclusive merch.

    Fires after a new Vault access grant. Never includes Vault body/media/secrets.
    """
    try:
        from app.admin_notifications.settings_service import get_or_create_setting

        setting = get_or_create_setting(db, "vault.merch_unlocked")
        if not setting.enabled:
            return
    except Exception:  # noqa: BLE001
        pass

    from sqlalchemy import or_

    stmt = select(EventMerchProduct).where(
        EventMerchProduct.host_id == host_id,
        EventMerchProduct.status == "active",
        EventMerchProduct.archived_at.is_(None),
        or_(
            EventMerchProduct.is_vault_exclusive.is_(True),
            EventMerchProduct.requires_vault_access.is_(True),
        ),
    )
    if vault_item_id is not None:
        stmt = stmt.where(
            or_(
                EventMerchProduct.required_vault_item_id == vault_item_id,
                EventMerchProduct.required_vault_item_id.is_(None),
            )
        )
    products = list(db.scalars(stmt.limit(5)))
    if not products:
        return

    # One notification covering newly unlocked exclusive merch — product names only.
    names = ", ".join(p.name for p in products[:3])
    if len(products) > 3:
        names += ", …"
    title = "Vault merch unlocked"
    body = f"You can now shop exclusive merch: {names}."
    host = db.get(Host, host_id)
    slug = host.slug if host else None
    link = f"/@{slug}/merch" if slug else "/dashboard/merchandise"
    _add_in_app(
        db,
        user_id=user_id,
        kind="merch.vault_unlocked",
        title=title,
        body=body,
        link_path=link,
    )


def maybe_notify_host_low_stock(
    db: Session,
    *,
    fulfillment: MerchFulfillment,
) -> None:
    variant = db.get(EventMerchVariant, fulfillment.merch_variant_id)
    if variant is None:
        return
    from app.merch.service import available_variant_stock

    available = available_variant_stock(variant)
    if available > LOW_STOCK_THRESHOLD or available <= 0:
        return
    product = db.get(EventMerchProduct, variant.product_id)
    host = db.get(Host, fulfillment.host_id)
    if product is None or host is None:
        return
    title = f"Low stock: {product.name}"
    body = (
        f"{product.name} ({variant.label}) is low — about {available} left."
    )
    _add_in_app(
        db,
        user_id=host.user_id,
        kind="merch.low_stock",
        title=title,
        body=body,
        link_path=f"/host/events/{fulfillment.event_id}/merchandise",
    )


def notify_buyers_post_event_drop_live(
    db: Session,
    *,
    product: EventMerchProduct,
    buyer_user_ids: list,
    event_title: str,
    audience: str,
) -> int:
    """In-app notices when a post-event drop goes live. No PII, payment, or address."""
    if not buyer_user_ids:
        return 0
    title = f"New post-event merch drop from {event_title}"[:160]
    if audience in {"ticket_buyers", "checked_in", "vip"}:
        body = "Ticket holders can now access the recap merch drop"
    elif audience == "vault_members":
        body = f"Vault members can now access the recap merch drop for {event_title}."
    else:
        body = f"A new recap merch drop is live for {event_title} on Pàdéyá."

    link = f"/dashboard/merchandise?drop={product.id}"
    if product.event_id:
        event = db.get(Event, product.event_id)
        if event and event.slug:
            link = f"/events/{event.slug}/merch?drop={product.id}"

    sent = 0
    for user_id in buyer_user_ids:
        if user_id is None:
            continue
        # Dedupe per user+drop via link_path (title stays human-readable).
        from app.notifications.service import notify_user

        row = notify_user(
            db,
            user_id=user_id,
            kind="merch.post_event_drop",
            title=title,
            body=body[:240],
            link_path=link,
            dedupe_key=f"merch.drop:{product.id}:user:{user_id}",
            send_push=True,
        )
        if row is None:
            continue
        buyer = db.get(User, user_id)
        if buyer and buyer.email:
            enqueue_template(
                db,
                template="post_event_drop_available",
                to=buyer.email,
                recipient_user_id=buyer.id,
                dedupe_key=f"drop:{product.id}:user:{user_id}",
                context={"event_title": event_title},
            )
        sent += 1
    db.flush()
    return sent


def notify_buyer_merch_badge_earned(
    db: Session,
    *,
    user_id,
    badge,
) -> None:
    """Optional Fan Passport merch badge notice — badge name only, no PII/orders/spend."""
    name = getattr(badge, "name", None) or "a merch badge"
    title = f"You earned {name} on Pàdéyá"
    body = "A new Fan Passport merch badge was added to your collection."
    _add_in_app(
        db,
        user_id=user_id,
        kind="merch.badge_earned",
        title=title,
        body=body,
        link_path="/dashboard/badges",
    )
