"""Demo analytics seeder — 90 days of varied funnel traffic + rollups.

Writes raw ``AnalyticsEvent`` rows (unique sessions so dashboards look real),
keeps trusted commerce counts aligned with actual tickets/orders, then
recalculates daily rollups.
"""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.analytics.rollups import recalculate_all_for_event_day
from app.analytics.taxonomy import TrackedAction
from app.core.config import get_settings
from app.demo.models import DemoEntityMarker
from app.checkins.models import CheckIn
from app.events.models import Event, TicketType
from app.payments.models import Order
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket

MARKER_TYPE = "analytics_seed"
MARKER_KEY = "v2-90d"

# Event keys → host brand personality for dashboards.
EVENT_PROFILES: dict[str, dict[str, Any]] = {
    # DJ Maze — high impressions, high sales
    "afrobeats-night-live": {
        "label": "DJ Maze",
        "impressions": (22, 38),
        "click_rate": 0.24,
        "view_of_click": 0.85,
        "select_of_view": 0.45,
        "checkout_of_select": 0.70,
        "fail_of_checkout": 0.08,
        "share_of_view": 0.12,
        "save_of_view": 0.08,
        "follow_of_view": 0.06,
        "sources": [
            ("instagram", "social", 0.32),
            ("direct", "(none)", 0.18),
            ("whatsapp", "social", 0.12),
            ("x", "social", 0.10),
            ("google", "organic", 0.10),
            ("ambassador", "referral", 0.08),
            ("email", "email", 0.05),
            ("referral", "referral", 0.03),
            ("sponsor", "paid", 0.02),
        ],
        "campaigns": ["detty-december", "early-bird-drop", "influencer-tola"],
    },
    # Lagos Comedy Hub — moderate reach, strong conversion
    "lagos-comedy-jam": {
        "label": "Lagos Comedy Hub",
        "impressions": (12, 22),
        "click_rate": 0.28,
        "view_of_click": 0.90,
        "select_of_view": 0.55,
        "checkout_of_select": 0.78,
        "fail_of_checkout": 0.05,
        "share_of_view": 0.10,
        "save_of_view": 0.07,
        "follow_of_view": 0.05,
        "sources": [
            ("instagram", "social", 0.28),
            ("direct", "(none)", 0.22),
            ("whatsapp", "social", 0.14),
            ("google", "organic", 0.12),
            ("email", "email", 0.10),
            ("referral", "referral", 0.08),
            ("x", "social", 0.04),
            ("ambassador", "referral", 0.02),
        ],
        "campaigns": ["early-bird-drop", "campus-reps"],
    },
    # Mainland Vibes — high impressions, average conversion
    "mainland-vibes-summer": {
        "label": "Mainland Vibes",
        "impressions": (24, 40),
        "click_rate": 0.16,
        "view_of_click": 0.72,
        "select_of_view": 0.32,
        "checkout_of_select": 0.55,
        "fail_of_checkout": 0.12,
        "share_of_view": 0.09,
        "save_of_view": 0.05,
        "follow_of_view": 0.04,
        "sources": [
            ("instagram", "social", 0.35),
            ("direct", "(none)", 0.20),
            ("x", "social", 0.12),
            ("whatsapp", "social", 0.10),
            ("google", "organic", 0.08),
            ("referral", "referral", 0.07),
            ("sponsor", "paid", 0.05),
            ("email", "email", 0.03),
        ],
        "campaigns": ["detty-december", "whatsapp-broadcast"],
    },
    # Tech Connect — lower impressions, high free RSVP conversion
    "product-builders-meetup": {
        "label": "Tech Connect Africa",
        "impressions": (6, 14),
        "click_rate": 0.35,
        "view_of_click": 0.92,
        "select_of_view": 0.70,
        "checkout_of_select": 0.88,
        "fail_of_checkout": 0.02,
        "share_of_view": 0.08,
        "save_of_view": 0.10,
        "follow_of_view": 0.09,
        "sources": [
            ("direct", "(none)", 0.25),
            ("google", "organic", 0.22),
            ("email", "email", 0.18),
            ("x", "social", 0.12),
            ("ambassador", "referral", 0.08),
            ("referral", "referral", 0.08),
            ("instagram", "social", 0.05),
            ("sponsor", "paid", 0.02),
        ],
        "campaigns": ["campus-reps", "early-bird-drop"],
    },
    # Praise Experience — strong referral / WhatsApp
    "praise-experience-live": {
        "label": "Praise Experience",
        "impressions": (14, 26),
        "click_rate": 0.26,
        "view_of_click": 0.88,
        "select_of_view": 0.48,
        "checkout_of_select": 0.72,
        "fail_of_checkout": 0.06,
        "share_of_view": 0.18,
        "save_of_view": 0.09,
        "follow_of_view": 0.11,
        "sources": [
            ("whatsapp", "social", 0.34),
            ("referral", "referral", 0.18),
            ("ambassador", "referral", 0.14),
            ("instagram", "social", 0.12),
            ("direct", "(none)", 0.10),
            ("email", "email", 0.07),
            ("google", "organic", 0.03),
            ("x", "social", 0.02),
        ],
        "campaigns": ["whatsapp-broadcast", "campus-reps", "influencer-tola"],
    },
}

