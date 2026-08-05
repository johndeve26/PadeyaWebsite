"""Demo hosts for Legacy trust UI / Playwright archetypes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.demo.constants import DEMO_EMAIL_DOMAIN
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.legacy.models import HostLegacyScore, LegacyTier
from app.legacy.service import refresh_host_legacy_score
from app.payments.models import Order, OrderItem
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name, get_user_by_email


def _ensure_host(
    db: Session,
    *,
    slug: str,
    email: str,
    display_name: str,
) -> Host:
    existing = db.scalar(select(Host).where(Host.slug == slug))
    if existing is not None:
        return existing
    user = get_user_by_email(db, email)
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password("DemoPass123!"),
            full_name=display_name,
            is_active=True,
        )
        role = get_role_by_name(db, "host")
        assert role is not None
        user.roles.append(role)
        db.add(user)
        db.flush()
    host = Host(user_id=user.id, display_name=display_name, slug=slug, status="active")
    db.add(host)
    db.flush()
    if db.scalar(select(HostProfile).where(HostProfile.host_id == host.id)) is None:
        db.add(HostProfile(host_id=host.id, bio=f"Legacy trust demo — {display_name}"))
        db.flush()
    return host


def _make_buyer(db: Session, email: str, name: str) -> User:
    user = get_user_by_email(db, email)
    if user is not None:
        return user
    user = User(
        email=email,
        password_hash=hash_password("DemoPass123!"),
        full_name=name,
        is_active=True,
    )
    role = get_role_by_name(db, "buyer")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def _host_completed_events(db: Session, host_id) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.host_id == host_id, Event.status == "completed")
        )
        or 0
    )


def _host_ticket_count(db: Session, host_id) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .join(Event, Event.id == Ticket.event_id)
            .where(Event.host_id == host_id)
        )
        or 0
    )


def _clear_host_events(db: Session, host: Host, slug_prefix: str) -> None:
    """Remove prior demo events (and dependent rows) for a clean reseed."""
    events = list(
        db.scalars(
            select(Event).where(
                Event.host_id == host.id,
                Event.slug.like(f"{slug_prefix}-event-%"),
            )
        ).all()
    )
    if not events:
        return
    event_ids = [e.id for e in events]
    tickets = list(
        db.scalars(select(Ticket).where(Ticket.event_id.in_(event_ids))).all()
    )
    ticket_ids = [t.id for t in tickets]
    if ticket_ids:
        for review in db.scalars(
            select(VerifiedReview).where(VerifiedReview.ticket_id.in_(ticket_ids))
        ).all():
            db.delete(review)
    for ticket in tickets:
        db.delete(ticket)
    order_ids = [
        o.id
        for o in db.scalars(select(Order).where(Order.event_id.in_(event_ids))).all()
    ]
    if order_ids:
        for item in db.scalars(
            select(OrderItem).where(OrderItem.order_id.in_(order_ids))
        ).all():
            db.delete(item)
        for order in db.scalars(select(Order).where(Order.id.in_(order_ids))).all():
            db.delete(order)
    for tt in db.scalars(
        select(TicketType).where(TicketType.event_id.in_(event_ids))
    ).all():
        db.delete(tt)
    for event in events:
        db.delete(event)
    db.flush()


def _seed_host_activity(
    db: Session,
    host: Host,
    *,
    completed_events: int,
    tickets: int,
    checkins: int,
    reviews: int,
    slug_prefix: str,
) -> None:
    """Create verified orders/tickets/reviews so Legacy scoring uses real data."""
    if (
        _host_completed_events(db, host.id) >= completed_events
        and _host_ticket_count(db, host.id) >= tickets
    ):
        return

    _clear_host_events(db, host, slug_prefix)

    category = db.scalar(select(EventCategory).limit(1))
    ticket_rows: list[Ticket] = []

    for i in range(completed_events):
        start = datetime.now(UTC) - timedelta(days=30 + i)
        event = Event(
            title=f"{host.display_name} Event {i + 1}",
            slug=f"{slug_prefix}-event-{i + 1}",
            description="Demo completed event for Legacy trust showcase.",
            category_id=category.id if category else None,
            host_id=host.id,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            city="Lagos",
            status="completed",
            featured=False,
            published_at=start - timedelta(days=1),
        )
        db.add(event)
        db.flush()
        tt = TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("1000.00"),
            quantity=500,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
        db.add(tt)
        db.flush()

        per_event_tickets = tickets // completed_events + (
            tickets % completed_events if i == 0 else 0
        )
        per_event_checkins = checkins // completed_events + (
            checkins % completed_events if i == 0 else 0
        )
        for n in range(per_event_tickets):
            buyer = _make_buyer(
                db,
                f"{slug_prefix}-buyer-{i}-{n}@{DEMO_EMAIL_DOMAIN}",
                f"Buyer {i}-{n}",
            )
            order = Order(
                reference=f"PDY-{slug_prefix.upper()}-{i}-{n}",
                buyer_user_id=buyer.id,
                event_id=event.id,
                status="paid",
                currency="NGN",
                subtotal_amount=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
                buyer_email=buyer.email,
                buyer_name=buyer.full_name,
                paid_at=datetime.now(UTC),
            )
            db.add(order)
            item = OrderItem(
                order_id=order.id,
                ticket_type_id=tt.id,
                quantity=1,
                unit_price=Decimal("1000.00"),
                line_total=Decimal("1000.00"),
                ticket_type_name="GA",
            )
            db.add(item)
            db.flush()
            status = "checked_in" if n < per_event_checkins else "active"
            ticket = Ticket(
                public_code=new_public_ticket_code(),
                order_id=order.id,
                order_item_id=item.id,
                event_id=event.id,
                ticket_type_id=tt.id,
                buyer_user_id=buyer.id,
                status=status,
                ticket_type_name="GA",
                holder_name=buyer.full_name,
                holder_email=buyer.email,
                checked_in_at=datetime.now(UTC) if status == "checked_in" else None,
            )
            db.add(ticket)
            ticket_rows.append(ticket)
        db.flush()

    checked_in = [t for t in ticket_rows if t.status == "checked_in"]
    existing_reviews = int(
        db.scalar(
            select(func.count())
            .select_from(VerifiedReview)
            .where(VerifiedReview.host_id == host.id, VerifiedReview.status == "visible")
        )
        or 0
    )
    for idx, ticket in enumerate(checked_in[existing_reviews:reviews]):
        db.add(
            VerifiedReview(
                event_id=ticket.event_id,
                host_id=host.id,
                reviewer_user_id=ticket.buyer_user_id,
                ticket_id=ticket.id,
                rating=5,
                body="Verified review for Legacy trust demo.",
                status="visible",
            )
        )
    db.flush()


def _apply_manual_score(
    db: Session,
    host: Host,
    *,
    tier_slug: str,
    events_hosted: int,
    completed_events: int,
    tickets_sold: int,
    verified_checkins: int,
    review_count: int,
    average_verified_rating: Decimal | None,
    followers: int,
    composite_score: Decimal,
    legacy_status: str,
) -> None:
    """Pinned showcase scores for gate-blocked / top-tier archetypes (no rescore)."""
    score = db.scalar(select(HostLegacyScore).where(HostLegacyScore.host_id == host.id))
    if score is None:
        score = HostLegacyScore(host_id=host.id)
        db.add(score)
    tier = db.scalar(select(LegacyTier).where(LegacyTier.slug == tier_slug))
    score.tier_id = tier.id if tier else None
    score.events_hosted = events_hosted
    score.completed_events = completed_events
    score.tickets_sold = tickets_sold
    score.verified_checkins = verified_checkins
    score.review_count = review_count
    score.average_verified_rating = average_verified_rating
    score.followers = followers
    score.composite_score = composite_score
    score.legacy_status = legacy_status
    db.flush()


def seed_legacy_trust_showcase_hosts(db: Session) -> dict[str, str]:
    """Idempotent archetype hosts for Legacy trust Playwright flows."""
    out: dict[str, str] = {}

    empty = _ensure_host(
        db,
        slug="legacy-empty",
        email=f"legacy-empty@{DEMO_EMAIL_DOMAIN}",
        display_name="Legacy Empty Demo",
    )
    refresh_host_legacy_score(db, empty.id, reason="demo_seed")
    out["no_history"] = empty.slug

    provisional = _ensure_host(
        db,
        slug="legacy-provisional",
        email=f"legacy-provisional@{DEMO_EMAIL_DOMAIN}",
        display_name="Legacy Provisional Demo",
    )
    _apply_manual_score(
        db,
        provisional,
        tier_slug="rising",
        events_hosted=2,
        completed_events=2,
        tickets_sold=40,
        verified_checkins=20,
        review_count=1,
        average_verified_rating=Decimal("4.5"),
        followers=5,
        composite_score=Decimal("28.00"),
        legacy_status="Rising",
    )
    out["provisional"] = provisional.slug

    gated = _ensure_host(
        db,
        slug="legacy-gated",
        email=f"legacy-gated@{DEMO_EMAIL_DOMAIN}",
        display_name="Legacy Gated Demo",
    )
    _apply_manual_score(
        db,
        gated,
        tier_slug="rising",
        events_hosted=1,
        completed_events=1,
        tickets_sold=30,
        verified_checkins=15,
        review_count=2,
        average_verified_rating=Decimal("4.6"),
        followers=12,
        composite_score=Decimal("72.00"),
        legacy_status="Rising",
    )
    out["gate_blocked"] = gated.slug

    legend_host = _ensure_host(
        db,
        slug="legacy-legend",
        email=f"legacy-legend@{DEMO_EMAIL_DOMAIN}",
        display_name="Legacy Legend Demo",
    )
    _apply_manual_score(
        db,
        legend_host,
        tier_slug="legend",
        events_hosted=30,
        completed_events=30,
        tickets_sold=6000,
        verified_checkins=3000,
        review_count=80,
        average_verified_rating=Decimal("4.8"),
        followers=500,
        composite_score=Decimal("90.00"),
        legacy_status="Legend",
    )
    out["top_tier"] = legend_host.slug

    established = _ensure_host(
        db,
        slug="legacy-established",
        email=f"legacy-established@{DEMO_EMAIL_DOMAIN}",
        display_name="Legacy Established Demo",
    )
    # Pin stored score for Playwright reliability (remote DB). Authoritative
    # repeat/refund collectors are covered by unit tests with real orders.
    _apply_manual_score(
        db,
        established,
        tier_slug="established",
        events_hosted=4,
        completed_events=4,
        tickets_sold=200,
        verified_checkins=100,
        review_count=8,
        average_verified_rating=Decimal("4.3"),
        followers=120,
        composite_score=Decimal("51.00"),
        legacy_status="Established",
    )
    out["established"] = established.slug

    db.commit()
    return out
