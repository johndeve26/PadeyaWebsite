"""Aggregation helpers for host and admin analytics dashboards.

Keep heavy SQL here (indexed filters + date ranges) rather than in routers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import Date

from app.analytics.constants import (
    ATTENDED_TICKET_STATUSES,
    DEFAULT_RANGE_DAYS,
    NO_SHOW_TICKET_STATUSES,
    OWNED_TICKET_STATUSES,
    PLATFORM_FEE_RATE,
)
from app.analytics.models import (
    AnalyticsEvent,
    ConversionEvent,
    EventClick,
    EventImpression,
    PageView,
)
from app.analytics.taxonomy import TrackedAction
from app.analytics.utils import visitor_identity
from app.events.models import Event, EventCategory, TicketType
from app.finance.models import PayoutRequest, Refund
from app.hosts.models import Host
from app.legacy.models import HostLegacyScoreHistory
from app.payments.models import Order, Payment
from app.promos.models import Ambassador, AmbassadorSale, PromoClick, PromoCode, PromoRedemption
from app.tickets.models import Ticket
from app.users.models import User
from app.vault.models import VaultPurchase


def resolve_range(
    *,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    days: int = DEFAULT_RANGE_DAYS,
) -> tuple[datetime, datetime]:
    end = range_end or datetime.now(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    start = range_start or (end - timedelta(days=days))
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return start, end


def _dec(value: object | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _rate(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator) * Decimal("100")).quantize(
        Decimal("0.1")
    )


def conversion_counts(
    db: Session,
    *,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
    range_start: datetime,
    range_end: datetime,
) -> dict[str, int]:
    q = select(ConversionEvent.stage, func.count()).where(
        ConversionEvent.created_at >= range_start,
        ConversionEvent.created_at <= range_end,
    )
    if host_id is not None:
        q = q.where(ConversionEvent.host_id == host_id)
    if event_id is not None:
        q = q.where(ConversionEvent.event_id == event_id)
    q = q.group_by(ConversionEvent.stage)
    rows = db.execute(q).all()
    counts = {stage: 0 for stage in ("impression", "click", "checkout_start", "checkout_complete", "payment_failed")}
    for stage, count in rows:
        counts[str(stage)] = int(count)
    return counts


def compute_conversion_rate(counts: dict[str, int]) -> Decimal | None:
    """Checkout completes / clicks (fallback to impressions)."""
    completes = counts.get("checkout_complete", 0)
    base = counts.get("click", 0) or counts.get("impression", 0)
    return _rate(completes, base)


def host_sales_metrics(
    db: Session,
    *,
    host_id: UUID,
    range_start: datetime,
    range_end: datetime,
    event_id: UUID | None = None,
) -> dict:
    event_ids_q = select(Event.id).where(Event.host_id == host_id)
    if event_id is not None:
        event_ids_q = event_ids_q.where(Event.id == event_id)

    order_q = select(Order).where(
        Order.event_id.in_(event_ids_q),
        Order.status == "paid",
        Order.paid_at.is_not(None),
        Order.paid_at >= range_start,
        Order.paid_at <= range_end,
    )
    orders = list(db.scalars(order_q).all())
    revenue = sum((_dec(o.total_amount) for o in orders), Decimal("0"))

    ticket_q = select(func.count()).select_from(Ticket).where(
        Ticket.event_id.in_(event_ids_q),
        Ticket.status.in_(OWNED_TICKET_STATUSES),
        Ticket.created_at >= range_start,
        Ticket.created_at <= range_end,
    )
    tickets_sold = int(db.scalar(ticket_q) or 0)

    check_ins = int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.event_id.in_(event_ids_q),
                Ticket.status.in_(ATTENDED_TICKET_STATUSES),
            )
        )
        or 0
    )
    no_shows = int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.event_id.in_(event_ids_q),
                Ticket.status.in_(NO_SHOW_TICKET_STATUSES),
            )
        )
        or 0
    )

    breakdown_rows = db.execute(
        select(
            Ticket.ticket_type_id,
            Ticket.ticket_type_name,
            func.count(Ticket.id),
        )
        .join(Order, Order.id == Ticket.order_id)
        .where(
            Ticket.event_id.in_(event_ids_q),
            Ticket.status.in_(OWNED_TICKET_STATUSES),
            Order.status == "paid",
            Order.paid_at >= range_start,
            Order.paid_at <= range_end,
        )
        .group_by(Ticket.ticket_type_id, Ticket.ticket_type_name)
    ).all()

    tt_stats: list[dict] = []
    for tid, name, count in breakdown_rows:
        sold = int(count)
        tt = db.get(TicketType, tid) if tid else None
        unit = _dec(tt.price) if tt is not None else Decimal("0")
        tt_stats.append(
            {
                "ticket_type_id": tid,
                "name": name,
                "tickets_sold": sold,
                "revenue": (unit * sold).quantize(Decimal("0.01")),
            }
        )

    # Sales over time (by paid_at date)
    sales_series = db.execute(
        select(cast(Order.paid_at, Date), func.coalesce(func.sum(Order.total_amount), 0))
        .where(
            Order.event_id.in_(event_ids_q),
            Order.status == "paid",
            Order.paid_at.is_not(None),
            Order.paid_at >= range_start,
            Order.paid_at <= range_end,
        )
        .group_by(cast(Order.paid_at, Date))
        .order_by(cast(Order.paid_at, Date))
    ).all()

    unique_buyers = int(
        db.scalar(
            select(func.count(func.distinct(Order.buyer_user_id))).where(
                Order.event_id.in_(event_ids_q),
                Order.status == "paid",
                Order.paid_at >= range_start,
                Order.paid_at <= range_end,
            )
        )
        or 0
    )
    repeat_buyers = int(
        db.scalar(
            select(func.count()).select_from(
                select(Order.buyer_user_id)
                .where(
                    Order.event_id.in_(event_ids_q),
                    Order.status == "paid",
                    Order.paid_at >= range_start,
                    Order.paid_at <= range_end,
                )
                .group_by(Order.buyer_user_id)
                .having(func.count(Order.id) > 1)
                .subquery()
            )
        )
        or 0
    )

    return {
        "tickets_sold": tickets_sold,
        "revenue": revenue.quantize(Decimal("0.01")),
        "check_ins": check_ins,
        "no_shows": no_shows,
        "unique_buyers": unique_buyers,
        "repeat_buyers": repeat_buyers,
        "ticket_type_breakdown": tt_stats,
        "sales_over_time": [
            {"date": str(d), "value": _dec(v)} for d, v in sales_series if d is not None
        ],
    }


def host_promo_performance(
    db: Session, *, host_id: UUID, range_start: datetime, range_end: datetime
) -> list[dict]:
    promos = db.scalars(select(PromoCode).where(PromoCode.host_id == host_id)).all()
    rows: list[dict] = []
    for promo in promos:
        redemptions = list(
            db.scalars(
                select(PromoRedemption).where(
                    PromoRedemption.promo_code_id == promo.id,
                    PromoRedemption.created_at >= range_start,
                    PromoRedemption.created_at <= range_end,
                    PromoRedemption.status == "redeemed",
                )
            ).all()
        )
        if not redemptions and promo.usage_count == 0:
            continue
        discount_total = sum((_dec(r.discount_amount) for r in redemptions), Decimal("0"))
        rows.append(
            {
                "promo_code_id": promo.id,
                "code": promo.code,
                "redemptions": len(redemptions),
                "discount_total": discount_total,
                "orders": len({r.order_id for r in redemptions}),
            }
        )
    rows.sort(key=lambda r: r["redemptions"], reverse=True)
    return rows[:50]


def host_ambassador_performance(
    db: Session, *, host_id: UUID, range_start: datetime, range_end: datetime
) -> list[dict]:
    ambassadors = db.scalars(select(Ambassador).where(Ambassador.host_id == host_id)).all()
    out: list[dict] = []
    for amb in ambassadors:
        from app.ambassadors.referral_click_stats import ambassador_click_bundle

        bundle = ambassador_click_bundle(
            db,
            ambassador_ids=[amb.id],
            since=range_start,
            until=range_end,
        )
        clicks = bundle["total_clicks"]
        unique_clicks = bundle["unique_clicks"]
        sales = list(
            db.scalars(
                select(AmbassadorSale).where(
                    AmbassadorSale.ambassador_id == amb.id,
                    AmbassadorSale.created_at >= range_start,
                    AmbassadorSale.created_at <= range_end,
                )
            ).all()
        )
        tickets = sum(s.tickets_sold for s in sales)
        revenue = sum((_dec(s.revenue_amount) for s in sales), Decimal("0"))
        out.append(
            {
                "ambassador_id": amb.id,
                "name": amb.display_name or amb.referral_code,
                "referral_code": amb.referral_code,
                "clicks": clicks,
                "total_clicks": clicks,
                "unique_clicks": unique_clicks,
                "tickets_sold": tickets,
                "revenue": revenue,
                "conversion_rate": _rate(len(sales), unique_clicks or clicks),
            }
        )
    out.sort(key=lambda r: r["revenue"], reverse=True)
    return out[:50]


def host_traffic_metrics(
    db: Session,
    *,
    host_id: UUID,
    range_start: datetime,
    range_end: datetime,
    event_id: UUID | None = None,
    include_bots: bool = False,
) -> dict:
    """Traffic metrics for host dashboards.

    Default excludes bot-flagged stream rows. Totals for page views still use
    ``page_views`` (repeat visits count). Impressions/clicks prefer the
    append-only stream when present, falling back to legacy tables.
    """
    stream_base = [
        AnalyticsEvent.host_id == host_id,
        AnalyticsEvent.received_at >= range_start,
        AnalyticsEvent.received_at <= range_end,
    ]
    if event_id is not None:
        stream_base.append(AnalyticsEvent.target_event_id == event_id)
    if not include_bots:
        stream_base.append(AnalyticsEvent.is_bot.is_(False))

    def _stream_count(*names: str) -> int:
        return int(
            db.scalar(
                select(func.count())
                .select_from(AnalyticsEvent)
                .where(*stream_base, AnalyticsEvent.event_name.in_(names))
            )
            or 0
        )

    def _stream_unique(*names: str) -> int:
        rows = db.execute(
            select(
                AnalyticsEvent.user_id,
                AnalyticsEvent.anonymous_id,
                AnalyticsEvent.session_id,
            ).where(*stream_base, AnalyticsEvent.event_name.in_(names))
        ).all()
        identities = {
            visitor_identity(user_id=u, anonymous_id=a, session_id=s)
            for u, a, s in rows
        }
        return len({i for i in identities if i})

    impressions = _stream_count(
        TrackedAction.EVENT_CARD_IMPRESSION,
        TrackedAction.FEATURED_EVENT_IMPRESSION,
        TrackedAction.PADEYA_PICK_IMPRESSION,
        TrackedAction.FEATURED_PLACEMENT_IMPRESSION,
    )
    clicks = _stream_count(
        TrackedAction.EVENT_CARD_CLICK,
        TrackedAction.FEATURED_EVENT_CLICK,
        TrackedAction.PADEYA_PICK_CLICK,
        TrackedAction.FEATURED_PLACEMENT_CLICK,
    )
    unique_impressions = _stream_unique(
        TrackedAction.EVENT_CARD_IMPRESSION,
        TrackedAction.FEATURED_EVENT_IMPRESSION,
        TrackedAction.PADEYA_PICK_IMPRESSION,
        TrackedAction.FEATURED_PLACEMENT_IMPRESSION,
    )
    unique_clicks = _stream_unique(
        TrackedAction.EVENT_CARD_CLICK,
        TrackedAction.FEATURED_EVENT_CLICK,
        TrackedAction.PADEYA_PICK_CLICK,
        TrackedAction.FEATURED_PLACEMENT_CLICK,
    )
    unique_detail_views = _stream_unique(TrackedAction.EVENT_DETAIL_VIEW)

    # Fallback to legacy tables when stream is empty (older data)
    if impressions == 0 and clicks == 0:
        imp_q = select(func.count()).select_from(EventImpression).where(
            EventImpression.host_id == host_id,
            EventImpression.created_at >= range_start,
            EventImpression.created_at <= range_end,
        )
        click_q = select(func.count()).select_from(EventClick).where(
            EventClick.host_id == host_id,
            EventClick.created_at >= range_start,
            EventClick.created_at <= range_end,
        )
        if event_id is not None:
            imp_q = imp_q.where(EventImpression.event_id == event_id)
            click_q = click_q.where(EventClick.event_id == event_id)
        impressions = int(db.scalar(imp_q) or 0)
        clicks = int(db.scalar(click_q) or 0)

    pv_q = select(func.count()).select_from(PageView).where(
        PageView.host_id == host_id,
        PageView.created_at >= range_start,
        PageView.created_at <= range_end,
    )
    if event_id is not None:
        pv_q = pv_q.where(PageView.event_id == event_id)

    # Exclude bot page views when possible: sessions flagged bot on stream
    if not include_bots:
        bot_sessions = select(AnalyticsEvent.session_id).where(
            AnalyticsEvent.host_id == host_id,
            AnalyticsEvent.is_bot.is_(True),
            AnalyticsEvent.session_id.is_not(None),
            AnalyticsEvent.received_at >= range_start,
            AnalyticsEvent.received_at <= range_end,
        )
        pv_q = pv_q.where(
            (PageView.session_id.is_(None))
            | (PageView.session_id.notin_(bot_sessions))
        )

    pv_series = db.execute(
        select(cast(PageView.created_at, Date), func.count())
        .where(
            PageView.host_id == host_id,
            PageView.created_at >= range_start,
            PageView.created_at <= range_end,
            *((PageView.event_id == event_id,) if event_id is not None else ()),
        )
        .group_by(cast(PageView.created_at, Date))
        .order_by(cast(PageView.created_at, Date))
    ).all()

    return {
        "page_views": int(db.scalar(pv_q) or 0),
        "event_impressions": impressions,
        "event_clicks": clicks,
        "unique_impressions": unique_impressions,
        "unique_clicks": unique_clicks,
        "unique_detail_views": unique_detail_views,
        "page_views_over_time": [
            {"date": str(d), "value": int(c)} for d, c in pv_series if d is not None
        ],
    }


def host_vault_earnings(db: Session, *, host_id: UUID, range_start: datetime, range_end: datetime) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(VaultPurchase.amount), 0)).where(
            VaultPurchase.host_id == host_id,
            VaultPurchase.status == "paid",
            VaultPurchase.created_at >= range_start,
            VaultPurchase.created_at <= range_end,
        )
    )
    return _dec(total)


def host_legacy_score_trend(db: Session, *, host_id: UUID, limit: int = 30) -> list[dict]:
    rows = db.scalars(
        select(HostLegacyScoreHistory)
        .where(HostLegacyScoreHistory.host_id == host_id)
        .order_by(HostLegacyScoreHistory.created_at.desc())
        .limit(limit)
    ).all()
    series = [
        {"date": r.created_at.date().isoformat(), "value": _dec(r.composite_score)}
        for r in reversed(rows)
    ]
    return series


def build_host_analytics(
    db: Session,
    *,
    host_id: UUID,
    range_start: datetime,
    range_end: datetime,
    include_bots: bool = False,
) -> dict:
    sales = host_sales_metrics(
        db, host_id=host_id, range_start=range_start, range_end=range_end
    )
    traffic = host_traffic_metrics(
        db,
        host_id=host_id,
        range_start=range_start,
        range_end=range_end,
        include_bots=include_bots,
    )
    conv = conversion_counts(
        db, host_id=host_id, range_start=range_start, range_end=range_end
    )
    return {
        "host_id": host_id,
        "range_start": range_start,
        "range_end": range_end,
        "tickets_sold": sales["tickets_sold"],
        "revenue": sales["revenue"],
        "check_ins": sales["check_ins"],
        "no_shows": sales["no_shows"],
        "page_views": traffic["page_views"],
        "event_impressions": traffic["event_impressions"],
        "event_clicks": traffic["event_clicks"],
        "unique_impressions": traffic["unique_impressions"],
        "unique_clicks": traffic["unique_clicks"],
        "unique_detail_views": traffic["unique_detail_views"],
        "checkout_starts": conv.get("checkout_start", 0),
        "checkout_completes": conv.get("checkout_complete", 0),
        "conversion_rate": compute_conversion_rate(conv),
        "repeat_buyers": sales["repeat_buyers"],
        "unique_buyers": sales["unique_buyers"],
        "vault_earnings": host_vault_earnings(
            db, host_id=host_id, range_start=range_start, range_end=range_end
        ),
        "ticket_type_breakdown": sales["ticket_type_breakdown"],
        "promo_performance": host_promo_performance(
            db, host_id=host_id, range_start=range_start, range_end=range_end
        ),
        "ambassador_performance": host_ambassador_performance(
            db, host_id=host_id, range_start=range_start, range_end=range_end
        ),
        "sales_over_time": sales["sales_over_time"],
        "page_views_over_time": traffic["page_views_over_time"],
        "legacy_score_trend": host_legacy_score_trend(db, host_id=host_id),
    }


def build_event_analytics(
    db: Session,
    *,
    host_id: UUID,
    event_id: UUID,
    range_start: datetime,
    range_end: datetime,
    include_bots: bool = False,
) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise ValueError("Event not found for host")

    sales = host_sales_metrics(
        db,
        host_id=host_id,
        range_start=range_start,
        range_end=range_end,
        event_id=event_id,
    )
    traffic = host_traffic_metrics(
        db,
        host_id=host_id,
        range_start=range_start,
        range_end=range_end,
        event_id=event_id,
        include_bots=include_bots,
    )
    conv = conversion_counts(
        db,
        host_id=host_id,
        event_id=event_id,
        range_start=range_start,
        range_end=range_end,
    )
    return {
        "event_id": event.id,
        "host_id": host_id,
        "title": event.title,
        "tickets_sold": sales["tickets_sold"],
        "revenue": sales["revenue"],
        "check_ins": sales["check_ins"],
        "no_shows": sales["no_shows"],
        "page_views": traffic["page_views"],
        "impressions": traffic["event_impressions"],
        "clicks": traffic["event_clicks"],
        "unique_impressions": traffic["unique_impressions"],
        "unique_clicks": traffic["unique_clicks"],
        "unique_detail_views": traffic["unique_detail_views"],
        "checkout_starts": conv.get("checkout_start", 0),
        "checkout_completes": conv.get("checkout_complete", 0),
        "conversion_rate": compute_conversion_rate(conv),
        "ticket_type_breakdown": sales["ticket_type_breakdown"],
        "sales_over_time": sales["sales_over_time"],
    }


def build_admin_platform_summary(
    db: Session, *, range_start: datetime, range_end: datetime
) -> dict:
    total_users = int(db.scalar(select(func.count()).select_from(User)) or 0)
    total_hosts = int(db.scalar(select(func.count()).select_from(Host)) or 0)
    total_events = int(db.scalar(select(func.count()).select_from(Event)) or 0)

    gross = _dec(
        db.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.status == "paid",
                Order.paid_at.is_not(None),
                Order.paid_at >= range_start,
                Order.paid_at <= range_end,
            )
        )
    )
    platform_fees = (gross * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))

    tickets_sold = int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.status.in_(OWNED_TICKET_STATUSES),
                Ticket.created_at >= range_start,
                Ticket.created_at <= range_end,
            )
        )
        or 0
    )

    refund_amount = _dec(
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.created_at >= range_start,
                Refund.created_at <= range_end,
            )
        )
    )
    refund_rate = (
        (refund_amount / gross * Decimal("100")).quantize(Decimal("0.1"))
        if gross > 0
        else None
    )

    payout_totals = _dec(
        db.scalar(
            select(func.coalesce(func.sum(PayoutRequest.amount), 0)).where(
                PayoutRequest.status == "paid",
                PayoutRequest.updated_at >= range_start,
                PayoutRequest.updated_at <= range_end,
            )
        )
    )

    vault_revenue = _dec(
        db.scalar(
            select(func.coalesce(func.sum(VaultPurchase.amount), 0)).where(
                VaultPurchase.status == "paid",
                VaultPurchase.created_at >= range_start,
                VaultPurchase.created_at <= range_end,
            )
        )
    )

    failed_payments = int(
        db.scalar(
            select(func.count())
            .select_from(Payment)
            .where(
                Payment.status.in_(["failed", "abandoned", "cancelled"]),
                Payment.created_at >= range_start,
                Payment.created_at <= range_end,
            )
        )
        or 0
    )

    # Support volume placeholder — no support ticket model yet
    from app.finance.models import RefundRequest

    under_review = int(
        db.scalar(
            select(func.count())
            .select_from(RefundRequest)
            .where(RefundRequest.status == "under_review")
        )
        or 0
    )
    support_volume = under_review  # proxy until support tickets exist

    top_events = [
        {
            "event_id": str(eid),
            "title": title,
            "tickets_sold": int(cnt),
            "revenue": str(_dec(rev)),
        }
        for eid, title, cnt, rev in db.execute(
            select(
                Event.id,
                Event.title,
                func.count(Ticket.id),
                func.coalesce(func.sum(Order.total_amount), 0),
            )
            .join(Ticket, Ticket.event_id == Event.id)
            .join(Order, Order.id == Ticket.order_id)
            .where(
                Order.status == "paid",
                Order.paid_at >= range_start,
                Order.paid_at <= range_end,
                Ticket.status.in_(OWNED_TICKET_STATUSES),
            )
            .group_by(Event.id, Event.title)
            .order_by(func.count(Ticket.id).desc())
            .limit(10)
        ).all()
    ]

    top_hosts = [
        {
            "host_id": str(hid),
            "display_name": name,
            "username": slug,
            "revenue": str(_dec(rev)),
        }
        for hid, name, slug, rev in db.execute(
            select(
                Host.id,
                Host.display_name,
                Host.slug,
                func.coalesce(func.sum(Order.total_amount), 0),
            )
            .join(Event, Event.host_id == Host.id)
            .join(Order, Order.event_id == Event.id)
            .where(
                Order.status == "paid",
                Order.paid_at >= range_start,
                Order.paid_at <= range_end,
            )
            .group_by(Host.id, Host.display_name, Host.slug)
            .order_by(func.coalesce(func.sum(Order.total_amount), 0).desc())
            .limit(10)
        ).all()
    ]

    category_trends = [
        {"category": name or "uncategorized", "events": int(cnt)}
        for name, cnt in db.execute(
            select(EventCategory.name, func.count(Event.id))
            .select_from(Event)
            .outerjoin(EventCategory, EventCategory.id == Event.category_id)
            .where(Event.created_at >= range_start, Event.created_at <= range_end)
            .group_by(EventCategory.name)
            .order_by(func.count(Event.id).desc())
            .limit(20)
        ).all()
    ]

    city_trends = [
        {"city": city or "unknown", "events": int(cnt)}
        for city, cnt in db.execute(
            select(Event.city, func.count(Event.id))
            .where(Event.created_at >= range_start, Event.created_at <= range_end)
            .group_by(Event.city)
            .order_by(func.count(Event.id).desc())
            .limit(20)
        ).all()
    ]

    sales_series = db.execute(
        select(cast(Order.paid_at, Date), func.coalesce(func.sum(Order.total_amount), 0))
        .where(
            Order.status == "paid",
            Order.paid_at.is_not(None),
            Order.paid_at >= range_start,
            Order.paid_at <= range_end,
        )
        .group_by(cast(Order.paid_at, Date))
        .order_by(cast(Order.paid_at, Date))
    ).all()

    return {
        "range_start": range_start,
        "range_end": range_end,
        "total_users": total_users,
        "total_hosts": total_hosts,
        "total_events": total_events,
        "tickets_sold": tickets_sold,
        "gross_revenue": gross,
        "platform_fees": platform_fees,
        "refund_rate": refund_rate,
        "refund_amount": refund_amount,
        "payout_totals": payout_totals,
        "vault_revenue": vault_revenue,
        "failed_payments": failed_payments,
        "support_volume": support_volume,
        "fraud_signals": [
            {
                "code": "placeholder",
                "label": "Fraud signals not yet wired",
                "severity": 0,
            }
        ],
        "top_events": top_events,
        "top_hosts": top_hosts,
        "category_trends": category_trends,
        "city_trends": city_trends,
        "sales_over_time": [
            {"date": str(d), "value": _dec(v)} for d, v in sales_series if d is not None
        ],
    }


def build_admin_revenue(
    db: Session, *, range_start: datetime, range_end: datetime
) -> dict:
    summary = build_admin_platform_summary(
        db, range_start=range_start, range_end=range_end
    )
    return {
        "gross_revenue": summary["gross_revenue"],
        "platform_fees": summary["platform_fees"],
        "refund_amount": summary["refund_amount"],
        "payout_totals": summary["payout_totals"],
        "vault_revenue": summary["vault_revenue"],
        "net_after_refunds": (
            summary["gross_revenue"] - summary["refund_amount"]
        ).quantize(Decimal("0.01")),
        "sales_over_time": summary["sales_over_time"],
    }


def build_admin_events(
    db: Session, *, range_start: datetime, range_end: datetime
) -> dict:
    summary = build_admin_platform_summary(
        db, range_start=range_start, range_end=range_end
    )
    by_status = [
        {"status": status, "count": int(cnt)}
        for status, cnt in db.execute(
            select(Event.status, func.count(Event.id)).group_by(Event.status)
        ).all()
    ]
    return {
        "total_events": summary["total_events"],
        "by_status": by_status,
        "top_events": summary["top_events"],
        "category_trends": summary["category_trends"],
        "city_trends": summary["city_trends"],
    }


def build_admin_hosts(
    db: Session, *, range_start: datetime, range_end: datetime
) -> dict:
    summary = build_admin_platform_summary(
        db, range_start=range_start, range_end=range_end
    )
    active_hosts = int(
        db.scalar(select(func.count()).select_from(Host).where(Host.status == "active"))
        or 0
    )
    return {
        "total_hosts": summary["total_hosts"],
        "active_hosts": active_hosts,
        "top_hosts": summary["top_hosts"],
    }


def build_admin_support(db: Session) -> dict:
    from app.finance.models import RefundRequest

    open_refunds = int(
        db.scalar(
            select(func.count())
            .select_from(RefundRequest)
            .where(RefundRequest.status.in_(["requested", "under_review"]))
        )
        or 0
    )
    under_review = int(
        db.scalar(
            select(func.count())
            .select_from(RefundRequest)
            .where(RefundRequest.status == "under_review")
        )
        or 0
    )
    return {
        "support_volume": under_review,
        "open_refund_requests": open_refunds,
        "escalated_refunds": under_review,
        "note": "Support ticket model not implemented; volume uses refunds under review as a proxy.",
        "fraud_signals": [
            {
                "code": "placeholder",
                "label": "Fraud signals not yet wired",
                "severity": 0,
            }
        ],
    }
