"""Recalculate analytics rollup tables from the append-only event stream.

Rollups are upserted and safe to re-run. Host/admin overview and funnel
prefer these daily tables when no dimension filters are applied; filtered
and specialized reports still use live SQL.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.analytics.rollup_models import (
    EventDailyAnalytics,
    EventGeoDeviceAnalytics,
    EventSourceAnalytics,
    EventTicketTypeAnalytics,
)
from app.analytics.taxonomy import TrackedAction
from app.events.models import Event

_NONE = "(none)"

_IMPRESSION_ACTIONS = frozenset(
    {
        TrackedAction.EVENT_CARD_IMPRESSION,
        TrackedAction.FEATURED_EVENT_IMPRESSION,
        TrackedAction.PADEYA_PICK_IMPRESSION,
        TrackedAction.FEATURED_PLACEMENT_IMPRESSION,
        TrackedAction.TICKET_TYPE_IMPRESSION,
    }
)
_CLICK_ACTIONS = frozenset(
    {
        TrackedAction.EVENT_CARD_CLICK,
        TrackedAction.FEATURED_EVENT_CLICK,
        TrackedAction.PADEYA_PICK_CLICK,
        TrackedAction.FEATURED_PLACEMENT_CLICK,
    }
)
_VIEW_ACTIONS = frozenset(
    {
        TrackedAction.EVENT_DETAIL_VIEW,
        TrackedAction.COUNTRY_PAGE_VIEW,
        TrackedAction.STATE_PAGE_VIEW,
        TrackedAction.CITY_PAGE_VIEW,
        TrackedAction.AREA_PAGE_VIEW,
    }
)
_CHECKOUT_START_ACTIONS = frozenset(
    {
        TrackedAction.CHECKOUT_START_CLICK,
        TrackedAction.CHECKOUT_PAGE_VIEW,
        TrackedAction.CHECKOUT_STEP_STARTED,
    }
)
_PAYMENT_START_ACTIONS = frozenset({TrackedAction.CHECKOUT_PAYMENT_STARTED})
_PAYMENT_SUCCESS_ACTIONS = frozenset(
    {TrackedAction.PAYMENT_SUCCESS, TrackedAction.TICKET_ISSUED}
)
_PAYMENT_FAIL_ACTIONS = frozenset({TrackedAction.PAYMENT_FAILED})


def _rate(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.000001"))


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


def _dim(value: str | None) -> str:
    cleaned = (value or "").strip()
    return cleaned[:160] if cleaned else _NONE


def _event_time_expr():
    return func.coalesce(AnalyticsEvent.occurred_at, AnalyticsEvent.received_at)


def recalculate_event_daily(
    db: Session,
    *,
    event_id: UUID,
    day: date,
    host_id: UUID | None = None,
) -> EventDailyAnalytics:
    """Rebuild one event×day rollup from analytics_events (+ commerce fields later)."""
    start, end = _day_bounds(day)
    t = _event_time_expr()

    if host_id is None:
        event = db.get(Event, event_id)
        host_id = event.host_id if event else None

    base = (
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.target_event_id == event_id,
            AnalyticsEvent.is_bot.is_(False),
            t >= start,
            t < end,
        )
    )
    rows = list(db.scalars(base))

    impressions = sum(1 for r in rows if r.event_name in _IMPRESSION_ACTIONS)
    card_clicks = sum(1 for r in rows if r.event_name in _CLICK_ACTIONS)
    detail_views = sum(1 for r in rows if r.event_name in _VIEW_ACTIONS)
    ticket_panel_views = sum(
        1 for r in rows if r.event_name == TrackedAction.TICKET_PANEL_VIEW
    )
    ticket_selections = sum(
        1 for r in rows if r.event_name == TrackedAction.TICKET_TYPE_SELECTED
    )
    checkout_starts = sum(1 for r in rows if r.event_name in _CHECKOUT_START_ACTIONS)
    payment_starts = sum(1 for r in rows if r.event_name in _PAYMENT_START_ACTIONS)
    payment_successes = sum(1 for r in rows if r.event_name in _PAYMENT_SUCCESS_ACTIONS)
    payment_failures = sum(1 for r in rows if r.event_name in _PAYMENT_FAIL_ACTIONS)
    shares = sum(1 for r in rows if r.event_name == TrackedAction.EVENT_SHARE_CLICK)
    saves = sum(1 for r in rows if r.event_name == TrackedAction.SAVE_EVENT_CLICK)
    follows = sum(
        1
        for r in rows
        if r.event_name
        in {
            TrackedAction.FOLLOW_HOST_CLICK_FROM_EVENT,
            TrackedAction.HOST_FOLLOWED_FROM_EVENT,
        }
    )
    reviews_submitted = sum(
        1 for r in rows if r.event_name == TrackedAction.REVIEW_SUBMITTED
    )
    checkins = sum(1 for r in rows if r.event_name == TrackedAction.CHECKIN_SUCCESS)
    promo_uses = sum(1 for r in rows if r.event_name == TrackedAction.PROMO_CODE_APPLIED)
    ambassador_sales = sum(
        1
        for r in rows
        if r.event_name in _PAYMENT_SUCCESS_ACTIONS
        and isinstance(r.event_metadata, dict)
        and r.event_metadata.get("ambassador_code")
    )

    unique_impressions = len(
        {
            (r.session_id or r.anonymous_id or str(r.id))
            for r in rows
            if r.event_name in _IMPRESSION_ACTIONS
        }
    )
    unique_detail_views = len(
        {
            (r.session_id or r.anonymous_id or str(r.id))
            for r in rows
            if r.event_name in _VIEW_ACTIONS
        }
    )

    tickets_sold = 0
    gross_revenue = Decimal("0")
    for r in rows:
        if r.event_name not in _PAYMENT_SUCCESS_ACTIONS:
            continue
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        qty = meta.get("quantity")
        if isinstance(qty, (int, float)):
            tickets_sold += int(qty)
        value = meta.get("conversion_value") or meta.get("amount")
        if value is not None:
            try:
                gross_revenue += Decimal(str(value))
            except Exception:
                pass

    existing = db.scalar(
        select(EventDailyAnalytics).where(
            EventDailyAnalytics.event_id == event_id,
            EventDailyAnalytics.date == day,
        )
    )
    now = datetime.now(UTC)
    row = existing or EventDailyAnalytics(
        id=uuid4(), date=day, event_id=event_id, host_id=host_id
    )
    row.host_id = host_id
    row.impressions = impressions
    row.unique_impressions = unique_impressions
    row.card_clicks = card_clicks
    row.detail_views = detail_views
    row.unique_detail_views = unique_detail_views
    row.ticket_panel_views = ticket_panel_views
    row.ticket_selections = ticket_selections
    row.checkout_starts = checkout_starts
    row.payment_starts = payment_starts
    row.payment_successes = payment_successes
    row.payment_failures = payment_failures
    row.tickets_sold = tickets_sold
    row.gross_revenue = gross_revenue
    row.promo_uses = promo_uses
    row.ambassador_sales = ambassador_sales
    row.shares = shares
    row.saves = saves
    row.follows = follows
    row.reviews_submitted = reviews_submitted
    row.checkins = checkins
    row.conversion_impression_to_view = _rate(detail_views, impressions)
    row.conversion_view_to_checkout = _rate(checkout_starts, detail_views)
    row.conversion_checkout_to_purchase = _rate(payment_successes, checkout_starts)
    row.conversion_view_to_purchase = _rate(payment_successes, detail_views)
    row.recalculated_at = now
    row.updated_at = now
    if existing is None:
        db.add(row)
    db.flush()
    return row


def recalculate_event_source_daily(
    db: Session, *, event_id: UUID, day: date
) -> list[EventSourceAnalytics]:
    start, end = _day_bounds(day)
    t = _event_time_expr()
    rows = list(
        db.scalars(
            select(AnalyticsEvent).where(
                AnalyticsEvent.target_event_id == event_id,
                AnalyticsEvent.is_bot.is_(False),
                t >= start,
                t < end,
            )
        )
    )
    buckets: dict[tuple[str, str, str], dict[str, Decimal | int]] = {}
    for r in rows:
        key = (_dim(r.utm_source or r.source), _dim(r.utm_medium or r.medium), _dim(r.utm_campaign or r.campaign))
        bucket = buckets.setdefault(
            key,
            {
                "impressions": 0,
                "clicks": 0,
                "views": 0,
                "checkout_starts": 0,
                "purchases": 0,
                "tickets_sold": 0,
                "revenue": Decimal("0"),
            },
        )
        if r.event_name in _IMPRESSION_ACTIONS:
            bucket["impressions"] = int(bucket["impressions"]) + 1
        if r.event_name in _CLICK_ACTIONS:
            bucket["clicks"] = int(bucket["clicks"]) + 1
        if r.event_name in _VIEW_ACTIONS:
            bucket["views"] = int(bucket["views"]) + 1
        if r.event_name in _CHECKOUT_START_ACTIONS:
            bucket["checkout_starts"] = int(bucket["checkout_starts"]) + 1
        if r.event_name in _PAYMENT_SUCCESS_ACTIONS:
            bucket["purchases"] = int(bucket["purchases"]) + 1
            meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
            qty = meta.get("quantity")
            if isinstance(qty, (int, float)):
                bucket["tickets_sold"] = int(bucket["tickets_sold"]) + int(qty)
            value = meta.get("conversion_value") or meta.get("amount")
            if value is not None:
                try:
                    bucket["revenue"] = Decimal(bucket["revenue"]) + Decimal(str(value))
                except Exception:
                    pass

    now = datetime.now(UTC)
    out: list[EventSourceAnalytics] = []
    for (source, medium, campaign), metrics in buckets.items():
        existing = db.scalar(
            select(EventSourceAnalytics).where(
                EventSourceAnalytics.event_id == event_id,
                EventSourceAnalytics.date == day,
                EventSourceAnalytics.source == source,
                EventSourceAnalytics.medium == medium,
                EventSourceAnalytics.campaign == campaign,
            )
        )
        row = existing or EventSourceAnalytics(
            id=uuid4(),
            date=day,
            event_id=event_id,
            source=source,
            medium=medium,
            campaign=campaign,
        )
        views = int(metrics["views"])
        purchases = int(metrics["purchases"])
        row.impressions = int(metrics["impressions"])
        row.clicks = int(metrics["clicks"])
        row.views = views
        row.checkout_starts = int(metrics["checkout_starts"])
        row.purchases = purchases
        row.tickets_sold = int(metrics["tickets_sold"])
        row.revenue = Decimal(metrics["revenue"])
        row.conversion_rate = _rate(purchases, views)
        row.recalculated_at = now
        row.updated_at = now
        if existing is None:
            db.add(row)
        out.append(row)
    db.flush()
    return out


def recalculate_event_geo_device_daily(
    db: Session, *, event_id: UUID, day: date
) -> list[EventGeoDeviceAnalytics]:
    start, end = _day_bounds(day)
    t = _event_time_expr()
    rows = list(
        db.scalars(
            select(AnalyticsEvent).where(
                AnalyticsEvent.target_event_id == event_id,
                AnalyticsEvent.is_bot.is_(False),
                t >= start,
                t < end,
            )
        )
    )
    buckets: dict[tuple[str, str, str, str], dict[str, Decimal | int]] = {}
    for r in rows:
        key = (
            _dim(r.country)[:64],
            _dim(r.city)[:96],
            _dim(r.device_type)[:32],
            _dim(r.browser)[:64],
        )
        bucket = buckets.setdefault(
            key,
            {
                "views": 0,
                "checkout_starts": 0,
                "purchases": 0,
                "tickets_sold": 0,
                "revenue": Decimal("0"),
            },
        )
        if r.event_name in _VIEW_ACTIONS:
            bucket["views"] = int(bucket["views"]) + 1
        if r.event_name in _CHECKOUT_START_ACTIONS:
            bucket["checkout_starts"] = int(bucket["checkout_starts"]) + 1
        if r.event_name in _PAYMENT_SUCCESS_ACTIONS:
            bucket["purchases"] = int(bucket["purchases"]) + 1
            meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
            qty = meta.get("quantity")
            if isinstance(qty, (int, float)):
                bucket["tickets_sold"] = int(bucket["tickets_sold"]) + int(qty)
            value = meta.get("conversion_value") or meta.get("amount")
            if value is not None:
                try:
                    bucket["revenue"] = Decimal(bucket["revenue"]) + Decimal(str(value))
                except Exception:
                    pass

    now = datetime.now(UTC)
    out: list[EventGeoDeviceAnalytics] = []
    for (country, city, device_type, browser), metrics in buckets.items():
        existing = db.scalar(
            select(EventGeoDeviceAnalytics).where(
                EventGeoDeviceAnalytics.event_id == event_id,
                EventGeoDeviceAnalytics.date == day,
                EventGeoDeviceAnalytics.country == country,
                EventGeoDeviceAnalytics.city == city,
                EventGeoDeviceAnalytics.device_type == device_type,
                EventGeoDeviceAnalytics.browser == browser,
            )
        )
        row = existing or EventGeoDeviceAnalytics(
            id=uuid4(),
            date=day,
            event_id=event_id,
            country=country,
            city=city,
            device_type=device_type,
            browser=browser,
        )
        row.views = int(metrics["views"])
        row.checkout_starts = int(metrics["checkout_starts"])
        row.purchases = int(metrics["purchases"])
        row.tickets_sold = int(metrics["tickets_sold"])
        row.revenue = Decimal(metrics["revenue"])
        row.recalculated_at = now
        row.updated_at = now
        if existing is None:
            db.add(row)
        out.append(row)
    db.flush()
    return out


def recalculate_event_ticket_type_daily(
    db: Session, *, event_id: UUID, day: date
) -> list[EventTicketTypeAnalytics]:
    """Rebuild ticket-type rollups from metadata.ticket_type_id on the stream."""
    start, end = _day_bounds(day)
    t = _event_time_expr()
    rows = list(
        db.scalars(
            select(AnalyticsEvent).where(
                AnalyticsEvent.target_event_id == event_id,
                AnalyticsEvent.is_bot.is_(False),
                t >= start,
                t < end,
            )
        )
    )
    buckets: dict[UUID, dict[str, Decimal | int]] = {}
    for r in rows:
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        raw_tt = meta.get("ticket_type_id")
        if not raw_tt:
            continue
        try:
            ticket_type_id = UUID(str(raw_tt))
        except (TypeError, ValueError):
            continue
        bucket = buckets.setdefault(
            ticket_type_id,
            {
                "impressions": 0,
                "selections": 0,
                "checkout_starts": 0,
                "tickets_sold": 0,
                "revenue": Decimal("0"),
            },
        )
        if r.event_name == TrackedAction.TICKET_TYPE_IMPRESSION:
            bucket["impressions"] = int(bucket["impressions"]) + 1
        if r.event_name == TrackedAction.TICKET_TYPE_SELECTED:
            bucket["selections"] = int(bucket["selections"]) + 1
        if r.event_name in _CHECKOUT_START_ACTIONS:
            bucket["checkout_starts"] = int(bucket["checkout_starts"]) + 1
        if r.event_name in _PAYMENT_SUCCESS_ACTIONS:
            qty = meta.get("quantity")
            if isinstance(qty, (int, float)):
                bucket["tickets_sold"] = int(bucket["tickets_sold"]) + int(qty)
            else:
                bucket["tickets_sold"] = int(bucket["tickets_sold"]) + 1
            value = meta.get("conversion_value") or meta.get("amount") or meta.get("ticket_price")
            if value is not None:
                try:
                    bucket["revenue"] = Decimal(bucket["revenue"]) + Decimal(str(value))
                except Exception:
                    pass

    now = datetime.now(UTC)
    out: list[EventTicketTypeAnalytics] = []
    for ticket_type_id, metrics in buckets.items():
        existing = db.scalar(
            select(EventTicketTypeAnalytics).where(
                EventTicketTypeAnalytics.event_id == event_id,
                EventTicketTypeAnalytics.date == day,
                EventTicketTypeAnalytics.ticket_type_id == ticket_type_id,
            )
        )
        row = existing or EventTicketTypeAnalytics(
            id=uuid4(),
            date=day,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
        )
        selections = int(metrics["selections"])
        sold = int(metrics["tickets_sold"])
        row.impressions = int(metrics["impressions"])
        row.selections = selections
        row.checkout_starts = int(metrics["checkout_starts"])
        row.tickets_sold = sold
        row.revenue = Decimal(metrics["revenue"])
        row.conversion_rate = _rate(sold, selections)
        row.recalculated_at = now
        row.updated_at = now
        if existing is None:
            db.add(row)
        out.append(row)
    db.flush()
    return out


def recalculate_all_for_event_day(
    db: Session, *, event_id: UUID, day: date
) -> dict[str, object]:
    """Recalculate every rollup slice for one event×day."""
    daily = recalculate_event_daily(db, event_id=event_id, day=day)
    sources = recalculate_event_source_daily(db, event_id=event_id, day=day)
    ticket_types = recalculate_event_ticket_type_daily(db, event_id=event_id, day=day)
    geo = recalculate_event_geo_device_daily(db, event_id=event_id, day=day)
    return {
        "daily": daily,
        "sources": sources,
        "ticket_types": ticket_types,
        "geo_device": geo,
    }


def iter_dates(date_from: date, date_to: date) -> list[date]:
    """Inclusive calendar days from ``date_from`` through ``date_to`` (UTC days)."""
    if date_to < date_from:
        raise ValueError("date_to must be on or after date_from")
    days: list[date] = []
    cursor = date_from
    while cursor <= date_to:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def resolve_rollup_window(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    last_days: int | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Resolve CLI/job window. Prefer ``last_days`` when set; else require both dates."""
    today = today or datetime.now(UTC).date()
    if last_days is not None:
        if last_days < 1:
            raise ValueError("last_days must be >= 1")
        end = today
        start = end - timedelta(days=last_days - 1)
        return start, end
    if date_from is None or date_to is None:
        raise ValueError("Provide last_days or both date_from and date_to")
    return date_from, date_to