DEVICES = [
    ("mobile", 0.72),
    ("desktop", 0.22),
    ("tablet", 0.06),
]
BROWSERS = [
    ("Chrome", 0.45),
    ("Safari", 0.28),
    ("Instagram", 0.15),
    ("Firefox", 0.07),
    ("Samsung Internet", 0.05),
]
CITIES = [
    ("Lagos", "NG", 0.55),
    ("Abuja", "NG", 0.18),
    ("Ibadan", "NG", 0.12),
    ("Port Harcourt", "NG", 0.08),
    ("Accra", "GH", 0.07),
]


def _weighted(rng: random.Random, pairs: list[tuple[Any, ...]]) -> Any:
    """pairs are (value..., weight) with weight as last element."""
    weights = [p[-1] for p in pairs]
    idx = rng.choices(range(len(pairs)), weights=weights, k=1)[0]
    return pairs[idx][:-1]


def _already_seeded(db: Session) -> bool:
    return (
        db.scalar(
            select(DemoEntityMarker.id).where(
                DemoEntityMarker.entity_type == MARKER_TYPE,
                DemoEntityMarker.entity_key == MARKER_KEY,
            )
        )
        is not None
    )


def _mark_done(db: Session, *, events_seeded: int, rows: int) -> None:
    existing = db.scalar(
        select(DemoEntityMarker).where(
            DemoEntityMarker.entity_type == MARKER_TYPE,
            DemoEntityMarker.entity_key == MARKER_KEY,
        )
    )
    meta = {"events": events_seeded, "analytics_rows": rows, "version": 2}
    if existing is None:
        db.add(
            DemoEntityMarker(
                entity_type=MARKER_TYPE,
                entity_key=MARKER_KEY,
                meta=meta,
            )
        )
    else:
        existing.meta = meta


def _make_row(
    *,
    action: str,
    event: Event,
    occurred_at: datetime,
    rng: random.Random,
    source_tuple: tuple[str, str],
    campaign: str | None,
    ticket_type_id: UUID | None = None,
    user_id: UUID | None = None,
    is_bot: bool = False,
    extra_meta: dict[str, Any] | None = None,
) -> AnalyticsEvent:
    source, medium = source_tuple
    device = _weighted(rng, [(d, w) for d, w in DEVICES])[0]
    browser = _weighted(rng, [(b, w) for b, w in BROWSERS])[0]
    city, country = _weighted(rng, [(c, co, w) for c, co, w in CITIES])
    anon = f"demo-anon-{rng.randint(1, 50_000):05d}"
    session = f"demo-sess-{rng.randint(1, 80_000):05d}"
    meta: dict[str, Any] = {"seed": "demo_analytics_v2"}
    if ticket_type_id is not None:
        meta["ticket_type_id"] = str(ticket_type_id)
    if extra_meta:
        meta.update(extra_meta)

    ua = f"PadeyaDemo/{device}/{browser}"
    ua_hash = hashlib.sha256(ua.encode()).hexdigest()[:32]

    return AnalyticsEvent(
        id=uuid4(),
        event_name=action,
        target_event_id=event.id,
        host_id=event.host_id,
        user_id=user_id,
        anonymous_id=anon,
        session_id=session,
        occurred_at=occurred_at,
        received_at=occurred_at,
        source=source,
        medium=medium,
        campaign=campaign,
        utm_source=source,
        utm_medium=medium,
        utm_campaign=campaign,
        path=f"/events/{event.slug}",
        current_path=f"/events/{event.slug}",
        landing_page=f"/events/{event.slug}?utm_campaign={campaign or 'direct'}",
        referrer=(
            None
            if source == "direct"
            else f"https://{source}.example/{campaign or 'ref'}"
        ),
        user_agent=ua,
        user_agent_hash=ua_hash,
        device_type=device,
        browser=browser,
        os="iOS" if device == "mobile" and browser == "Safari" else "Android",
        country=country,
        city=city,
        event_metadata=meta,
        properties=meta,
        is_bot=is_bot,
        environment="demo",
    )


