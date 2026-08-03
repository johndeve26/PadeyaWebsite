"""Shared referral aggregation — authoritative dashboard totals from the ledger."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.promos.models import Ambassador, AmbassadorCampaign, PromoClick
from app.promos.referral_ledger import ReferralAttribution, ReferralCommissionEntry
from app.promos.referral_programs import ReferralProgram, ReferralProgramRule
from app.users.models import User


def _q(amount: Decimal) -> Decimal:
    return Decimal(amount or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money(amount: Decimal) -> str:
    return str(_q(amount))


def _entry_filters(
    *,
    ambassador_user_id: UUID | None = None,
    enrollment_ids: list[UUID] | None = None,
    host_id: UUID | None = None,
    payer_type: str | None = None,
    program_id: UUID | None = None,
    product_type: str | None = None,
    scope: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    clauses = []
    if ambassador_user_id is not None:
        clauses.append(ReferralCommissionEntry.ambassador_user_id == ambassador_user_id)
    if enrollment_ids is not None:
        if not enrollment_ids:
            clauses.append(ReferralCommissionEntry.enrollment_id.is_(None))
        else:
            clauses.append(ReferralCommissionEntry.enrollment_id.in_(enrollment_ids))
    if host_id is not None:
        clauses.append(ReferralCommissionEntry.host_id == host_id)
    if payer_type:
        clauses.append(ReferralCommissionEntry.payer_type == payer_type)
    if program_id is not None:
        clauses.append(ReferralCommissionEntry.program_id == program_id)
    if product_type:
        clauses.append(ReferralCommissionEntry.product_type == product_type)
    if date_from is not None:
        clauses.append(ReferralCommissionEntry.created_at >= date_from)
    if date_to is not None:
        clauses.append(ReferralCommissionEntry.created_at <= date_to)
    if scope == "platform":
        clauses.append(ReferralCommissionEntry.payer_type == "platform")
    elif scope in {"event", "host"}:
        clauses.append(ReferralCommissionEntry.payer_type == "host")
    return clauses


def _aggregate_entries(rows: list[ReferralCommissionEntry]) -> dict:
    pending = Decimal("0")
    available = Decimal("0")
    paid = Decimal("0")
    reversed_abs = Decimal("0")
    net = Decimal("0")
    eligible = Decimal("0")
    gross = Decimal("0")
    order_ids: set[UUID] = set()
    item_keys: set[str] = set()
    bases_counted: set[str] = set()

    for row in rows:
        amt = _q(Decimal(row.commission_amount))
        net += amt
        if row.entry_type == "earning":
            item_key = f"{row.order_id}:{row.attribution_item_key}"
            # Dual host+platform earnings share one item base — count once
            if item_key not in bases_counted:
                eligible += _q(Decimal(row.eligible_commission_base))
                gross += _q(Decimal(row.gross_item_amount))
                bases_counted.add(item_key)
            order_ids.add(row.order_id)
            item_keys.add(item_key)
            if row.status == "paid":
                paid += amt
            elif row.status in {"approved", "payable"}:
                available += amt
            else:
                pending += amt
        elif row.entry_type == "reversal":
            reversed_abs += abs(amt)
            if row.status == "paid":
                paid += amt  # negative
            elif row.status in {"approved", "payable"}:
                available += amt
            else:
                pending += amt
        elif row.entry_type == "payout":
            paid += amt
        else:
            # adjustment
            if row.status == "paid":
                paid += amt
            elif row.status in {"approved", "payable"}:
                available += amt
            else:
                pending += amt

    return {
        "converted_orders": len(order_ids),
        "attributed_items": len(item_keys),
        "referred_gross_sales": _money(gross),
        "eligible_sales": _money(eligible),
        "pending_commission": _money(pending),
        "available_commission": _money(available),
        "paid_commission": _money(paid),
        "reversed_commission": _money(reversed_abs),
        "net_commission": _money(net),
    }


def _click_count(db: Session, enrollment_ids: list[UUID]) -> int:
    if not enrollment_ids:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(PromoClick)
            .where(PromoClick.ambassador_id.in_(enrollment_ids))
        )
        or 0
    )


def get_ambassador_referral_summary(
    db: Session,
    *,
    user: User,
    scope: str | None = None,
    product_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    enrollments = list(
        db.scalars(select(Ambassador).where(Ambassador.user_id == user.id)).all()
    )
    ids = [e.id for e in enrollments]
    clauses = _entry_filters(
        ambassador_user_id=user.id,
        scope=scope,
        product_type=product_type,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = select(ReferralCommissionEntry)
    if clauses:
        stmt = stmt.where(*clauses)
    else:
        stmt = stmt.where(ReferralCommissionEntry.ambassador_user_id == user.id)
    rows = list(db.scalars(stmt).all())

    agg = _aggregate_entries(rows)
    clicks = _click_count(db, ids)
    converted = int(agg["converted_orders"])
    rate = (
        round((converted / clicks) * 100, 2) if clicks > 0 else 0.0
    )
    active_enrollments = [e for e in enrollments if e.status == "active"]
    has_platform = any(
        e.program_kind == "platform_wide" for e in active_enrollments
    )
    has_host = any(
        e.program_kind != "platform_wide" for e in active_enrollments
    )
    primary_link = None
    for e in active_enrollments:
        if e.program_kind == "platform_wide" and e.referral_code:
            primary_link = f"/r/{e.referral_code}"
            break
    if primary_link is None:
        for e in active_enrollments:
            if e.referral_code:
                primary_link = f"/r/{e.referral_code}"
                break

    return {
        "clicks": clicks,
        "conversion_rate": rate,
        "enrollments_active": len(active_enrollments),
        "has_platform_enrollment": has_platform,
        "has_host_enrollment": has_host,
        "primary_referral_link_path": primary_link,
        "scopes": (
            (["platform"] if has_platform else [])
            + (["host"] if has_host else [])
        ),
        **agg,
    }


def get_ambassador_program_breakdown(
    db: Session,
    *,
    user: User,
    scope: str | None = None,
) -> list[dict]:
    enrollments = list(
        db.scalars(
            select(Ambassador)
            .where(Ambassador.user_id == user.id)
            .order_by(Ambassador.created_at.desc())
        ).all()
    )
    out: list[dict] = []
    for amb in enrollments:
        program = db.get(ReferralProgram, amb.program_id) if amb.program_id else None
        campaign = (
            db.get(AmbassadorCampaign, amb.campaign_id) if amb.campaign_id else None
        )
        is_platform = amb.program_kind == "platform_wide" or (
            program is not None and program.scope == "platform"
        )
        if scope == "platform" and not is_platform:
            continue
        if scope in {"host", "event"} and is_platform:
            continue

        event_title = None
        event_slug = None
        if amb.event_id:
            event = db.get(Event, amb.event_id)
            if event:
                event_title = event.title
                event_slug = event.slug

        rules = []
        if program is not None:
            rules = list(
                db.scalars(
                    select(ReferralProgramRule).where(
                        ReferralProgramRule.program_id == program.id,
                        ReferralProgramRule.is_active.is_(True),
                    )
                ).all()
            )
        coverage = []
        if rules:
            coverage = [r.product_type for r in rules]
        elif campaign is not None:
            coverage = [
                "merchandise"
                if getattr(campaign, "campaign_type", "") == "event_merch"
                else "ticket"
            ]

        rows = list(
            db.scalars(
                select(ReferralCommissionEntry).where(
                    ReferralCommissionEntry.enrollment_id == amb.id
                )
            ).all()
        )
        agg = _aggregate_entries(rows)
        code = amb.referral_code or ""
        out.append(
            {
                "enrollment_id": amb.id,
                "program_id": amb.program_id,
                "campaign_id": amb.campaign_id,
                "name": (program.name if program else None)
                or (campaign.name if campaign else None)
                or amb.display_name,
                "scope_badge": "Platform" if is_platform else "Host",
                "scope": "platform" if is_platform else "event",
                "event_title": event_title,
                "event_slug": event_slug,
                "product_coverage": coverage,
                "commission_rules": [
                    {
                        "product_type": r.product_type,
                        "commission_mode": r.commission_mode,
                        "commission_value": str(r.commission_value),
                    }
                    for r in rules
                ]
                or (
                    [
                        {
                            "product_type": coverage[0] if coverage else "ticket",
                            "commission_mode": getattr(
                                campaign, "commission_type", "percentage"
                            )
                            if campaign
                            else "percentage",
                            "commission_value": str(
                                getattr(campaign, "commission_value", amb.commission_rate_percent)
                                if campaign
                                else amb.commission_rate_percent
                            ),
                        }
                    ]
                    if campaign or amb.commission_rate_percent is not None
                    else []
                ),
                "status": amb.status,
                "referral_code": code,
                "referral_link_path": f"/r/{code}" if is_platform and code else None,
                "clicks": _click_count(db, [amb.id]),
                **agg,
            }
        )
    return out


def get_ambassador_earnings(
    db: Session,
    *,
    user: User,
    scope: str | None = None,
    product_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    clauses = _entry_filters(
        ambassador_user_id=user.id,
        scope=scope,
        product_type=product_type,
    )
    stmt = (
        select(ReferralCommissionEntry)
        .where(*clauses)
        .order_by(ReferralCommissionEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())
    out = []
    for row in rows:
        program = db.get(ReferralProgram, row.program_id) if row.program_id else None
        campaign = (
            db.get(AmbassadorCampaign, row.campaign_id) if row.campaign_id else None
        )
        event_title = None
        if row.event_id:
            event = db.get(Event, row.event_id)
            event_title = event.title if event else None
        out.append(
            {
                "id": row.id,
                "date": row.created_at,
                "entry_type": row.entry_type,
                "source": "platform" if row.payer_type == "platform" else "host",
                "payer_type": row.payer_type,
                "program_name": (program.name if program else None)
                or (campaign.name if campaign else None),
                "event_title": event_title,
                "product_type": row.product_type,
                "eligible_sale": _money(Decimal(row.eligible_commission_base)),
                "commission": _money(Decimal(row.commission_amount)),
                "currency": row.currency,
                "status": row.status,
                "order_reference": None,  # privacy: no buyer; optional safe ref later
                "attribution_item_key": row.attribution_item_key,
                "payout_reference": None,
            }
        )
    return out


def get_host_referral_summary(db: Session, *, host_id: UUID) -> dict:
    rows = list(
        db.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.host_id == host_id,
                ReferralCommissionEntry.payer_type == "host",
            )
        ).all()
    )
    platform_attrs = int(
        db.scalar(
            select(func.count())
            .select_from(ReferralAttribution)
            .where(
                ReferralAttribution.host_id == host_id,
                ReferralAttribution.payer_type == "platform",
            )
        )
        or 0
    )
    agg = _aggregate_entries(rows)
    return {
        **agg,
        "platform_attributed_items": platform_attrs,
        "host_funded_only": True,
    }


def get_host_platform_attributed_sales(
    db: Session,
    *,
    host_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Read-only platform-funded attributions for a host's events."""
    from app.payments.models import Order

    attrs = list(
        db.scalars(
            select(ReferralAttribution)
            .where(
                ReferralAttribution.host_id == host_id,
                ReferralAttribution.payer_type == "platform",
            )
            .order_by(ReferralAttribution.resolved_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    out = []
    for attr in attrs:
        order = db.get(Order, attr.order_id)
        event = db.get(Event, attr.event_id) if attr.event_id else None
        earning = db.scalar(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.attribution_id == attr.id,
                ReferralCommissionEntry.entry_type == "earning",
            )
        )
        out.append(
            {
                "order_id": attr.order_id,
                "order_reference": order.reference if order else None,
                "event_id": attr.event_id,
                "event_title": event.title if event else None,
                "product_type": attr.product_type,
                "gross_attributed_sale": _money(
                    Decimal(earning.gross_item_amount) if earning else Decimal("0")
                ),
                "host_proceeds_note": "Platform referral commission is funded by Pàdéyá and is not deducted from host settlement.",
                "attribution_badge": "Platform referral",
                "commission_funded_by": "Padeya",
                "resolved_at": attr.resolved_at,
            }
        )
    return out


def get_admin_referral_summary(
    db: Session,
    *,
    scope: str | None = None,
    payer: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    from app.promos.campaigns import campaign_is_live

    source_host = "host"
    source_platform = "platform"

    clauses = _entry_filters(
        scope=scope,
        payer_type=payer,
        date_from=date_from,
        date_to=date_to,
    )
    rows = list(
        db.scalars(
            select(ReferralCommissionEntry).where(*clauses)
            if clauses
            else select(ReferralCommissionEntry)
        ).all()
    )
    host_rows = [r for r in rows if r.payer_type == "host"]
    platform_rows = [r for r in rows if r.payer_type == "platform"]
    host_agg = _aggregate_entries(host_rows)
    plat_agg = _aggregate_entries(platform_rows)
    all_agg = _aggregate_entries(rows)

    active_programs = int(
        db.scalar(
            select(func.count())
            .select_from(ReferralProgram)
            .where(
                ReferralProgram.scope == "platform",
                ReferralProgram.status == "active",
            )
        )
        or 0
    )
    active_ambassadors = int(
        db.scalar(
            select(func.count())
            .select_from(Ambassador)
            .where(
                Ambassador.program_kind == "platform_wide",
                Ambassador.status == "active",
            )
        )
        or 0
    )

    campaigns = list(db.scalars(select(AmbassadorCampaign)).all())
    host_campaigns_live = sum(
        1
        for c in campaigns
        if campaign_is_live(c)
        and getattr(c, "source", source_host) != source_platform
    )
    # Platform-sourced campaigns (rare admin-created) counted separately from programs
    platform_campaigns_live = sum(
        1
        for c in campaigns
        if campaign_is_live(c)
        and getattr(c, "source", source_host) == source_platform
    )

    platform_enrollments = active_ambassadors
    host_enrollments = int(
        db.scalar(
            select(func.count())
            .select_from(Ambassador)
            .where(
                Ambassador.status == "active",
                Ambassador.program_kind != "platform_wide",
            )
        )
        or 0
    )
    unique_active = int(
        db.scalar(
            select(func.count(func.distinct(Ambassador.user_id))).where(
                Ambassador.status == "active",
                Ambassador.user_id.is_not(None),
            )
        )
        or 0
    )

    def _owed(agg: dict) -> str:
        pending = Decimal(str(agg["pending_commission"]))
        available = Decimal(str(agg["available_commission"]))
        return _money(pending + available)

    host_owed = _owed(host_agg)
    platform_owed = _owed(plat_agg)
    total_owed = _money(
        Decimal(host_owed) + Decimal(platform_owed)
    )

    return {
        "total_referred_gross_sales": all_agg["referred_gross_sales"],
        "host_funded_commission": host_agg["net_commission"],
        "platform_funded_commission": plat_agg["net_commission"],
        "pending_platform_liability": plat_agg["pending_commission"],
        "approved_platform_liability": plat_agg["available_commission"],
        "paid_platform_commission": plat_agg["paid_commission"],
        "platform_reversals": plat_agg["reversed_commission"],
        "host_reversals": host_agg["reversed_commission"],
        "active_platform_programs": active_programs,
        "active_platform_ambassadors": active_ambassadors,
        "converted_orders": all_agg["converted_orders"],
        "attributed_items": all_agg["attributed_items"],
        # Overview hub fields (additive; ledger-backed)
        "active_host_campaigns": host_campaigns_live,
        "active_platform_campaigns": platform_campaigns_live,
        "active_arrangements": active_programs + host_campaigns_live,
        "unique_active_ambassadors": unique_active,
        "platform_enrollments_active": platform_enrollments,
        "host_enrollments_active": host_enrollments,
        "commission_owed_total": total_owed,
        "host_funded_owed": host_owed,
        "platform_funded_owed": platform_owed,
        "pending_commission": all_agg["pending_commission"],
        "available_commission": all_agg["available_commission"],
        "paid_commission": all_agg["paid_commission"],
    }


def get_admin_referral_liabilities(
    db: Session,
    *,
    payer: str = "platform",
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    clauses = [
        ReferralCommissionEntry.payer_type == payer,
        ReferralCommissionEntry.entry_type.in_(("earning", "reversal", "adjustment")),
    ]
    if status:
        clauses.append(ReferralCommissionEntry.status == status)
    rows = list(
        db.scalars(
            select(ReferralCommissionEntry)
            .where(*clauses)
            .order_by(ReferralCommissionEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return [
        {
            "id": r.id,
            "entry_type": r.entry_type,
            "payer_type": r.payer_type,
            "status": r.status,
            "commission_amount": _money(Decimal(r.commission_amount)),
            "currency": r.currency,
            "order_id": r.order_id,
            "enrollment_id": r.enrollment_id,
            "program_id": r.program_id,
            "product_type": r.product_type,
            "created_at": r.created_at,
            "original_entry_id": r.original_entry_id,
        }
        for r in rows
    ]


def get_admin_referral_commissions(
    db: Session,
    *,
    payer: str | None = None,
    program_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    clauses = _entry_filters(payer_type=payer, program_id=program_id)
    stmt = select(ReferralCommissionEntry).order_by(
        ReferralCommissionEntry.created_at.desc()
    )
    if clauses:
        stmt = stmt.where(*clauses)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    return [
        {
            "id": r.id,
            "entry_type": r.entry_type,
            "payer_type": r.payer_type,
            "status": r.status,
            "commission_amount": _money(Decimal(r.commission_amount)),
            "eligible_commission_base": _money(Decimal(r.eligible_commission_base)),
            "currency": r.currency,
            "product_type": r.product_type,
            "order_id": r.order_id,
            "attribution_item_key": r.attribution_item_key,
            "enrollment_id": r.enrollment_id,
            "program_id": r.program_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]
