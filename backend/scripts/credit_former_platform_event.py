"""Credit former-platform ticket sales + ratings onto a migrated event.

Used for events that sold on the previous Pàdéyá server and were recreated
without ticket/review rows on the new stack.

  cd backend
  DATABASE_URL=... PYTHONPATH=. python scripts/credit_former_platform_event.py \\
    --host rhazzy --event-slug with-the-geng --tickets 120 --reviews 5 --rating 5

Idempotent: skips when the marker order reference already exists.
"""

from __future__ import annotations

import argparse
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host
from app.legacy.service import refresh_host_legacy_score
from app.payments.models import Order, OrderItem
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name, get_user_by_email

# Register ORM relationship targets before Session use (same set as seed_demo_data).
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.hosts import models as host_models  # noqa: F401
from app.events import models as event_models  # noqa: F401
from app.payments import models as payment_models  # noqa: F401
from app.tickets import models as ticket_models  # noqa: F401
from app.checkins import models as checkin_models  # noqa: F401
from app.reviews import models as review_models  # noqa: F401
from app.legacy import models as legacy_models  # noqa: F401
from app.promos import models as promo_models  # noqa: F401
from app.crm import models as crm_models  # noqa: F401
from app.finance import models as finance_models  # noqa: F401
from app.vault import models as vault_models  # noqa: F401
from app.passport import models as passport_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401
from app.memories import models as memories_models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.ai import models as ai_models  # noqa: F401
from app.sponsorships import models as sponsorships_models  # noqa: F401
from app.tickets import advanced_models as ticket_advanced_models  # noqa: F401
from app.demo import models as demo_models  # noqa: F401
from app.taxonomy import models as taxonomy_models  # noqa: F401
from app.placements import models as placements_models  # noqa: F401

MARKER_PREFIX = "PDY-FM"


def _marker_ref(event_slug: str) -> str:
    slug = event_slug.replace("-", "").upper()[:12]
    return f"{MARKER_PREFIX}-{slug}"


