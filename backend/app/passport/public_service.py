"""Public Fan Passport reads and privacy-safe serialization."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.http_errors import raise_not_found
from app.crm.models import HostFollower
from app.events.models import Event
from app.fan_connect import constants as FC
from app.fan_connect.models import FanConnection
from app.hosts.models import Host, HostProfile
from app.passport.constants import ATTENDED_TICKET_STATUSES
from app.passport.models import FanBadge, FanPassport, UserBadge
from app.passport.merch_proof import fan_merch_proof_summaries
from app.passport.privacy import (
    event_is_safe_for_public_passport,
    is_publicly_reachable,
    normalize_username,
    public_city_for_event,
)
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.users.models import User
from app.vault.models import VaultItem, VaultPurchase


def get_passport_by_username(db: Session, username: str) -> FanPassport | None:
    key = normalize_username(username)
    if not key:
        return None
    return db.scalar(select(FanPassport).where(FanPassport.username == key))


def require_reachable_passport(db: Session, username: str) -> tuple[FanPassport, User]:
    passport = get_passport_by_username(db, username)
    if passport is None or not is_publicly_reachable(passport.visibility):
        raise_not_found()
    if passport.admin_hidden_at is not None:
        raise_not_found()
    user = db.get(User, passport.user_id)
    if user is None or not user.is_active:
        raise_not_found()
    return passport, user


def _attended_tickets(db: Session, user_id: UUID) -> list[Ticket]:
    return list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user_id,
                Ticket.status.in_(ATTENDED_TICKET_STATUSES),
            )
        )
    )


def _events_map(db: Session, event_ids: set[UUID]) -> dict[UUID, Event]:
    if not event_ids:
        return {}
    return {
        e.id: e for e in db.scalars(select(Event).where(Event.id.in_(event_ids)))
    }


def _hosts_map(db: Session, host_ids: set[UUID]) -> dict[UUID, Host]:
    if not host_ids:
        return {}
    return {
        h.id: h for h in db.scalars(select(Host).where(Host.id.in_(host_ids)))
    }


def public_attended_events(db: Session, passport: FanPassport) -> list[dict]:
    if not passport.show_attended_events:
        return []
    tickets = _attended_tickets(db, passport.user_id)
    events = _events_map(db, {t.event_id for t in tickets})
    host_ids = {e.host_id for e in events.values()}
    hosts = _hosts_map(db, host_ids)
    out: list[dict] = []
    seen: set[UUID] = set()
    for t in tickets:
        ev = events.get(t.event_id)
        if not ev or ev.id in seen:
            continue
        if not event_is_safe_for_public_passport(
            ev, hide_private_events_always=passport.hide_private_events_always
        ):
            continue
        seen.add(ev.id)
        host = hosts.get(ev.host_id)
        out.append(
            {
                "event_id": ev.id,
                "title": ev.title,
                "slug": ev.slug,
                "host_username": host.slug if host else None,
                "host_display_name": host.display_name if host else None,
                "start_datetime": ev.start_datetime,
                "city": public_city_for_event(ev),
                "checked_in": True,
            }
        )
    out.sort(key=lambda c: c["start_datetime"], reverse=True)
    return out[:40]


def public_badges(db: Session, passport: FanPassport) -> list[dict]:
    if not passport.show_badges:
        return []
    awarded = {
        ub.badge_id: ub
        for ub in db.scalars(
            select(UserBadge).where(UserBadge.user_id == passport.user_id)
        )
    }
    badges = list(
        db.scalars(select(FanBadge).where(FanBadge.is_active.is_(True)).order_by(FanBadge.name))
    )
    return [
        {
            "id": b.id,
            "slug": b.slug,
            "name": b.name,
            "description": b.description,
            "criteria_key": b.criteria_key,
            "earned": True,
            "awarded_at": awarded[b.id].awarded_at,
        }
        for b in badges
        if b.id in awarded
    ]


def public_followed_hosts(db: Session, passport: FanPassport) -> list[dict]:
    if not passport.show_followed_hosts:
        return []
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    followers = list(
        db.scalars(
            select(HostFollower)
            .where(HostFollower.user_id == passport.user_id)
            .order_by(HostFollower.created_at.desc())
        )
    )
    hosts = _hosts_map(db, {f.host_id for f in followers})
    # Safe public profile fields only — never email/payment/private CRM.
    profiles = {
        p.host_id: p
        for p in db.scalars(
            select(HostProfile).where(HostProfile.host_id.in_(hosts.keys()))
        )
    } if hosts else {}
    out: list[dict] = []
    for f in followers:
        # Own-host follows must not inflate Passport reputation.
        if is_user_owner_of_host(
            db, user_id=passport.user_id, host_profile_id=f.host_id
        ):
            continue
        host = hosts.get(f.host_id)
        if host is None:
            continue
        profile = profiles.get(f.host_id)
        out.append(
            {
                "host_id": str(f.host_id),
                "display_name": host.display_name,
                "username": host.slug,
                "share_path": f"/@{host.slug}",
                "avatar_url": profile.avatar_url if profile else None,
                "city": profile.city if profile else None,
            }
        )
    return out[:30]


def public_reviews(db: Session, passport: FanPassport) -> list[dict]:
    if not passport.show_reviews:
        return []
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    rows = list(
        db.scalars(
            select(VerifiedReview)
            .where(
                VerifiedReview.reviewer_user_id == passport.user_id,
                VerifiedReview.status == "visible",
            )
            .order_by(VerifiedReview.created_at.desc())
            .limit(40)
        )
    )
    # Drop self-host reviews first, then cap public list.
    rows = [
        r
        for r in rows
        if not is_user_owner_of_host(
            db, user_id=passport.user_id, host_profile_id=r.host_id
        )
    ][:20]
    event_ids = {r.event_id for r in rows}
    events = _events_map(db, event_ids)
    hosts = _hosts_map(db, {r.host_id for r in rows})
    out = []
    for r in rows:
        ev = events.get(r.event_id)
        host = hosts.get(r.host_id)
        if ev and not event_is_safe_for_public_passport(
            ev, hide_private_events_always=passport.hide_private_events_always
        ):
            event_title = None
        else:
            event_title = ev.title if ev else None
        out.append(
            {
                "id": r.id,
                "rating": int(r.rating),
                "body": r.body,
                "event_title": event_title,
                "host_username": host.slug if host else None,
                "created_at": r.created_at,
            }
        )
    return out


def public_vault_unlocks(db: Session, passport: FanPassport) -> list[dict]:
    if not passport.show_vault_unlocks:
        return []
    purchases = list(
        db.scalars(
            select(VaultPurchase).where(
                VaultPurchase.user_id == passport.user_id,
                VaultPurchase.status == "paid",
            )
        )
    )
    item_ids = {p.vault_item_id for p in purchases}
    items = {
        i.id: i
        for i in db.scalars(
            select(VaultItem).where(
                VaultItem.id.in_(item_ids),
                VaultItem.status == "published",
            )
        )
    } if item_ids else {}
    host_ids = {i.host_id for i in items.values()}
    hosts = _hosts_map(db, host_ids)
    out = []
    for item in items.values():
        host = hosts.get(item.host_id)
        out.append(
            {
                "title": item.title,
                "host_username": host.slug if host else None,
                "access_label": "Ticket-holder unlock",
            }
        )
    return out[:20]


def favorite_cities_for_user(db: Session, user_id: UUID) -> list[str]:
    tickets = _attended_tickets(db, user_id)
    events = _events_map(db, {t.event_id for t in tickets})
    counts: dict[str, int] = {}
    for ev in events.values():
        city = public_city_for_event(ev)
        if city:
            counts[city] = counts.get(city, 0) + 1
    return sorted(counts.keys(), key=lambda c: (-counts[c], c))[:5]


def reviews_written_count(db: Session, user_id: UUID) -> int:
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    rows = list(
        db.scalars(
            select(VerifiedReview).where(
                VerifiedReview.reviewer_user_id == user_id,
                VerifiedReview.status.in_(["visible", "hidden", "flagged"]),
            )
        )
    )
    return sum(
        1
        for r in rows
        if not is_user_owner_of_host(
            db, user_id=user_id, host_profile_id=r.host_id
        )
    )


def count_fan_connections(db: Session, user_id: UUID) -> int:
    """Accepted Fan Connect connections for a passport profile.

    Self-rows (user_low_id == user_high_id) never count.
    """
    return int(
        db.scalar(
            select(func.count())
            .select_from(FanConnection)
            .where(
                FanConnection.status == FC.STATUS_CONNECTED,
                FanConnection.user_low_id != FanConnection.user_high_id,
                or_(
                    FanConnection.user_low_id == user_id,
                    FanConnection.user_high_id == user_id,
                ),
            )
        )
        or 0
    )


def build_public_passport_page(db: Session, username: str) -> dict:
    passport, _user = require_reachable_passport(db, username)
    badges = public_badges(db, passport)
    attended = public_attended_events(db, passport)
    followed = public_followed_hosts(db, passport)
    reviews = public_reviews(db, passport)
    vault = public_vault_unlocks(db, passport)
    cities = (
        favorite_cities_for_user(db, passport.user_id)
        if passport.show_city_category_stats
        else []
    )
    categories = (
        list(passport.favorite_categories or [])
        if passport.show_city_category_stats
        else []
    )
    merch_proof = (
        fan_merch_proof_summaries(db, passport.user_id) if passport.show_badges else []
    )
    return {
        "username": passport.username,
        "user_id": passport.user_id,
        "display_name": passport.display_name,
        "avatar_url": passport.avatar_url,
        "tagline": passport.tagline,
        "bio": passport.bio,
        "visibility": passport.visibility,
        "is_superfan": passport.is_superfan,
        "events_attended": len(attended) if passport.show_attended_events else 0,
        "hosts_followed": len(followed) if passport.show_followed_hosts else 0,
        "badges_earned_count": len(badges) if passport.show_badges else 0,
        "reviews_written": len(reviews) if passport.show_reviews else 0,
        "cities_explored": len(cities),
        "categories_explored": len(categories),
        "connections_count": count_fan_connections(db, passport.user_id),
        "favorite_categories": categories,
        "favorite_cities": cities,
        "badges": badges,
        "attended_events": attended,
        "followed_hosts": followed,
        "reviews": reviews,
        "vault_unlocks": vault,
        "merch_proof_summaries": merch_proof,
        "share_path": f"/f/{passport.username}",
    }


def build_public_activity(db: Session, username: str) -> dict:
    passport, _user = require_reachable_passport(db, username)
    return {"items": public_attended_events(db, passport)}


def build_public_badges(db: Session, username: str) -> list[dict]:
    passport, _user = require_reachable_passport(db, username)
    return public_badges(db, passport)
