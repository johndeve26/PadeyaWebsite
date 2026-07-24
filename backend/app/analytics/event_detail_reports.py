"""Detailed per-event analytics report builders.

Live SQL over ``analytics_events`` + commerce tables. Filters default to
excluding bots. Designed for host and admin read endpoints.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.aggregations import _dec, _rate
from app.analytics.constants import ATTENDED_TICKET_STATUSES, OWNED_TICKET_STATUSES
from app.analytics.event_filters import (
    EventAnalyticsFilters,
    apply_stream_filters,
    classify_traffic_source,
    metadata_ticket_type_matches,
    stream_time_column,
)
from app.analytics.models import AnalyticsEvent
from app.analytics.rollup_models import EventDailyAnalytics
from app.analytics.taxonomy import TrackedAction
from app.analytics.utils import visitor_identity
from app.crm.models import HostFollower
from app.events.models import Event, TicketType
from app.finance.models import Refund, RefundRequest
from app.payments.models import Order
from app.promos.models import Ambassador, AmbassadorSale, PromoClick, PromoCode, PromoRedemption
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket

IMPRESSION_ACTIONS = (
    TrackedAction.EVENT_CARD_IMPRESSION,
    TrackedAction.FEATURED_EVENT_IMPRESSION,
    TrackedAction.PADEYA_PICK_IMPRESSION,
    TrackedAction.FEATURED_PLACEMENT_IMPRESSION,
)
CLICK_ACTIONS = (
    TrackedAction.EVENT_CARD_CLICK,
    TrackedAction.FEATURED_EVENT_CLICK,
    TrackedAction.PADEYA_PICK_CLICK,
    TrackedAction.FEATURED_PLACEMENT_CLICK,
)
DETAIL_ACTIONS = (TrackedAction.EVENT_DETAIL_VIEW,)
TICKET_SELECT_ACTIONS = (TrackedAction.TICKET_TYPE_SELECTED,)
CHECKOUT_START_ACTIONS = (
    TrackedAction.CHECKOUT_START_CLICK,
    TrackedAction.CHECKOUT_PAGE_VIEW,
)
PAYMENT_START_ACTIONS = (TrackedAction.CHECKOUT_PAYMENT_STARTED,)
PURCHASE_ACTIONS = (TrackedAction.PAYMENT_SUCCESS,)
TICKET_ISSUED_ACTIONS = (TrackedAction.TICKET_ISSUED,)
CHECKIN_ACTIONS = (TrackedAction.CHECKIN_SUCCESS,)
REVIEW_ACTIONS = (TrackedAction.REVIEW_SUBMITTED,)
TICKET_IMPRESSION_ACTIONS = (TrackedAction.TICKET_TYPE_IMPRESSION,)


def _filters_echo(filters: EventAnalyticsFilters) -> dict:
    return {
        "date_from": filters.date_from,
        "date_to": filters.date_to,
        "source": filters.source,
        "medium": filters.medium,
        "campaign": filters.campaign,
        "ticket_type_id": filters.ticket_type_id,
        "device_type": filters.device_type,
        "city": filters.city,
        "include_bots": filters.include_bots,
    }


def _filters_support_daily_rollups(filters: EventAnalyticsFilters) -> bool:
    """Daily rollups are unscoped — only use when no dimension filters are set."""
    return (
        not filters.include_bots
        and filters.source is None
        and filters.medium is None
        and filters.campaign is None
        and filters.ticket_type_id is None
        and filters.device_type is None
        and filters.city is None
    )


def _sum_event_daily_rollups(
    db: Session, *, event_id: UUID, filters: EventAnalyticsFilters
) -> dict[str, int] | None:
    """Sum persisted daily rollups for the filter window. None if no rows."""
    day_from = filters.date_from.date()
    day_to = filters.date_to.date()
    rows = list(
        db.scalars(
            select(EventDailyAnalytics).where(
                EventDailyAnalytics.event_id == event_id,
                EventDailyAnalytics.date >= day_from,
                EventDailyAnalytics.date <= day_to,
            )
        ).all()
    )
    if not rows:
        return None
    return {
        "impressions": sum(r.impressions for r in rows),
        "unique_impressions": sum(r.unique_impressions for r in rows),
        "card_clicks": sum(r.card_clicks for r in rows),
        "detail_views": sum(r.detail_views for r in rows),
        "unique_detail_views": sum(r.unique_detail_views for r in rows),
        "ticket_selections": sum(r.ticket_selections for r in rows),
        "checkout_starts": sum(r.checkout_starts for r in rows),
        "payment_starts": sum(r.payment_starts for r in rows),
        "payment_successes": sum(r.payment_successes for r in rows),
        "checkins": sum(r.checkins for r in rows),
        "reviews_submitted": sum(r.reviews_submitted for r in rows),
    }


def _load_event(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise ValueError("Event not found")
    return event


def _stream_rows(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID | None,
    filters: EventAnalyticsFilters,
    actions: tuple[str, ...] | None = None,
) -> list[AnalyticsEvent]:
    clauses: list = []
    apply_stream_filters(clauses, filters, event_id=event_id, host_id=host_id)
    if actions:
        clauses.append(AnalyticsEvent.event_name.in_(actions))
    rows = list(db.scalars(select(AnalyticsEvent).where(*clauses)).all())
    if filters.ticket_type_id is not None:
        rows = [
            r
            for r in rows
            if metadata_ticket_type_matches(r.event_metadata, filters.ticket_type_id)
            or metadata_ticket_type_matches(r.properties, filters.ticket_type_id)
        ]
    return rows


def _count_actions(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID | None,
    filters: EventAnalyticsFilters,
    actions: tuple[str, ...],
) -> int:
    return len(
        _stream_rows(
            db,
            event_id=event_id,
            host_id=host_id,
            filters=filters,
            actions=actions,
        )
    )


def _unique_visitors(
    rows: list[AnalyticsEvent],
) -> set[str]:
    out: set[str] = set()
    for row in rows:
        ident = visitor_identity(
            user_id=row.user_id,
            anonymous_id=row.anonymous_id,
            session_id=row.session_id,
        )
        if ident:
            out.add(ident)
    return out


def _paid_orders(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
) -> list[Order]:
    orders = list(
        db.scalars(
            select(Order).where(
                Order.event_id == event_id,
                Order.status == "paid",
                Order.paid_at.is_not(None),
                Order.paid_at >= filters.date_from,
                Order.paid_at <= filters.date_to,
            )
        ).all()
    )
    if filters.ticket_type_id is None:
        return orders
    # Keep orders that include the filtered ticket type
    keep: list[Order] = []
    for order in orders:
        has_tt = db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.order_id == order.id,
                Ticket.ticket_type_id == filters.ticket_type_id,
                Ticket.status.in_(OWNED_TICKET_STATUSES),
            )
        )
        if int(has_tt or 0) > 0:
            keep.append(order)
    return keep


def _tickets_sold_metrics(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
) -> tuple[int, Decimal, int]:
    ticket_q = select(Ticket).where(
        Ticket.event_id == event_id,
        Ticket.status.in_(OWNED_TICKET_STATUSES),
        Ticket.created_at >= filters.date_from,
        Ticket.created_at <= filters.date_to,
    )
    if filters.ticket_type_id is not None:
        ticket_q = ticket_q.where(Ticket.ticket_type_id == filters.ticket_type_id)
    tickets = list(db.scalars(ticket_q).all())
    tickets_sold = len(tickets)

    orders = _paid_orders(db, event_id=event_id, filters=filters)
    if filters.ticket_type_id is not None:
        revenue = Decimal("0")
        for ticket in tickets:
            tt = db.get(TicketType, ticket.ticket_type_id) if ticket.ticket_type_id else None
            revenue += _dec(tt.price) if tt else Decimal("0")
    else:
        revenue = sum((_dec(o.total_amount) for o in orders), Decimal("0"))

    check_ins = int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.event_id == event_id,
                Ticket.status.in_(ATTENDED_TICKET_STATUSES),
                *(
                    (Ticket.ticket_type_id == filters.ticket_type_id,)
                    if filters.ticket_type_id is not None
                    else ()
                ),
            )
        )
        or 0
    )
    return tickets_sold, revenue.quantize(Decimal("0.01")), check_ins


def _refund_metrics(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    purchases: int,
) -> tuple[int, Decimal | None]:
    refund_count = int(
        db.scalar(
            select(func.count())
            .select_from(Refund)
            .join(RefundRequest, RefundRequest.id == Refund.refund_request_id)
            .where(
                RefundRequest.event_id == event_id,
                Refund.created_at >= filters.date_from,
                Refund.created_at <= filters.date_to,
                Refund.status == "completed",
            )
        )
        or 0
    )
    return refund_count, _rate(refund_count, purchases)


def _review_metrics(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
) -> tuple[int, Decimal | None]:
    rows = list(
        db.scalars(
            select(VerifiedReview).where(
                VerifiedReview.event_id == event_id,
                VerifiedReview.status == "visible",
                VerifiedReview.created_at >= filters.date_from,
                VerifiedReview.created_at <= filters.date_to,
            )
        ).all()
    )
    if not rows:
        return 0, None
    avg = Decimal(sum(r.rating for r in rows)) / Decimal(len(rows))
    return len(rows), avg.quantize(Decimal("0.01"))


def build_event_overview(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")

    traffic_source = "live"
    rollup = None
    if _filters_support_daily_rollups(filters):
        rollup = _sum_event_daily_rollups(db, event_id=event_id, filters=filters)

    if rollup is not None:
        traffic_source = "rollup"
        impressions = rollup["impressions"]
        unique_impressions = rollup["unique_impressions"]
        card_clicks = rollup["card_clicks"]
        detail_views = rollup["detail_views"]
        unique_visitors = rollup["unique_detail_views"]
        ticket_selections = rollup["ticket_selections"]
        checkout_starts = rollup["checkout_starts"]
        purchases_stream = rollup["payment_successes"]
    else:
        impressions = _count_actions(
            db,
            event_id=event_id,
            host_id=host_id or event.host_id,
            filters=filters,
            actions=IMPRESSION_ACTIONS,
        )
        unique_impressions = len(
            _unique_visitors(
                _stream_rows(
                    db,
                    event_id=event_id,
                    host_id=host_id or event.host_id,
                    filters=filters,
                    actions=IMPRESSION_ACTIONS,
                )
            )
        )
        card_clicks = _count_actions(
            db,
            event_id=event_id,
            host_id=host_id or event.host_id,
            filters=filters,
            actions=CLICK_ACTIONS,
        )
        detail_rows = _stream_rows(
            db,
            event_id=event_id,
            host_id=host_id or event.host_id,
            filters=filters,
            actions=DETAIL_ACTIONS,
        )
        detail_views = len(detail_rows)
        unique_visitors = len(_unique_visitors(detail_rows))
        ticket_selections = _count_actions(
            db,
            event_id=event_id,
            host_id=host_id or event.host_id,
            filters=filters,
            actions=TICKET_SELECT_ACTIONS,
        )
        checkout_starts = _count_actions(
            db,
            event_id=event_id,
            host_id=host_id or event.host_id,
            filters=filters,
            actions=CHECKOUT_START_ACTIONS,
        )
        purchases_stream = _count_actions(
            db,
            event_id=event_id,
            host_id=host_id or event.host_id,
            filters=filters,
            actions=PURCHASE_ACTIONS,
        )

    orders = _paid_orders(db, event_id=event_id, filters=filters)
    purchases = max(purchases_stream, len(orders))
    tickets_sold, revenue, check_in_count = _tickets_sold_metrics(
        db, event_id=event_id, filters=filters
    )
    refund_count, refund_rate = _refund_metrics(
        db, event_id=event_id, filters=filters, purchases=purchases
    )
    review_count, average_rating = _review_metrics(
        db, event_id=event_id, filters=filters
    )
    aov = (
        (revenue / Decimal(purchases)).quantize(Decimal("0.01"))
        if purchases > 0
        else None
    )

    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "title": event.title,
        "filters": _filters_echo(filters),
        "impressions": impressions,
        "unique_impressions": unique_impressions,
        "event_card_clicks": card_clicks,
        "event_detail_views": detail_views,
        "unique_visitors": unique_visitors,
        "ticket_selections": ticket_selections,
        "checkout_starts": checkout_starts,
        "purchases": purchases,
        "tickets_sold": tickets_sold,
        "revenue": revenue,
        "conversion_rates": {
            "impression_to_click": _rate(card_clicks, impressions),
            "click_to_detail": _rate(detail_views, card_clicks),
            "detail_to_ticket_selection": _rate(ticket_selections, detail_views),
            "ticket_selection_to_checkout": _rate(checkout_starts, ticket_selections),
            "checkout_to_purchase": _rate(purchases, checkout_starts),
            "view_to_purchase": _rate(purchases, detail_views),
            "impression_to_purchase": _rate(purchases, impressions),
        },
        "average_order_value": aov,
        "refund_count": refund_count,
        "refund_rate": refund_rate,
        "check_in_count": check_in_count,
        "check_in_rate": _rate(check_in_count, tickets_sold),
        "review_count": review_count,
        "average_rating": average_rating,
        "traffic_source": traffic_source,
    }


def build_event_funnel(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")
    hid = host_id or event.host_id

    rollup = (
        _sum_event_daily_rollups(db, event_id=event_id, filters=filters)
        if _filters_support_daily_rollups(filters)
        else None
    )
    if rollup is not None:
        impressions = rollup["impressions"]
        card_clicks = rollup["card_clicks"]
        detail_views = rollup["detail_views"]
        ticket_selections = rollup["ticket_selections"]
        checkout_starts = rollup["checkout_starts"]
        payment_starts = rollup["payment_starts"]
        purchases_stream = rollup["payment_successes"]
        checkins_stream = rollup["checkins"]
        reviews_stream = rollup["reviews_submitted"]
    else:
        impressions = _count_actions(
            db, event_id=event_id, host_id=hid, filters=filters, actions=IMPRESSION_ACTIONS
        )
        card_clicks = _count_actions(
            db, event_id=event_id, host_id=hid, filters=filters, actions=CLICK_ACTIONS
        )
        detail_views = _count_actions(
            db, event_id=event_id, host_id=hid, filters=filters, actions=DETAIL_ACTIONS
        )
        ticket_selections = _count_actions(
            db,
            event_id=event_id,
            host_id=hid,
            filters=filters,
            actions=TICKET_SELECT_ACTIONS,
        )
        checkout_starts = _count_actions(
            db,
            event_id=event_id,
            host_id=hid,
            filters=filters,
            actions=CHECKOUT_START_ACTIONS,
        )
        payment_starts = _count_actions(
            db,
            event_id=event_id,
            host_id=hid,
            filters=filters,
            actions=PAYMENT_START_ACTIONS,
        )
        purchases_stream = _count_actions(
            db, event_id=event_id, host_id=hid, filters=filters, actions=PURCHASE_ACTIONS
        )
        checkins_stream = _count_actions(
            db, event_id=event_id, host_id=hid, filters=filters, actions=CHECKIN_ACTIONS
        )
        reviews_stream = _count_actions(
            db, event_id=event_id, host_id=hid, filters=filters, actions=REVIEW_ACTIONS
        )

    purchases = max(
        purchases_stream,
        len(_paid_orders(db, event_id=event_id, filters=filters)),
    )
    tickets_issued = max(
        _count_actions(
            db,
            event_id=event_id,
            host_id=hid,
            filters=filters,
            actions=TICKET_ISSUED_ACTIONS,
        )
        if rollup is None
        else purchases_stream,
        _tickets_sold_metrics(db, event_id=event_id, filters=filters)[0],
    )
    check_ins = max(
        checkins_stream,
        _tickets_sold_metrics(db, event_id=event_id, filters=filters)[2],
    )
    reviews = max(
        reviews_stream,
        _review_metrics(db, event_id=event_id, filters=filters)[0],
    )

    stages = [
        ("impressions", impressions),
        ("card_clicks", card_clicks),
        ("detail_views", detail_views),
        ("ticket_selections", ticket_selections),
        ("checkout_starts", checkout_starts),
        ("payment_starts", payment_starts),
        ("purchases", purchases),
        ("tickets_issued", tickets_issued),
        ("check_ins", check_ins),
        ("reviews", reviews),
    ]
    dropoffs: dict[str, int] = {}
    for i in range(len(stages) - 1):
        name_a, val_a = stages[i]
        name_b, val_b = stages[i + 1]
        dropoffs[f"{name_a}_to_{name_b}"] = max(0, val_a - val_b)

    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "filters": _filters_echo(filters),
        "impressions": impressions,
        "card_clicks": card_clicks,
        "detail_views": detail_views,
        "ticket_selections": ticket_selections,
        "checkout_starts": checkout_starts,
        "payment_starts": payment_starts,
        "purchases": purchases,
        "tickets_issued": tickets_issued,
        "check_ins": check_ins,
        "reviews": reviews,
        "dropoffs": dropoffs,
    }


def _choose_granularity(filters: EventAnalyticsFilters) -> str:
    span = filters.date_to - filters.date_from
    if span <= timedelta(days=2):
        return "hour"
    if span <= timedelta(days=90):
        return "day"
    return "week"


def _bucket_key(dt: datetime, granularity: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    if granularity == "hour":
        return dt.strftime("%Y-%m-%dT%H:00:00Z")
    if granularity == "week":
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return dt.strftime("%Y-%m-%d")


def build_event_timeseries(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")
    hid = host_id or event.host_id
    granularity = _choose_granularity(filters)

    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "impressions": 0,
            "views": 0,
            "checkout_starts": 0,
            "purchases": 0,
            "revenue": Decimal("0.00"),
        }
    )

    action_map = {
        **{a: "impressions" for a in IMPRESSION_ACTIONS},
        **{a: "views" for a in DETAIL_ACTIONS},
        **{a: "checkout_starts" for a in CHECKOUT_START_ACTIONS},
    }
    rows = _stream_rows(
        db,
        event_id=event_id,
        host_id=hid,
        filters=filters,
        actions=tuple(action_map.keys()),
    )
    for row in rows:
        ts = row.occurred_at or row.received_at
        if ts is None:
            continue
        key = _bucket_key(ts, granularity)
        metric = action_map.get(row.event_name)
        if metric:
            buckets[key][metric] += 1

    order_purchase_counts: dict[str, int] = defaultdict(int)
    for order in _paid_orders(db, event_id=event_id, filters=filters):
        if order.paid_at is None:
            continue
        key = _bucket_key(order.paid_at, granularity)
        order_purchase_counts[key] += 1
        buckets[key]["revenue"] += _dec(order.total_amount)
    for key, count in order_purchase_counts.items():
        buckets[key]["purchases"] = count

    points = [
        {
            "bucket": key,
            "impressions": vals["impressions"],
            "views": vals["views"],
            "checkout_starts": vals["checkout_starts"],
            "purchases": vals["purchases"],
            "revenue": vals["revenue"].quantize(Decimal("0.01")),
        }
        for key, vals in sorted(buckets.items())
    ]
    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "filters": _filters_echo(filters),
        "granularity": granularity,
        "points": points,
    }


def build_event_sources(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")
    hid = host_id or event.host_id

    bucket_names = [
        "direct",
        "social",
        "search",
        "referral",
        "ambassador",
        "email",
        "whatsapp",
        "paid",
        "unknown",
    ]
    buckets: dict[str, dict] = {
        name: {
            "source_bucket": name,
            "impressions": 0,
            "clicks": 0,
            "detail_views": 0,
            "checkout_starts": 0,
            "purchases": 0,
            "revenue": Decimal("0.00"),
        }
        for name in bucket_names
    }
    campaigns: dict[tuple[str | None, str | None, str | None], dict] = {}

    rows = _stream_rows(db, event_id=event_id, host_id=hid, filters=filters)
    for row in rows:
        src = row.utm_source or row.source
        med = row.utm_medium or row.medium
        camp = row.utm_campaign or row.campaign
        bucket = classify_traffic_source(source=src, medium=med, campaign=camp)
        if bucket not in buckets:
            bucket = "unknown"
        if row.event_name in IMPRESSION_ACTIONS:
            buckets[bucket]["impressions"] += 1
        elif row.event_name in CLICK_ACTIONS:
            buckets[bucket]["clicks"] += 1
        elif row.event_name in DETAIL_ACTIONS:
            buckets[bucket]["detail_views"] += 1
        elif row.event_name in CHECKOUT_START_ACTIONS:
            buckets[bucket]["checkout_starts"] += 1
        elif row.event_name in PURCHASE_ACTIONS:
            buckets[bucket]["purchases"] += 1

        key = (src, med, camp)
        if any([src, med, camp]):
            camp_row = campaigns.setdefault(
                key,
                {
                    "source": src,
                    "medium": med,
                    "campaign": camp,
                    "impressions": 0,
                    "clicks": 0,
                    "detail_views": 0,
                    "checkout_starts": 0,
                    "purchases": 0,
                },
            )
            if row.event_name in IMPRESSION_ACTIONS:
                camp_row["impressions"] += 1
            elif row.event_name in CLICK_ACTIONS:
                camp_row["clicks"] += 1
            elif row.event_name in DETAIL_ACTIONS:
                camp_row["detail_views"] += 1
            elif row.event_name in CHECKOUT_START_ACTIONS:
                camp_row["checkout_starts"] += 1
            elif row.event_name in PURCHASE_ACTIONS:
                camp_row["purchases"] += 1

    # Attribute paid order revenue to unknown when no stream purchase dims
    for order in _paid_orders(db, event_id=event_id, filters=filters):
        buckets["unknown"]["revenue"] += _dec(order.total_amount)

    utm_campaigns = sorted(
        campaigns.values(),
        key=lambda r: r["impressions"] + r["detail_views"] + r["purchases"],
        reverse=True,
    )[:100]

    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "filters": _filters_echo(filters),
        "buckets": list(buckets.values()),
        "utm_campaigns": utm_campaigns,
    }


def build_event_tickets(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")
    hid = host_id or event.host_id

    types = list(
        db.scalars(select(TicketType).where(TicketType.event_id == event_id)).all()
    )
    if filters.ticket_type_id is not None:
        types = [t for t in types if t.id == filters.ticket_type_id]

    impression_rows = _stream_rows(
        db,
        event_id=event_id,
        host_id=hid,
        filters=filters,
        actions=TICKET_IMPRESSION_ACTIONS,
    )
    selection_rows = _stream_rows(
        db,
        event_id=event_id,
        host_id=hid,
        filters=filters,
        actions=TICKET_SELECT_ACTIONS,
    )

    def _tt_id_from_meta(meta: dict | None) -> str | None:
        if not meta:
            return None
        raw = meta.get("ticket_type_id")
        return str(raw) if raw is not None else None

    rows_out: list[dict] = []
    for tt in types:
        tid = str(tt.id)
        impressions = sum(
            1
            for r in impression_rows
            if _tt_id_from_meta(r.event_metadata) == tid
            or _tt_id_from_meta(r.properties) == tid
        )
        selections = sum(
            1
            for r in selection_rows
            if _tt_id_from_meta(r.event_metadata) == tid
            or _tt_id_from_meta(r.properties) == tid
        )
        sold = int(
            db.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(
                    Ticket.event_id == event_id,
                    Ticket.ticket_type_id == tt.id,
                    Ticket.status.in_(OWNED_TICKET_STATUSES),
                    Ticket.created_at >= filters.date_from,
                    Ticket.created_at <= filters.date_to,
                )
            )
            or 0
        )
        revenue = (_dec(tt.price) * sold).quantize(Decimal("0.01"))
        remaining = max(0, int(tt.quantity) - int(tt.quantity_sold) - int(tt.quantity_reserved))
        inventory = int(tt.quantity) or 0
        rows_out.append(
            {
                "ticket_type_id": tt.id,
                "name": tt.name,
                "price": _dec(tt.price),
                "impressions": impressions,
                "selections": selections,
                "sold": sold,
                "revenue": revenue,
                "conversion_rate": _rate(sold, selections or impressions),
                "remaining_inventory": remaining,
                "sell_through_rate": _rate(int(tt.quantity_sold), inventory),
            }
        )

    rows_out.sort(key=lambda r: r["revenue"], reverse=True)
    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "filters": _filters_echo(filters),
        "ticket_types": rows_out,
    }


def build_event_audience(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")
    hid = host_id or event.host_id

    detail_rows = _stream_rows(
        db,
        event_id=event_id,
        host_id=hid,
        filters=filters,
        actions=DETAIL_ACTIONS,
    )
    purchase_rows = _stream_rows(
        db,
        event_id=event_id,
        host_id=hid,
        filters=filters,
        actions=PURCHASE_ACTIONS,
    )
    purchase_ids = _unique_visitors(purchase_rows)
    # Also include paid order buyers
    for order in _paid_orders(db, event_id=event_id, filters=filters):
        if order.buyer_user_id:
            purchase_ids.add(f"u:{order.buyer_user_id}")

    # Prior visits before range → returning
    prior_visitors: set[str] = set()
    prior = db.execute(
        select(
            AnalyticsEvent.user_id,
            AnalyticsEvent.anonymous_id,
            AnalyticsEvent.session_id,
        ).where(
            AnalyticsEvent.target_event_id == event_id,
            AnalyticsEvent.event_name.in_(DETAIL_ACTIONS),
            stream_time_column() < filters.date_from,
            *((AnalyticsEvent.is_bot.is_(False),) if not filters.include_bots else ()),
        )
    ).all()
    for u, a, s in prior:
        ident = visitor_identity(user_id=u, anonymous_id=a, session_id=s)
        if ident:
            prior_visitors.add(ident)

    def _bucket_map(getter) -> dict[str, dict]:
        acc: dict[str, dict] = {}
        for row in detail_rows:
            key = getter(row) or "unknown"
            ident = visitor_identity(
                user_id=row.user_id,
                anonymous_id=row.anonymous_id,
                session_id=row.session_id,
            )
            slot = acc.setdefault(
                key, {"key": key, "visitors": set(), "detail_views": 0, "purchases": set()}
            )
            slot["detail_views"] += 1
            if ident:
                slot["visitors"].add(ident)
                if ident in purchase_ids:
                    slot["purchases"].add(ident)
        return {
            k: {
                "key": v["key"],
                "visitors": len(v["visitors"]),
                "detail_views": v["detail_views"],
                "purchases": len(v["purchases"]),
            }
            for k, v in acc.items()
        }

    new_vs: dict[str, dict] = {
        "new": {"key": "new", "visitors": set(), "detail_views": 0, "purchases": set()},
        "returning": {
            "key": "returning",
            "visitors": set(),
            "detail_views": 0,
            "purchases": set(),
        },
    }
    auth: dict[str, dict] = {
        "logged_in": {
            "key": "logged_in",
            "visitors": set(),
            "detail_views": 0,
            "purchases": set(),
        },
        "anonymous": {
            "key": "anonymous",
            "visitors": set(),
            "detail_views": 0,
            "purchases": set(),
        },
    }
    for row in detail_rows:
        ident = visitor_identity(
            user_id=row.user_id,
            anonymous_id=row.anonymous_id,
            session_id=row.session_id,
        )
        cohort = "returning" if ident in prior_visitors else "new"
        new_vs[cohort]["detail_views"] += 1
        if ident:
            new_vs[cohort]["visitors"].add(ident)
            if ident in purchase_ids:
                new_vs[cohort]["purchases"].add(ident)
        auth_key = "logged_in" if row.user_id else "anonymous"
        auth[auth_key]["detail_views"] += 1
        if ident:
            auth[auth_key]["visitors"].add(ident)
            if ident in purchase_ids:
                auth[auth_key]["purchases"].add(ident)

    def _finalize(raw: dict[str, dict]) -> list[dict]:
        return [
            {
                "key": v["key"],
                "visitors": len(v["visitors"]) if isinstance(v["visitors"], set) else v["visitors"],
                "detail_views": v["detail_views"],
                "purchases": len(v["purchases"]) if isinstance(v["purchases"], set) else v["purchases"],
            }
            for v in raw.values()
        ]

    devices = sorted(
        _bucket_map(lambda r: (r.device_type or "unknown").lower()).values(),
        key=lambda r: r["visitors"],
        reverse=True,
    )
    cities = sorted(
        _bucket_map(lambda r: r.city or "unknown").values(),
        key=lambda r: r["visitors"],
        reverse=True,
    )[:50]
    countries = sorted(
        _bucket_map(lambda r: r.country or "unknown").values(),
        key=lambda r: r["visitors"],
        reverse=True,
    )[:50]
    browsers = sorted(
        _bucket_map(lambda r: r.browser or "unknown").values(),
        key=lambda r: r["visitors"],
        reverse=True,
    )[:50]

    # Follower conversion: buyers who follow the host
    buyer_user_ids = {
        o.buyer_user_id
        for o in _paid_orders(db, event_id=event_id, filters=filters)
        if o.buyer_user_id
    }
    follower_buyers = 0
    if buyer_user_ids:
        follower_buyers = int(
            db.scalar(
                select(func.count())
                .select_from(HostFollower)
                .where(
                    HostFollower.host_id == event.host_id,
                    HostFollower.user_id.in_(buyer_user_ids),
                )
            )
            or 0
        )
    follower_conversion = {
        "buyers": len(buyer_user_ids),
        "follower_buyers": follower_buyers,
        "rate": _rate(follower_buyers, len(buyer_user_ids)),
    }

    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "filters": _filters_echo(filters),
        "new_vs_returning": _finalize(new_vs),
        "auth_status": _finalize(auth),
        "devices": devices,
        "cities": cities,
        "countries": countries,
        "browsers": browsers,
        "follower_conversion": follower_conversion,
    }


def build_event_promos(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")

    promos = db.scalars(
        select(PromoCode).where(
            (PromoCode.event_id == event_id) | (PromoCode.host_id == event.host_id)
        )
    ).all()
    rows: list[dict] = []
    for promo in promos:
        redemptions = list(
            db.scalars(
                select(PromoRedemption).where(
                    PromoRedemption.promo_code_id == promo.id,
                    PromoRedemption.created_at >= filters.date_from,
                    PromoRedemption.created_at <= filters.date_to,
                    PromoRedemption.status == "redeemed",
                )
            ).all()
        )
        # Prefer event-scoped redemptions when order belongs to event
        event_redemptions = []
        for r in redemptions:
            if r.order_id is None:
                if promo.event_id == event_id:
                    event_redemptions.append(r)
                continue
            order = db.get(Order, r.order_id)
            if order and order.event_id == event_id:
                event_redemptions.append(r)
        if not event_redemptions:
            continue
        rows.append(
            {
                "promo_code_id": promo.id,
                "code": promo.code,
                "redemptions": len(event_redemptions),
                "discount_total": sum(
                    (_dec(r.discount_amount) for r in event_redemptions), Decimal("0")
                ),
                "orders": len({r.order_id for r in event_redemptions if r.order_id}),
            }
        )
    rows.sort(key=lambda r: r["redemptions"], reverse=True)
    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "filters": _filters_echo(filters),
        "promos": rows[:50],
    }


def build_event_ambassadors(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
    host_id: UUID | None = None,
) -> dict:
    event = _load_event(db, event_id)
    if host_id is not None and event.host_id != host_id:
        raise ValueError("Event not found")

    ambassadors = db.scalars(
        select(Ambassador).where(Ambassador.host_id == event.host_id)
    ).all()
    out: list[dict] = []
    for amb in ambassadors:
        clicks = int(
            db.scalar(
                select(func.count())
                .select_from(PromoClick)
                .where(
                    PromoClick.ambassador_id == amb.id,
                    PromoClick.event_id == event_id,
                    PromoClick.created_at >= filters.date_from,
                    PromoClick.created_at <= filters.date_to,
                )
            )
            or 0
        )
        sales = list(
            db.scalars(
                select(AmbassadorSale).where(
                    AmbassadorSale.ambassador_id == amb.id,
                    AmbassadorSale.event_id == event_id,
                    AmbassadorSale.created_at >= filters.date_from,
                    AmbassadorSale.created_at <= filters.date_to,
                )
            ).all()
        )
        if clicks == 0 and not sales:
            continue
        tickets = sum(s.tickets_sold for s in sales)
        revenue = sum((_dec(s.revenue_amount) for s in sales), Decimal("0"))
        commission = sum((_dec(s.commission_owed) for s in sales), Decimal("0"))
        out.append(
            {
                "ambassador_id": amb.id,
                "name": amb.display_name or amb.referral_code,
                "referral_code": amb.referral_code,
                "clicks": clicks,
                "tickets_sold": tickets,
                "revenue": revenue,
                "commission_owed": commission.quantize(Decimal("0.01")),
                "conversion_rate": _rate(len(sales), clicks),
            }
        )
    out.sort(key=lambda r: r["revenue"], reverse=True)
    return {
        "event_id": event.id,
        "host_id": event.host_id,
        "filters": _filters_echo(filters),
        "ambassadors": out[:50],
    }


def build_admin_event_bundle(
    db: Session,
    *,
    event_id: UUID,
    filters: EventAnalyticsFilters,
) -> dict:
    return {
        "overview": build_event_overview(db, event_id=event_id, filters=filters),
        "funnel": build_event_funnel(db, event_id=event_id, filters=filters),
        "sources": build_event_sources(db, event_id=event_id, filters=filters),
        "tickets": build_event_tickets(db, event_id=event_id, filters=filters),
    }


def build_admin_channel_performance(
    db: Session,
    *,
    filters: EventAnalyticsFilters,
) -> dict:
    """Platform-wide source/channel rollup from the analytics stream."""
    ts = stream_time_column()
    clauses = [
        ts >= filters.date_from,
        ts <= filters.date_to,
    ]
    if not filters.include_bots:
        clauses.append(AnalyticsEvent.is_bot.is_(False))
    if filters.source:
        clauses.append(
            (AnalyticsEvent.utm_source == filters.source)
            | (AnalyticsEvent.source == filters.source)
        )
    if filters.medium:
        clauses.append(
            (AnalyticsEvent.utm_medium == filters.medium)
            | (AnalyticsEvent.medium == filters.medium)
        )

    bucket_names = [
        "direct",
        "social",
        "search",
        "referral",
        "ambassador",
        "email",
        "whatsapp",
        "paid",
        "unknown",
    ]
    buckets: dict[str, dict] = {
        name: {
            "source_bucket": name,
            "impressions": 0,
            "clicks": 0,
            "detail_views": 0,
            "checkout_starts": 0,
            "purchases": 0,
        }
        for name in bucket_names
    }

    rows = list(db.scalars(select(AnalyticsEvent).where(*clauses)).all())
    for row in rows:
        src = row.utm_source or row.source
        med = row.utm_medium or row.medium
        camp = row.utm_campaign or row.campaign
        bucket = classify_traffic_source(source=src, medium=med, campaign=camp)
        if bucket not in buckets:
            bucket = "unknown"
        if row.event_name in IMPRESSION_ACTIONS:
            buckets[bucket]["impressions"] += 1
        elif row.event_name in CLICK_ACTIONS:
            buckets[bucket]["clicks"] += 1
        elif row.event_name in DETAIL_ACTIONS:
            buckets[bucket]["detail_views"] += 1
        elif row.event_name in CHECKOUT_START_ACTIONS:
            buckets[bucket]["checkout_starts"] += 1
        elif row.event_name in PURCHASE_ACTIONS:
            buckets[bucket]["purchases"] += 1

    out = [
        b
        for b in buckets.values()
        if b["impressions"] + b["clicks"] + b["detail_views"] + b["checkout_starts"] + b["purchases"]
        > 0
    ]
    out.sort(
        key=lambda r: r["impressions"] + r["detail_views"] + r["purchases"],
        reverse=True,
    )
    return {
        "filters": _filters_echo(filters),
        "buckets": out,
    }


def build_admin_event_leaderboard(
    db: Session,
    *,
    filters: EventAnalyticsFilters,
    sort_by: str = "revenue",
    limit: int = 50,
) -> dict:
    from app.hosts.models import Host

    events = list(
        db.scalars(
            select(Event).where(Event.status.in_(("published", "completed", "paused")))
        ).all()
    )
    rows: list[dict] = []
    for event in events:
        overview = build_event_overview(db, event_id=event.id, filters=filters)
        host = db.get(Host, event.host_id)
        rows.append(
            {
                "event_id": event.id,
                "host_id": event.host_id,
                "title": event.title,
                "host_display_name": host.display_name if host else None,
                "impressions": overview["impressions"],
                "detail_views": overview["event_detail_views"],
                "checkout_starts": overview["checkout_starts"],
                "purchases": overview["purchases"],
                "tickets_sold": overview["tickets_sold"],
                "revenue": overview["revenue"],
                "conversion_rate": overview["conversion_rates"]["view_to_purchase"],
            }
        )

    allowed = {
        "revenue",
        "tickets_sold",
        "purchases",
        "impressions",
        "detail_views",
        "checkout_starts",
        "conversion_rate",
    }
    key = sort_by if sort_by in allowed else "revenue"
    rows.sort(
        key=lambda r: (r.get(key) is not None, r.get(key) or 0),
        reverse=True,
    )
    return {
        "filters": _filters_echo(filters),
        "sort_by": key,
        "events": rows[:limit],
    }


def build_admin_event_compare(
    db: Session,
    *,
    event_ids: list[UUID],
    filters: EventAnalyticsFilters,
) -> dict:
    unique_ids = list(dict.fromkeys(event_ids))[:10]
    events = [
        build_event_overview(db, event_id=eid, filters=filters) for eid in unique_ids
    ]
    return {
        "filters": _filters_echo(filters),
        "events": events,
    }


def export_event_analytics_csv_rows(
    overview: dict,
    funnel: dict | None = None,
) -> tuple[list[str], list[list[object]]]:
    headers = ["metric", "value"]
    rows: list[list[object]] = [
        ["event_id", overview["event_id"]],
        ["host_id", overview["host_id"]],
        ["title", overview["title"]],
        ["date_from", overview["filters"]["date_from"]],
        ["date_to", overview["filters"]["date_to"]],
        ["impressions", overview["impressions"]],
        ["unique_impressions", overview["unique_impressions"]],
        ["event_card_clicks", overview["event_card_clicks"]],
        ["event_detail_views", overview["event_detail_views"]],
        ["unique_visitors", overview["unique_visitors"]],
        ["ticket_selections", overview["ticket_selections"]],
        ["checkout_starts", overview["checkout_starts"]],
        ["purchases", overview["purchases"]],
        ["tickets_sold", overview["tickets_sold"]],
        ["revenue", overview["revenue"]],
        ["average_order_value", overview["average_order_value"]],
        ["refund_count", overview["refund_count"]],
        ["refund_rate", overview["refund_rate"]],
        ["check_in_count", overview["check_in_count"]],
        ["check_in_rate", overview["check_in_rate"]],
        ["review_count", overview["review_count"]],
        ["average_rating", overview["average_rating"]],
    ]
    for k, v in overview["conversion_rates"].items():
        rows.append([f"conversion:{k}", v])
    if funnel:
        for key in (
            "payment_starts",
            "tickets_issued",
            "check_ins",
            "reviews",
        ):
            rows.append([f"funnel:{key}", funnel.get(key)])
    return headers, rows
