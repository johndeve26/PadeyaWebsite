"""Aggregate referral click metrics from canonical referral_clicks rows."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.promos.models import AmbassadorSale, PromoClick
from app.promos.referral_clicks import ReferralClick

DUPLICATE_WINDOW_SECONDS = 30
DEFAULT_UNIQUE_WINDOW_HOURS = 24


def _empty_click_metrics() -> dict:
    return {
        "total_clicks": 0,
        "unique_clicks": 0,
        "qualified_clicks": 0,
        "first_click_at": None,
        "last_click_at": None,
    }


def _referral_clicks_table_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "referral_clicks" in msg and (
        "does not exist" in msg or "undefinedtable" in msg or "no such table" in msg
    )


def _click_filters(
    *,
    ambassador_ids: list[UUID] | None = None,
    participant_ids: list[UUID] | None = None,
    campaign_ids: list[UUID] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
):
    clauses = []
    if ambassador_ids:
        clauses.append(ReferralClick.ambassador_id.in_(ambassador_ids))
    if participant_ids:
        clauses.append(ReferralClick.participant_id.in_(participant_ids))
    if campaign_ids:
        clauses.append(ReferralClick.campaign_id.in_(campaign_ids))
    if since is not None:
        clauses.append(ReferralClick.created_at >= since)
    if until is not None:
        clauses.append(ReferralClick.created_at <= until)
    return clauses


def referral_click_metrics(
    db: Session,
    *,
    ambassador_ids: list[UUID] | None = None,
    participant_ids: list[UUID] | None = None,
    campaign_ids: list[UUID] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    """Total vs unique clicks with first/last timestamps."""
    clauses = _click_filters(
        ambassador_ids=ambassador_ids,
        participant_ids=participant_ids,
        campaign_ids=campaign_ids,
        since=since,
        until=until,
    )
    try:
        total_clicks = int(
            db.scalar(
                select(func.count())
                .select_from(ReferralClick)
                .where(*(clauses + [ReferralClick.is_duplicate_30s.is_(False)]))
            )
            or 0
        )
        unique_clicks = int(
            db.scalar(
                select(func.count())
                .select_from(ReferralClick)
                .where(*(clauses + [ReferralClick.is_unique_24h.is_(True)]))
            )
            or 0
        )
        qualified_clicks = int(
            db.scalar(
                select(func.count())
                .select_from(ReferralClick)
                .where(*(clauses + [ReferralClick.is_qualified.is_(True)]))
            )
            or 0
        )
        first_click_at = db.scalar(
            select(func.min(ReferralClick.created_at))
            .select_from(ReferralClick)
            .where(*(clauses + [ReferralClick.is_duplicate_30s.is_(False)]))
        )
        last_click_at = db.scalar(
            select(func.max(ReferralClick.created_at))
            .select_from(ReferralClick)
            .where(*(clauses + [ReferralClick.is_duplicate_30s.is_(False)]))
        )
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        if _referral_clicks_table_error(exc):
            return _empty_click_metrics()
        raise
    return {
        "total_clicks": total_clicks,
        "unique_clicks": unique_clicks,
        "qualified_clicks": qualified_clicks,
        "first_click_at": first_click_at,
        "last_click_at": last_click_at,
    }


def legacy_promo_click_count(
    db: Session,
    *,
    ambassador_ids: list[UUID],
    since: datetime | None = None,
    until: datetime | None = None,
) -> int:
    if not ambassador_ids:
        return 0
    stmt = (
        select(func.count())
        .select_from(PromoClick)
        .where(PromoClick.ambassador_id.in_(ambassador_ids))
    )
    if since is not None:
        stmt = stmt.where(PromoClick.created_at >= since)
    if until is not None:
        stmt = stmt.where(PromoClick.created_at <= until)
    return int(db.scalar(stmt) or 0)


def ambassador_click_bundle(
    db: Session,
    *,
    ambassador_ids: list[UUID],
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict:
    """Metrics for v1 ambassador rows with legacy fallback."""
    metrics = referral_click_metrics(
        db,
        ambassador_ids=ambassador_ids,
        since=since,
        until=until,
    )
    if metrics["total_clicks"] == 0 and ambassador_ids:
        legacy = legacy_promo_click_count(
            db, ambassador_ids=ambassador_ids, since=since, until=until
        )
        if legacy:
            metrics = {
                **metrics,
                "total_clicks": legacy,
                "unique_clicks": legacy,
                "clicks": legacy,
            }
    else:
        metrics["clicks"] = metrics["total_clicks"]
    return metrics


def conversion_rate_percent(
    conversions: int, *, total_clicks: int, unique_clicks: int
) -> Decimal:
    denom = unique_clicks if unique_clicks > 0 else total_clicks
    if denom <= 0:
        return Decimal("0")
    return (Decimal(conversions) / Decimal(denom) * Decimal("100")).quantize(
        Decimal("0.01")
    )


def ambassador_sales_bundle(db: Session, ambassador_ids: list[UUID]) -> dict:
    if not ambassador_ids:
        return {
            "conversions": 0,
            "confirmed_sales": 0,
            "tickets_sold": 0,
            "merch_units_sold": 0,
            "gross_revenue": Decimal("0"),
            "confirmed_revenue": Decimal("0"),
            "reward_amount": Decimal("0"),
        }
    sales = list(
        db.scalars(
            select(AmbassadorSale).where(
                AmbassadorSale.ambassador_id.in_(ambassador_ids)
            )
        )
    )
    counted = [s for s in sales if s.status != "reversed"]
    tickets = sum(s.tickets_sold for s in counted)
    merch = sum(getattr(s, "merch_units_sold", 0) or 0 for s in counted)
    gross = sum((s.revenue_amount for s in sales), Decimal("0"))
    confirmed_rev = sum((s.revenue_amount for s in counted), Decimal("0"))
    reward = sum((s.commission_owed for s in counted), Decimal("0"))
    return {
        "conversions": len(counted),
        "confirmed_sales": len(counted),
        "tickets_sold": tickets,
        "merch_units_sold": merch,
        "gross_revenue": gross,
        "confirmed_revenue": confirmed_rev,
        "reward_amount": reward,
    }


def merge_ambassador_dashboard_stats(
    db: Session, *, ambassador_ids: list[UUID]
) -> dict:
    clicks = ambassador_click_bundle(db, ambassador_ids=ambassador_ids)
    sales = ambassador_sales_bundle(db, ambassador_ids)
    rate = conversion_rate_percent(
        sales["conversions"],
        total_clicks=clicks["total_clicks"],
        unique_clicks=clicks["unique_clicks"],
    )
    return {
        **clicks,
        **sales,
        "conversion_rate": rate,
        "revenue_generated": sales["confirmed_revenue"],
        "commission_owed": sales["reward_amount"],
    }
