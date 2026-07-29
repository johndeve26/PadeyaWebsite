"""Resolve host audience members by segment and filters."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.constants import VIP_SPEND_THRESHOLD
from app.crm.models import HostFollower
from app.events.models import Event, TicketType
from app.payments.models import Order
from app.tickets.models import Ticket
from app.users.models import User


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _display_name(full_name: str) -> str:
    """Privacy-safe list label (First L.). Prefer full given name for greetings elsewhere."""
    parts = (full_name or "").strip().split()
    if not parts:
        return "Attendee"
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


def _greeting_name(full_name: str) -> str:
    """Given name from account settings for announcement personalization."""
    parts = (full_name or "").strip().split()
    return parts[0] if parts else "there"


def _host_event_ids(db: Session, host_id: UUID) -> list[UUID]:
    return list(db.scalars(select(Event.id).where(Event.host_id == host_id)))


def _paid_orders(db: Session, host_id: UUID, *, event_id: UUID | None = None) -> list[Order]:
    q = (
        select(Order)
        .join(Event, Event.id == Order.event_id)
        .where(Event.host_id == host_id, Order.status == "paid")
    )
    if event_id is not None:
        q = q.where(Order.event_id == event_id)
    return list(db.scalars(q))


def _marketing_map(db: Session, host_id: UUID, user_ids: set[UUID]) -> dict[UUID, bool]:
    if not user_ids:
        return {}
    rows = db.scalars(
        select(HostFollower).where(
            HostFollower.host_id == host_id,
            HostFollower.user_id.in_(user_ids),
        )
    ).all()
    return {r.user_id: bool(r.marketing_opt_in) for r in rows}


def _member(
    user: User,
    *,
    marketing_opt_in: bool,
    events_attended: int = 0,
    tickets_purchased: int = 0,
    last_order_at: datetime | None = None,
    tags: list[str] | None = None,
) -> dict:
    from app.users.gender import public_cache_safe_gender_payload

    gender = public_cache_safe_gender_payload(user)
    return {
        "user_id": user.id,
        "display_name": _display_name(user.full_name),
        # Given name from account settings — used for {{name}} in announcements.
        "greeting_name": _greeting_name(user.full_name),
        "email": user.email,
        "marketing_opt_in": marketing_opt_in,
        "events_attended": events_attended,
        "tickets_purchased": tickets_purchased,
        "last_order_at": last_order_at,
        "tags": tags or [],
        **gender,
    }


def resolve_segment_members(
    db: Session,
    *,
    host_id: UUID,
    segment_key: str,
    filters: dict | None = None,
) -> list[dict]:
    filters = filters or {}
    event_id = UUID(str(filters["event_id"])) if filters.get("event_id") else None
    ticket_type_id = (
        UUID(str(filters["ticket_type_id"])) if filters.get("ticket_type_id") else None
    )
    check_in_status = filters.get("check_in_status")  # checked_in | not_checked_in | any

    if segment_key == "followers":
        return _followers(db, host_id)
    if segment_key == "past_buyers":
        return _past_buyers(db, host_id, event_id=event_id, ticket_type_id=ticket_type_id)
    if segment_key == "repeat_buyers":
        return _repeat_buyers(db, host_id)
    if segment_key == "vip_buyers":
        return _vip_buyers(db, host_id, event_id=event_id)
    if segment_key == "checked_in_attendees":
        return _checked_in(db, host_id, event_id=event_id, ticket_type_id=ticket_type_id)
    if segment_key == "no_shows":
        return _no_shows(db, host_id, event_id=event_id, ticket_type_id=ticket_type_id)
    if segment_key == "promo_code_buyers":
        return _promo_buyers(db, host_id, event_id=event_id)
    if segment_key == "ambassador_referrals":
        return _ambassador_buyers(db, host_id, event_id=event_id)
    if segment_key == "superfans":
        return []  # placeholder
    if segment_key == "vault_subscribers":
        return _vault_subscribers(db, host_id)
    if segment_key == "filtered":
        return _filtered_buyers(
            db,
            host_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            check_in_status=check_in_status,
        )
    return []


def _followers(db: Session, host_id: UUID) -> list[dict]:
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    rows = db.scalars(
        select(HostFollower).where(HostFollower.host_id == host_id)
    ).all()
    out: list[dict] = []
    for row in rows:
        if is_user_owner_of_host(
            db, user_id=row.user_id, host_profile_id=host_id
        ):
            continue
        user = db.get(User, row.user_id)
        if user is None:
            continue
        out.append(
            _member(
                user,
                marketing_opt_in=row.marketing_opt_in,
                tags=["follower"],
            )
        )
    return out


def _vault_subscribers(db: Session, host_id: UUID) -> list[dict]:
    from app.vault.models import VaultSubscription

    rows = db.scalars(
        select(VaultSubscription).where(
            VaultSubscription.host_id == host_id,
            VaultSubscription.status == "active",
            VaultSubscription.archived_at.is_(None),
        )
    ).all()
    marketing = _marketing_map(db, host_id, {r.buyer_user_id for r in rows})
    out: list[dict] = []
    for row in rows:
        user = db.get(User, row.buyer_user_id)
        if user is None:
            continue
        out.append(
            _member(
                user,
                marketing_opt_in=marketing.get(user.id, True),
                tags=["vault_subscriber"],
            )
        )
    return out


def _buyer_stats(
    db: Session, host_id: UUID, *, event_id: UUID | None = None
) -> dict[UUID, dict]:
    orders = _paid_orders(db, host_id, event_id=event_id)
    stats: dict[UUID, dict] = {}
    for order in orders:
        entry = stats.setdefault(
            order.buyer_user_id,
            {
                "events": set(),
                "tickets": 0,
                "spend": Decimal("0"),
                "last_order_at": None,
                "promo": False,
                "ambassador": False,
            },
        )
        entry["events"].add(order.event_id)
        entry["spend"] += Decimal(order.total_amount)
        if order.paid_at and (
            entry["last_order_at"] is None or order.paid_at > entry["last_order_at"]
        ):
            entry["last_order_at"] = order.paid_at
        if order.promo_code_id is not None:
            entry["promo"] = True
        if order.ambassador_id is not None:
            entry["ambassador"] = True

    ticket_q = (
        select(Ticket)
        .join(Event, Event.id == Ticket.event_id)
        .where(Event.host_id == host_id, Ticket.status.in_(["active", "checked_in"]))
    )
    if event_id is not None:
        ticket_q = ticket_q.where(Ticket.event_id == event_id)
    for ticket in db.scalars(ticket_q):
        if ticket.buyer_user_id in stats:
            stats[ticket.buyer_user_id]["tickets"] += 1
    return stats


def _users_as_members(
    db: Session,
    host_id: UUID,
    user_ids: set[UUID],
    stats: dict[UUID, dict],
    *,
    tag: str,
) -> list[dict]:
    opt_in = _marketing_map(db, host_id, user_ids)
    out: list[dict] = []
    for uid in user_ids:
        user = db.get(User, uid)
        if user is None:
            continue
        st = stats.get(uid, {})
        out.append(
            _member(
                user,
                marketing_opt_in=opt_in.get(uid, False),
                events_attended=len(st.get("events", set())),
                tickets_purchased=int(st.get("tickets", 0)),
                last_order_at=st.get("last_order_at"),
                tags=[tag],
            )
        )
    out.sort(key=lambda m: m["display_name"].lower())
    return out


def _past_buyers(
    db: Session,
    host_id: UUID,
    *,
    event_id: UUID | None,
    ticket_type_id: UUID | None,
) -> list[dict]:
    stats = _buyer_stats(db, host_id, event_id=event_id)
    user_ids = set(stats.keys())
    if ticket_type_id is not None:
        ticket_buyers = set(
            db.scalars(
                select(Ticket.buyer_user_id)
                .join(Event, Event.id == Ticket.event_id)
                .where(
                    Event.host_id == host_id,
                    Ticket.ticket_type_id == ticket_type_id,
                    Ticket.status.in_(["active", "checked_in"]),
                )
            )
        )
        user_ids &= ticket_buyers
    return _users_as_members(db, host_id, user_ids, stats, tag="past_buyer")


def _repeat_buyers(db: Session, host_id: UUID) -> list[dict]:
    stats = _buyer_stats(db, host_id)
    user_ids = {uid for uid, st in stats.items() if len(st["events"]) >= 2}
    return _users_as_members(db, host_id, user_ids, stats, tag="repeat_buyer")


def _vip_buyers(
    db: Session, host_id: UUID, *, event_id: UUID | None
) -> list[dict]:
    stats = _buyer_stats(db, host_id, event_id=event_id)
    vip_type_ids = set(
        db.scalars(
            select(TicketType.id)
            .join(Event, Event.id == TicketType.event_id)
            .where(Event.host_id == host_id, TicketType.type.in_(["vip", "vvip"]))
        )
    )
    vip_buyers = set(
        db.scalars(
            select(Ticket.buyer_user_id)
            .join(Event, Event.id == Ticket.event_id)
            .where(
                Event.host_id == host_id,
                Ticket.ticket_type_id.in_(vip_type_ids) if vip_type_ids else False,
                Ticket.status.in_(["active", "checked_in"]),
            )
        )
    ) if vip_type_ids else set()
    for uid, st in stats.items():
        if st["spend"] >= VIP_SPEND_THRESHOLD:
            vip_buyers.add(uid)
    return _users_as_members(db, host_id, vip_buyers, stats, tag="vip")


def _checked_in(
    db: Session,
    host_id: UUID,
    *,
    event_id: UUID | None,
    ticket_type_id: UUID | None,
) -> list[dict]:
    q = (
        select(Ticket)
        .join(Event, Event.id == Ticket.event_id)
        .where(Event.host_id == host_id, Ticket.status == "checked_in")
    )
    if event_id is not None:
        q = q.where(Ticket.event_id == event_id)
    if ticket_type_id is not None:
        q = q.where(Ticket.ticket_type_id == ticket_type_id)
    tickets = list(db.scalars(q))
    stats = _buyer_stats(db, host_id, event_id=event_id)
    user_ids = {t.buyer_user_id for t in tickets}
    return _users_as_members(db, host_id, user_ids, stats, tag="checked_in")


def _no_shows(
    db: Session,
    host_id: UUID,
    *,
    event_id: UUID | None,
    ticket_type_id: UUID | None,
) -> list[dict]:
    now = datetime.now(UTC)
    q = (
        select(Ticket, Event)
        .join(Event, Event.id == Ticket.event_id)
        .where(
            Event.host_id == host_id,
            Ticket.status == "active",
            Ticket.checked_in_at.is_(None),
        )
    )
    if event_id is not None:
        q = q.where(Ticket.event_id == event_id)
    if ticket_type_id is not None:
        q = q.where(Ticket.ticket_type_id == ticket_type_id)

    user_ids: set[UUID] = set()
    for ticket, event in db.execute(q).all():
        end = _aware(event.end_datetime)
        if end < now or event.status == "completed":
            user_ids.add(ticket.buyer_user_id)
    stats = _buyer_stats(db, host_id, event_id=event_id)
    return _users_as_members(db, host_id, user_ids, stats, tag="no_show")


def _promo_buyers(
    db: Session, host_id: UUID, *, event_id: UUID | None
) -> list[dict]:
    stats = _buyer_stats(db, host_id, event_id=event_id)
    user_ids = {uid for uid, st in stats.items() if st.get("promo")}
    return _users_as_members(db, host_id, user_ids, stats, tag="promo_buyer")


def _ambassador_buyers(
    db: Session, host_id: UUID, *, event_id: UUID | None
) -> list[dict]:
    stats = _buyer_stats(db, host_id, event_id=event_id)
    user_ids = {uid for uid, st in stats.items() if st.get("ambassador")}
    return _users_as_members(db, host_id, user_ids, stats, tag="ambassador_referral")


def _filtered_buyers(
    db: Session,
    host_id: UUID,
    *,
    event_id: UUID | None,
    ticket_type_id: UUID | None,
    check_in_status: str | None,
) -> list[dict]:
    q = (
        select(Ticket)
        .join(Event, Event.id == Ticket.event_id)
        .where(
            Event.host_id == host_id,
            Ticket.status.in_(["active", "checked_in"]),
        )
    )
    if event_id is not None:
        q = q.where(Ticket.event_id == event_id)
    if ticket_type_id is not None:
        q = q.where(Ticket.ticket_type_id == ticket_type_id)
    if check_in_status == "checked_in":
        q = q.where(Ticket.status == "checked_in")
    elif check_in_status == "not_checked_in":
        q = q.where(Ticket.status == "active", Ticket.checked_in_at.is_(None))

    tickets = list(db.scalars(q))
    user_ids = {t.buyer_user_id for t in tickets}
    stats = _buyer_stats(db, host_id, event_id=event_id)
    return _users_as_members(db, host_id, user_ids, stats, tag="filtered")


def audience_stats(db: Session, host_id: UUID) -> dict:
    keys = [
        "followers",
        "past_buyers",
        "repeat_buyers",
        "vip_buyers",
        "checked_in_attendees",
        "no_shows",
        "promo_code_buyers",
        "ambassador_referrals",
    ]
    counts = {k: len(resolve_segment_members(db, host_id=host_id, segment_key=k)) for k in keys}
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    opted_rows = db.scalars(
        select(HostFollower).where(
            HostFollower.host_id == host_id, HostFollower.marketing_opt_in.is_(True)
        )
    ).all()
    opted = sum(
        1
        for row in opted_rows
        if not is_user_owner_of_host(
            db, user_id=row.user_id, host_profile_id=host_id
        )
    )
    return {
        "followers": counts["followers"],
        "past_buyers": counts["past_buyers"],
        "repeat_buyers": counts["repeat_buyers"],
        "vip_buyers": counts["vip_buyers"],
        "checked_in_attendees": counts["checked_in_attendees"],
        "no_shows": counts["no_shows"],
        "promo_code_buyers": counts["promo_code_buyers"],
        "ambassador_referrals": counts["ambassador_referrals"],
        "marketing_opted_in": int(opted),
    }
