"""Promo validation, redemptions, and ambassador attribution."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event, TicketType
from app.events.service import assert_can_manage_event, get_event_by_id
from app.hosts.service import require_user_host
from app.payments.models import Order
from app.promos.constants import AMBASSADOR_TERMS_VERSION
from app.promos.models import (
    Ambassador,
    AmbassadorSale,
    PromoClick,
    PromoCode,
    PromoRedemption,
)
from app.promos.schemas import (
    AmbassadorCreate,
    AmbassadorUpdate,
    PromoCodeCreate,
    PromoCodeUpdate,
)
from app.users.models import User
from app.users.service import get_user_by_email

PROGRAM_HOST_CURATED = "host_curated"
PROGRAM_OPEN_EVENT = "open_event"


def _assert_user_can_participate_as_ambassador(user: User) -> None:
    """Core eligibility — account active + not blocked from Ambassadors."""
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your Pàdéyá account must be active to join Ambassadors",
        )
    if bool(getattr(user, "ambassadors_blocked", False)):
        raise HTTPException(
            status_code=403,
            detail="You are blocked from Pàdéyá Ambassadors programs",
        )


def _ambassador_attribution_allowed(db: Session, ambassador: Ambassador) -> bool:
    """Active enrollment whose linked user (if any) may still earn attribution."""
    if ambassador.status != "active":
        return False
    if ambassador.user_id is None:
        return True
    linked = db.get(User, ambassador.user_id)
    if linked is None or not linked.is_active:
        return False
    if bool(getattr(linked, "ambassadors_blocked", False)):
        return False
    return True


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def serialize_promo(promo: PromoCode) -> PromoCode:
    return promo


def list_host_promos(db: Session, user: User) -> list[PromoCode]:
    host = require_user_host(db, user)
    return list(
        db.scalars(
            select(PromoCode)
            .where(PromoCode.host_id == host.id)
            .order_by(PromoCode.created_at.desc())
        )
    )


def create_promo(db: Session, *, user: User, payload: PromoCodeCreate) -> PromoCode:
    host = require_user_host(db, user)
    if payload.event_id is not None:
        event = get_event_by_id(db, payload.event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        assert_can_manage_event(db, user, event, host)
    if payload.ticket_type_id is not None:
        tt = db.get(TicketType, payload.ticket_type_id)
        if tt is None:
            raise HTTPException(status_code=404, detail="Ticket type not found")
        event = get_event_by_id(db, tt.event_id)
        if event is None or event.host_id != host.id:
            raise HTTPException(status_code=403, detail="Ticket type not owned by host")
        if payload.event_id and payload.event_id != tt.event_id:
            raise HTTPException(status_code=400, detail="Ticket type does not belong to event")

    if payload.discount_type == "percentage" and payload.discount_value > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100")

    existing = db.scalar(
        select(PromoCode).where(
            PromoCode.host_id == host.id,
            PromoCode.code == payload.code,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Promo code already exists")

    promo = PromoCode(
        host_id=host.id,
        code=payload.code,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        usage_limit=payload.usage_limit,
        expires_at=payload.expires_at,
        event_id=payload.event_id,
        ticket_type_id=payload.ticket_type_id,
        status=payload.status,
        max_per_user=payload.max_per_user,
    )
    db.add(promo)
    write_audit_log(
        db,
        action="promos.create",
        actor_user_id=user.id,
        resource_type="promo_code",
        resource_id=str(promo.id),
        details={"code": promo.code},
    )
    db.commit()
    db.refresh(promo)
    return promo


def update_promo(
    db: Session, *, user: User, promo_id: UUID, payload: PromoCodeUpdate
) -> PromoCode:
    host = require_user_host(db, user)
    promo = db.get(PromoCode, promo_id)
    if promo is None or promo.host_id != host.id:
        raise HTTPException(status_code=404, detail="Promo code not found")

    data = payload.model_dump(exclude_unset=True)
    if data.get("discount_type") == "percentage" or (
        promo.discount_type == "percentage" and "discount_value" in data
    ):
        value = data.get("discount_value", promo.discount_value)
        dtype = data.get("discount_type", promo.discount_type)
        if dtype == "percentage" and Decimal(value) > 100:
            raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100")

    for key, value in data.items():
        setattr(promo, key, value)

    audit_details = {
        key: (float(value) if isinstance(value, Decimal) else str(value) if hasattr(value, "hex") else value)
        for key, value in data.items()
    }
    write_audit_log(
        db,
        action="promos.update",
        actor_user_id=user.id,
        resource_type="promo_code",
        resource_id=str(promo.id),
        details=audit_details,
    )
    db.commit()
    db.refresh(promo)
    return promo


def delete_promo(db: Session, *, user: User, promo_id: UUID) -> None:
    """Hard-delete unused promos only. Used codes must remain for reporting."""
    host = require_user_host(db, user)
    promo = db.get(PromoCode, promo_id)
    if promo is None or promo.host_id != host.id:
        raise HTTPException(status_code=404, detail="Promo code not found")
    redemptions = db.scalar(
        select(func.count())
        .select_from(PromoRedemption)
        .where(PromoRedemption.promo_code_id == promo.id)
    )
    if (promo.usage_count or 0) > 0 or int(redemptions or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Used promo codes cannot be deleted — disable/archive instead",
        )
    write_audit_log(
        db,
        action="promos.delete",
        actor_user_id=user.id,
        resource_type="promo_code",
        resource_id=str(promo.id),
        details={"code": promo.code},
    )
    db.delete(promo)
    db.commit()


def _eligible_subtotal(
    *,
    promo: PromoCode,
    line_items: list[tuple[TicketType, int, Decimal]],
) -> Decimal:
    """Subtotal that the promo may discount (ticket-type restricted when set)."""
    total = Decimal("0")
    for tt, quantity, unit_price in line_items:
        if promo.ticket_type_id is not None and tt.id != promo.ticket_type_id:
            continue
        total += unit_price * quantity
    return total


def validate_promo_for_cart(
    db: Session,
    *,
    code: str,
    event: Event,
    user: User | None,
    line_items: list[tuple[TicketType, int, Decimal]],
    reserve_usage: bool = False,
) -> tuple[PromoCode, Decimal]:
    """
    Validate promo and return (promo, discount_amount).
    Raises HTTPException on invalid use.
    """
    normalized = _normalize_code(code)
    promo = db.scalar(
        select(PromoCode)
        .where(
            PromoCode.code == normalized,
            PromoCode.host_id == event.host_id,
        )
        .with_for_update()
    )
    if promo is None:
        raise HTTPException(status_code=400, detail="Invalid promo code")
    if promo.status != "active":
        raise HTTPException(status_code=400, detail="Promo code is inactive")
    if promo.expires_at is not None and _aware(promo.expires_at) <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Promo code has expired")
    if promo.event_id is not None and promo.event_id != event.id:
        raise HTTPException(status_code=400, detail="Promo code is not valid for this event")
    if promo.usage_limit is not None and promo.usage_count >= promo.usage_limit:
        raise HTTPException(status_code=400, detail="Promo code usage limit reached")

    if promo.ticket_type_id is not None:
        if not any(tt.id == promo.ticket_type_id for tt, _, _ in line_items):
            raise HTTPException(
                status_code=400,
                detail="Promo code is restricted to a different ticket type",
            )

    if user is not None and promo.max_per_user > 0:
        used = db.scalar(
            select(func.count())
            .select_from(PromoRedemption)
            .where(
                PromoRedemption.promo_code_id == promo.id,
                PromoRedemption.user_id == user.id,
                PromoRedemption.status.in_(["pending", "redeemed"]),
            )
        ) or 0
        if int(used) >= promo.max_per_user:
            raise HTTPException(
                status_code=400,
                detail="You have already used this promo code",
            )

    eligible = _eligible_subtotal(promo=promo, line_items=line_items)
    if eligible <= 0:
        raise HTTPException(status_code=400, detail="Promo code does not apply to selected tickets")

    if promo.discount_type == "percentage":
        discount = _q(eligible * (Decimal(promo.discount_value) / Decimal("100")))
    else:
        discount = _q(min(Decimal(promo.discount_value), eligible))

    discount = min(discount, eligible)
    if discount <= 0:
        raise HTTPException(status_code=400, detail="Promo produces no discount")

    if reserve_usage:
        if promo.usage_limit is not None and promo.usage_count >= promo.usage_limit:
            raise HTTPException(status_code=400, detail="Promo code usage limit reached")
        promo.usage_count += 1

    return promo, discount


def preview_promo(
    db: Session,
    *,
    user: User,
    code: str,
    event_id: UUID,
    items: list[dict],
) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.status != "published":
        return {
            "valid": False,
            "reason": "Event is not available",
            "discount_amount": Decimal("0"),
            "subtotal_amount": Decimal("0"),
            "total_amount": Decimal("0"),
        }

    line_items: list[tuple[TicketType, int, Decimal]] = []
    subtotal = Decimal("0")
    for item in items:
        tt_id = UUID(str(item["ticket_type_id"]))
        quantity = int(item["quantity"])
        tt = db.get(TicketType, tt_id)
        if tt is None or tt.event_id != event.id:
            return {
                "valid": False,
                "reason": "Invalid ticket type",
                "discount_amount": Decimal("0"),
                "subtotal_amount": Decimal("0"),
                "total_amount": Decimal("0"),
            }
        unit = Decimal(tt.price)
        line_items.append((tt, quantity, unit))
        subtotal += unit * quantity

    try:
        promo, discount = validate_promo_for_cart(
            db,
            code=code,
            event=event,
            user=user,
            line_items=line_items,
            reserve_usage=False,
        )
    except HTTPException as exc:
        return {
            "valid": False,
            "reason": str(exc.detail),
            "discount_amount": Decimal("0"),
            "subtotal_amount": subtotal,
            "total_amount": subtotal,
        }

    return {
        "valid": True,
        "code": promo.code,
        "discount_amount": discount,
        "subtotal_amount": subtotal,
        "total_amount": max(Decimal("0"), subtotal - discount),
        "reason": None,
    }


def attach_promo_to_order(
    db: Session,
    *,
    order: Order,
    promo: PromoCode,
    user: User | None,
    discount: Decimal,
) -> PromoRedemption:
    redemption = PromoRedemption(
        promo_code_id=promo.id,
        order_id=order.id,
        user_id=user.id if user is not None else None,
        discount_amount=discount,
        status="pending",
    )
    db.add(redemption)
    order.promo_code_id = promo.id
    order.discount_amount = discount
    order.promo_code_snapshot = promo.code
    return redemption


def resolve_ambassador_for_event(
    db: Session,
    *,
    referral_code: str,
    event: Event,
    prefer_merch: bool = False,
) -> Ambassador | None:
    """Resolve an active ambassador by code for an event.

    Codes are unique per campaign; the same readable code may exist on ticket
    and merch campaigns. When multiple match, prefer campaign type matching
    the cart (merch vs tickets).
    """
    from app.promos.constants import CAMPAIGN_TYPE_EVENT_MERCH, CAMPAIGN_TYPE_EVENT_TICKETS
    from app.promos.models import AmbassadorCampaign

    code = referral_code.strip().lower()
    if not code:
        return None
    open_rows = list(
        db.scalars(
            select(Ambassador).where(
                Ambassador.event_id == event.id,
                Ambassador.referral_code == code,
                Ambassador.status == "active",
                Ambassador.program_kind == PROGRAM_OPEN_EVENT,
            )
        )
    )
    open_rows = [a for a in open_rows if _ambassador_attribution_allowed(db, a)]
    if open_rows:
        if len(open_rows) == 1:
            return open_rows[0]
        typed: list[tuple[Ambassador, str]] = []
        for amb in open_rows:
            ctype = CAMPAIGN_TYPE_EVENT_TICKETS
            if amb.campaign_id is not None:
                camp = db.get(AmbassadorCampaign, amb.campaign_id)
                if camp is not None:
                    ctype = getattr(camp, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
            typed.append((amb, ctype))
        wanted = (
            CAMPAIGN_TYPE_EVENT_MERCH
            if prefer_merch
            else CAMPAIGN_TYPE_EVENT_TICKETS
        )
        for amb, ctype in typed:
            if ctype == wanted:
                return amb
        return typed[0][0]

    curated_for_event = db.scalar(
        select(Ambassador).where(
            Ambassador.host_id == event.host_id,
            Ambassador.event_id == event.id,
            Ambassador.referral_code == code,
            Ambassador.status == "active",
            Ambassador.program_kind == PROGRAM_HOST_CURATED,
            Ambassador.campaign_id.is_(None),
        )
    )
    if curated_for_event is not None:
        return (
            curated_for_event
            if _ambassador_attribution_allowed(db, curated_for_event)
            else None
        )

    curated = db.scalar(
        select(Ambassador).where(
            Ambassador.host_id == event.host_id,
            Ambassador.event_id.is_(None),
            Ambassador.referral_code == code,
            Ambassador.status == "active",
            Ambassador.program_kind == PROGRAM_HOST_CURATED,
        )
    )
    if curated is None:
        return None
    return curated if _ambassador_attribution_allowed(db, curated) else None


def attach_ambassador_to_order(
    db: Session,
    *,
    order: Order,
    ambassador: Ambassador,
    attribution_source: str | None = None,
) -> None:
    from app.promos.constants import (
        REFERRAL_SOURCE_EXPLICIT,
        REFERRAL_SOURCES,
    )

    # Self-referral: never attribute a purchase to the ambassador themselves.
    if (
        ambassador.user_id is not None
        and order.buyer_user_id is not None
        and ambassador.user_id == order.buyer_user_id
    ):
        return
    from app.ambassadors.fraud import commission_blocked_for_host_owner

    if commission_blocked_for_host_owner(
        db, user_id=ambassador.user_id, ambassador=ambassador
    ):
        return
    if (
        ambassador.program_kind == PROGRAM_OPEN_EVENT
        and ambassador.event_id is not None
        and ambassador.event_id != order.event_id
    ):
        return
    # Explicit checkout code wins — never overwrite with link/cookie.
    existing_source = getattr(order, "referral_attribution_source", None)
    if (
        order.ambassador_id is not None
        and existing_source == REFERRAL_SOURCE_EXPLICIT
        and attribution_source != REFERRAL_SOURCE_EXPLICIT
    ):
        return
    order.ambassador_id = ambassador.id
    order.referral_code = ambassador.referral_code
    if attribution_source in REFERRAL_SOURCES:
        order.referral_attribution_source = attribution_source


def finalize_promo_and_attribution(db: Session, *, order: Order) -> None:
    """Called from payment finalize — redeem promo and attribute ambassador sale.

    Commission is created only for verified paid orders. Duplicate webhook calls
    are idempotent (unique order_id on ambassador_sales / early return).
    """
    from app.analytics.trusted import emit_ambassador_sale, emit_promo_redemption
    from app.events.models import Event
    from app.promos.commission import (
        compute_commission_owed,
        filter_units_and_revenue,
        hold_until_for_sale,
        maybe_grant_free_ticket_reward,
        resolve_commission_rules,
    )
    from app.promos.models import AmbassadorCampaign

    event = db.get(Event, order.event_id)
    host_id = event.host_id if event else None

    redemption = db.scalar(
        select(PromoRedemption).where(PromoRedemption.order_id == order.id)
    )
    if redemption is not None and redemption.status == "pending":
        # Only redeem after verified payment — never on pending/failed.
        if order.status == "paid":
            redemption.status = "redeemed"
            redemption.redeemed_at = datetime.now(UTC)
            write_audit_log(
                db,
                action="promos.redeemed",
                actor_user_id=order.buyer_user_id,
                resource_type="promo_redemption",
                resource_id=str(redemption.id),
                details={
                    "order_id": str(order.id),
                    "promo_code_id": str(redemption.promo_code_id),
                    "discount": str(redemption.discount_amount),
                },
            )
            emit_promo_redemption(
                db,
                order_id=order.id,
                event_id=order.event_id,
                host_id=host_id,
                user_id=order.buyer_user_id,
                promo_code_id=redemption.promo_code_id,
                discount=redemption.discount_amount,
            )

    if order.ambassador_id is None:
        return
    # No commission on pending/failed/cancelled — only verified paid.
    if order.status != "paid":
        return

    existing = db.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
    )
    if existing is not None:
        return

    ambassador = db.get(Ambassador, order.ambassador_id)
    if ambassador is None or not _ambassador_attribution_allowed(db, ambassador):
        return
    if (
        ambassador.user_id is not None
        and order.buyer_user_id is not None
        and ambassador.user_id == order.buyer_user_id
    ):
        return

    from app.ambassadors.fraud import commission_blocked_for_host_owner

    if commission_blocked_for_host_owner(
        db, user_id=ambassador.user_id, ambassador=ambassador
    ):
        return

    tickets_raw = sum(
        item.quantity
        for item in order.items
        if getattr(item, "item_kind", "ticket") == "ticket"
    )
    merch_raw = sum(
        item.quantity
        for item in order.items
        if getattr(item, "item_kind", "ticket") in {"merch", "bundle"}
    )
    ticket_revenue = sum(
        (
            Decimal(item.line_total)
            for item in order.items
            if getattr(item, "item_kind", "ticket") == "ticket"
        ),
        Decimal("0"),
    )
    merch_revenue = sum(
        (
            Decimal(item.line_total)
            for item in order.items
            if getattr(item, "item_kind", "ticket") in {"merch", "bundle"}
        ),
        Decimal("0"),
    )

    campaign = None
    if ambassador.campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, ambassador.campaign_id)
    rules = resolve_commission_rules(campaign, ambassador=ambassador)
    tickets_sold, merch_units, _t_rev, _m_rev, revenue = filter_units_and_revenue(
        applies_to=rules["applies_to"],
        tickets_sold=tickets_raw,
        merch_units=merch_raw,
        ticket_revenue=ticket_revenue,
        merch_revenue=merch_revenue,
    )

    if revenue <= 0 and tickets_sold <= 0 and merch_units <= 0:
        return

    commission = compute_commission_owed(
        commission_type=rules["commission_type"],
        commission_value=rules["commission_value"],
        applies_to=rules["applies_to"],
        tickets_sold=tickets_sold,
        merch_units=merch_units,
        commissionable_revenue=revenue,
        max_commission_per_order=rules["max_commission_per_order"],
    )
    hold_until = hold_until_for_sale(hold_period_days=rules["hold_period_days"])

    sale = AmbassadorSale(
        ambassador_id=ambassador.id,
        order_id=order.id,
        event_id=order.event_id,
        tickets_sold=tickets_sold,
        merch_units_sold=merch_units,
        revenue_amount=revenue,
        commission_owed=commission,
        commission_type=rules["commission_type"],
        hold_until=hold_until,
        status="attributed",
    )
    db.add(sale)
    db.flush()
    maybe_grant_free_ticket_reward(db, ambassador=ambassador, campaign=campaign)
    write_audit_log(
        db,
        action="ambassadors.sale_attributed",
        actor_user_id=order.buyer_user_id,
        resource_type="ambassador_sale",
        resource_id=str(sale.id),
        details={
            "ambassador_id": str(ambassador.id),
            "referral_code": ambassador.referral_code,
            "order_id": str(order.id),
            "revenue": str(revenue),
            "commission_owed": str(commission),
            "commission_type": rules["commission_type"],
            "applies_to": rules["applies_to"],
            "hold_until": hold_until.isoformat(),
        },
    )
    emit_ambassador_sale(
        db,
        order_id=order.id,
        event_id=order.event_id,
        host_id=host_id,
        ambassador_id=ambassador.id,
        revenue=revenue,
        commission=commission,
        tickets_sold=tickets_sold,
        buyer_user_id=order.buyer_user_id,
    )
    from app.ambassadors.notifications import on_v1_sale_created

    on_v1_sale_created(db, ambassador=ambassador, sale=sale)


def release_promo_reservation(db: Session, *, order: Order) -> None:
    """Release pending promo usage when payment fails."""
    redemption = db.scalar(
        select(PromoRedemption).where(
            PromoRedemption.order_id == order.id,
            PromoRedemption.status == "pending",
        )
    )
    if redemption is None:
        return
    redemption.status = "released"
    promo = db.get(PromoCode, redemption.promo_code_id)
    if promo is not None and promo.usage_count > 0:
        promo.usage_count -= 1


def record_referral_click(
    db: Session,
    *,
    referral_code: str,
    event_id: UUID | None,
    landing_path: str | None,
    ip_address: str | None,
    user_agent: str | None,
    source: str = "event_page",
    anonymous_visitor_id: str | None = None,
    user: User | None = None,
) -> PromoClick:
    from app.ambassadors.referral_tracking import ReferralTrackingService

    row = ReferralTrackingService.record_promos_referral(
        db,
        referral_code=referral_code,
        event_id=event_id,
        landing_path=landing_path,
        source=source,
        anonymous_visitor_id=anonymous_visitor_id,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if isinstance(row, PromoClick):
        return row
    if row is not None and row.ambassador_id:
        legacy = db.scalar(
            select(PromoClick)
            .where(PromoClick.ambassador_id == row.ambassador_id)
            .order_by(PromoClick.created_at.desc())
        )
        if legacy is not None:
            return legacy
    raise HTTPException(status_code=500, detail="Referral click not recorded")


def _ambassador_stats(db: Session, ambassador: Ambassador) -> dict:
    from app.ambassadors.referral_click_stats import merge_ambassador_dashboard_stats

    bundle = merge_ambassador_dashboard_stats(db, ambassador_ids=[ambassador.id])
    return {
        "clicks": bundle["total_clicks"],
        "total_clicks": bundle["total_clicks"],
        "unique_clicks": bundle["unique_clicks"],
        "qualified_clicks": bundle.get("qualified_clicks", 0),
        "first_click_at": bundle.get("first_click_at"),
        "last_click_at": bundle.get("last_click_at"),
        "tickets_sold": bundle["tickets_sold"],
        "merch_units_sold": bundle["merch_units_sold"],
        "revenue_generated": _q(bundle["confirmed_revenue"]),
        "gross_revenue": _q(bundle["gross_revenue"]),
        "confirmed_revenue": _q(bundle["confirmed_revenue"]),
        "reward_amount": _q(bundle["reward_amount"]),
        "conversions": bundle["conversions"],
        "conversion_rate": bundle["conversion_rate"],
        "commission_owed": _q(bundle["reward_amount"]),
    }


def serialize_ambassador(db: Session, ambassador: Ambassador) -> dict:
    from app.promos.constants import CAMPAIGN_TYPE_EVENT_TICKETS, CAMPAIGN_TYPE_LABELS
    from app.promos.models import AmbassadorCampaign

    stats = _ambassador_stats(db, ambassador)
    event_title = None
    event_slug = None
    if ambassador.event_id is not None:
        event = db.get(Event, ambassador.event_id)
        if event is not None:
            event_title = event.title
            event_slug = event.slug
    campaign_type = None
    campaign_type_label = None
    if ambassador.campaign_id is not None:
        camp = db.get(AmbassadorCampaign, ambassador.campaign_id)
        if camp is not None:
            campaign_type = getattr(camp, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
            campaign_type_label = CAMPAIGN_TYPE_LABELS.get(
                campaign_type, campaign_type
            )
    code = ambassador.referral_code or ""
    return {
        "id": ambassador.id,
        "host_id": ambassador.host_id,
        "event_id": ambassador.event_id,
        "campaign_id": ambassador.campaign_id,
        "user_id": ambassador.user_id,
        "program_kind": ambassador.program_kind,
        "campaign_type": campaign_type,
        "campaign_type_label": campaign_type_label,
        "referral_code": code,
        "referral_code_display": code.upper() if code else code,
        "display_name": ambassador.display_name,
        "email": ambassador.email,
        "status": ambassador.status,
        "commission_rate_percent": ambassador.commission_rate_percent,
        "created_at": ambassador.created_at,
        "event_title": event_title,
        "event_slug": event_slug,
        **stats,
    }


def list_host_ambassadors(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    rows = db.scalars(
        select(Ambassador)
        .where(Ambassador.host_id == host.id)
        .order_by(Ambassador.created_at.desc())
    ).all()
    return [serialize_ambassador(db, a) for a in rows]


def create_ambassador(db: Session, *, user: User, payload: AmbassadorCreate) -> dict:
    host = require_user_host(db, user)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,62}", payload.referral_code):
        raise HTTPException(
            status_code=400,
            detail="Referral code must be lowercase alphanumeric (2–64 chars)",
        )

    event_id = payload.event_id
    if event_id is not None:
        event = db.get(Event, event_id)
        if event is None or event.host_id != host.id:
            raise HTTPException(status_code=404, detail="Event not found")
        existing = db.scalar(
            select(Ambassador).where(
                Ambassador.host_id == host.id,
                Ambassador.event_id == event_id,
                Ambassador.referral_code == payload.referral_code,
                Ambassador.campaign_id.is_(None),
            )
        )
    else:
        existing = db.scalar(
            select(Ambassador).where(
                Ambassador.host_id == host.id,
                Ambassador.event_id.is_(None),
                Ambassador.referral_code == payload.referral_code,
            )
        )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ambassador code already exists")

    linked_user_id = None
    if payload.user_email:
        linked = get_user_by_email(db, payload.user_email.lower())
        if linked is None:
            raise HTTPException(status_code=404, detail="User email not found — register first")
        linked_user_id = linked.id
        # Host owners cannot be curated onto their own host for rewards.
        if linked_user_id == host.user_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Campaign host owners cannot join as Ambassadors unless "
                    "allow_host_owner_commission is enabled on the campaign"
                ),
            )

    ambassador = Ambassador(
        host_id=host.id,
        event_id=event_id,
        program_kind=PROGRAM_HOST_CURATED,
        user_id=linked_user_id,
        referral_code=payload.referral_code,
        display_name=payload.display_name.strip(),
        email=payload.email or payload.user_email,
        status=payload.status,
        commission_rate_percent=payload.commission_rate_percent,
    )
    db.add(ambassador)
    write_audit_log(
        db,
        action="ambassadors.create",
        actor_user_id=user.id,
        resource_type="ambassador",
        resource_id=str(ambassador.id),
        details={
            "referral_code": ambassador.referral_code,
            "event_id": str(event_id) if event_id else None,
        },
    )
    db.commit()
    db.refresh(ambassador)
    return serialize_ambassador(db, ambassador)


def update_ambassador(
    db: Session, *, user: User, ambassador_id: UUID, payload: AmbassadorUpdate
) -> dict:
    host = require_user_host(db, user)
    ambassador = db.get(Ambassador, ambassador_id)
    if ambassador is None or ambassador.host_id != host.id:
        raise HTTPException(status_code=404, detail="Ambassador not found")
    if ambassador.program_kind != PROGRAM_HOST_CURATED:
        # Open-event enrollments keep campaign/event binding from join flow.
        data = payload.model_dump(exclude_unset=True)
        data.pop("event_id", None)
        for key, value in data.items():
            setattr(ambassador, key, value)
    else:
        data = payload.model_dump(exclude_unset=True)
        if "event_id" in data:
            next_event_id = data["event_id"]
            if next_event_id is not None:
                event = db.get(Event, next_event_id)
                if event is None or event.host_id != host.id:
                    raise HTTPException(status_code=404, detail="Event not found")
                clash = db.scalar(
                    select(Ambassador).where(
                        Ambassador.host_id == host.id,
                        Ambassador.event_id == next_event_id,
                        Ambassador.referral_code == ambassador.referral_code,
                        Ambassador.campaign_id.is_(None),
                        Ambassador.id != ambassador.id,
                    )
                )
            else:
                clash = db.scalar(
                    select(Ambassador).where(
                        Ambassador.host_id == host.id,
                        Ambassador.event_id.is_(None),
                        Ambassador.referral_code == ambassador.referral_code,
                        Ambassador.id != ambassador.id,
                    )
                )
            if clash is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Ambassador code already exists for that event",
                )
            ambassador.event_id = next_event_id
            del data["event_id"]
        for key, value in data.items():
            setattr(ambassador, key, value)
    write_audit_log(
        db,
        action="ambassadors.update",
        actor_user_id=user.id,
        resource_type="ambassador",
        resource_id=str(ambassador.id),
        details=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    db.refresh(ambassador)
    return serialize_ambassador(db, ambassador)


def delete_ambassador(db: Session, *, user: User, ambassador_id: UUID) -> None:
    """Hard-delete only if no sales/clicks. Otherwise deactivate."""
    host = require_user_host(db, user)
    ambassador = db.get(Ambassador, ambassador_id)
    if ambassador is None or ambassador.host_id != host.id:
        raise HTTPException(status_code=404, detail="Ambassador not found")
    sales = db.scalar(
        select(func.count())
        .select_from(AmbassadorSale)
        .where(AmbassadorSale.ambassador_id == ambassador.id)
    )
    clicks = db.scalar(
        select(func.count())
        .select_from(PromoClick)
        .where(PromoClick.ambassador_id == ambassador.id)
    )
    if int(sales or 0) > 0 or int(clicks or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Ambassadors with sales/clicks cannot be deleted — deactivate instead",
        )
    write_audit_log(
        db,
        action="ambassadors.delete",
        actor_user_id=user.id,
        resource_type="ambassador",
        resource_id=str(ambassador.id),
        details={"referral_code": ambassador.referral_code},
    )
    db.delete(ambassador)
    db.commit()


def _ambassador_detail(
    db: Session, ambassador: Ambassador, *, include_order_refs: bool = False
) -> dict:
    """Sales ledger for dashboards.

    Ambassador self view uses an allowlisted sale row (no order_id / refs /
    event_id / buyer PII). Hosts may see order_reference for ops; still no
    buyer private fields here. See ``app.ambassadors.privacy``.
    """
    from app.ambassadors.privacy import sale_row_for_ambassador

    sales = list(
        db.scalars(
            select(AmbassadorSale)
            .where(AmbassadorSale.ambassador_id == ambassador.id)
            .order_by(AmbassadorSale.created_at.desc())
        )
    )
    sale_rows = []
    for sale in sales:
        event = db.get(Event, sale.event_id)
        event_title = event.title if event else None
        if include_order_refs:
            order = db.get(Order, sale.order_id)
            sale_rows.append(
                {
                    "id": sale.id,
                    "ambassador_id": sale.ambassador_id,
                    "order_id": sale.order_id,
                    "event_id": sale.event_id,
                    "tickets_sold": sale.tickets_sold,
                    "merch_units_sold": getattr(sale, "merch_units_sold", 0) or 0,
                    "revenue_amount": sale.revenue_amount,
                    "commission_owed": sale.commission_owed,
                    "commission_type": getattr(sale, "commission_type", None),
                    "hold_until": getattr(sale, "hold_until", None),
                    "status": sale.status,
                    "created_at": sale.created_at,
                    "event_title": event_title,
                    "order_reference": order.reference if order else None,
                }
            )
        else:
            sale_rows.append(
                sale_row_for_ambassador(
                    sale_id=sale.id,
                    ambassador_id=sale.ambassador_id,
                    tickets_sold=sale.tickets_sold,
                    merch_units_sold=getattr(sale, "merch_units_sold", 0) or 0,
                    revenue_amount=sale.revenue_amount,
                    commission_owed=sale.commission_owed,
                    commission_type=getattr(sale, "commission_type", None),
                    hold_until=getattr(sale, "hold_until", None),
                    status=sale.status,
                    created_at=sale.created_at,
                    event_title=event_title,
                )
            )
    stats = _ambassador_stats(db, ambassador)
    return {
        "ambassador": serialize_ambassador(db, ambassador),
        "sales": sale_rows,
        **stats,
    }


def get_host_ambassador_detail(db: Session, *, user: User, ambassador_id: UUID) -> dict:
    host = require_user_host(db, user)
    ambassador = db.get(Ambassador, ambassador_id)
    if ambassador is None or ambassador.host_id != host.id:
        raise HTTPException(status_code=404, detail="Ambassador not found")
    return _ambassador_detail(db, ambassador, include_order_refs=True)


def get_my_ambassador_dashboard(db: Session, user: User) -> dict:
    ambassador = db.scalar(
        select(Ambassador)
        .where(Ambassador.user_id == user.id, Ambassador.status == "active")
        .order_by(Ambassador.created_at.desc())
    )
    if ambassador is None:
        raise HTTPException(
            status_code=404,
            detail="No ambassador profile linked to this account",
        )
    return _ambassador_detail(db, ambassador, include_order_refs=False)


def list_my_ambassador_enrollments(db: Session, user: User) -> list[dict]:
    rows = db.scalars(
        select(Ambassador)
        .where(Ambassador.user_id == user.id)
        .order_by(Ambassador.created_at.desc())
    ).all()
    return [_ambassador_detail(db, a, include_order_refs=False) for a in rows]


def get_open_ambassador_program(db: Session, *, event_id: UUID) -> dict:
    from app.promos.admin_service import is_ambassadors_feature_enabled
    from app.promos.campaigns import list_live_campaigns_for_event
    from app.promos.constants import CAMPAIGN_TYPE_EVENT_TICKETS, CAMPAIGN_TYPE_LABELS

    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    live = list_live_campaigns_for_event(db, event_id=event.id)
    platform_on = is_ambassadors_feature_enabled(db)
    enabled = platform_on and (
        bool(live) or bool(getattr(event, "open_ambassadors_enabled", False))
    )
    from app.promos.constants import COMMISSION_TYPE_PERCENTAGE

    primary = live[0] if live else None
    commission = (
        primary.commission_percent
        if primary is not None
        else getattr(event, "open_ambassador_commission_percent", Decimal("5.00"))
    )
    ctype = (
        getattr(primary, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
        if primary
        else CAMPAIGN_TYPE_EVENT_TICKETS
    )
    commission_type = (
        getattr(primary, "commission_type", COMMISSION_TYPE_PERCENTAGE)
        if primary
        else COMMISSION_TYPE_PERCENTAGE
    )
    commission_value = (
        getattr(primary, "commission_value", commission)
        if primary
        else commission
    )
    return {
        "event_id": event.id,
        "enabled": enabled,
        "commission_percent": commission,
        "commission_type": commission_type or COMMISSION_TYPE_PERCENTAGE,
        "commission_value": commission_value,
        "event_slug": event.slug,
        "event_title": event.title,
        "terms_version": AMBASSADOR_TERMS_VERSION,
        "campaign_id": primary.id if primary else None,
        "campaign_type": ctype,
        "merch_included": primary.merch_included if primary else False,
        "campaigns": [
            {
                "id": c.id,
                "campaign_type": getattr(c, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS),
                "campaign_type_label": CAMPAIGN_TYPE_LABELS.get(
                    getattr(c, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS),
                    getattr(c, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS),
                ),
                "commission_percent": c.commission_percent,
                "commission_type": getattr(
                    c, "commission_type", COMMISSION_TYPE_PERCENTAGE
                )
                or COMMISSION_TYPE_PERCENTAGE,
                "commission_value": getattr(
                    c, "commission_value", c.commission_percent
                ),
                "applies_to": getattr(c, "applies_to", None)
                or (
                    "merch"
                    if getattr(c, "campaign_type", "") == "event_merch"
                    else "tickets"
                ),
                "merch_included": c.merch_included,
                "is_live": True,
            }
            for c in live
        ],
    }


def _code_taken_on_campaign(
    db: Session, *, campaign_id: UUID | None, event_id: UUID, code: str
) -> bool:
    if campaign_id is not None:
        return (
            db.scalar(
                select(Ambassador).where(
                    Ambassador.campaign_id == campaign_id,
                    Ambassador.referral_code == code,
                )
            )
            is not None
        )
    return (
        db.scalar(
            select(Ambassador).where(
                Ambassador.event_id == event_id,
                Ambassador.campaign_id.is_(None),
                Ambassador.referral_code == code,
            )
        )
        is not None
    )


def _generate_open_referral_code(
    db: Session,
    *,
    event_id: UUID,
    user: User,
    campaign_id: UUID | None = None,
) -> str:
    """Readable shareable code, unique per campaign.

    Reuses the user's existing open-event code on this event when free on the
    target campaign so one promoter keeps one memorable code.
    """
    existing = db.scalar(
        select(Ambassador).where(
            Ambassador.event_id == event_id,
            Ambassador.user_id == user.id,
            Ambassador.program_kind == PROGRAM_OPEN_EVENT,
        )
    )
    if existing is not None and existing.referral_code:
        if not _code_taken_on_campaign(
            db,
            campaign_id=campaign_id,
            event_id=event_id,
            code=existing.referral_code,
        ):
            return existing.referral_code

    base = re.sub(r"[^a-z0-9]+", "", (user.full_name or "").lower())[:10]
    if len(base) < 3:
        base = "amb"
    # Prefer short readable tokens: name + short numeric suffix on clash.
    for attempt in range(32):
        if attempt == 0:
            code = base
        elif attempt < 10:
            code = f"{base}{attempt + 1}"
        else:
            code = f"{base}{secrets.token_hex(2)}"
        code = code[:64]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,62}", code):
            code = f"amb{secrets.token_hex(3)}"
        if not _code_taken_on_campaign(
            db, campaign_id=campaign_id, event_id=event_id, code=code
        ):
            return code
    raise HTTPException(status_code=500, detail="Could not allocate ambassador code")


def join_open_event_ambassador(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    accept_terms: bool,
    campaign_type: str | None = None,
    campaign_id: UUID | None = None,
) -> dict:
    """Self-serve open join. Never grants host team, staff, or scanner access."""
    from app.promos.admin_service import is_ambassadors_feature_enabled
    from app.promos.campaigns import (
        get_live_campaign_for_event,
        normalize_campaign_type,
    )
    from app.promos.constants import CAMPAIGN_TYPE_EVENT_TICKETS, CAMPAIGN_TYPE_LABELS
    from app.promos.models import AmbassadorCampaign

    _assert_user_can_participate_as_ambassador(user)
    if not accept_terms:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Ambassador terms to join",
        )
    if not is_ambassadors_feature_enabled(db):
        raise HTTPException(
            status_code=403,
            detail="Pàdéyá Ambassadors is temporarily unavailable",
        )

    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status not in {"published", "paused"}:
        raise HTTPException(
            status_code=400,
            detail="Event Ambassadors are only available for live events",
        )

    from app.promos.campaigns import campaign_is_live

    campaign: AmbassadorCampaign | None = None
    if campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, campaign_id)
        if (
            campaign is None
            or campaign.event_id != event.id
            or not campaign_is_live(campaign)
        ):
            raise HTTPException(
                status_code=400,
                detail="That Ambassadors campaign is not open for join",
            )
    else:
        wanted = normalize_campaign_type(
            campaign_type or CAMPAIGN_TYPE_EVENT_TICKETS
        )
        campaign = get_live_campaign_for_event(
            db, event_id=event.id, campaign_type=wanted
        )
        if campaign is None:
            # Legacy fallback: event flag without a campaign row (tickets only).
            if wanted == CAMPAIGN_TYPE_EVENT_TICKETS and bool(
                getattr(event, "open_ambassadors_enabled", False)
            ):
                campaign = None
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{CAMPAIGN_TYPE_LABELS.get(wanted, 'Ambassadors')} "
                        "is not enabled for this event"
                    ),
                )

    from app.promos.constants import COMMISSION_TYPE_PERCENTAGE
    from app.ambassadors.fraud import assert_user_may_join_campaign
    from app.hosts.models import Host

    if campaign is not None:
        assert_user_may_join_campaign(db, user_id=user.id, campaign=campaign)
        ctype = getattr(campaign, "commission_type", COMMISSION_TYPE_PERCENTAGE)
        if ctype == COMMISSION_TYPE_PERCENTAGE:
            commission = getattr(
                campaign, "commission_value", campaign.commission_percent
            )
        else:
            # Flat / reward-only: rate snapshot unused at attribution time.
            commission = Decimal("0")
    else:
        # Legacy event-flag path: host owners still cannot join by default.
        host = db.get(Host, event.host_id) if event.host_id else None
        if host is not None and host.user_id == user.id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Campaign host owners cannot join as Ambassadors unless "
                    "allow_host_owner_commission is enabled on the campaign"
                ),
            )
        commission = getattr(
            event, "open_ambassador_commission_percent", Decimal("5.00")
        )
    resolved_campaign_id = campaign.id if campaign is not None else None
    resolved_type = (
        getattr(campaign, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
        if campaign
        else CAMPAIGN_TYPE_EVENT_TICKETS
    )

    now = datetime.now(UTC)
    if resolved_campaign_id is not None:
        existing = db.scalar(
            select(Ambassador).where(
                Ambassador.campaign_id == resolved_campaign_id,
                Ambassador.user_id == user.id,
                Ambassador.program_kind == PROGRAM_OPEN_EVENT,
            )
        )
    else:
        existing = db.scalar(
            select(Ambassador).where(
                Ambassador.event_id == event.id,
                Ambassador.user_id == user.id,
                Ambassador.program_kind == PROGRAM_OPEN_EVENT,
                Ambassador.campaign_id.is_(None),
            )
        )
    if existing is not None:
        if existing.status == "removed":
            raise HTTPException(
                status_code=403,
                detail="You were removed from this Ambassadors campaign",
            )
        if existing.status != "active":
            existing.status = "active"
            existing.commission_rate_percent = commission
            existing.campaign_id = resolved_campaign_id or existing.campaign_id
            existing.terms_accepted_at = now
            existing.terms_version = AMBASSADOR_TERMS_VERSION
            write_audit_log(
                db,
                action="ambassadors.open_rejoin",
                actor_user_id=user.id,
                resource_type="ambassador",
                resource_id=str(existing.id),
                details={
                    "event_id": str(event.id),
                    "campaign_id": str(resolved_campaign_id)
                    if resolved_campaign_id
                    else None,
                    "campaign_type": resolved_type,
                    "referral_code": existing.referral_code,
                    "terms_version": AMBASSADOR_TERMS_VERSION,
                },
            )
            db.commit()
            db.refresh(existing)
            from app.ambassadors.notifications import notify_ambassador_joined

            notify_ambassador_joined(
                db,
                user=user,
                event_id=event.id,
                campaign=campaign,
                enrollment_id=existing.id,
            )
        return serialize_ambassador(db, existing)

    code = _generate_open_referral_code(
        db,
        event_id=event.id,
        user=user,
        campaign_id=resolved_campaign_id,
    )
    ambassador = Ambassador(
        host_id=event.host_id,
        event_id=event.id,
        campaign_id=resolved_campaign_id,
        program_kind=PROGRAM_OPEN_EVENT,
        user_id=user.id,
        referral_code=code,
        display_name=(user.full_name or "Ambassador").strip()[:160],
        email=user.email,
        status="active",
        commission_rate_percent=commission,
        terms_accepted_at=now,
        terms_version=AMBASSADOR_TERMS_VERSION,
    )
    db.add(ambassador)
    write_audit_log(
        db,
        action="ambassadors.open_join",
        actor_user_id=user.id,
        resource_type="ambassador",
        resource_id=str(ambassador.id),
        details={
            "event_id": str(event.id),
            "campaign_id": str(resolved_campaign_id)
            if resolved_campaign_id
            else None,
            "campaign_type": resolved_type,
            "referral_code": ambassador.referral_code,
            "commission_rate_percent": str(commission),
            "terms_version": AMBASSADOR_TERMS_VERSION,
            "grants_host_access": False,
            "grants_staff_access": False,
        },
    )
    db.commit()
    db.refresh(ambassador)
    from app.ambassadors.notifications import notify_ambassador_joined

    notify_ambassador_joined(
        db,
        user=user,
        event_id=event.id,
        campaign=campaign,
        enrollment_id=ambassador.id,
    )
    return serialize_ambassador(db, ambassador)


def get_my_open_event_ambassador(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    campaign_type: str | None = None,
) -> dict:
    from app.promos.campaigns import normalize_campaign_type
    from app.promos.constants import CAMPAIGN_TYPE_EVENT_TICKETS
    from app.promos.models import AmbassadorCampaign

    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    stmt = select(Ambassador).where(
        Ambassador.event_id == event.id,
        Ambassador.user_id == user.id,
        Ambassador.program_kind == PROGRAM_OPEN_EVENT,
    )
    if campaign_type:
        wanted = normalize_campaign_type(campaign_type)
        stmt = stmt.join(
            AmbassadorCampaign,
            AmbassadorCampaign.id == Ambassador.campaign_id,
        ).where(AmbassadorCampaign.campaign_type == wanted)
    else:
        # Prefer tickets enrollment when type omitted.
        rows = list(db.scalars(stmt.order_by(Ambassador.created_at.desc())).all())
        if not rows:
            raise HTTPException(
                status_code=404,
                detail="You are not an ambassador for this event",
            )
        for row in rows:
            if row.campaign_id is None:
                return serialize_ambassador(db, row)
            camp = db.get(AmbassadorCampaign, row.campaign_id)
            if (
                camp is not None
                and getattr(camp, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
                == CAMPAIGN_TYPE_EVENT_TICKETS
            ):
                return serialize_ambassador(db, row)
        return serialize_ambassador(db, rows[0])

    ambassador = db.scalar(stmt.order_by(Ambassador.created_at.desc()))
    if ambassador is None:
        raise HTTPException(
            status_code=404,
            detail="You are not an ambassador for this event",
        )
    return serialize_ambassador(db, ambassador)


def list_eligible_ambassador_events(db: Session) -> list[dict]:
    """Published listed events with a live public_open Ambassadors campaign."""
    from app.hosts.models import Host
    from app.promos.admin_service import is_ambassadors_feature_enabled
    from app.promos.campaigns import campaign_is_live
    from app.promos.models import AmbassadorCampaign

    if not is_ambassadors_feature_enabled(db):
        return []

    campaigns = list(
        db.scalars(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.status == "public_open"
            )
        )
    )
    now = datetime.now(UTC)
    live_event_ids = {
        c.event_id for c in campaigns if campaign_is_live(c, now=now)
    }
    # Legacy fallback: event flag without campaign row
    legacy = list(
        db.scalars(
            select(Event).where(
                Event.status == "published",
                Event.visibility.in_(("listed", "approval_required")),
                Event.open_ambassadors_enabled.is_(True),
            )
        )
    )
    for event in legacy:
        live_event_ids.add(event.id)

    if not live_event_ids:
        return []

    rows = list(
        db.scalars(
            select(Event)
            .where(
                Event.id.in_(tuple(live_event_ids)),
                Event.status == "published",
                Event.visibility.in_(("listed", "approval_required")),
            )
            .order_by(Event.start_datetime.asc())
        )
    )
    out: list[dict] = []
    for event in rows:
        host = db.get(Host, event.host_id)
        campaign = next((c for c in campaigns if c.event_id == event.id), None)
        out.append(
            {
                "id": event.id,
                "title": event.title,
                "slug": event.slug,
                "city": event.city,
                "start_datetime": event.start_datetime,
                "banner_url": event.banner_url,
                "host_display_name": host.display_name if host else None,
                "open_ambassador_commission_percent": (
                    campaign.commission_percent
                    if campaign is not None
                    else getattr(
                        event, "open_ambassador_commission_percent", Decimal("5.00")
                    )
                ),
                "open_ambassadors_enabled": True,
            }
        )
    return out


def get_my_ambassador_earnings_summary(db: Session, user: User) -> dict:
    """Aggregate earnings across all linked enrollments (no payment refs)."""
    enrollments = list(
        db.scalars(select(Ambassador).where(Ambassador.user_id == user.id)).all()
    )
    active = [a for a in enrollments if a.status == "active"]
    ambassador_ids = [a.id for a in enrollments]
    if not ambassador_ids:
        return {
            "clicks": 0,
            "total_clicks": 0,
            "unique_clicks": 0,
            "tickets_sold": 0,
            "merch_units_sold": 0,
            "confirmed_sales": 0,
            "revenue_generated": Decimal("0"),
            "estimated_earnings": Decimal("0"),
            "approved_earnings": Decimal("0"),
            "payable_earnings": Decimal("0"),
            "paid_earnings": Decimal("0"),
            "payout_status": "unavailable",
            "payout_status_label": "Payouts not available yet",
            "enrollments_active": 0,
        }

    from app.ambassadors.referral_click_stats import ambassador_click_bundle

    click_bundle = ambassador_click_bundle(db, ambassador_ids=ambassador_ids)
    clicks = click_bundle["total_clicks"]
    unique_clicks = click_bundle["unique_clicks"]
    sales = list(
        db.scalars(
            select(AmbassadorSale).where(
                AmbassadorSale.ambassador_id.in_(ambassador_ids)
            )
        )
    )
    from app.promos.commission import sale_is_past_hold

    active_sales = [s for s in sales if s.status != "reversed"]
    estimated = sum(
        (
            s.commission_owed
            for s in active_sales
            if s.status in {"attributed", "approved", "paid"}
        ),
        Decimal("0"),
    )
    approved = sum(
        (s.commission_owed for s in active_sales if s.status in {"approved", "paid"}),
        Decimal("0"),
    )
    payable = sum(
        (
            s.commission_owed
            for s in active_sales
            if s.status == "approved"
            or (s.status == "attributed" and sale_is_past_hold(s))
        ),
        Decimal("0"),
    )
    paid = sum(
        (s.commission_owed for s in active_sales if s.status == "paid"),
        Decimal("0"),
    )
    # Until ambassador payout rails ship, attributed = estimated only.
    payout_status = "unavailable"
    payout_label = "Payouts not available yet — estimated earnings shown from confirmed sales"
    if paid > 0:
        payout_status = "paid"
        payout_label = "Some Ambassador earnings have been paid"
    elif payable > 0:
        payout_status = "payable"
        payout_label = "Approved earnings ready for payout"
    elif approved > 0:
        payout_status = "approved"
        payout_label = "Earnings approved; payout pending"
    elif estimated > 0:
        payout_status = "estimated"
        payout_label = "Estimated from confirmed paid sales (pending approval)"

    return {
        "clicks": int(clicks),
        "total_clicks": int(clicks),
        "unique_clicks": int(unique_clicks),
        "tickets_sold": sum(s.tickets_sold for s in active_sales),
        "merch_units_sold": sum(
            getattr(s, "merch_units_sold", 0) or 0 for s in active_sales
        ),
        "confirmed_sales": len(active_sales),
        "revenue_generated": _q(
            sum((s.revenue_amount for s in active_sales), Decimal("0"))
        ),
        "estimated_earnings": _q(estimated),
        "approved_earnings": _q(approved),
        "payable_earnings": _q(payable),
        "paid_earnings": _q(paid),
        "payout_status": payout_status,
        "payout_status_label": payout_label,
        "enrollments_active": len(active),
    }


def leave_open_event_ambassador(db: Session, *, user: User, event_id: UUID) -> None:
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    rows = list(
        db.scalars(
            select(Ambassador).where(
                Ambassador.event_id == event.id,
                Ambassador.user_id == user.id,
                Ambassador.program_kind == PROGRAM_OPEN_EVENT,
            )
        )
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="You are not an ambassador for this event",
        )
    changed = False
    for ambassador in rows:
        if ambassador.status == "inactive":
            continue
        ambassador.status = "inactive"
        changed = True
        write_audit_log(
            db,
            action="ambassadors.open_leave",
            actor_user_id=user.id,
            resource_type="ambassador",
            resource_id=str(ambassador.id),
            details={"event_id": str(event.id)},
        )
    if changed:
        db.commit()