def discover_event_ids_for_range(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    event_id: UUID | None = None,
) -> list[UUID]:
    """Product events that have non-bot analytics stream rows in the window."""
    start, _ = _day_bounds(date_from)
    _, end = _day_bounds(date_to)
    t = _event_time_expr()
    stmt = (
        select(AnalyticsEvent.target_event_id)
        .where(
            AnalyticsEvent.target_event_id.is_not(None),
            AnalyticsEvent.is_bot.is_(False),
            t >= start,
            t < end,
        )
        .distinct()
    )
    if event_id is not None:
        stmt = stmt.where(AnalyticsEvent.target_event_id == event_id)
    return [eid for eid in db.scalars(stmt).all() if eid is not None]


def recalculate_range(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    event_id: UUID | None = None,
    commit_every: int = 25,
) -> dict[str, int]:
    """Recalculate all rollup slices for every event×day with stream activity.

    Idempotent: each ``recalculate_*`` upserts existing rows. Safe to re-run.
    Commits periodically so long backfills do not hold one giant transaction.
    """
    days = iter_dates(date_from, date_to)
    event_ids = discover_event_ids_for_range(
        db, date_from=date_from, date_to=date_to, event_id=event_id
    )
    event_days = 0
    for eid in event_ids:
        for day in days:
            recalculate_all_for_event_day(db, event_id=eid, day=day)
            event_days += 1
            if commit_every > 0 and event_days % commit_every == 0:
                db.commit()
    db.commit()
    return {
        "events": len(event_ids),
        "days": len(days),
        "event_days": event_days,
    }


def run_rollups(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    last_days: int | None = None,
    event_id: UUID | None = None,
    commit_every: int = 25,
) -> dict[str, object]:
    """High-level entry used by the CLI and ops jobs."""
    start, end = resolve_rollup_window(
        date_from=date_from, date_to=date_to, last_days=last_days
    )
    stats = recalculate_range(
        db,
        date_from=start,
        date_to=end,
        event_id=event_id,
        commit_every=commit_every,
    )
    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "events": stats["events"],
        "days": stats["days"],
        "event_days": stats["event_days"],
        "event_id": str(event_id) if event_id else None,
    }
