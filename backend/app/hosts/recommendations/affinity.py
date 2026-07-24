"""Load fan-side signals for host recommendation scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event
from app.fan_connect import constants as FC
from app.fan_connect.context import (
    _followed_host_ids,
    _safe_attended_event_ids,
    _safe_upcoming_ticket_event_ids,
)
from app.fan_connect.models import FanConnection, FanConnectLocationPreference
from app.hosts.models import HostProfile
from app.passport.models import FanPassport
from app.passport.public_service import favorite_cities_for_user
from app.legacy.models import HostLegacyPage
from app.tickets.models import Ticket


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@dataclass
class FanHostAffinity:
    attended_host_ids: set[UUID] = field(default_factory=set)
    ticketed_host_ids: set[UUID] = field(default_factory=set)
    followed_host_ids: set[UUID] = field(default_factory=set)
    network_host_follow_counts: dict[UUID, int] = field(default_factory=dict)
    favorite_categories: set[str] = field(default_factory=set)
    favorite_cities: set[str] = field(default_factory=set)
    followed_category_slugs: set[str] = field(default_factory=set)
    followed_city_labels: set[str] = field(default_factory=set)
    location_city: str | None = None
    location_area: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    own_host_ids: set[UUID] = field(default_factory=set)
    more_like_category_slugs: set[str] = field(default_factory=set)
    more_like_city_labels: set[str] = field(default_factory=set)
    hidden_category_slugs: set[str] = field(default_factory=set)
    penalized_category_slugs: set[str] = field(default_factory=set)


def _event_host_map(db: Session, event_ids: set[UUID]) -> dict[UUID, UUID]:
    if not event_ids:
        return {}
    rows = db.scalars(select(Event).where(Event.id.in_(event_ids))).all()
    return {e.id: e.host_id for e in rows if e.host_id}


def _ticket_purchase_hosts(db: Session, user_id: UUID) -> set[UUID]:
    """Hosts from any non-cancelled ticket the fan holds or held."""
    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user_id,
                Ticket.status.in_(("active", "checked_in", "transferred")),
            )
        ).all()
    )
    if not tickets:
        return set()
    event_ids = {t.event_id for t in tickets}
    host_map = _event_host_map(db, event_ids)
    return {host_map[eid] for eid in event_ids if eid in host_map}


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
        if row.user_low_id == user_id:
            peers.add(row.user_high_id)
        else:
            peers.add(row.user_low_id)
    return peers


def _network_follow_counts(db: Session, peer_ids: set[UUID]) -> dict[UUID, int]:
    if not peer_ids:
        return {}
    follows = db.execute(
        select(HostFollower.host_id, HostFollower.user_id).where(
            HostFollower.user_id.in_(peer_ids)
        )
    ).all()
    counts: dict[UUID, int] = {}
    for host_id, _uid in follows:
        counts[host_id] = counts.get(host_id, 0) + 1
    return counts


def _page_slugs_for_hosts(db: Session, host_ids: set[UUID]) -> dict[UUID, HostLegacyPage]:
    if not host_ids:
        return {}
    pages = list(
        db.scalars(select(HostLegacyPage).where(HostLegacyPage.host_id.in_(host_ids))).all()
    )
    return {p.host_id: p for p in pages}


def _profile_cities(db: Session, host_ids: set[UUID]) -> dict[UUID, str]:
    if not host_ids:
        return {}
    profiles = list(
        db.scalars(select(HostProfile).where(HostProfile.host_id.in_(host_ids))).all()
    )
    out: dict[UUID, str] = {}
    for p in profiles:
        if p.city:
            out[p.host_id] = p.city.strip().lower()
    return out


def _resolve_actor_geo(
    db: Session, user_id: UUID
) -> tuple[str | None, str | None, float | None, float | None]:
    pref = db.scalar(
        select(FanConnectLocationPreference).where(
            FanConnectLocationPreference.user_id == user_id
        )
    )
    if pref is None:
        return None, None, None, None
    city = (pref.city or "").strip() or None
    area = (pref.area or "").strip() or None
    if pref.precision == FC.LOCATION_PRECISION_APPROXIMATE:
        from app.events.geo import parse_coord

        lat = parse_coord(pref.latitude_approx)
        lng = parse_coord(pref.longitude_approx)
        if lat is not None and lng is not None:
            return city, area, lat, lng
    from app.events.geo import parse_coord
    from app.events.maps import city_centroid

    centroid = city_centroid(city or "", area or "")
    if centroid:
        lat = parse_coord(centroid[0])
        lng = parse_coord(centroid[1])
        if lat is not None and lng is not None:
            return city, area, lat, lng
    return city, area, None, None


def load_fan_host_affinity(
    db: Session,
    *,
    user_id: UUID,
    own_host_ids: set[UUID] | None = None,
    more_like_host_ids: set[UUID] | None = None,
) -> FanHostAffinity:
    attended_events = _safe_attended_event_ids(db, user_id)
    upcoming_events = _safe_upcoming_ticket_event_ids(db, user_id)
    host_map = _event_host_map(db, attended_events | upcoming_events)

    attended_hosts = {host_map[eid] for eid in attended_events if eid in host_map}
    upcoming_hosts = {host_map[eid] for eid in upcoming_events if eid in host_map}
    ticketed = _ticket_purchase_hosts(db, user_id) | upcoming_hosts

    followed = _followed_host_ids(db, user_id)
    peers = _connected_fan_user_ids(db, user_id)
    network_counts = _network_follow_counts(db, peers)

    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    fav_cats = {
        str(c).strip().lower()
        for c in (passport.favorite_categories or [] if passport else [])
        if str(c).strip()
    }
    fav_cities = {c.lower() for c in favorite_cities_for_user(db, user_id) if c}

    followed_pages = _page_slugs_for_hosts(db, followed)
    followed_cities = _profile_cities(db, followed)
    cat_slugs: set[str] = set()
    city_labels: set[str] = set()
    for hid in followed:
        page = followed_pages.get(hid)
        if page and page.primary_category_slug:
            cat_slugs.add(page.primary_category_slug.lower())
        if page and page.host_type_slug:
            cat_slugs.add(page.host_type_slug.lower())
        if hid in followed_cities:
            city_labels.add(followed_cities[hid])

    more_like_cats: set[str] = set()
    more_like_cities: set[str] = set()
    if more_like_host_ids:
        ml_pages = _page_slugs_for_hosts(db, more_like_host_ids)
        ml_cities = _profile_cities(db, more_like_host_ids)
        for hid in more_like_host_ids:
            page = ml_pages.get(hid)
            if page and page.primary_category_slug:
                more_like_cats.add(page.primary_category_slug.lower())
            if page and page.host_type_slug:
                more_like_cats.add(page.host_type_slug.lower())
            if hid in ml_cities:
                more_like_cities.add(ml_cities[hid])

    loc_city, loc_area, lat, lng = _resolve_actor_geo(db, user_id)

    from app.hosts.recommendations import constants as C
    from app.hosts.recommendations.models import (
        HostRecommendationCategoryHide,
        HostRecommendationFeedback,
    )

    now = datetime.now(UTC)
    hidden_cats: set[str] = set()
    for row in db.scalars(
        select(HostRecommendationCategoryHide).where(
            HostRecommendationCategoryHide.user_id == user_id
        )
    ).all():
        exp = _aware(row.expires_at)
        if exp is not None and exp <= now:
            continue
        hidden_cats.add(row.category_slug.strip().lower())

    penalized: set[str] = set()
    for fb in db.scalars(
        select(HostRecommendationFeedback).where(
            HostRecommendationFeedback.user_id == user_id,
            HostRecommendationFeedback.action == C.FEEDBACK_NOT_INTERESTED,
        ).limit(40)
    ).all():
        ctx = fb.context or {}
        for slug in ctx.get("category_slugs") or []:
            penalized.add(str(slug).lower())

    return FanHostAffinity(
        attended_host_ids=attended_hosts,
        ticketed_host_ids=ticketed,
        followed_host_ids=followed,
        network_host_follow_counts=network_counts,
        favorite_categories=fav_cats,
        favorite_cities=fav_cities,
        followed_category_slugs=cat_slugs,
        followed_city_labels=city_labels,
        location_city=loc_city.lower() if loc_city else None,
        location_area=loc_area.lower() if loc_area else None,
        location_lat=lat,
        location_lng=lng,
        own_host_ids=own_host_ids or set(),
        more_like_category_slugs=more_like_cats,
        more_like_city_labels=more_like_cities,
        hidden_category_slugs=hidden_cats,
        penalized_category_slugs=penalized,
    )


def host_category_slugs(card: dict) -> set[str]:
    slugs: set[str] = set()
    for key in ("primary_category", "host_type"):
        raw = card.get(key)
        if raw:
            slugs.add(str(raw).lower())
    return slugs


def host_city_label(card: dict) -> str | None:
    for key in ("primary_city",):
        raw = card.get(key)
        if raw:
            return str(raw).strip().lower()
    next_ev = card.get("next_upcoming_event") or {}
    city = next_ev.get("city")
    if city:
        return str(city).strip().lower()
    return None


def host_has_upcoming_soon(card: dict, *, within_days: int) -> bool:
    next_ev = card.get("next_upcoming_event")
    if not next_ev or not next_ev.get("start_datetime"):
        return False
    raw = next_ev["start_datetime"]
    if isinstance(raw, datetime):
        start = _aware(raw)
    elif isinstance(raw, str):
        start = _aware(datetime.fromisoformat(raw.replace("Z", "+00:00")))
    else:
        return False
    if start is None:
        return False
    return start <= datetime.now(UTC) + timedelta(days=within_days)
