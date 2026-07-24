"""Deterministic Fan Passport badge evaluation."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.passport.constants import (
    ATTENDED_TICKET_STATUSES,
    CATEGORY_BADGE_THRESHOLD,
    EVENT_HOPPER_THRESHOLD,
    OWNED_TICKET_STATUSES,
    SUPERFAN_CHECKIN_THRESHOLD,
    VIP_REGULAR_THRESHOLD,
)
from app.passport.merch_proof import evaluate_merch_badge_flags
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.vault.models import VaultPurchase


def _owned_tickets(db: Session, user_id: UUID) -> list[Ticket]:
    return list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user_id,
                Ticket.status.in_(OWNED_TICKET_STATUSES),
            )
        )
    )


def _attended_tickets(db: Session, user_id: UUID) -> list[Ticket]:
    return list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user_id,
                Ticket.status.in_(ATTENDED_TICKET_STATUSES),
            )
        )
    )


def evaluate_badge_criteria(db: Session, user_id: UUID) -> dict[str, bool]:
    """Return criteria_key → whether earned. Pure / deterministic."""
    owned = _owned_tickets(db, user_id)
    attended = _attended_tickets(db, user_id)

    ticket_type_ids = {t.ticket_type_id for t in owned}
    types_by_id: dict[UUID, TicketType] = {}
    if ticket_type_ids:
        for tt in db.scalars(select(TicketType).where(TicketType.id.in_(ticket_type_ids))):
            types_by_id[tt.id] = tt

    event_ids = {t.event_id for t in owned} | {t.event_id for t in attended}
    events_by_id: dict[UUID, Event] = {}
    if event_ids:
        for ev in db.scalars(select(Event).where(Event.id.in_(event_ids))):
            events_by_id[ev.id] = ev

    category_ids = {e.category_id for e in events_by_id.values() if e.category_id}
    categories_by_id: dict[UUID, EventCategory] = {}
    if category_ids:
        for cat in db.scalars(select(EventCategory).where(EventCategory.id.in_(category_ids))):
            categories_by_id[cat.id] = cat

    followed_host_ids = {
        r.host_id
        for r in db.scalars(select(HostFollower).where(HostFollower.user_id == user_id))
    }

    vip_count = 0
    for t in owned:
        tt = types_by_id.get(t.ticket_type_id)
        if tt and tt.type in {"vip", "vvip"}:
            vip_count += 1

    checkins_by_host: dict[UUID, set[UUID]] = defaultdict(set)
    for t in attended:
        ev = events_by_id.get(t.event_id)
        if ev:
            checkins_by_host[ev.host_id].add(t.event_id)

    max_host_checkins = max((len(s) for s in checkins_by_host.values()), default=0)

    day_one = False
    for t in attended:
        ev = events_by_id.get(t.event_id)
        if ev and ev.host_id in followed_host_ids:
            day_one = True
            break

    attended_event_ids = {t.event_id for t in attended}

    nightlife = 0
    music = 0
    comedy = 0
    tech = 0
    campus = 0
    lagos = 0
    for eid in attended_event_ids:
        ev = events_by_id.get(eid)
        if not ev:
            continue
        if (ev.city or "").strip().lower() == "lagos":
            lagos += 1
        if not ev.category_id:
            continue
        cat = categories_by_id.get(ev.category_id)
        if not cat:
            continue
        if cat.slug == "nightlife":
            nightlife += 1
        if cat.slug == "music":
            music += 1
        if cat.slug == "comedy":
            comedy += 1
        if cat.slug in {"tech", "business"}:
            tech += 1
        if cat.slug == "campus":
            campus += 1

    has_early_bird = any(
        (types_by_id.get(t.ticket_type_id) and types_by_id[t.ticket_type_id].type == "early_bird")
        for t in owned
    )
    has_table = any(
        (types_by_id.get(t.ticket_type_id) and types_by_id[t.ticket_type_id].type == "table")
        for t in owned
    )

    vault_paid = db.scalar(
        select(VaultPurchase.id).where(
            VaultPurchase.user_id == user_id,
            VaultPurchase.status == "paid",
        ).limit(1)
    )
    reviews_n = int(
        db.scalar(
            select(func.count())
            .select_from(VerifiedReview)
            .where(
                VerifiedReview.reviewer_user_id == user_id,
                VerifiedReview.status.in_(["visible", "hidden", "flagged"]),
            )
        )
        or 0
    )

    # Merch badges — paid (non-cancelled) fulfillments only; never spend amounts.
    merch_flags = evaluate_merch_badge_flags(db, user_id)

    return {
        "first_ticket": len(owned) >= 1,
        "verified_attendee": len(attended) >= 1,
        "checked_in_attendee": len(attended) >= 1,
        "day_one_fan": day_one,
        "vip_regular": vip_count >= VIP_REGULAR_THRESHOLD,
        "superfan": max_host_checkins >= SUPERFAN_CHECKIN_THRESHOLD,
        "early_bird": has_early_bird,
        "nightlife_explorer": nightlife >= CATEGORY_BADGE_THRESHOLD,
        "concert_lover": music >= CATEGORY_BADGE_THRESHOLD,
        "comedy_fan": comedy >= CATEGORY_BADGE_THRESHOLD,
        "tech_regular": tech >= CATEGORY_BADGE_THRESHOLD,
        "campus_explorer": campus >= 1,
        "event_hopper": len(attended_event_ids) >= EVENT_HOPPER_THRESHOLD,
        "table_buyer": has_table,
        "vault_member": vault_paid is not None,
        "lagos_explorer": lagos >= CATEGORY_BADGE_THRESHOLD,
        "reviewer": reviews_n >= 1,
        "review_writer": reviews_n >= 2,
        **merch_flags,
    }
