"""API routes for advanced merch commerce features."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.events.models import Event, TicketType
from app.hosts.models import Host
from app.hosts.team_access import require_host_for_permission
from app.merch import bundles as bundles_svc
from app.merch import cart as cart_svc
from app.merch import discounts as discounts_svc
from app.merch import pod as pod_svc
from app.merch import post_event_drops as drops_svc
from app.merch import qr_pickup as qr_svc
from app.merch import reviews as reviews_svc
from app.merch import revenue as revenue_svc
from app.merch import shipping as shipping_svc
from app.merch import size_charts as charts_svc
from app.merch import stock_alerts as alerts_svc
from app.merch import storefront as storefront_svc
from app.merch.discounts import serialize_discount
from app.merch.fulfillment import update_fulfillment_status
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchFulfillment
from app.merch.service import can_manage_event_merch, effective_variant_price
from app.merch.size_charts import serialize_chart
from app.users.models import User

router = APIRouter(tags=["merch-commerce"])


def _require_host(
    db: Session, user: User, permission: str | tuple[str, ...]
) -> Host:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission=permission
    )
    return host


class BundleCreateIn(BaseModel):
    name: str
    description: str | None = None
    bundle_price: Decimal
    currency: str = "NGN"
    ticket_type_id: UUID
    merch_variant_rules: list[dict[str, Any]]
    inventory_limit: int | None = None
    max_per_buyer: int | None = None
    sales_start_at: datetime | None = None
    sales_end_at: datetime | None = None
    status: str = "draft"


class BundleUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    bundle_price: Decimal | None = None
    currency: str | None = None
    ticket_type_id: UUID | None = None
    merch_variant_rules: list[dict[str, Any]] | None = None
    inventory_limit: int | None = None
    max_per_buyer: int | None = None
    sales_start_at: datetime | None = None
    sales_end_at: datetime | None = None
    status: str | None = None


class DiscountCreateIn(BaseModel):
    code: str
    description: str | None = None
    discount_type: str
    discount_value: Decimal
    currency: str | None = None
    applies_to: str = "merch_only"
    event_id: UUID | None = None
    product_ids: list[str] | None = None
    min_order_amount: Decimal | None = None
    usage_limit: int | None = None
    per_buyer_limit: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str = "active"


class DiscountUpdateIn(BaseModel):
    description: str | None = None
    discount_type: str | None = None
    discount_value: Decimal | None = None
    currency: str | None = None
    applies_to: str | None = None
    event_id: UUID | None = None
    clear_event_id: bool = False
    product_ids: list[str] | None = None
    min_order_amount: Decimal | None = None
    usage_limit: int | None = None
    per_buyer_limit: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = None


class MerchDiscountValidateItemIn(BaseModel):
    merch_variant_id: UUID | None = None
    ticket_type_id: UUID | None = None
    quantity: int = Field(ge=1, le=50)
    from_bundle: bool = False


class MerchDiscountValidateIn(BaseModel):
    code: str
    event_id: UUID
    items: list[MerchDiscountValidateItemIn] = Field(min_length=1)
    shipping_amount: Decimal = Decimal("0")


class ShippingZoneIn(BaseModel):
    name: str
    country: str
    state: str | None = None
    city: str | None = None
    flat_fee: Decimal = Decimal("0")
    event_id: UUID | None = None


class ShippingZoneUpdateIn(BaseModel):
    name: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    flat_fee: Decimal | None = None
    event_id: UUID | None = None
    clear_event_id: bool = False
    status: str | None = None


class SizeChartIn(BaseModel):
    name: str
    product_type: str | None = None
    units: str = "cm"
    chart_json: Any = Field(default_factory=dict)
    fit_notes: str | None = None


class SizeChartUpdateIn(BaseModel):
    name: str | None = None
    product_type: str | None = None
    units: str | None = None
    chart_json: Any | None = None
    fit_notes: str | None = None
    status: str | None = None


class ReviewCreateIn(BaseModel):
    order_item_id: UUID
    rating: int = Field(ge=1, le=5)
    body: str | None = None


class CartItemIn(BaseModel):
    variant_id: UUID
    quantity: int = Field(ge=1, le=50)


class CartItemQuantityIn(BaseModel):
    quantity: int = Field(ge=1, le=50)


class MerchQrScanIn(BaseModel):
    token: str | None = None
    pickup_code: str | None = None


class ShipIn(BaseModel):
    tracking_number: str | None = None
    carrier: str | None = None


class HostStorefrontSettingsIn(BaseModel):
    enabled: bool | None = None
    title: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    visibility: str | None = Field(default=None, max_length=32)


@router.get("/u/{username}/merch")
def public_host_merch_storefront(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    event: str | None = None,
    product_type: str | None = None,
    availability: str | None = None,
    kind: str | None = None,
) -> dict:
    return storefront_svc.get_host_storefront(
        db,
        username=username,
        buyer_user_id=user.id if user else None,
        viewer=user,
        event=event,
        product_type=product_type,
        availability=availability,
        kind=kind,
    )


@router.get("/u/{username}/merch/{product_id}")
def public_host_merch_product(
    username: str,
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> dict:
    return storefront_svc.get_storefront_product(
        db,
        username=username,
        product_id=product_id,
        buyer_user_id=user.id if user else None,
        viewer=user,
    )


@router.get("/host/merchandise/storefront")
def get_host_merch_storefront_settings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission=("merch.view", "merch.edit"))
    return storefront_svc.get_host_storefront_settings(db, host=host)


@router.patch("/host/merchandise/storefront")
def patch_host_merch_storefront_settings(
    payload: HostStorefrontSettingsIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.edit")
    data = storefront_svc.update_host_storefront_settings(
        db,
        host=host,
        enabled=payload.enabled,
        title=payload.title,
        description=payload.description,
        visibility=payload.visibility,
    )
    db.commit()
    return data


class PostEventDropCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    base_price: Decimal = Field(ge=0)
    audience: str = Field(default="public", max_length=32)
    drop_description: str | None = Field(default=None, max_length=4000)
    post_event_drop_at: datetime | None = None
    currency: str = Field(default="NGN", max_length=8)
    product_type: str | None = Field(default="souvenir", max_length=64)
    image_url: str | None = Field(default=None, max_length=500)
    status: str = Field(default="draft", max_length=32)
    inventory_count: int = Field(default=0, ge=0, le=100000)
    variant_label: str = Field(default="Default", max_length=80)


class PostEventDropPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    drop_description: str | None = Field(default=None, max_length=4000)
    audience: str | None = Field(default=None, max_length=32)
    post_event_drop_at: datetime | None = None
    status: str | None = Field(default=None, max_length=32)
    base_price: Decimal | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=500)


@router.get("/host/events/{event_id}/post-event-drops")
def list_host_post_event_drops(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    from app.merch import post_event_drops as drops_svc

    return drops_svc.list_post_event_drops(db, user=user, event_id=event_id)


@router.post("/host/events/{event_id}/post-event-drops")
def create_host_post_event_drop(
    event_id: UUID,
    payload: PostEventDropCreateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    from app.merch import post_event_drops as drops_svc

    return drops_svc.create_post_event_drop(
        db,
        user=user,
        event_id=event_id,
        name=payload.name,
        base_price=payload.base_price,
        audience=payload.audience,
        drop_description=payload.drop_description,
        post_event_drop_at=payload.post_event_drop_at,
        currency=payload.currency,
        product_type=payload.product_type,
        image_url=payload.image_url,
        status=payload.status,
        inventory_count=payload.inventory_count,
        variant_label=payload.variant_label,
    )


@router.patch("/host/events/{event_id}/post-event-drops/{product_id}")
def patch_host_post_event_drop(
    event_id: UUID,
    product_id: UUID,
    payload: PostEventDropPatchIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    from app.merch import post_event_drops as drops_svc

    product = db.get(EventMerchProduct, product_id)
    if product is None or product.event_id != event_id:
        raise HTTPException(status_code=404, detail="Drop not found")
    return drops_svc.patch_post_event_drop(
        db,
        user=user,
        product_id=product_id,
        name=payload.name,
        drop_description=payload.drop_description,
        audience=payload.audience,
        post_event_drop_at=payload.post_event_drop_at,
        status=payload.status,
        base_price=payload.base_price,
        image_url=payload.image_url,
    )


@router.get("/merch/me/post-event-drops")
def list_my_eligible_post_event_drops(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    from app.merch import post_event_drops as drops_svc

    return drops_svc.list_buyer_eligible_drops(db, buyer_user_id=user.id)


@router.get("/host/events/{event_id}/bundles")
def list_host_bundles(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    if not can_manage_event_merch(
        db,
        user,
        event_id,
        permission=("merch.view", "merch.manage_bundles", "merch.edit"),
    ):
        raise HTTPException(status_code=403, detail="Not allowed")
    return bundles_svc.list_event_bundles(db, event_id=event_id, public_only=False)


@router.post("/host/events/{event_id}/bundles")
def create_bundle(
    event_id: UUID,
    payload: BundleCreateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    if not can_manage_event_merch(
        db, user, event_id, permission="merch.manage_bundles"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    host = db.get(Host, event.host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    row = bundles_svc.create_bundle(
        db,
        host_id=host.id,
        event_id=event_id,
        name=payload.name,
        ticket_type_id=payload.ticket_type_id,
        merch_variant_rules=payload.merch_variant_rules,
        bundle_price=payload.bundle_price,
        description=payload.description,
        currency=payload.currency,
        inventory_limit=payload.inventory_limit,
        max_per_buyer=payload.max_per_buyer,
        sales_start_at=payload.sales_start_at,
        sales_end_at=payload.sales_end_at,
        status=payload.status,
    )
    db.commit()
    db.refresh(row)
    return bundles_svc.serialize_bundle(db, row)


@router.get("/host/events/{event_id}/bundles/{bundle_id}")
def get_host_bundle(
    event_id: UUID,
    bundle_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    if not can_manage_event_merch(
        db,
        user,
        event_id,
        permission=("merch.view", "merch.manage_bundles", "merch.edit"),
    ):
        raise HTTPException(status_code=403, detail="Not allowed")
    row = bundles_svc.get_event_bundle(db, event_id=event_id, bundle_id=bundle_id)
    return bundles_svc.serialize_bundle(db, row)


@router.patch("/host/events/{event_id}/bundles/{bundle_id}")
def patch_host_bundle(
    event_id: UUID,
    bundle_id: UUID,
    payload: BundleUpdateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    if not can_manage_event_merch(
        db, user, event_id, permission="merch.manage_bundles"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")
    row = bundles_svc.get_event_bundle(db, event_id=event_id, bundle_id=bundle_id)
    data = payload.model_dump(exclude_unset=True)
    bundles_svc.update_bundle(db, bundle=row, data=data)
    db.commit()
    db.refresh(row)
    return bundles_svc.serialize_bundle(db, row)


@router.post("/host/events/{event_id}/bundles/{bundle_id}/archive")
def archive_host_bundle(
    event_id: UUID,
    bundle_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    if not can_manage_event_merch(
        db, user, event_id, permission="merch.manage_bundles"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")
    row = bundles_svc.get_event_bundle(db, event_id=event_id, bundle_id=bundle_id)
    bundles_svc.archive_bundle(db, bundle=row)
    db.commit()
    db.refresh(row)
    return bundles_svc.serialize_bundle(db, row)


@router.get("/events/{event_id}/bundles")
def public_bundles(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    return bundles_svc.list_event_bundles(db, event_id=event_id, public_only=True)


@router.get("/host/merchandise/discounts")
def list_discounts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    host = _require_host(db, user, permission="merch.manage_discounts")
    return discounts_svc.list_host_discounts(db, host_id=host.id)


@router.post("/host/merchandise/discounts")
def create_discount(
    payload: DiscountCreateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.manage_discounts")
    row = discounts_svc.create_discount(
        db,
        host_id=host.id,
        code=payload.code,
        description=payload.description,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        currency=payload.currency,
        applies_to=payload.applies_to,
        event_id=payload.event_id,
        product_ids=payload.product_ids,
        min_order_amount=payload.min_order_amount,
        usage_limit=payload.usage_limit,
        per_buyer_limit=payload.per_buyer_limit,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=payload.status,
    )
    db.commit()
    db.refresh(row)
    return serialize_discount(row)


@router.patch("/host/merchandise/discounts/{discount_id}")
def patch_discount(
    discount_id: UUID,
    payload: DiscountUpdateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.manage_discounts")
    data = payload.model_dump(exclude_unset=True)
    clear_event_id = bool(data.pop("clear_event_id", False))
    row = discounts_svc.update_discount(
        db,
        host_id=host.id,
        discount_id=discount_id,
        clear_event_id=clear_event_id,
        **data,
    )
    db.commit()
    db.refresh(row)
    return serialize_discount(row)


@router.post("/host/merchandise/discounts/{discount_id}/archive")
def archive_discount(
    discount_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.manage_discounts")
    row = discounts_svc.archive_discount(
        db, host_id=host.id, discount_id=discount_id
    )
    db.commit()
    db.refresh(row)
    return serialize_discount(row)


@router.post("/merch/discounts/validate")
def validate_merch_discount_code(
    payload: MerchDiscountValidateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    event = db.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    merch_lines: list[tuple[EventMerchProduct, Decimal, bool]] = []
    ticket_subtotal = Decimal("0.00")
    for item in payload.items:
        if item.merch_variant_id is not None:
            variant = db.get(EventMerchVariant, item.merch_variant_id)
            if variant is None:
                raise HTTPException(status_code=400, detail="Merch variant not found")
            product = db.get(EventMerchProduct, variant.product_id)
            if product is None or product.host_id != event.host_id:
                raise HTTPException(status_code=400, detail="Merch product not found")
            unit = effective_variant_price(product, variant)
            merch_lines.append(
                (product, unit * item.quantity, item.from_bundle)
            )
        elif item.ticket_type_id is not None:
            ticket = db.get(TicketType, item.ticket_type_id)
            if ticket is None or ticket.event_id != event.id:
                raise HTTPException(status_code=400, detail="Ticket type not found")
            ticket_subtotal += Decimal(ticket.price) * item.quantity
        else:
            raise HTTPException(
                status_code=400,
                detail="Each item needs merch_variant_id or ticket_type_id",
            )

    try:
        code, discount, shipping_after = discounts_svc.validate_merch_discount(
            db,
            code_str=payload.code,
            host_id=event.host_id,
            buyer=user,
            merch_lines=merch_lines,
            ticket_subtotal=ticket_subtotal,
            shipping_amount=Decimal(payload.shipping_amount or 0),
        )
    except HTTPException as exc:
        return {
            "valid": False,
            "code": None,
            "discount_amount": "0.00",
            "shipping_amount": str(Decimal(payload.shipping_amount or 0)),
            "reason": exc.detail if isinstance(exc.detail, str) else "Invalid code",
        }

    return {
        "valid": True,
        "code": code.code,
        "discount_amount": str(discount),
        "shipping_amount": str(shipping_after),
        "discount_type": code.discount_type,
        "reason": None,
    }


@router.get("/host/merchandise/shipping-zones")
def list_zones(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    host = _require_host(db, user, permission="merch.manage_shipping")
    zones = shipping_svc.list_host_zones(db, host_id=host.id)
    return [shipping_svc.serialize_zone(z) for z in zones]


@router.post("/host/merchandise/shipping-zones")
def create_zone(
    payload: ShippingZoneIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.manage_shipping")
    row = shipping_svc.upsert_zone(
        db,
        host_id=host.id,
        name=payload.name,
        country=payload.country,
        state=payload.state,
        city=payload.city,
        flat_fee=payload.flat_fee,
        event_id=payload.event_id,
    )
    db.commit()
    db.refresh(row)
    return shipping_svc.serialize_zone(row)


@router.patch("/host/merchandise/shipping-zones/{zone_id}")
def patch_zone(
    zone_id: UUID,
    payload: ShippingZoneUpdateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.manage_shipping")
    data = payload.model_dump(exclude_unset=True)
    clear_event_id = bool(data.pop("clear_event_id", False))
    row = shipping_svc.update_zone(
        db,
        host_id=host.id,
        zone_id=zone_id,
        clear_event_id=clear_event_id,
        **data,
    )
    db.commit()
    db.refresh(row)
    return shipping_svc.serialize_zone(row)


@router.post("/host/merchandise/shipping-zones/{zone_id}/archive")
def archive_zone(
    zone_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    """Soft-archive — excluded from new checkout; existing order fees unchanged."""
    host = _require_host(db, user, permission="merch.manage_shipping")
    row = shipping_svc.archive_zone(db, host_id=host.id, zone_id=zone_id)
    db.commit()
    db.refresh(row)
    return shipping_svc.serialize_zone(row)


@router.post("/host/merchandise/order-items/{fulfillment_id}/ship")
def mark_shipped(
    fulfillment_id: UUID,
    payload: ShipIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(
        db, user, permission=("merch.fulfill_orders", "merch.mark_picked_up")
    )
    row = db.get(MerchFulfillment, fulfillment_id)
    if row is None or row.host_id != host.id:
        raise HTTPException(status_code=404, detail="Fulfillment not found")
    if row.fulfillment_method != "shipping":
        raise HTTPException(status_code=400, detail="Not a shipping fulfillment")
    if row.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled merch cannot ship")
    previous_status = row.status
    row.status = "shipped"
    from datetime import UTC, datetime

    row.shipped_at = datetime.now(UTC)
    if payload.tracking_number:
        row.tracking_number = payload.tracking_number.strip()[:120]
    if payload.carrier:
        row.carrier = payload.carrier.strip()[:80]
    db.add(row)
    if previous_status != "shipped":
        from app.analytics.trusted import emit_merch_shipped
        from app.merch.models import EventMerchVariant

        variant = db.get(EventMerchVariant, row.merch_variant_id)
        emit_merch_shipped(
            db,
            fulfillment_id=row.id,
            event_id=row.event_id,
            host_id=row.host_id,
            actor_user_id=user.id,
            merch_product_id=variant.product_id if variant else None,
            merch_variant_id=row.merch_variant_id,
            quantity=row.quantity,
        )
    try:
        from app.merch.notifications import notify_buyer_merch_shipped

        notify_buyer_merch_shipped(db, fulfillment=row)
    except Exception:
        pass
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "status": row.status,
        "tracking_number": row.tracking_number,
        "carrier": row.carrier,
        "shipped_at": row.shipped_at,
    }


@router.post("/host/merchandise/order-items/{fulfillment_id}/deliver")
def mark_delivered(
    fulfillment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(
        db, user, permission=("merch.fulfill_orders", "merch.mark_picked_up")
    )
    row = db.get(MerchFulfillment, fulfillment_id)
    if row is None or row.host_id != host.id:
        raise HTTPException(status_code=404, detail="Fulfillment not found")
    if row.status not in {"shipped", "packed", "awaiting_shipment"}:
        raise HTTPException(status_code=400, detail="Fulfillment is not in transit")
    from datetime import UTC, datetime

    previous_status = row.status
    row.status = "delivered"
    row.delivered_at = datetime.now(UTC)
    db.add(row)
    if previous_status != "delivered":
        from app.analytics.trusted import emit_merch_delivered
        from app.merch.models import EventMerchVariant

        variant = db.get(EventMerchVariant, row.merch_variant_id)
        emit_merch_delivered(
            db,
            fulfillment_id=row.id,
            event_id=row.event_id,
            host_id=row.host_id,
            actor_user_id=user.id,
            merch_product_id=variant.product_id if variant else None,
            merch_variant_id=row.merch_variant_id,
            quantity=row.quantity,
        )
    try:
        from app.merch.notifications import notify_buyer_merch_delivered

        notify_buyer_merch_delivered(db, fulfillment=row)
    except Exception:
        pass
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status, "delivered_at": row.delivered_at}


@router.post("/host/events/{event_id}/merchandise/scan-qr")
def scan_merch_qr(
    event_id: UUID,
    payload: MerchQrScanIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return qr_svc.scan_merch_pickup(
        db,
        user=user,
        event_id=event_id,
        token=payload.token,
        pickup_code=payload.pickup_code,
    )


@router.get("/dashboard/merchandise/{fulfillment_id}/qr")
def buyer_merch_qr(
    fulfillment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    row = db.get(MerchFulfillment, fulfillment_id)
    if row is None or row.buyer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    data = {"id": row.id, "pickup_code": row.pickup_code, "status": row.status}
    return qr_svc.attach_qr_to_serialize(db, data, row)


@router.get("/host/merchandise/size-charts")
def list_host_charts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    host = _require_host(db, user, permission=("merch.view", "merch.edit"))
    return charts_svc.list_charts(db, host_id=host.id)


@router.post("/host/merchandise/size-charts")
def create_chart(
    payload: SizeChartIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.edit")
    row = charts_svc.create_chart(
        db,
        host_id=host.id,
        name=payload.name,
        chart_json=payload.chart_json,
        product_type=payload.product_type,
        units=payload.units,
        fit_notes=payload.fit_notes,
    )
    db.commit()
    db.refresh(row)
    return serialize_chart(row)


@router.patch("/host/merchandise/size-charts/{chart_id}")
def patch_chart(
    chart_id: UUID,
    payload: SizeChartUpdateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.edit")
    row = charts_svc.update_chart(
        db,
        host_id=host.id,
        chart_id=chart_id,
        **payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(row)
    return serialize_chart(row)


@router.post("/host/merchandise/size-charts/{chart_id}/archive")
def archive_chart(
    chart_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.edit")
    row = charts_svc.archive_chart(db, host_id=host.id, chart_id=chart_id)
    db.commit()
    db.refresh(row)
    return serialize_chart(row)


@router.get("/merch/size-charts/{chart_id}")
def public_chart(
    chart_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    data = charts_svc.get_public_chart(db, chart_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Size chart not found")
    return data


class ReviewUpdateIn(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    body: str | None = None


class HostReplyIn(BaseModel):
    reply: str = Field(min_length=2, max_length=4000)


class AdminReviewModerateIn(BaseModel):
    action: str = Field(description="hide or restore")
    note: str | None = None


@router.post("/dashboard/merchandise/reviews")
def create_review(
    payload: ReviewCreateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return reviews_svc.create_review(
        db,
        user=user,
        order_item_id=payload.order_item_id,
        rating=payload.rating,
        body=payload.body,
    )


@router.get("/dashboard/merchandise/reviews/by-order-item/{order_item_id}")
def get_own_review_for_order_item(
    order_item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict | None:
    return reviews_svc.get_own_review_for_order_item(
        db, user=user, order_item_id=order_item_id
    )


@router.patch("/dashboard/merchandise/reviews/{review_id}")
def update_own_review(
    review_id: UUID,
    payload: ReviewUpdateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return reviews_svc.update_own_review(
        db,
        user=user,
        review_id=review_id,
        rating=payload.rating,
        body=payload.body,
    )


@router.delete("/dashboard/merchandise/reviews/{review_id}")
def remove_own_review(
    review_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return reviews_svc.remove_own_review(db, user=user, review_id=review_id)


@router.get("/merch/products/{product_id}/reviews")
def list_reviews(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return reviews_svc.list_product_reviews(db, product_id=product_id)


@router.get("/host/merchandise/reviews")
def list_host_reviews(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    host = _require_host(db, user, permission=("merch.view", "merch.edit"))
    return reviews_svc.list_host_reviews(db, host_id=host.id)


@router.post("/host/merchandise/reviews/{review_id}/reply")
def host_reply_review(
    review_id: UUID,
    payload: HostReplyIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.edit")
    return reviews_svc.host_reply(
        db,
        host_id=host.id,
        review_id=review_id,
        reply=payload.reply,
        actor_user_id=user.id,
    )


@router.delete("/host/merchandise/reviews/{review_id}")
def host_delete_review_forbidden(review_id: UUID, user: CurrentUser) -> None:
    # Product invariant: hosts cannot delete reviews.
    raise HTTPException(
        status_code=403,
        detail="Hosts cannot delete product reviews",
    )


@router.get("/admin/merchandise/reviews")
def list_admin_reviews(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    _ = user
    return reviews_svc.list_admin_reviews(
        db, status=status, limit=limit, offset=offset
    )


@router.post("/admin/merchandise/reviews/{review_id}/moderate")
def admin_moderate_review(
    review_id: UUID,
    payload: AdminReviewModerateIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
) -> dict:
    return reviews_svc.admin_moderate_review(
        db,
        review_id=review_id,
        action=payload.action,
        note=payload.note,
        actor_user_id=user.id,
    )


@router.get("/host/merchandise/stock-alerts")
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    host = _require_host(db, user, permission="merch.manage_inventory")
    return alerts_svc.list_host_alerts(db, host_id=host.id)


@router.get("/host/merchandise/revenue")
def host_revenue(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    event_id: UUID | None = None,
) -> dict:
    host = _require_host(
        db, user, permission=("finance.view_sales_summary", "merch.view")
    )
    return revenue_svc.host_revenue_report(
        db, host_id=host.id, event_id=event_id
    )


@router.get("/host/merchandise/revenue/export.csv")
def host_revenue_export(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    host = _require_host(
        db, user, permission=("finance.view_sales_summary", "merch.view")
    )
    csv_text = revenue_svc.export_host_revenue_csv(db, host_id=host.id)
    write_audit_log(
        db,
        action="merch.revenue.export.host",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host.id),
    )
    db.commit()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=host-merch-revenue.csv"
        },
    )


@router.get("/admin/merchandise/revenue")
def admin_revenue(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "admin.full_access"))
    ],
) -> dict:
    return revenue_svc.admin_revenue_report(db)


@router.get("/admin/merchandise/revenue/export.csv")
def admin_revenue_export(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "admin.full_access"))
    ],
) -> Response:
    csv_text = revenue_svc.export_admin_revenue_csv(db)
    write_audit_log(
        db,
        action="merch.revenue.export.admin",
        actor_user_id=user.id,
        resource_type="platform",
        resource_id="merch_revenue",
    )
    db.commit()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=admin-merch-revenue.csv"
        },
    )


class PostEventDropCreateIn(BaseModel):
    name: str
    base_price: Decimal
    audience: str = "public"
    drop_description: str | None = None
    post_event_drop_at: datetime | None = None
    currency: str = "NGN"
    product_type: str | None = "souvenir"
    image_url: str | None = None
    status: str = "draft"
    inventory_count: int = 0
    variant_label: str = "Default"


class PostEventDropPatchIn(BaseModel):
    name: str | None = None
    drop_description: str | None = None
    audience: str | None = None
    post_event_drop_at: datetime | None = None
    status: str | None = None
    base_price: Decimal | None = None
    image_url: str | None = None


@router.get("/host/events/{event_id}/post-event-drops")
def host_list_post_event_drops(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return drops_svc.list_post_event_drops(db, user=user, event_id=event_id)


@router.post("/host/events/{event_id}/post-event-drops")
def host_create_post_event_drop(
    event_id: UUID,
    payload: PostEventDropCreateIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return drops_svc.create_post_event_drop(
        db,
        user=user,
        event_id=event_id,
        name=payload.name,
        base_price=payload.base_price,
        audience=payload.audience,
        drop_description=payload.drop_description,
        post_event_drop_at=payload.post_event_drop_at,
        currency=payload.currency,
        product_type=payload.product_type,
        image_url=payload.image_url,
        status=payload.status,
        inventory_count=payload.inventory_count,
        variant_label=payload.variant_label,
    )


@router.patch("/host/merchandise/post-event-drops/{product_id}")
def host_patch_post_event_drop(
    product_id: UUID,
    payload: PostEventDropPatchIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return drops_svc.patch_post_event_drop(
        db,
        user=user,
        product_id=product_id,
        name=payload.name,
        drop_description=payload.drop_description,
        audience=payload.audience,
        post_event_drop_at=payload.post_event_drop_at,
        status=payload.status,
        base_price=payload.base_price,
        image_url=payload.image_url,
    )


@router.get("/dashboard/merchandise/post-event-drops")
def buyer_eligible_post_event_drops(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return drops_svc.list_buyer_eligible_drops(db, buyer_user_id=user.id)


@router.get("/dashboard/cart")
def get_cart(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    data = cart_svc.get_buyer_cart(db, user=user)
    return data or {"id": None, "status": "empty", "items": []}


@router.post("/dashboard/cart/items")
def add_cart_item(
    payload: CartItemIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return cart_svc.add_cart_item(
        db,
        user=user,
        variant_id=payload.variant_id,
        quantity=payload.quantity,
    )


@router.patch("/dashboard/cart/items/{item_id}")
def update_cart_item_quantity(
    item_id: UUID,
    payload: CartItemQuantityIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return cart_svc.set_cart_item_quantity(
        db, user=user, item_id=item_id, quantity=payload.quantity
    )


@router.delete("/dashboard/cart/items/{item_id}")
def remove_cart_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    data = cart_svc.remove_cart_item(db, user=user, item_id=item_id)
    return data or {"id": None, "status": "empty", "items": []}


class PodIntegrationUpsertIn(BaseModel):
    provider: str = "manual"
    status: str = "connected"
    provider_store_ref: str | None = None
    credentials: str | None = None


@router.get("/host/merchandise/print-on-demand")
def host_pod_jobs(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    host = _require_host(
        db, user, permission=("merch.fulfill_orders", "merch.manage_inventory")
    )
    return pod_svc.list_host_jobs(db, host_id=host.id)


@router.get("/host/merchandise/print-on-demand/integrations")
def host_pod_integrations(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    host = _require_host(db, user, permission="merch.edit")
    return pod_svc.list_host_integrations(db, host_id=host.id)


@router.put("/host/merchandise/print-on-demand/integrations")
def host_upsert_pod_integration(
    payload: PodIntegrationUpsertIn,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(db, user, permission="merch.edit")
    row = pod_svc.upsert_integration(
        db,
        host_id=host.id,
        provider=payload.provider,
        status=payload.status,
        provider_store_ref=payload.provider_store_ref,
        credentials=payload.credentials,
        actor_user_id=user.id,
        commit=True,
    )
    return pod_svc.serialize_integration(row)


@router.post("/host/merchandise/print-on-demand/jobs/{job_id}/fulfill")
def host_mark_pod_job_fulfilled(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(
        db, user, permission=("merch.fulfill_orders", "merch.mark_picked_up")
    )
    return pod_svc.mark_job_manually_fulfilled(
        db, user=user, job_id=job_id, host_id=host.id
    )


@router.post("/host/merchandise/print-on-demand/jobs/{job_id}/retry")
def host_retry_pod_job(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = _require_host(
        db, user, permission=("merch.fulfill_orders", "merch.manage_inventory")
    )
    return pod_svc.retry_failed_job(db, user=user, job_id=job_id, host_id=host.id)


@router.get("/admin/merchandise/print-on-demand")
def admin_pod_jobs(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "admin.full_access"))
    ],
) -> list[dict]:
    return pod_svc.list_admin_jobs(db)


@router.post("/admin/merchandise/print-on-demand/jobs/{job_id}/fulfill")
def admin_mark_pod_job_fulfilled(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "admin.full_access"))
    ],
) -> dict:
    return pod_svc.mark_job_manually_fulfilled(db, user=user, job_id=job_id)


@router.post("/admin/merchandise/print-on-demand/jobs/{job_id}/retry")
def admin_retry_pod_job(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "admin.full_access"))
    ],
) -> dict:
    return pod_svc.retry_failed_job(db, user=user, job_id=job_id)
