"""Fan Passport aggregation, loyalty, and badge awarding."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host
from app.passport.badges import evaluate_badge_criteria
from app.passport.constants import (
    ATTENDED_TICKET_STATUSES,
    MERCH_BADGE_CRITERIA,
    OWNED_TICKET_STATUSES,
    SUPERFAN_CHECKIN_THRESHOLD,
)
from app.passport.merch_proof import fan_merch_proof_summaries
from fastapi import HTTPException, status

from app.passport.models import FanBadge, FanPassport, LoyaltyRecord, UserBadge
from app.passport.privacy import (
    VISIBILITY_PRIVATE,
    VISIBILITY_PUBLIC,
    is_valid_passport_username,
    normalize_username,
    slugify_username_from_name,
)
from app.passport.public_service import favorite_cities_for_user, reviews_written_count
from app.passport.seed import seed_fan_badges
from app.tickets.models import Ticket
from app.users.models import User
from app.vault.models import VaultItem, VaultPurchase


def _allocate_username(db: Session, user: User, preferred: str | None = None) -> str:
    base = normalize_username(preferred or "") or slugify_username_from_name(
        user.full_name, fallback=f"fan_{str(user.id).replace('-', '')[:8]}"
    )
    if not is_valid_passport_username(base):
        base = f"fan_{str(user.id).replace('-', '')[:8]}"
    candidate = base
    n = 0
    while True:
        existing = db.scalar(
            select(FanPassport).where(
                FanPassport.username == candidate,
                FanPassport.user_id != user.id,
            )
        )
        if existing is None:
            return candidate
        n += 1
        candidate = f"{base[:28]}_{n}"


def ensure_passport(
    db: Session,
    user: User,
    *,
    preferred_username: str | None = None,
    display_name: str | None = None,
) -> FanPassport:
    seed_fan_badges(db)
    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user.id))
    default_display = display_name or user.full_name
    if passport is None:
        allocated = _allocate_username(
            db, user, preferred=preferred_username or default_display
        )
        passport = FanPassport(
            user_id=user.id,
            display_name=default_display,
            username=allocated,
            visibility=VISIBILITY_PUBLIC,
            appear_in_directory=True,
            favorite_categories=[],
        )
        db.add(passport)
        db.flush()
    elif not passport.username:
        passport.username = _allocate_username(
            db, user, preferred=preferred_username or passport.display_name
        )
        if display_name and not passport.display_name:
            passport.display_name = display_name
        db.flush()
    return passport


def settings_payload(passport: FanPassport) -> dict:
    return {
        "username": passport.username,
        "display_name": passport.display_name,
        "avatar_url": passport.avatar_url,
        "tagline": passport.tagline,
        "bio": passport.bio,
        "visibility": passport.visibility,
        "appear_in_directory": bool(passport.appear_in_directory),
        "show_attended_events": passport.show_attended_events,
        "show_badges": passport.show_badges,
        "show_followed_hosts": passport.show_followed_hosts,
        "show_reviews": passport.show_reviews,
        "show_vault_unlocks": passport.show_vault_unlocks,
        "show_city_category_stats": passport.show_city_category_stats,
        "hide_private_events_always": passport.hide_private_events_always,
        "share_path": f"/f/{passport.username}" if passport.username else None,
    }


def update_passport_settings(db: Session, user: User, payload) -> FanPassport:
    from app.users.restrictions import assert_can_edit_passport

    assert_can_edit_passport(db, user)

    passport = ensure_passport(db, user)
    previous_username = passport.username
    data = payload.model_dump(exclude_unset=True)
    if "username" in data and data["username"] is not None:
        username = normalize_username(data["username"])
        if not is_valid_passport_username(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be 3–32 characters: lowercase letters, numbers, underscore.",
            )
        clash = db.scalar(
            select(FanPassport).where(
                FanPassport.username == username,
                FanPassport.user_id != user.id,
            )
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That Fan Passport username is already taken.",
            )
        passport.username = username
    for field in (
        "display_name",
        "avatar_url",
        "tagline",
        "bio",
        "visibility",
        "appear_in_directory",
        "show_attended_events",
        "show_badges",
        "show_followed_hosts",
        "show_reviews",
        "show_vault_unlocks",
        "show_city_category_stats",
        "hide_private_events_always",
    ):
        if field in data and data[field] is not None:
            setattr(passport, field, data[field])
    # Directory listing requires public + appear_in_directory (both default on)
    if passport.visibility != VISIBILITY_PUBLIC:
        passport.appear_in_directory = False
    db.commit()
    db.refresh(passport)
    try:
        from app.core.cache_invalidation import invalidate_fan_public_caches

        invalidate_fan_public_caches(
            username=passport.username,
            previous_username=(
                previous_username
                if previous_username and previous_username != passport.username
                else None
            ),
        )
    except Exception:
        pass
    return passport


def completion_score(passport: FanPassport, *, reviews: int, badges: int) -> int:
    checks = [
        bool(passport.username),
        bool(passport.display_name),
        bool(passport.avatar_url),
        bool(passport.tagline or passport.bio),
        passport.events_attended > 0,
        passport.hosts_followed > 0,
        badges > 0,
        reviews > 0,
        passport.vault_unlocks > 0,
        passport.visibility in {"public", "unlisted"},
    ]
    return int(round(100 * sum(1 for c in checks if c) / len(checks)))


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def refresh_loyalty_and_badges(db: Session, user: User) -> FanPassport:
    passport = ensure_passport(db, user)
    owned = list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user.id,
                Ticket.status.in_(OWNED_TICKET_STATUSES),
            )
        )
    )
    attended = list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user.id,
                Ticket.status.in_(ATTENDED_TICKET_STATUSES),
            )
        )
    )

    ticket_type_ids = {t.ticket_type_id for t in owned}
    types_by_id: dict[UUID, TicketType] = {}
    if ticket_type_ids:
        types_by_id = {
            tt.id: tt
            for tt in db.scalars(select(TicketType).where(TicketType.id.in_(ticket_type_ids)))
        }

    event_ids = {t.event_id for t in owned} | {t.event_id for t in attended}
    events_by_id: dict[UUID, Event] = {}
    if event_ids:
        events_by_id = {
            e.id: e for e in db.scalars(select(Event).where(Event.id.in_(event_ids)))
        }

    followers = list(
        db.scalars(select(HostFollower).where(HostFollower.user_id == user.id))
    )
    followed_host_ids = {f.host_id for f in followers}

    tickets_by_host: dict[UUID, int] = defaultdict(int)
    checkins_by_host: dict[UUID, set[UUID]] = defaultdict(set)
    vip_by_host: dict[UUID, int] = defaultdict(int)

    for t in owned:
        ev = events_by_id.get(t.event_id)
        if not ev:
            continue
        tickets_by_host[ev.host_id] += 1
        tt = types_by_id.get(t.ticket_type_id)
        if tt and tt.type in {"vip", "vvip"}:
            vip_by_host[ev.host_id] += 1

    for t in attended:
        ev = events_by_id.get(t.event_id)
        if ev:
            checkins_by_host[ev.host_id].add(t.event_id)

    host_ids = set(tickets_by_host) | set(checkins_by_host) | followed_host_ids
    any_superfan = False
    for host_id in host_ids:
        check_ins = len(checkins_by_host.get(host_id, set()))
        is_sf = check_ins >= SUPERFAN_CHECKIN_THRESHOLD
        if is_sf:
            any_superfan = True
        row = db.scalar(
            select(LoyaltyRecord).where(
                LoyaltyRecord.user_id == user.id,
                LoyaltyRecord.host_id == host_id,
            )
        )
        if row is None:
            row = LoyaltyRecord(user_id=user.id, host_id=host_id)
            db.add(row)
        row.tickets_bought = tickets_by_host.get(host_id, 0)
        row.check_ins = check_ins
        row.vip_purchases = vip_by_host.get(host_id, 0)
        row.is_superfan = is_sf
        row.follows_host = host_id in followed_host_ids

    category_counts: dict[str, int] = defaultdict(int)
    category_ids = {e.category_id for e in events_by_id.values() if e.category_id}
    cats: dict[UUID, EventCategory] = {}
    if category_ids:
        cats = {
            c.id: c
            for c in db.scalars(select(EventCategory).where(EventCategory.id.in_(category_ids)))
        }
    for t in attended:
        ev = events_by_id.get(t.event_id)
        if ev and ev.category_id and ev.category_id in cats:
            category_counts[cats[ev.category_id].slug] += 1
    favorites = sorted(category_counts.keys(), key=lambda s: (-category_counts[s], s))[:5]

    vault_count = (
        db.scalar(
            select(func.count())
            .select_from(VaultPurchase)
            .where(VaultPurchase.user_id == user.id, VaultPurchase.status == "paid")
        )
        or 0
    )

    passport.tickets_bought = len(owned)
    passport.events_attended = len({t.event_id for t in attended})
    passport.hosts_followed = len(followers)
    passport.vip_purchases = sum(
        1
        for t in owned
        if (tt := types_by_id.get(t.ticket_type_id)) and tt.type in {"vip", "vvip"}
    )
    passport.vault_unlocks = int(vault_count)
    passport.is_superfan = any_superfan
    passport.favorite_categories = favorites

    criteria = evaluate_badge_criteria(db, user.id)
    badges = list(db.scalars(select(FanBadge).where(FanBadge.is_active.is_(True))))
    existing = {
        ub.badge_id: ub
        for ub in db.scalars(select(UserBadge).where(UserBadge.user_id == user.id))
    }
    for badge in badges:
        earned = bool(criteria.get(badge.criteria_key))
        if earned and badge.id not in existing:
            meta = {"criteria_key": badge.criteria_key}
            if badge.criteria_key in MERCH_BADGE_CRITERIA:
                meta["source"] = "merch"
            db.add(
                UserBadge(
                    user_id=user.id,
                    badge_id=badge.id,
                    meta=meta,
                )
            )
        elif (
            not earned
            and badge.criteria_key in MERCH_BADGE_CRITERIA
            and badge.id in existing
        ):
            # Merch refunds: revoke when criteria no longer hold
            db.delete(existing[badge.id])

    db.commit()
    db.refresh(passport)
    return passport


def list_my_badges(db: Session, user: User) -> list[dict]:
    refresh_loyalty_and_badges(db, user)
    badges = list(
        db.scalars(select(FanBadge).where(FanBadge.is_active.is_(True)).order_by(FanBadge.name))
    )
    awarded = {
        ub.badge_id: ub
        for ub in db.scalars(select(UserBadge).where(UserBadge.user_id == user.id))
    }
    return [
        {
            "id": b.id,
            "slug": b.slug,
            "name": b.name,
            "description": b.description,
            "criteria_key": b.criteria_key,
            "earned": b.id in awarded,
            "awarded_at": awarded[b.id].awarded_at if b.id in awarded else None,
        }
        for b in badges
    ]


def get_my_passport(db: Session, user: User) -> dict:
    passport = refresh_loyalty_and_badges(db, user)
    return _serialize_passport(db, user, passport)


def _serialize_passport(db: Session, user: User, passport: FanPassport) -> dict:
    badge_rows = list(
        db.scalars(select(FanBadge).where(FanBadge.is_active.is_(True)).order_by(FanBadge.name))
    )
    awarded = {
        ub.badge_id: ub
        for ub in db.scalars(select(UserBadge).where(UserBadge.user_id == user.id))
    }
    badges_earned = [
        {
            "id": b.id,
            "slug": b.slug,
            "name": b.name,
            "description": b.description,
            "criteria_key": b.criteria_key,
            "earned": True,
            "awarded_at": awarded[b.id].awarded_at,
        }
        for b in badge_rows
        if b.id in awarded
    ]

    loyalty_rows = list(
        db.scalars(
            select(LoyaltyRecord)
            .where(LoyaltyRecord.user_id == user.id)
            .order_by(LoyaltyRecord.check_ins.desc(), LoyaltyRecord.tickets_bought.desc())
        )
    )
    host_ids = [r.host_id for r in loyalty_rows]
    hosts = {
        h.id: h for h in db.scalars(select(Host).where(Host.id.in_(host_ids)))
    } if host_ids else {}
    loyalty = [
        {
            "host_id": r.host_id,
            "host_display_name": hosts[r.host_id].display_name if r.host_id in hosts else "Host",
            "host_username": hosts[r.host_id].slug if r.host_id in hosts else "",
            "tickets_bought": r.tickets_bought,
            "check_ins": r.check_ins,
            "vip_purchases": r.vip_purchases,
            "is_superfan": r.is_superfan,
            "follows_host": r.follows_host,
        }
        for r in loyalty_rows
    ]

    owned = list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user.id,
                Ticket.status.in_(OWNED_TICKET_STATUSES),
            )
        )
    )
    event_ids = {t.event_id for t in owned}
    events = {
        e.id: e for e in db.scalars(select(Event).where(Event.id.in_(event_ids)))
    } if event_ids else {}
    type_ids = {t.ticket_type_id for t in owned}
    types = {
        tt.id: tt for tt in db.scalars(select(TicketType).where(TicketType.id.in_(type_ids)))
    } if type_ids else {}
    host_ids_for_events = {e.host_id for e in events.values()}
    host_map = {
        h.id: h for h in db.scalars(select(Host).where(Host.id.in_(host_ids_for_events)))
    } if host_ids_for_events else {}

    now = datetime.now(UTC)

    def event_card(t: Ticket) -> dict | None:
        ev = events.get(t.event_id)
        if not ev:
            return None
        tt = types.get(t.ticket_type_id)
        host = host_map.get(ev.host_id)
        return {
            "event_id": ev.id,
            "title": ev.title,
            "slug": ev.slug,
            "host_username": host.slug if host else None,
            "start_datetime": ev.start_datetime,
            "city": ev.city,
            "ticket_status": t.status,
            "ticket_type_name": t.ticket_type_name,
            "checked_in": t.status == "checked_in",
            "is_vip": bool(tt and tt.type in {"vip", "vvip"}),
        }

    attended_events = []
    upcoming_tickets = []
    vip_history = []
    for t in owned:
        card = event_card(t)
        if not card:
            continue
        ev = events[t.event_id]
        if t.status == "checked_in":
            attended_events.append(card)
        if _aware(ev.start_datetime) >= now and t.status == "active":
            upcoming_tickets.append(card)
        if card["is_vip"]:
            vip_history.append(card)

    attended_events.sort(key=lambda c: c["start_datetime"], reverse=True)
    upcoming_tickets.sort(key=lambda c: c["start_datetime"])

    followers = list(
        db.scalars(
            select(HostFollower)
            .where(HostFollower.user_id == user.id)
            .order_by(HostFollower.created_at.desc())
        )
    )
    f_host_ids = {f.host_id for f in followers}
    f_hosts = {
        h.id: h for h in db.scalars(select(Host).where(Host.id.in_(f_host_ids)))
    } if f_host_ids else {}
    followed_hosts = [
        {
            "host_id": str(f.host_id),
            "display_name": f_hosts[f.host_id].display_name if f.host_id in f_hosts else "Host",
            "username": f_hosts[f.host_id].slug if f.host_id in f_hosts else "",
        }
        for f in followers
    ]

    paid_purchases = list(
        db.scalars(
            select(VaultPurchase).where(
                VaultPurchase.user_id == user.id, VaultPurchase.status == "paid"
            )
        )
    )
    pending_count = (
        db.scalar(
            select(func.count())
            .select_from(VaultPurchase)
            .where(VaultPurchase.user_id == user.id, VaultPurchase.status == "pending")
        )
        or 0
    )
    item_ids = {p.vault_item_id for p in paid_purchases}
    titles = (
        [i.title for i in db.scalars(select(VaultItem).where(VaultItem.id.in_(item_ids)))]
        if item_ids
        else []
    )

    favorite_cities = favorite_cities_for_user(db, user.id)
    reviews_count = reviews_written_count(db, user.id)
    categories = list(passport.favorite_categories or [])

    return {
        "id": passport.id,
        "user_id": passport.user_id,
        "display_name": passport.display_name,
        "username": passport.username,
        "avatar_url": passport.avatar_url,
        "tagline": passport.tagline,
        "bio": passport.bio,
        "visibility": passport.visibility,
        "share_path": f"/f/{passport.username}" if passport.username else None,
        "tickets_bought": passport.tickets_bought,
        "events_attended": passport.events_attended,
        "hosts_followed": passport.hosts_followed,
        "vip_purchases": passport.vip_purchases,
        "vault_unlocks": passport.vault_unlocks,
        "is_superfan": passport.is_superfan,
        "favorite_categories": categories,
        "favorite_cities": favorite_cities,
        "reviews_written": reviews_count,
        "cities_explored": len(favorite_cities),
        "categories_explored": len(categories),
        "completion_score": completion_score(
            passport, reviews=reviews_count, badges=len(badges_earned)
        ),
        "badges_earned": badges_earned,
        "loyalty": loyalty,
        "attended_events": attended_events,
        "upcoming_tickets": upcoming_tickets,
        "vip_history": vip_history,
        "recent_checkins": attended_events[:8],
        "followed_hosts": followed_hosts,
        "vault_summary": {
            "paid_unlocks": len(paid_purchases),
            "pending_unlocks": int(pending_count),
            "unlocked_item_titles": titles[:20],
        },
        "merch_proof_summaries": fan_merch_proof_summaries(db, user.id),
        "settings": settings_payload(passport),
        "created_at": passport.created_at,
        "updated_at": passport.updated_at,
    }