def _ensure_buyer(db, *, email: str, name: str) -> User:
    user = get_user_by_email(db, email)
    if user is not None:
        return user
    user = User(
        email=email,
        password_hash=hash_password(secrets.token_urlsafe(24)),
        full_name=name,
        is_active=True,
    )
    role = get_role_by_name(db, "buyer")
    if role is not None:
        user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def credit_event(
    db,
    *,
    host_slug: str,
    event_slug: str,
    tickets: int,
    reviews: int,
    rating: int,
    dry_run: bool,
) -> dict:
    host = db.scalar(select(Host).where(Host.slug == host_slug.lower()))
    if host is None:
        raise SystemExit(f"Host not found: {host_slug}")

    event = db.scalar(
        select(Event).where(
            Event.host_id == host.id,
            Event.slug == event_slug.lower(),
        )
    )
    if event is None:
        raise SystemExit(f"Event not found for @{host_slug}: {event_slug}")

    marker = _marker_ref(event_slug)
    existing = db.scalar(select(Order).where(Order.reference == marker))
    if existing is not None:
        score = refresh_host_legacy_score(db, host.id, reason="former_platform_credit_refresh")
        db.commit()
        return {
            "status": "already_credited",
            "marker": marker,
            "tickets_sold": score.tickets_sold,
            "review_count": score.review_count,
            "average_verified_rating": (
                float(score.average_verified_rating)
                if score.average_verified_rating is not None
                else None
            ),
            "composite_score": float(score.composite_score),
        }

    types = list(
        db.scalars(
            select(TicketType)
            .where(TicketType.event_id == event.id)
            .order_by(TicketType.price.asc())
        )
    )
    if not types:
        raise SystemExit("Event has no ticket types")

    # Prefer cheapest tiers first (Early Bird → Regular …)
    remaining = tickets
    allotments: list[tuple[TicketType, int]] = []
    for tt in types:
        if remaining <= 0:
            break
        # Raise inventory if former-server sales exceed current cap.
        capacity = max(int(tt.quantity or 0), remaining if tt is types[-1] else int(tt.quantity or 0))
        take = min(remaining, capacity if tt is not types[-1] else remaining)
        if take <= 0:
            continue
        if int(tt.quantity or 0) < int(tt.quantity_sold or 0) + take:
            tt.quantity = int(tt.quantity_sold or 0) + take
        allotments.append((tt, take))
        remaining -= take

    if remaining > 0:
        # Dump leftover onto last type and expand inventory.
        last, n = allotments[-1] if allotments else (types[-1], 0)
        if allotments:
            allotments[-1] = (last, n + remaining)
        else:
            allotments.append((last, remaining))
        last.quantity = max(int(last.quantity or 0), int(last.quantity_sold or 0) + n + remaining)
        remaining = 0

    unit_total = sum(
        (Decimal(str(tt.price)) * Decimal(n) for tt, n in allotments),
        Decimal("0.00"),
    )
    paid_at = (event.end_datetime or event.start_datetime or datetime.now(UTC)) - timedelta(
        hours=6
    )
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=UTC)

    if dry_run:
        return {
            "status": "dry_run",
            "marker": marker,
            "host": host.slug,
            "event": event.slug,
            "tickets": tickets,
            "reviews": reviews,
            "rating": rating,
            "allotments": [(tt.name, n, str(tt.price)) for tt, n in allotments],
            "order_total": str(unit_total),
        }

    order = Order(
        reference=marker,
        buyer_user_id=None,
        event_id=event.id,
        host_id=host.id,
        status="paid",
        currency="NGN",
        subtotal_amount=unit_total,
        total_amount=unit_total,
        buyer_email=f"former-platform+{event.slug}@padeya.internal",
        buyer_name="Former platform sales credit",
        paid_at=paid_at,
        host_net_estimate=Decimal("0.00"),
        platform_revenue_total=Decimal("0.00"),
    )
    db.add(order)
    db.flush()

    issued: list[Ticket] = []
    for tt, count in allotments:
        item = OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_id=tt.id,
            quantity=count,
            unit_price=Decimal(str(tt.price)),
            line_total=Decimal(str(tt.price)) * count,
            ticket_type_name=tt.name,
        )
        db.add(item)
        db.flush()
        tt.quantity_sold = int(tt.quantity_sold or 0) + count
        for i in range(count):
            # First `reviews` tickets are checked_in so they can carry verified ratings.
            status = "checked_in" if len(issued) < reviews else "active"
            ticket = Ticket(
                public_code=new_public_ticket_code(),
                order_id=order.id,
                order_item_id=item.id,
                event_id=event.id,
                ticket_type_id=tt.id,
                buyer_user_id=None,
                status=status,
                ticket_type_name=tt.name,
                holder_name=f"Former attendee {len(issued) + 1}",
                holder_email=f"former-{event.slug}-{len(issued) + 1}@padeya.internal",
                checked_in_at=paid_at + timedelta(hours=8) if status == "checked_in" else None,
            )
            db.add(ticket)
            db.flush()
            issued.append(ticket)

    # Attach reviewer accounts to the checked-in tickets and leave 5★ reviews.
    review_tickets = [t for t in issued if t.status == "checked_in"][:reviews]
    for idx, ticket in enumerate(review_tickets):
        buyer = _ensure_buyer(
            db,
            email=f"former-reviewer-{event.slug}-{idx + 1}@padeya.internal",
            name=f"Former reviewer {idx + 1}",
        )
        ticket.buyer_user_id = buyer.id
        ticket.holder_name = buyer.full_name or ticket.holder_name
        ticket.holder_email = buyer.email
        existing_review = db.scalar(
            select(VerifiedReview).where(VerifiedReview.ticket_id == ticket.id)
        )
        if existing_review is None:
            db.add(
                VerifiedReview(
                    event_id=event.id,
                    host_id=host.id,
                    reviewer_user_id=buyer.id,
                    ticket_id=ticket.id,
                    rating=rating,
                    title=None,
                    body="Credited from former Pàdéyá platform history.",
                    status="visible",
                )
            )

    db.flush()
    score = refresh_host_legacy_score(
        db, host.id, reason="former_platform_credit", force_history=True
    )
    db.commit()
    return {
        "status": "credited",
        "marker": marker,
        "tickets_created": len(issued),
        "reviews_created": len(review_tickets),
        "tickets_sold": score.tickets_sold,
        "verified_checkins": score.verified_checkins,
        "review_count": score.review_count,
        "average_verified_rating": (
            float(score.average_verified_rating)
            if score.average_verified_rating is not None
            else None
        ),
        "composite_score": float(score.composite_score),
        "legacy_status": score.legacy_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--event-slug", required=True)
    parser.add_argument("--tickets", type=int, default=120)
    parser.add_argument("--reviews", type=int, default=5)
    parser.add_argument("--rating", type=int, default=5, choices=range(1, 6))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.reviews > args.tickets:
        raise SystemExit("--reviews cannot exceed --tickets")

    db = SessionLocal()
    try:
        result = credit_event(
            db,
            host_slug=args.host,
            event_slug=args.event_slug,
            tickets=args.tickets,
            reviews=args.reviews,
            rating=args.rating,
            dry_run=args.dry_run,
        )
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
