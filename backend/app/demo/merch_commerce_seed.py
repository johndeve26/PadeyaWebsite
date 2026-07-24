"""Advanced merch commerce demo extras (discounts, vault, carts, shipping, QR)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.demo.constants import DEMO_EMAIL_DOMAIN
from app.events.models import Event, TicketType
from app.hosts.models import Host
from app.merch.bundles import create_bundle
from app.merch.discounts import create_discount
from app.merch.fulfillment import (
    cancel_fulfillments_for_refunded_order,
    mark_fulfilled,
    update_fulfillment_status,
)
from app.merch.models import (
    EventMerchProduct,
    EventMerchVariant,
    MerchBundle,
    MerchCart,
    MerchCartItem,
    MerchDiscountCode,
    MerchFulfillment,
    MerchReview,
    MerchSizeChart,
    MerchShippingZone,
)
from app.merch.qr_pickup import issue_pickup_qr_for_fulfillment
from app.merch.schemas import MerchProductCreate, MerchVariantCreate
from app.merch.service import create_product, sync_variant_sold_out
from app.merch.shipping import upsert_zone
from app.merch.stock_alerts import evaluate_variant_stock_alerts
from app.payments.models import Order, OrderItem, Payment
from app.payments.schemas import (
    CheckoutAnswerIn,
    OrderCreate,
    OrderItemCreate,
    ShippingAddressIn,
)
from app.payments.service import create_order, get_order_by_id, initialize_checkout
from app.payments.webhook import finalize_successful_payment
from app.users.models import User
from app.vault.models import VaultItem


def _checkout_answers_for_event(
    event: Event, *, buyer_index: int = 0
) -> list[CheckoutAnswerIn]:
    """Satisfy required Studio checkout questions for demo merch orders."""
    answers: list[CheckoutAnswerIn] = []
    for question in list(event.checkout_questions or []):
        if getattr(question, "status", "active") != "active" or not question.required:
            continue
        if question.type == "phone":
            value: str | list[str] = f"+234801{buyer_index:07d}"[:14]
        elif question.type == "email":
            value = f"fan{buyer_index}@{DEMO_EMAIL_DOMAIN}"
        elif question.type == "dropdown":
            opts = list(question.options or [])
            value = opts[buyer_index % len(opts)] if opts else "Pàdéyá browse"
        elif question.type == "checkbox":
            opts = list(question.options or [])
            value = [opts[0]] if opts else ["None"]
        else:
            value = "Demo attendee note"
        answers.append(CheckoutAnswerIn(question_id=question.id, value=value))
    return answers


def _safe(db: Session, fn, *args, **kwargs):
    """Run a demo step; failures must not abort the rest of the seed.

    Merch helpers such as ``create_product`` / ``create_order`` call
    ``db.commit()``, so nested savepoints cannot wrap them. Callers should
    ``commit()`` durable artifacts (discounts, carts) before risky steps.
    """
    try:
        return fn(*args, **kwargs)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None


def _host_owner(db: Session, event: Event) -> tuple[Host | None, User | None]:
    host = db.get(Host, event.host_id)
    if host is None:
        return None, None
    return host, db.get(User, host.user_id)


def _find_product(
    db: Session, *, event_id, name: str
) -> EventMerchProduct | None:
    return db.scalar(
        select(EventMerchProduct)
        .where(
            EventMerchProduct.event_id == event_id,
            EventMerchProduct.name == name,
            EventMerchProduct.archived_at.is_(None),
        )
        .options(selectinload(EventMerchProduct.variants))
    )


def _find_variant(
    db: Session, *, event_id, product_name: str, variant_label: str | None = None
) -> EventMerchVariant | None:
    product = _find_product(db, event_id=event_id, name=product_name)
    if product is None:
        return None
    variants = [v for v in (product.variants or []) if v.archived_at is None]
    if not variants:
        return None
    if variant_label:
        for v in variants:
            if v.label == variant_label:
                return v
    return variants[0]


def _buyer_has_fulfillment(
    db: Session,
    *,
    buyer_id,
    event_id,
    product_name: str,
    status: str | None = None,
) -> bool:
    stmt = select(MerchFulfillment.id).where(
        MerchFulfillment.buyer_user_id == buyer_id,
        MerchFulfillment.event_id == event_id,
        MerchFulfillment.product_name_snapshot == product_name,
    )
    if status is not None:
        stmt = stmt.where(MerchFulfillment.status == status)
    return db.scalar(stmt.limit(1)) is not None


def _pay_order(db: Session, order: Order, buyer: User) -> None:
    order = get_order_by_id(db, order.id)
    if order is None or order.status == "paid":
        return
    if order.total_amount <= 0:
        initialize_checkout(db, user=buyer, order_id=order.id)
        return
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        reference=order.reference,
        amount=order.total_amount,
        currency=order.currency,
        status="pending",
    )
    db.add(payment)
    db.flush()
    finalize_successful_payment(
        db,
        order=order,
        payment=payment,
        provider_payment_id=f"demo_{order.reference}",
        raw_payload={"demo": True, "reference": order.reference},
        actor_user_id=buyer.id,
    )


def _order_merch(
    db: Session,
    *,
    buyer: User,
    event: Event,
    variant: EventMerchVariant | None = None,
    variants: list[EventMerchVariant] | None = None,
    include_ticket: bool = False,
    vip_ticket: bool = False,
    bundle_id=None,
    pay: bool = True,
    fulfillment_method: str | None = None,
    shipping_address: ShippingAddressIn | None = None,
    merch_discount_code: str | None = None,
) -> Order | None:
    items: list[OrderItemCreate] = []
    if bundle_id is not None:
        items.append(
            OrderItemCreate(item_kind="bundle", bundle_id=bundle_id, quantity=1)
        )
    else:
        if include_ticket:
            types = list(event.ticket_types or [])
            tt = None
            if vip_ticket:
                tt = next(
                    (t for t in types if t.type in {"vip", "vvip"} and t.status == "active"),
                    None,
                )
            if tt is None:
                tt = next(
                    (
                        t
                        for t in types
                        if t.type in {"regular", "early_bird", "free", "free_rsvp"}
                        and t.status == "active"
                    ),
                    types[0] if types else None,
                )
            if tt is None:
                return None
            items.append(OrderItemCreate(ticket_type_id=tt.id, quantity=1))
        lines = variants or ([variant] if variant is not None else [])
        for v in lines:
            items.append(
                OrderItemCreate(
                    item_kind="merch",
                    merch_variant_id=v.id,
                    quantity=1,
                )
            )
    if not items:
        return None
    # Reload questions so required Studio answers can be satisfied.
    event_row = db.scalar(
        select(Event)
        .where(Event.id == event.id)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.checkout_questions),
        )
    ) or event
    buyer_index = 0
    email = (buyer.email or "").split("@", 1)[0]
    if email.startswith("fan"):
        try:
            buyer_index = int(email.removeprefix("fan"))
        except ValueError:
            buyer_index = 0
    order = _safe(
        db,
        create_order,
        db,
        user=buyer,
        payload=OrderCreate(
            event_id=event.id,
            items=items,
            checkout_answers=_checkout_answers_for_event(
                event_row, buyer_index=buyer_index
            ),
            fulfillment_method=fulfillment_method,  # type: ignore[arg-type]
            shipping_address=shipping_address,
            merch_discount_code=merch_discount_code,
        ),
    )
    if order is None:
        return None
    if pay:
        _safe(db, _pay_order, db, order, buyer)
    return order


def _ensure_size_chart(
    db: Session, *, host_id, name: str, product_type: str = "t_shirt"
) -> MerchSizeChart:
    chart = db.scalar(
        select(MerchSizeChart).where(
            MerchSizeChart.host_id == host_id,
            MerchSizeChart.name == name,
        )
    )
    if chart is not None:
        return chart
    chart = MerchSizeChart(
        host_id=host_id,
        name=name,
        product_type=product_type,
        units="cm",
        chart_json={
            "columns": ["Size", "Chest", "Length"],
            "rows": [
                ["S", "96", "68"],
                ["M", "102", "70"],
                ["L", "108", "72"],
                ["XL", "114", "74"],
            ],
        },
        fit_notes="Runs true to size. Demo size guide for Pàdéyá merch.",
    )
    db.add(chart)
    db.flush()
    return chart


def _ensure_discount(
    db: Session,
    *,
    host_id,
    code: str,
    event_id=None,
    discount_value: Decimal = Decimal("10"),
    description: str | None = None,
) -> None:
    exists = db.scalar(
        select(MerchDiscountCode.id).where(
            MerchDiscountCode.host_id == host_id,
            MerchDiscountCode.code == code.upper(),
        )
    )
    if exists:
        return
    create_discount(
        db,
        host_id=host_id,
        code=code,
        discount_type="percent",
        discount_value=discount_value,
        applies_to="merch_only",
        event_id=event_id,
        description=description,
    )


def _ensure_bundle(
    db: Session,
    *,
    host_id,
    event: Event,
    name: str,
    ticket_type: TicketType,
    variant: EventMerchVariant,
    bundle_price: Decimal,
    description: str,
) -> MerchBundle | None:
    existing = db.scalar(
        select(MerchBundle).where(
            MerchBundle.event_id == event.id,
            MerchBundle.name == name,
        )
    )
    if existing is not None:
        return existing
    # Rename legacy demo bundle names when present.
    legacy = db.scalar(
        select(MerchBundle).where(
            MerchBundle.event_id == event.id,
            MerchBundle.name == "GA + Tee Pack",
        )
    )
    if legacy is not None and name == "Ticket + T-shirt Bundle":
        legacy.name = name
        legacy.description = description
        db.flush()
        return legacy
    return create_bundle(
        db,
        host_id=host_id,
        event_id=event.id,
        name=name,
        ticket_type_id=ticket_type.id,
        merch_variant_rules=[
            {
                "product_id": str(variant.product_id),
                "variant_id": str(variant.id),
                "quantity": 1,
            }
        ],
        bundle_price=bundle_price,
        description=description,
        inventory_limit=25,
        status="active",
    )


def _apply_product_flags(product: EventMerchProduct, flags: dict[str, Any]) -> None:
    for key, value in flags.items():
        if hasattr(product, key):
            setattr(product, key, value)


def _ensure_abandoned_cart(
    db: Session,
    *,
    buyer: User,
    event: Event,
    variant: EventMerchVariant,
    product: EventMerchProduct,
) -> bool:
    existing = db.scalar(
        select(MerchCart.id).where(
            MerchCart.buyer_user_id == buyer.id,
            MerchCart.status == "abandoned",
            MerchCart.event_id == event.id,
        )
    )
    if existing is not None:
        return False
    stale = datetime.now(UTC) - timedelta(days=3)
    cart = MerchCart(
        buyer_user_id=buyer.id,
        event_id=event.id,
        host_id=event.host_id,
        status="abandoned",
        last_activity_at=stale,
        recovery_sent_at=None,
    )
    db.add(cart)
    db.flush()
    db.add(
        MerchCartItem(
            cart_id=cart.id,
            product_id=product.id,
            variant_id=variant.id,
            quantity=1,
            unit_price_snapshot=product.base_price,
            product_name_snapshot=product.name,
            variant_label_snapshot=variant.label,
        )
    )
    # Keep recovery-eligible: stale activity, abandoned, no recovery sent.
    cart.last_activity_at = stale
    cart.updated_at = stale
    db.flush()
    return True


def _ensure_review_for_paid_merch(
    db: Session,
    *,
    buyer: User,
    event: Event,
    product_name: str,
    rating: int = 5,
    body: str = "Great merch — verified purchase on Pàdéyá.",
) -> bool:
    fulfillment = db.scalar(
        select(MerchFulfillment)
        .where(
            MerchFulfillment.buyer_user_id == buyer.id,
            MerchFulfillment.event_id == event.id,
            MerchFulfillment.product_name_snapshot == product_name,
        )
        .limit(1)
    )
    if fulfillment is None:
        return False
    order = db.get(Order, fulfillment.order_id)
    if order is None or order.status != "paid":
        return False
    existing = db.scalar(
        select(MerchReview.id).where(
            MerchReview.order_item_id == fulfillment.order_item_id
        )
    )
    if existing is not None:
        return False
    item = db.get(OrderItem, fulfillment.order_item_id)
    if item is None or item.merch_product_id is None:
        return False
    db.add(
        MerchReview(
            product_id=item.merch_product_id,
            order_item_id=item.id,
            buyer_user_id=buyer.id,
            host_id=fulfillment.host_id,
            event_id=event.id,
            rating=rating,
            body=body,
            status="published",
        )
    )
    db.flush()
    return True


def _mark_refunded_lifecycle(db: Session, *, order: Order, buyer: User) -> None:
    order = get_order_by_id(db, order.id) or order
    if order.status == "refunded":
        return
    order.status = "refunded"
    for payment in order.payments or []:
        if payment.status == "successful":
            payment.status = "refunded"
    cancel_fulfillments_for_refunded_order(
        db, order=order, actor_user_id=buyer.id
    )
    db.flush()


def seed_merch_commerce_extras(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> dict[str, int]:
    """Idempotent commerce expansion: vault, POD, carts, QR, reviews, splits path."""
    stats = {
        "bundles": 0,
        "discounts": 0,
        "abandoned_carts": 0,
        "reviews": 0,
        "commerce_orders": 0,
    }

    def _fan(n: int) -> User | None:
        email = f"fan{n}@{DEMO_EMAIL_DOMAIN}"
        row = users.get(email)
        if row is not None:
            return row
        return db.scalar(select(User).where(User.email == email))

    fan1, fan2, fan3, fan4, fan5, fan6, fan7, fan8 = (
        _fan(1),
        _fan(2),
        _fan(3),
        _fan(4),
        _fan(5),
        _fan(6),
        _fan(7),
        _fan(8),
    )
    buyer = users.get(f"buyer@{DEMO_EMAIL_DOMAIN}") or db.scalar(
        select(User).where(User.email == f"buyer@{DEMO_EMAIL_DOMAIN}")
    )

    def _load(ev: Event | None) -> Event | None:
        if ev is None:
            return None
        return db.scalar(
            select(Event)
            .where(Event.id == ev.id)
            .options(selectinload(Event.ticket_types))
        )

    afro = _load(events.get("afrobeats-night-live"))
    comedy = _load(events.get("lagos-comedy-jam"))
    founders = _load(events.get("founders-mixer-lagos"))
    worship = _load(events.get("worship-under-stars"))
    food = _load(events.get("food-and-flow"))

    # --- DJ Maze / Afrobeats commerce flags ---
    if afro is not None:
        host, owner = _host_owner(db, afro)
        if host and owner:
            afro.allow_merch_only_checkout = True
            neon = _find_product(db, event_id=afro.id, name="Neon Cap")
            if neon is not None:
                _apply_product_flags(
                    neon,
                    {
                        "is_sponsor_branded": True,
                        "sponsor_brand_name": "Lagos Beats Co",
                        "sponsor_split_type": "percent",
                        "sponsor_split_value": Decimal("8"),
                        "low_stock_threshold": 5,
                        "storefront_visibility": "host_storefront",
                    },
                )
                for v in neon.variants or []:
                    if v.archived_at is None:
                        v.low_stock_threshold = 5
                        evaluate_variant_stock_alerts(db, product=neon, variant=v)

            tee = _find_product(db, event_id=afro.id, name="Afrobeats Night Tee")
            if tee is not None:
                # Sold-out demo variant
                for v in tee.variants or []:
                    if v.label == "XL / White":
                        v.inventory_count = 0
                        v.reserved_quantity = 0
                        sync_variant_sold_out(v)
                        evaluate_variant_stock_alerts(db, product=tee, variant=v)

            hoodie = _find_product(db, event_id=afro.id, name="Backstage Hoodie")
            vault = db.scalar(
                select(VaultItem).where(
                    VaultItem.host_id == host.id,
                    VaultItem.slug == "unreleased-set",
                )
            )
            if hoodie is not None:
                flags: dict[str, Any] = {
                    "is_vault_exclusive": True,
                    "requires_vault_access": True,
                    "storefront_visibility": "vault_exclusive",
                    "required_access_type": "paid_vault_member",
                    "is_featured": True,
                }
                if vault is not None:
                    flags["required_vault_item_id"] = vault.id
                _apply_product_flags(hoodie, flags)

            poster = _find_product(
                db, event_id=afro.id, name="Afrobeats Recap Poster"
            )
            if poster is not None:
                _apply_product_flags(
                    poster,
                    {
                        "storefront_visibility": "post_event_drop",
                        "post_event_drop_at": datetime.now(UTC) - timedelta(hours=2),
                        "is_featured": True,
                    },
                )

            if not db.scalar(
                select(MerchShippingZone.id).where(
                    MerchShippingZone.host_id == host.id,
                    MerchShippingZone.name == "Lagos metro",
                )
            ):
                upsert_zone(
                    db,
                    host_id=host.id,
                    name="Lagos metro",
                    country="Nigeria",
                    state="Lagos",
                    city=None,
                    flat_fee=Decimal("2500.00"),
                    event_id=afro.id,
                )

            before = db.scalar(
                select(MerchDiscountCode.id).where(
                    MerchDiscountCode.host_id == host.id,
                    MerchDiscountCode.code == "MERCH10",
                )
            )
            _ensure_discount(
                db,
                host_id=host.id,
                code="MERCH10",
                event_id=afro.id,
                description="Demo 10% off Maze merch",
            )
            if before is None and db.scalar(
                select(MerchDiscountCode.id).where(
                    MerchDiscountCode.host_id == host.id,
                    MerchDiscountCode.code == "MERCH10",
                )
            ):
                stats["discounts"] += 1

            ga = db.scalar(
                select(TicketType).where(
                    TicketType.event_id == afro.id,
                    TicketType.type == "regular",
                )
            )
            tee_var = _find_variant(
                db,
                event_id=afro.id,
                product_name="Afrobeats Night Tee",
                variant_label="M / Black",
            )
            if ga is not None and tee_var is not None:
                before_b = db.scalar(
                    select(MerchBundle.id).where(
                        MerchBundle.event_id == afro.id,
                        MerchBundle.name.in_(
                            ("Ticket + T-shirt Bundle", "GA + Tee Pack")
                        ),
                    )
                )
                bundle = _ensure_bundle(
                    db,
                    host_id=host.id,
                    event=afro,
                    name="Ticket + T-shirt Bundle",
                    ticket_type=ga,
                    variant=tee_var,
                    bundle_price=Decimal("10000.00"),
                    description="Regular ticket plus Afrobeats Night Tee.",
                )
                if before_b is None and bundle is not None:
                    stats["bundles"] += 1

    # --- Lagos Comedy Hub ---
    if comedy is not None:
        host, _owner = _host_owner(db, comedy)
        if host:
            comedy.allow_merch_only_checkout = True
            before = db.scalar(
                select(MerchDiscountCode.id).where(
                    MerchDiscountCode.host_id == host.id,
                    MerchDiscountCode.code == "LAUGH10",
                )
            )
            _ensure_discount(
                db,
                host_id=host.id,
                code="LAUGH10",
                event_id=comedy.id,
                description="Demo 10% off Comedy Hub merch",
            )
            if before is None and db.scalar(
                select(MerchDiscountCode.id).where(
                    MerchDiscountCode.host_id == host.id,
                    MerchDiscountCode.code == "LAUGH10",
                )
            ):
                stats["discounts"] += 1

            ga = db.scalar(
                select(TicketType).where(
                    TicketType.event_id == comedy.id,
                    TicketType.type == "regular",
                )
            )
            cap_var = _find_variant(
                db, event_id=comedy.id, product_name="Comedy Cap"
            )
            if ga is not None and cap_var is not None:
                before_b = db.scalar(
                    select(MerchBundle.id).where(
                        MerchBundle.event_id == comedy.id,
                        MerchBundle.name == "Ticket + Comedy Cap Bundle",
                    )
                )
                bundle = _ensure_bundle(
                    db,
                    host_id=host.id,
                    event=comedy,
                    name="Ticket + Comedy Cap Bundle",
                    ticket_type=ga,
                    variant=cap_var,
                    bundle_price=Decimal("9000.00"),
                    description="Comedy ticket plus Comedy Cap.",
                )
                if before_b is None and bundle is not None:
                    stats["bundles"] += 1

    # --- Tech Connect / Founders ---
    if founders is not None:
        host, owner = _host_owner(db, founders)
        if host and owner:
            founders.allow_merch_only_checkout = True
            pack = _find_product(db, event_id=founders.id, name="Startup Pack")
            if pack is not None:
                _apply_product_flags(
                    pack,
                    {
                        "is_sponsor_branded": True,
                        "sponsor_brand_name": "Tech Connect Partners",
                        "sponsor_split_type": "percent",
                        "sponsor_split_value": Decimal("10"),
                        "storefront_visibility": "host_storefront",
                    },
                )
            pod = _find_product(
                db, event_id=founders.id, name="Builder Sticker Sheet"
            )
            if pod is not None:
                _apply_product_flags(
                    pod,
                    {
                        "print_on_demand_enabled": True,
                        "pickup_enabled": True,
                        "storefront_visibility": "host_storefront",
                    },
                )
                for v in pod.variants or []:
                    if v.archived_at is None and not v.print_on_demand_variant_ref:
                        v.print_on_demand_variant_ref = "demo-pod-sticker-sheet"

    # --- Praise Experience size chart + post-event drop ---
    if worship is not None:
        host, owner = _host_owner(db, worship)
        if host and owner:
            chart = _ensure_size_chart(
                db,
                host_id=host.id,
                name="Praise Experience tee — standard",
                product_type="t_shirt",
            )
            tee = _find_product(
                db, event_id=worship.id, name="Praise Experience Tee"
            )
            if tee is not None:
                tee.size_chart_id = chart.id
            drop = _find_product(
                db, event_id=worship.id, name="Praise Night Recap Pin"
            )
            if drop is not None:
                _apply_product_flags(
                    drop,
                    {
                        "storefront_visibility": "post_event_drop",
                        "post_event_drop_at": datetime.now(UTC) - timedelta(hours=1),
                        "is_featured": True,
                    },
                )

    # --- Mainland Vibes shipping ---
    if food is not None:
        host, owner = _host_owner(db, food)
        if host:
            for name in ("Culture Fest Face Mask", "Culture Fest Bucket Hat"):
                prod = _find_product(db, event_id=food.id, name=name)
                if prod is not None:
                    prod.shipping_enabled = True
                    prod.pickup_enabled = True
            if not db.scalar(
                select(MerchShippingZone.id).where(
                    MerchShippingZone.host_id == host.id,
                    MerchShippingZone.name == "Lagos delivery",
                )
            ):
                upsert_zone(
                    db,
                    host_id=host.id,
                    name="Lagos delivery",
                    country="Nigeria",
                    state="Lagos",
                    city=None,
                    flat_fee=Decimal("2000.00"),
                    event_id=food.id,
                )

    db.flush()
    db.commit()  # persist discounts/bundles/zones before persona orders (_safe may rollback)

    # --- Persona advanced flows ---

    # Tolu — Ticket + T-shirt Bundle
    if fan1 and afro and afro.status == "published":
        bundle = db.scalar(
            select(MerchBundle).where(
                MerchBundle.event_id == afro.id,
                MerchBundle.name == "Ticket + T-shirt Bundle",
                MerchBundle.archived_at.is_(None),
            )
        )
        if bundle and not _buyer_has_fulfillment(
            db,
            buyer_id=fan1.id,
            event_id=afro.id,
            product_name="Afrobeats Night Tee",
        ):
            order = _order_merch(
                db, buyer=fan1, event=afro, bundle_id=bundle.id, pay=True
            )
            if order is not None:
                stats["commerce_orders"] += 1

    # Amaka — VIP wristband + Neon Cap (ready for pickup + signed QR)
    if fan2 and afro and afro.status == "published":
        host, owner = _host_owner(db, afro)
        wrist = _find_variant(
            db, event_id=afro.id, product_name="VIP Glow Wristband"
        )
        cap = _find_variant(db, event_id=afro.id, product_name="Neon Cap")
        if (
            wrist
            and cap
            and owner
            and not _buyer_has_fulfillment(
                db, buyer_id=fan2.id, event_id=afro.id, product_name="Neon Cap"
            )
        ):
            order = _order_merch(
                db,
                buyer=fan2,
                event=afro,
                variants=[wrist, cap],
                include_ticket=True,
                vip_ticket=True,
                pay=True,
            )
            if order is not None:
                stats["commerce_orders"] += 1
                fulfills = list(
                    db.scalars(
                        select(MerchFulfillment).where(
                            MerchFulfillment.order_id == order.id
                        )
                    )
                )
                for row in fulfills:
                    _safe(
                        db,
                        update_fulfillment_status,
                        db,
                        user=owner,
                        fulfillment_id=row.id,
                        status="collect_at_stand",
                    )
                    _safe(db, issue_pickup_qr_for_fulfillment, db, row)

    # Amaka — Vault-exclusive Backstage Hoodie (unlocked purchase)
    if fan2 and afro and afro.status == "published":
        hoodie_var = _find_variant(
            db, event_id=afro.id, product_name="Backstage Hoodie"
        )
        if hoodie_var and not _buyer_has_fulfillment(
            db,
            buyer_id=fan2.id,
            event_id=afro.id,
            product_name="Backstage Hoodie",
        ):
            order = _order_merch(
                db, buyer=fan2, event=afro, variant=hoodie_var, pay=True
            )
            if order is not None:
                stats["commerce_orders"] += 1

    # Chidi — Founder Mode Tote Bag (handled in base seed if present; ensure here)
    if fan3 and founders and founders.status == "published":
        variant = _find_variant(
            db, event_id=founders.id, product_name="Founder Mode Tote Bag"
        )
        if variant and not _buyer_has_fulfillment(
            db,
            buyer_id=fan3.id,
            event_id=founders.id,
            product_name="Founder Mode Tote Bag",
        ):
            order = _order_merch(
                db, buyer=fan3, event=founders, variant=variant, pay=True
            )
            if order is not None:
                stats["commerce_orders"] += 1

    # Sade — Comedy Cap + review
    if fan4 and comedy and comedy.status == "published":
        variant = _find_variant(db, event_id=comedy.id, product_name="Comedy Cap")
        if variant and not _buyer_has_fulfillment(
            db, buyer_id=fan4.id, event_id=comedy.id, product_name="Comedy Cap"
        ):
            order = _order_merch(
                db,
                buyer=fan4,
                event=comedy,
                variant=variant,
                include_ticket=True,
                pay=True,
            )
            if order is not None:
                stats["commerce_orders"] += 1
        if _ensure_review_for_paid_merch(
            db,
            buyer=fan4,
            event=comedy,
            product_name="Comedy Cap",
            body="Comedy Cap fits great — bought with my Pàdéyá ticket.",
        ):
            stats["reviews"] += 1

    # Kunle — sponsor-branded Startup Pack (Tech Connect)
    if fan5 and founders and founders.status == "published":
        variant = _find_variant(
            db, event_id=founders.id, product_name="Startup Pack"
        )
        if variant and not _buyer_has_fulfillment(
            db,
            buyer_id=fan5.id,
            event_id=founders.id,
            product_name="Startup Pack",
        ):
            order = _order_merch(
                db, buyer=fan5, event=founders, variant=variant, pay=True
            )
            if order is not None:
                stats["commerce_orders"] += 1

    # Bayo — shipping order (shipped)
    if fan8 and food and food.status in {"published", "completed"}:
        host, owner = _host_owner(db, food)
        variant = _find_variant(
            db, event_id=food.id, product_name="Culture Fest Bucket Hat"
        )
        if (
            variant
            and owner
            and not _buyer_has_fulfillment(
                db,
                buyer_id=fan8.id,
                event_id=food.id,
                product_name="Culture Fest Bucket Hat",
            )
        ):
            addr = ShippingAddressIn(
                recipient_name="Bayo Campus Fan",
                phone="+2348010000008",
                line1="12 Demo Street",
                city="Lagos",
                state="Lagos",
                country="Nigeria",
                postal_code="100001",
            )
            order = _order_merch(
                db,
                buyer=fan8,
                event=food,
                variant=variant,
                pay=True,
                fulfillment_method="shipping",
                shipping_address=addr,
            )
            if order is not None:
                stats["commerce_orders"] += 1
                fulfills = list(
                    db.scalars(
                        select(MerchFulfillment).where(
                            MerchFulfillment.order_id == order.id
                        )
                    )
                )
                for row in fulfills:
                    row.fulfillment_method = "shipping"
                    row.carrier = "Demo Courier"
                    row.tracking_number = "DEMO-SHIP-BAYO"
                    _safe(
                        db,
                        update_fulfillment_status,
                        db,
                        user=owner,
                        fulfillment_id=row.id,
                        status="shipped",
                    )

    # Mira — delivered shipping sample
    if fan6 and food and food.status in {"published", "completed"}:
        host, owner = _host_owner(db, food)
        variant = _find_variant(
            db, event_id=food.id, product_name="Culture Fest Face Mask"
        )
        if (
            variant
            and owner
            and not _buyer_has_fulfillment(
                db,
                buyer_id=fan6.id,
                event_id=food.id,
                product_name="Culture Fest Face Mask",
                status="delivered",
            )
        ):
            addr = ShippingAddressIn(
                recipient_name="Mira Demo Fan",
                phone="+2348010000006",
                line1="5 Demo Close",
                city="Lagos",
                state="Lagos",
                country="Nigeria",
            )
            if not _buyer_has_fulfillment(
                db,
                buyer_id=fan6.id,
                event_id=food.id,
                product_name="Culture Fest Face Mask",
            ):
                order = _order_merch(
                    db,
                    buyer=fan6,
                    event=food,
                    variant=variant,
                    pay=True,
                    fulfillment_method="shipping",
                    shipping_address=addr,
                )
                if order is not None:
                    stats["commerce_orders"] += 1
                    fulfills = list(
                        db.scalars(
                            select(MerchFulfillment).where(
                                MerchFulfillment.order_id == order.id
                            )
                        )
                    )
                    for row in fulfills:
                        row.fulfillment_method = "shipping"
                        _safe(
                            db,
                            update_fulfillment_status,
                            db,
                            user=owner,
                            fulfillment_id=row.id,
                            status="shipped",
                        )
                        _safe(
                            db,
                            update_fulfillment_status,
                            db,
                            user=owner,
                            fulfillment_id=row.id,
                            status="delivered",
                        )

    # Demo buyer — refunded merch + picked-up QR order + post-event drop
    if buyer and afro and afro.status == "published":
        host, owner = _host_owner(db, afro)

        if not _buyer_has_fulfillment(
            db,
            buyer_id=buyer.id,
            event_id=afro.id,
            product_name="Afrobeats Night Tee",
            status="cancelled",
        ):
            variant = _find_variant(
                db,
                event_id=afro.id,
                product_name="Afrobeats Night Tee",
                variant_label="S / Black",
            )
            if variant:
                order = _order_merch(
                    db, buyer=buyer, event=afro, variant=variant, pay=True
                )
                if order is not None:
                    stats["commerce_orders"] += 1
                    _mark_refunded_lifecycle(db, order=order, buyer=buyer)

        if owner is not None and not _buyer_has_fulfillment(
            db,
            buyer_id=buyer.id,
            event_id=afro.id,
            product_name="VIP Glow Wristband",
            status="fulfilled",
        ):
            variant = _find_variant(
                db, event_id=afro.id, product_name="VIP Glow Wristband"
            )
            if variant and not _buyer_has_fulfillment(
                db,
                buyer_id=buyer.id,
                event_id=afro.id,
                product_name="VIP Glow Wristband",
            ):
                order = _order_merch(
                    db,
                    buyer=buyer,
                    event=afro,
                    variant=variant,
                    include_ticket=True,
                    vip_ticket=True,
                    pay=True,
                )
                if order is not None:
                    stats["commerce_orders"] += 1
                    fulfills = list(
                        db.scalars(
                            select(MerchFulfillment).where(
                                MerchFulfillment.order_id == order.id
                            )
                        )
                    )
                    for row in fulfills:
                        _safe(db, issue_pickup_qr_for_fulfillment, db, row)
                        _safe(
                            db,
                            mark_fulfilled,
                            db,
                            user=owner,
                            fulfillment_id=row.id,
                        )

        # Post-event drop purchase
        poster_var = _find_variant(
            db, event_id=afro.id, product_name="Afrobeats Recap Poster"
        )
        if poster_var and not _buyer_has_fulfillment(
            db,
            buyer_id=buyer.id,
            event_id=afro.id,
            product_name="Afrobeats Recap Poster",
        ):
            order = _order_merch(
                db, buyer=buyer, event=afro, variant=poster_var, pay=True
            )
            if order is not None:
                stats["commerce_orders"] += 1

    # Cancelled (non-refund) sample if needed — keep a cancelled fulfillment distinct
    # from refunded via status already set by refund lifecycle.

    # Ada — abandoned cart last so later _safe rollbacks cannot wipe it.
    # food-and-flow is a completed showcase event — still seed recovery cart.
    if fan7 and food and food.status in {"published", "completed"}:
        product = _find_product(
            db, event_id=food.id, name="Culture Fest Bucket Hat"
        )
        variant = _find_variant(
            db, event_id=food.id, product_name="Culture Fest Bucket Hat"
        )
        if product and variant:
            if _ensure_abandoned_cart(
                db, buyer=fan7, event=food, variant=variant, product=product
            ):
                stats["abandoned_carts"] += 1
                db.commit()

    # Extra marketplace bundles (VIP + merch, couple caps, group wristbands)
    if afro is not None:
        host, _owner = _host_owner(db, afro)
        vip_tt = db.scalar(
            select(TicketType).where(
                TicketType.event_id == afro.id,
                TicketType.type == "vip",
            )
        )
        ga_tt = db.scalar(
            select(TicketType).where(
                TicketType.event_id == afro.id,
                TicketType.type == "regular",
            )
        )
        hoodie_var = _find_variant(
            db, event_id=afro.id, product_name="Backstage Hoodie"
        )
        neon_var = _find_variant(db, event_id=afro.id, product_name="Neon Cap")
        wrist_var = _find_variant(
            db, event_id=afro.id, product_name="VIP Glow Wristband"
        )
        if host and vip_tt and hoodie_var:
            before = db.scalar(
                select(MerchBundle.id).where(
                    MerchBundle.event_id == afro.id,
                    MerchBundle.name == "VIP + Merch Pack",
                )
            )
            bundle = _ensure_bundle(
                db,
                host_id=host.id,
                event=afro,
                name="VIP + Merch Pack",
                ticket_type=vip_tt,
                variant=hoodie_var,
                bundle_price=Decimal("45000.00"),
                description="VIP ticket plus Backstage Hoodie.",
            )
            if before is None and bundle is not None:
                stats["bundles"] += 1
        if host and ga_tt and neon_var:
            before = db.scalar(
                select(MerchBundle.id).where(
                    MerchBundle.event_id == afro.id,
                    MerchBundle.name == "Couple Ticket + Caps",
                )
            )
            bundle = _ensure_bundle(
                db,
                host_id=host.id,
                event=afro,
                name="Couple Ticket + Caps",
                ticket_type=ga_tt,
                variant=neon_var,
                bundle_price=Decimal("18000.00"),
                description="GA ticket with Neon Cap for couples.",
            )
            if before is None and bundle is not None:
                stats["bundles"] += 1
        if host and ga_tt and wrist_var:
            before = db.scalar(
                select(MerchBundle.id).where(
                    MerchBundle.event_id == afro.id,
                    MerchBundle.name == "Group Pass + Wristbands",
                )
            )
            bundle = _ensure_bundle(
                db,
                host_id=host.id,
                event=afro,
                name="Group Pass + Wristbands",
                ticket_type=ga_tt,
                variant=wrist_var,
                bundle_price=Decimal("16000.00"),
                description="GA ticket with glow wristband pack.",
            )
            if before is None and bundle is not None:
                stats["bundles"] += 1
        if host and vip_tt and hoodie_var:
            before = db.scalar(
                select(MerchBundle.id).where(
                    MerchBundle.event_id == afro.id,
                    MerchBundle.name == "Vault Access + Hoodie Bundle",
                )
            )
            bundle = _ensure_bundle(
                db,
                host_id=host.id,
                event=afro,
                name="Vault Access + Hoodie Bundle",
                ticket_type=vip_tt,
                variant=hoodie_var,
                bundle_price=Decimal("52000.00"),
                description="VIP + Vault-eligible Backstage Hoodie bundle.",
            )
            if before is None and bundle is not None:
                stats["bundles"] += 1

    stats["notifications"] = _seed_merch_demo_notifications(db, users=users, events=events)

    db.flush()
    return stats


def _seed_merch_demo_notifications(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> int:
    """Seed safe in-app merch notification examples for dashboards."""
    from datetime import UTC, datetime, timedelta

    from app.messaging.models import InAppNotification

    created = 0

    def ensure(
        *,
        user: User | None,
        kind: str,
        title: str,
        body: str,
        link_path: str,
        hours_ago: int = 2,
    ) -> None:
        nonlocal created
        if user is None:
            return
        existing = db.scalar(
            select(InAppNotification.id).where(
                InAppNotification.user_id == user.id,
                InAppNotification.kind == kind,
                InAppNotification.title == title[:160],
            )
        )
        if existing is not None:
            return
        db.add(
            InAppNotification(
                user_id=user.id,
                kind=kind[:64],
                title=title[:160],
                body=body[:240],
                link_path=link_path[:300],
                created_at=datetime.now(UTC) - timedelta(hours=hours_ago),
            )
        )
        created += 1

    fan1 = users.get(f"fan1@{DEMO_EMAIL_DOMAIN}") or users.get("fan1")
    fan2 = users.get(f"fan2@{DEMO_EMAIL_DOMAIN}") or users.get("fan2")
    buyer = users.get(f"buyer@{DEMO_EMAIL_DOMAIN}") or users.get("buyer")
    # users dict may be keyed by role labels — also try email lookups
    from app.users.service import get_user_by_email

    fan1 = fan1 or get_user_by_email(db, f"fan1@{DEMO_EMAIL_DOMAIN}")
    fan2 = fan2 or get_user_by_email(db, f"fan2@{DEMO_EMAIL_DOMAIN}")
    buyer = buyer or get_user_by_email(db, f"buyer@{DEMO_EMAIL_DOMAIN}")

    ensure(
        user=fan1,
        kind="merch.confirmed",
        title="Merch order confirmed",
        body="Your Pàdéyá merch order is confirmed. Pickup code is ready in My Merch.",
        link_path="/dashboard/merchandise",
        hours_ago=5,
    )
    ensure(
        user=fan2,
        kind="merch.ready_for_pickup",
        title="Merch ready for pickup",
        body="Your Neon Cap is ready at the merch stand. Show your pickup code.",
        link_path="/dashboard/merchandise",
        hours_ago=3,
    )
    ensure(
        user=buyer,
        kind="merch.picked_up",
        title="Merch fulfilled",
        body="Your VIP Glow Wristband was marked picked up. Enjoy the night.",
        link_path="/dashboard/merchandise",
        hours_ago=1,
    )
    ensure(
        user=fan2,
        kind="merch.post_event_drop",
        title="Post-event drop is live",
        body="Afrobeats Recap Poster is live for eligible fans.",
        link_path="/merch/drops",
        hours_ago=4,
    )
    ensure(
        user=fan2,
        kind="merch.vault_unlocked",
        title="Vault merch unlocked",
        body="Backstage Hoodie is unlocked with your Vault access.",
        link_path="/merch/vault",
        hours_ago=6,
    )
    db.flush()
    return created


def ensure_catalog_product(
    db: Session,
    *,
    host_owner: User,
    event: Event,
    spec: dict[str, Any],
) -> bool:
    """Create catalog product when missing. Returns True if created."""
    from app.demo.assets import merch_image

    existing = db.scalar(
        select(EventMerchProduct.id).where(
            EventMerchProduct.event_id == event.id,
            EventMerchProduct.name == spec["name"],
            EventMerchProduct.archived_at.is_(None),
        )
    )
    if existing is not None:
        product = db.get(EventMerchProduct, existing)
        if product is not None and not product.image_url:
            kind = {
                "t_shirt": "tee",
                "hoodie": "hoodie",
                "cap": "cap",
                "tote_bag": "tote",
                "wristband": "wristband",
                "poster": "poster",
                "face_mask": "mask",
            }.get(spec.get("product_type") or product.product_type or "", "apparel")
            product.image_url = merch_image(kind)
            product.marketplace_listed = True
            db.flush()
        return False

    image = merch_image(
        {
            "t_shirt": "tee",
            "hoodie": "hoodie",
            "cap": "cap",
            "tote_bag": "tote",
            "wristband": "wristband",
            "poster": "poster",
            "face_mask": "mask",
            "souvenir": "sticker",
        }.get(spec.get("product_type") or "", "apparel")
    )
    payload = MerchProductCreate(
        name=spec["name"],
        description=spec.get("description"),
        product_type=spec.get("product_type"),
        base_price=spec["base_price"],
        status=spec.get("status") or "active",
        image_url=image,
        cover_image_url=image,
        pickup_instructions=spec.get("pickup_instructions"),
        pickup_location_label=spec.get("pickup_location_label"),
        requires_ticket=bool(spec.get("requires_ticket")),
        show_on_event_page=True,
        is_featured=bool(spec.get("is_featured")),
        pickup_enabled=bool(spec.get("pickup_enabled", True)),
        shipping_enabled=bool(spec.get("shipping_enabled", False)),
        print_on_demand_enabled=bool(spec.get("print_on_demand_enabled", False)),
        is_sponsor_branded=bool(spec.get("is_sponsor_branded", False)),
        sponsor_brand_name=spec.get("sponsor_brand_name"),
        sponsor_split_type=spec.get("sponsor_split_type"),
        sponsor_split_value=spec.get("sponsor_split_value"),
        marketplace_listed=True,
        variants=[
            MerchVariantCreate(
                label=v["label"],
                size=v.get("size"),
                color=v.get("color"),
                sku=v.get("sku"),
                inventory_count=v["inventory_count"],
                status=v.get("status") or "active",
                print_on_demand_variant_ref=v.get("print_on_demand_variant_ref"),
            )
            for v in spec["variants"]
        ],
    )
    row = _safe(
        db,
        create_product,
        db,
        user=host_owner,
        event_id=event.id,
        payload=payload,
    )
    return row is not None
