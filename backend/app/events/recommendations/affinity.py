"""Fan signals for event recommendation scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event, EventCategory
from app.events.recommendations import constants as C
from app.events.recommendations.models import (
    EventRecommendationCategoryHide,
    EventRecommendationFeedback,
    EventRecommendationHostHide,
)
from app.fan_connect import constants as FC
from app.fan_connect.context import (
    _followed_host_ids,
    _safe_attended_event_ids,
    _safe_upcoming_ticket_event_ids,
)
from app.fan_connect.models import FanConnection, FanConnectLocationPreference
from app.hosts.models import Host, HostVerification
from app.passport.models import FanPassport
from app.passport.public_service import favorite_cities_for_user
from app.placements.service import list_padeya_picks
from app.tickets.models import Ticket


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@dataclass
class FanEventAffinity:
    attended_event_ids: set[UUID] = field(default_factory=set)
    upcoming_ticket_event_ids: set[UUID] = field(default_factory=set)
    attended_category_slugs: set[str] = field(default_factory=set)
    ticketed_category_slugs: set[str] = field(default_factory=set)
    favorite_categories: set[str] = field(default_factory=set)
    followed_host_ids: set[UUID] = field(default_factory=set)
    attended_host_ids: set[UUID] = field(default_factory=set)
    ticketed_host_ids: set[UUID] = field(default_factory=set)
    favorite_cities: set[str] = field(default_factory=set)
    location_city: str | None = None
    location_area: str | None = None
    network_event_counts: dict[UUID, int] = field(default_factory=dict)
    network_host_follow_counts: dict[UUID, int] = field(default_factory=dict)
    pick_event_ids: set[UUID] = field(default_factory=set)
    own_host_ids: set[UUID] = field(default_factory=set)
    hidden_host_ids: set[UUID] = field(default_factory=set)
    hidden_category_slugs: set[str] = field(default_factory=set)
    penalized_category_slugs: set[str] = field(default_factory=set)
    penalized_host_ids: set[UUID] = field(default_factory=set)
    more_like_category_slugs: set[str] = field(default_factory=set)
    more_like_host_ids: set[UUID] = field(default_factory=set)
    more_like_city_labels: set[str] = field(default_factory=set)
    verified_host_ids: set[UUID] = field(default_factory=set)


def _category_slugs_for_events(db: Session, event_ids: set[UUID]) -> dict[UUID, str]:
    if not event_ids:
        return {}
    rows = db.execute(
        select(Event.id, EventCategory.slug)
        .join(EventCategory, Event.category_id == EventCategory.id, isouter=True)
        .where(Event.id.in_(event_ids))
    ).all()
    out: dict[UUID, str] = {}
    for eid, slug in rows:
        if slug:
            out[eid] = str(slug).lower()
    return out


def _connected_fan_user_ids(db: Session, user_id: UUID) -> set[UUID]:
    rows = list(
        db.scalars(
            select(FanConnection).where(
                FanConnection.status == FC.STATUS_CONNECTED,
                (FanConnection.user_low_id == user_id)
                | (FanConnection.user_high_id == user_id),
            )
        ).all()
    )
    peers: set[UUID] = set()
    for row in rows:
        peers.add(
            row.user_high_id if row.user_low_id == user_id else row.user_low_id
        )
    return peers


def _network_event_ticket_counts(db: Session, peer_ids: set[UUID]) -> dict[UUID, int]:
    if not peer_ids:
        return {}
    tickets = db.execute(
        select(Ticket.event_id).where(
            Ticket.buyer_user_id.in_(peer_ids),
            Ticket.status.in_(("active", "checked_in")),
        )
    ).all()
    counts: dict[UUID, int] = {}
    for (event_id,) in tickets:
        counts[event_id] = counts.get(event_id, 0) + 1
    return counts


def _network_host_follow_counts(db: Session, peer_ids: set[UUID]) -> dict[UUID, int]:
    if not peer_ids:
        return {}
    follows = db.execute(
        select(HostFollower.host_id).where(HostFollower.user_id.in_(peer_ids))
    ).all()
    counts: dict[UUID, int] = {}
    for (host_id,) in follows:
        counts[host_id] = counts.get(host_id, 0) + 1
    return counts


def _resolve_actor_geo(db: Session, user_id: UUID) -> tuple[str | None, str | None]:
    pref = db.scalar(
        select(FanConnectLocationPreference).where(
            FanConnectLocationPreference.user_id == user_id
        )
    )
    if pref and pref.city:
        return pref.city.strip().lower(), (
            pref.area.strip().lower() if pref.area else None
        )
    cities = favorite_cities_for_user(db, user_id)
    if cities:
        return cities[0].lower(), None
    return None, None


def load_fan_event_affinity(
    db: Session,
    *,
    user_id: UUID,
    own_host_ids: set[UUID] | None = None,
) -> FanEventAffinity:
    attended = _safe_attended_event_ids(db, user_id)
    upcoming_tickets = _safe_upcoming_ticket_event_ids(db, user_id)

    attended_cats: set[str] = set()
    ticket_cats: set[str] = set()
    cat_map = _category_slugs_for_events(db, attended | upcoming_tickets)
    for eid in attended:
        if eid in cat_map:
            attended_cats.add(cat_map[eid])
    for eid in upcoming_tickets:
        if eid in cat_map:
            ticket_cats.add(cat_map[eid])

    followed = _followed_host_ids(db, user_id)
    peers = _connected_fan_user_ids(db, user_id)

    attended_hosts: set[UUID] = set()
    if attended:
        for row in db.scalars(select(Event.host_id).where(Event.id.in_(attended))).all():
            if row:
                attended_hosts.add(row)

    ticket_hosts: set[UUID] = set()
    if upcoming_tickets:
        for row in db.scalars(
            select(Event.host_id).where(Event.id.in_(upcoming_tickets))
        ).all():
            if row:
                ticket_hosts.add(row)

    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    fav_cats = {
        str(c).strip().lower()
        for c in (passport.favorite_categories or [] if passport else [])
        if str(c).strip()
    }
    fav_cities = {c.lower() for c in favorite_cities_for_user(db, user_id) if c}
    loc_city, loc_area = _resolve_actor_geo(db, user_id)

    pick_ids: set[UUID] = set()
    try:
        for ev in list_padeya_picks(db, context_type="homepage"):
            pick_ids.add(ev.id)
    except Exception:
        pick_ids = set()

    verified_hosts = set(
        db.scalars(
            select(HostVerification.host_id).where(
                HostVerification.status == "verified"
            )
        ).all()
    )

    now = datetime.now(UTC)
    hidden_cats: set[str] = set()
    for row in db.scalars(
        select(EventRecommendationCategoryHide).where(
            EventRecommendationCategoryHide.user_id == user_id
        )
    ).all():
        exp = _aware(row.expires_at)
        if exp is not None and exp <= now:
            continue
        hidden_cats.add(row.category_slug.strip().lower())

    hidden_hosts: set[UUID] = set()
    for row in db.scalars(
        select(EventRecommendationHostHide).where(
            EventRecommendationHostHide.user_id == user_id
        )
    ).all():
        exp = _aware(row.expires_at)
        if exp is not None and exp <= now:
            continue
        hidden_hosts.add(row.host_id)

    penalized_cats: set[str] = set()
    penalized_hosts: set[UUID] = set()
    more_like_cats: set[str] = set()
    more_like_hosts: set[UUID] = set()
    more_like_cities: set[str] = set()

    for fb in db.scalars(
        select(EventRecommendationFeedback).where(
            EventRecommendationFeedback.user_id == user_id,
        ).limit(80)
    ).all():
        ctx = fb.context or {}
        if fb.action == C.FEEDBACK_NOT_INTERESTED:
            for slug in ctx.get("category_slugs") or []:
                penalized_cats.add(str(slug).lower())
        if fb.action == C.FEEDBACK_HIDE_HOST:
            hid = ctx.get("host_id")
            if hid:
                penalized_hosts.add(UUID(str(hid)))
        if fb.action == C.FEEDBACK_MORE_LIKE_THIS:
            for slug in ctx.get("category_slugs") or []:
                more_like_cats.add(str(slug).lower())
            hid = ctx.get("host_id")
            if hid:
                more_like_hosts.add(UUID(str(hid)))
            city = ctx.get("city")
            if city:
                more_like_cities.add(str(city).lower())

    return FanEventAffinity(
        attended_event_ids=attended,
        upcoming_ticket_event_ids=upcoming_tickets,
        attended_category_slugs=attended_cats,
        ticketed_category_slugs=ticket_cats,
        favorite_categories=fav_cats,
        followed_host_ids=followed,
        attended_host_ids=attended_hosts,
        ticketed_host_ids=ticket_hosts,
        favorite_cities=fav_cities,
        location_city=loc_city,
        location_area=loc_area,
        network_event_counts=_network_event_ticket_counts(db, peers),
        network_host_follow_counts=_network_host_follow_counts(db, peers),
        pick_event_ids=pick_ids,
        own_host_ids=own_host_ids or set(),
        hidden_host_ids=hidden_hosts,
        hidden_category_slugs=hidden_cats,
        penalized_category_slugs=penalized_cats,
        penalized_host_ids=penalized_hosts,
        more_like_category_slugs=more_like_cats,
        more_like_host_ids=more_like_hosts,
        more_like_city_labels=more_like_cities,
        verified_host_ids=verified_hosts,
    )


def event_category_slug(event: Event) -> str | None:
    if event.category and event.category.slug:
        return event.category.slug.lower()
    return None


def event_city_label(event: Event) -> str | None:
    if event.city:
        return str(event.city).strip().lower()
    return None