def _count_stream(db: Session, *, event_id: UUID, action: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.target_event_id == event_id,
                AnalyticsEvent.event_name == action,
            )
        )
        or 0
    )


def _align_trusted_to_commerce(db: Session, event: Event, rng: random.Random) -> int:
    """Ensure stream payment_success / ticket_issued do not exceed commerce truth.

    Backfills only when stream is *behind* actual tickets/orders (never exceeds).
    """
    added = 0
    tickets = int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(Ticket.event_id == event.id, Ticket.status.in_(("active", "checked_in")))
        )
        or 0
    )
    orders = list(
        db.scalars(
            select(Order).where(Order.event_id == event.id, Order.status == "paid")
        ).all()
    )
    purchases_stream = _count_stream(
        db, event_id=event.id, action=TrackedAction.PAYMENT_SUCCESS
    )
    issued_stream = _count_stream(
        db, event_id=event.id, action=TrackedAction.TICKET_ISSUED
    )

    # Align purchases to paid order count (not tickets).
    need_purchases = max(0, len(orders) - purchases_stream)
    for order in orders[:need_purchases]:
        when = order.paid_at or datetime.now(UTC)
        db.add(
            _make_row(
                action=TrackedAction.PAYMENT_SUCCESS,
                event=event,
                occurred_at=when,
                rng=rng,
                source_tuple=("direct", "(none)"),
                campaign=None,
                user_id=order.buyer_user_id,
                extra_meta={
                    "order_id": str(order.id),
                    "aligned_to_commerce": True,
                },
            )
        )
        added += 1

    need_issued = max(0, tickets - issued_stream)
    # Cap issued backfill at ticket count; stamp synthetic only if no order link.
    for i in range(need_issued):
        order = orders[i % len(orders)] if orders else None
        when = (order.paid_at if order else None) or datetime.now(UTC)
        db.add(
            _make_row(
                action=TrackedAction.TICKET_ISSUED,
                event=event,
                occurred_at=when,
                rng=rng,
                source_tuple=("direct", "(none)"),
                campaign=None,
                user_id=order.buyer_user_id if order else None,
                extra_meta={
                    "order_id": str(order.id) if order else None,
                    "aligned_to_commerce": True,
                },
            )
        )
        added += 1

    # Check-ins / reviews: backfill stream up to commerce truth only (never exceed).
    checkins = int(
        db.scalar(
            select(func.count())
            .select_from(CheckIn)
            .where(CheckIn.event_id == event.id, CheckIn.outcome == "success")
        )
        or 0
    )
    reviews = int(
        db.scalar(
            select(func.count())
            .select_from(VerifiedReview)
            .where(VerifiedReview.event_id == event.id)
        )
        or 0
    )
    checkin_stream = _count_stream(
        db, event_id=event.id, action=TrackedAction.CHECKIN_SUCCESS
    )
    review_stream = _count_stream(
        db, event_id=event.id, action=TrackedAction.REVIEW_SUBMITTED
    )
    for _ in range(max(0, checkins - checkin_stream)):
        db.add(
            _make_row(
                action=TrackedAction.CHECKIN_SUCCESS,
                event=event,
                occurred_at=datetime.now(UTC) - timedelta(days=rng.randint(1, 20)),
                rng=rng,
                source_tuple=("direct", "(none)"),
                campaign=None,
                extra_meta={"aligned_to_commerce": True},
            )
        )
        added += 1
    for _ in range(max(0, reviews - review_stream)):
        db.add(
            _make_row(
                action=TrackedAction.REVIEW_SUBMITTED,
                event=event,
                occurred_at=datetime.now(UTC) - timedelta(days=rng.randint(1, 30)),
                rng=rng,
                source_tuple=("direct", "(none)"),
                campaign=None,
                extra_meta={"aligned_to_commerce": True},
            )
        )
        added += 1
    return added


def seed_event_analytics_traffic(
    db: Session,
    *,
    events: dict[str, Event],
) -> dict[str, int]:
    """Seed 90 days of client funnel analytics + rollups for named demo events."""
    if _already_seeded(db):
        return {"skipped": 1, "rows": 0, "events": 0}

    settings = get_settings()
    compact = settings.app_env in {"test", "testing"}
    day_step = 2 if compact else 1
    scale = 0.45 if compact else 1.0

    now = datetime.now(UTC)
    start_day = (now - timedelta(days=89)).date()
    rng = random.Random(20260717)
    buffer: list[AnalyticsEvent] = []
    rows_written = 0
    events_touched = 0
    days_for_rollup: dict[UUID, set[date]] = {}

    for key, profile in EVENT_PROFILES.items():
        event = events.get(key)
        if event is None:
            continue
        events_touched += 1
        ticket_types = list(
            db.scalars(select(TicketType).where(TicketType.event_id == event.id)).all()
        )
        source_weights = profile["sources"]
        campaigns: list[str] = profile["campaigns"]

        day = start_day
        while day <= now.date():
            # Weekend bump
            weekend = 1.25 if day.weekday() >= 5 else 1.0
            lo, hi = profile["impressions"]
            impressions = max(
                1, int(rng.randint(lo, hi) * scale * weekend)
            )
            clicks = max(0, int(impressions * profile["click_rate"]))
            views = max(0, int(clicks * profile["view_of_click"]))
            selections = max(0, int(views * profile["select_of_view"]))
            checkouts = max(0, int(selections * profile["checkout_of_select"]))
            failures = max(0, int(checkouts * profile["fail_of_checkout"]))
            shares = max(0, int(views * profile["share_of_view"]))
            saves = max(0, int(views * profile["save_of_view"]))
            follows = max(0, int(views * profile["follow_of_view"]))

            campaign = campaigns[day.toordinal() % len(campaigns)]
            base_hour = datetime(day.year, day.month, day.day, tzinfo=UTC)

            def _emit(action: str, count: int, **kwargs: Any) -> None:
                nonlocal rows_written
                for i in range(count):
                    src = _weighted(rng, source_weights)
                    occurred = base_hour + timedelta(
                        hours=rng.randint(8, 22),
                        minutes=rng.randint(0, 59),
                        seconds=rng.randint(0, 59),
                    )
                    # ~2% bots for realism (excluded from host dashboards by default)
                    is_bot = rng.random() < 0.02
                    tt_id = None
                    if action in {
                        TrackedAction.TICKET_TYPE_SELECTED,
                        TrackedAction.TICKET_TYPE_IMPRESSION,
                    } and ticket_types:
                        tt_id = ticket_types[i % len(ticket_types)].id
                    buffer.append(
                        _make_row(
                            action=action,
                            event=event,
                            occurred_at=occurred,
                            rng=rng,
                            source_tuple=(src[0], src[1]),
                            campaign=campaign,
                            ticket_type_id=tt_id,
                            is_bot=is_bot,
                            **kwargs,
                        )
                    )
                    rows_written += 1
                    if len(buffer) >= 200:
                        db.add_all(buffer)
                        db.flush()
                        buffer.clear()

            _emit(TrackedAction.EVENT_CARD_IMPRESSION, impressions)
            _emit(TrackedAction.EVENT_CARD_CLICK, clicks)
            _emit(TrackedAction.EVENT_DETAIL_VIEW, views)
            # Ticket panel + type impressions for detail traffic
            _emit(TrackedAction.TICKET_PANEL_VIEW, max(0, views // 2))
            _emit(TrackedAction.TICKET_TYPE_IMPRESSION, max(0, views // 2))
            _emit(TrackedAction.TICKET_TYPE_SELECTED, selections)
            # One checkout signal per intent (both actions count toward funnel starts).
            _emit(TrackedAction.CHECKOUT_PAGE_VIEW, checkouts)
            _emit(TrackedAction.CHECKOUT_PAYMENT_STARTED, max(0, checkouts - failures))
            _emit(TrackedAction.PAYMENT_FAILED, failures)
            _emit(TrackedAction.EVENT_SHARE_CLICK, shares)
            _emit(TrackedAction.SAVE_EVENT_CLICK, saves)
            _emit(TrackedAction.FOLLOW_HOST_CLICK_FROM_EVENT, follows)

            days_for_rollup.setdefault(event.id, set()).add(day)
            day += timedelta(days=day_step)

        # Align trusted commerce signals to actual tickets/orders (never exceed).
        rows_written += _align_trusted_to_commerce(db, event, rng)

    if buffer:
        db.add_all(buffer)
        db.flush()
        buffer.clear()
    db.commit()

    # Rollups from raw stream
    rollup_days = 0
    for event_id, days in days_for_rollup.items():
        for day in sorted(days):
            recalculate_all_for_event_day(db, event_id=event_id, day=day)
            rollup_days += 1
            if rollup_days % 25 == 0:
                db.commit()
    db.commit()

    _mark_done(db, events_seeded=events_touched, rows=rows_written)
    db.commit()
    return {
        "skipped": 0,
        "rows": rows_written,
        "events": events_touched,
        "rollup_days": rollup_days,
    }
