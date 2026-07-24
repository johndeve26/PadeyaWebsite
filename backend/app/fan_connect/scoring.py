"""Fan Connect matching — FanConnectScoringService (0–100).

Suggestions show only when score >= 40, both sides are eligible, and at least
one safe shared reason exists. Reasons never include VIP, spend, private
events, or hidden venues. Actor lat/lng is one-time matching only — never
returned or stored from suggestion scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.events.geo import discovery_point, haversine_km, parse_coord
from app.events.maps import city_centroid
from app.events.models import Event, EventCategory
from app.fan_connect import constants as C
from app.fan_connect.models import (
    FanConnectSettings,
    FanConnectSuggestionDismissal,
    FanConnectSuggestionFeedback,
    FanConnection,
    FanConnectionReport,
)
from app.hosts.models import Host
from app.messaging import constants as MC
from app.messaging.models import MessageReport
from app.passport.models import FanBadge, FanPassport, UserBadge
from app.passport.privacy import event_is_safe_for_public_passport, public_city_for_event
from app.taxonomy.models import HostTaxonomyLink
from app.tickets.models import Ticket
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@dataclass
class ScoreResult:
    score: int
    reasons: list[dict] = field(default_factory=list)
    recommendation_label: str | None = None
    show: bool = False
    hard_exclusions: list[str] = field(default_factory=list)
    breakdown: dict[str, int] = field(default_factory=dict)
    distance_km: float | None = None
    distance_label: str | None = None
    mutual_connection_count: int = 0
    buckets: list[str] = field(default_factory=list)


class FanConnectScoringService:
    """Weighted matching for Fan Connect suggestions."""

    def evaluate(
        self,
        db: Session,
        *,
        actor: User,
        target: User,
        shared: dict,
        connection: FanConnection | None,
        actor_passport: FanPassport | None,
        target_passport: FanPassport | None,
        actor_settings: FanConnectSettings | None,
        target_settings: FanConnectSettings | None,
        eligible: bool,
        actor_lat: float | None = None,
        actor_lng: float | None = None,
        radius_km: float | None = None,
    ) -> ScoreResult:
        enriched = self.enrich_shared(
            db,
            actor_id=actor.id,
            target_id=target.id,
            shared=shared,
            connection=connection,
            actor=actor,
            target=target,
            actor_passport=actor_passport,
            target_passport=target_passport,
            actor_settings=actor_settings,
            target_settings=target_settings,
            actor_lat=actor_lat,
            actor_lng=actor_lng,
            radius_km=radius_km,
        )
        exclusions = self.hard_exclusions(
            db,
            actor=actor,
            target=target,
            shared=enriched,
            actor_passport=actor_passport,
            target_passport=target_passport,
            actor_settings=actor_settings,
            target_settings=target_settings,
        )
        if exclusions:
            return ScoreResult(score=0, hard_exclusions=exclusions, show=False)

        score, breakdown = self.compute_score(enriched)
        reasons = self.safe_reasons(db, enriched)
        label = self.recommendation_label(score)
        show = (
            eligible
            and score >= C.SCORE_MIN_SHOW
            and bool(reasons)
            and not exclusions
        )
        return ScoreResult(
            score=score,
            reasons=reasons,
            recommendation_label=label if show else None,
            show=show,
            breakdown=breakdown,
            distance_km=enriched.get("_distance_km"),
            distance_label=enriched.get("_distance_label"),
            mutual_connection_count=int(
                enriched.get("_mutual_connection_count") or 0
            ),
            buckets=_bucket_tags(enriched, score),
        )

    def enrich_shared(
        self,
        db: Session,
        *,
        actor_id: UUID,
        target_id: UUID,
        shared: dict,
        connection: FanConnection | None,
        actor: User,
        target: User,
        actor_passport: FanPassport | None,
        target_passport: FanPassport | None,
        actor_settings: FanConnectSettings | None,
        target_settings: FanConnectSettings | None,
        actor_lat: float | None = None,
        actor_lng: float | None = None,
        radius_km: float | None = None,
    ) -> dict:
        """Add private `_` scoring signals; never put unsafe fields in public chips."""
        out = dict(shared)
        upcoming_a = _safe_upcoming_ticket_event_ids(db, actor_id)
        upcoming_b = _safe_upcoming_ticket_event_ids(db, target_id)
        shared_upcoming = upcoming_a & upcoming_b
        out["_shared_upcoming_event_ids"] = list(shared_upcoming)
        out["_has_shared_upcoming"] = bool(shared_upcoming)
        out["_both_ticketed_upcoming"] = bool(shared_upcoming)

        checked = set(out.get("_shared_event_ids") or [])
        out["_has_shared_checked_in"] = bool(checked)

        host_ids = out.get("_shared_host_ids") or []
        out["_shared_host_count"] = len(host_ids)
        cats = out.get("categories") or []
        cat_count = len(out.get("_shared_categories") or cats)
        out["_shared_category_count"] = cat_count

        show_city = bool(
            actor_settings
            and target_settings
            and actor_settings.show_public_city
            and target_settings.show_public_city
        )
        cities_a = _public_cities(db, actor_id) if show_city else set()
        cities_b = _public_cities(db, target_id) if show_city else set()
        shared_cities = sorted(cities_a & cities_b)
        out["_shared_cities"] = shared_cities
        out["_has_shared_city"] = bool(shared_cities)

        areas_a = _public_areas(db, actor_id)
        areas_b = _public_areas(db, target_id)
        shared_areas = sorted(areas_a & areas_b)
        out["_shared_areas"] = shared_areas
        out["_has_shared_area_zone"] = bool(shared_areas)

        badges = _shared_public_badges(db, actor_passport, target_passport)
        out["_shared_badges"] = badges
        out["_has_shared_badges"] = bool(badges)

        out["_both_recently_active"] = _both_recently_active(
            db, actor, target, actor_passport, target_passport
        )
        mutual_n = _mutual_connection_count(db, actor_id, target_id)
        out["_mutual_connection_count"] = mutual_n
        # FoF when shared accepted neighbors exist; mutual not stacked separately.
        out["_has_friend_of_friend"] = mutual_n > 0

        out["_passport_complete"] = _passport_complete(target_passport, target_settings)

        place = _place_affinity(db, actor_id, target_id)
        out.update(place)

        nearby = _nearby_signals(
            db,
            target_id=target_id,
            upcoming_ids=upcoming_b,
            actor_lat=actor_lat,
            actor_lng=actor_lng,
            radius_km=radius_km,
            show_city=show_city,
            target_cities=cities_b,
        )
        out.update(nearby)

        dismiss = _dismissal_state(db, actor_id, target_id)
        out["_dismiss_exclude"] = dismiss["exclude"]
        out["_penalty_dismissed"] = dismiss["penalty"]

        feedback = _feedback_signals(db, actor_id, target_id, out)
        out.update(feedback)

        out["_penalty_recently_declined"] = _recently_declined(connection)
        out["_penalty_too_many_outgoing"] = (
            _outgoing_request_count(db, actor_id) >= C.SCORE_OUTGOING_REQUEST_THRESHOLD
        )
        out["_penalty_low_trust"] = _low_trust(actor, target, actor_passport, target_passport)
        out["_penalty_report_risk"] = _report_risk(db, actor_id, target_id)

        out["_is_fresh_profile"] = _is_fresh_profile(target_passport)

        if shared_upcoming:
            events = list(
                db.scalars(select(Event).where(Event.id.in_(shared_upcoming))).all()
            )
            events.sort(key=lambda e: e.start_datetime or e.created_at)
            out["_upcoming_event_titles"] = [e.title for e in events[:3]]
        else:
            out["_upcoming_event_titles"] = []

        if checked:
            events = list(db.scalars(select(Event).where(Event.id.in_(checked))).all())
            cat_ids = {e.category_id for e in events if e.category_id}
            names: list[str] = []
            if cat_ids:
                names = [
                    c.name
                    for c in db.scalars(
                        select(EventCategory).where(EventCategory.id.in_(cat_ids))
                    ).all()
                ]
            out["_checked_in_category_names"] = names[:3]
            out["_checked_in_event_titles"] = [e.title for e in events[:3]]
        else:
            out["_checked_in_category_names"] = []
            out["_checked_in_event_titles"] = []

        if host_ids:
            hosts = list(
                db.scalars(
                    select(Host).where(Host.id.in_([UUID(h) for h in host_ids]))
                ).all()
            )
            out["_shared_host_names"] = [h.display_name for h in hosts[:3]]
        else:
            out["_shared_host_names"] = []

        return out

    def compute_score(self, shared: dict) -> tuple[int, dict[str, int]]:
        breakdown: dict[str, int] = {}
        score = 0

        # Core event / social
        if shared.get("_has_shared_upcoming"):
            breakdown["upcoming_event"] = C.SCORE_SAME_UPCOMING_EVENT
            score += C.SCORE_SAME_UPCOMING_EVENT

        if shared.get("_has_shared_checked_in"):
            breakdown["checked_in_event"] = C.SCORE_SHARED_CHECKED_IN
            score += C.SCORE_SHARED_CHECKED_IN

        if shared.get("_has_friend_of_friend"):
            breakdown["friend_of_friend"] = C.SCORE_FRIEND_OF_FRIEND
            score += C.SCORE_FRIEND_OF_FRIEND
        # SCORE_MUTUAL_CONNECTION intentionally not stacked with FoF.

        host_n = int(shared.get("_shared_host_count") or 0)
        if host_n:
            host_pts = min(host_n * C.SCORE_SHARED_HOST, C.SCORE_SHARED_HOST_MAX)
            breakdown["shared_hosts"] = host_pts
            score += host_pts

        if int(shared.get("_shared_category_count") or 0) > 0:
            breakdown["shared_categories"] = C.SCORE_SHARED_CATEGORY
            score += C.SCORE_SHARED_CATEGORY

        if shared.get("_passport_complete"):
            breakdown["passport_complete"] = C.SCORE_PASSPORT_COMPLETE
            score += C.SCORE_PASSPORT_COMPLETE

        if shared.get("_both_recently_active"):
            breakdown["recently_active"] = C.SCORE_BOTH_RECENTLY_ACTIVE
            score += C.SCORE_BOTH_RECENTLY_ACTIVE

        # Geolocation — one distance tier only
        dist_pts = int(shared.get("_nearby_distance_points") or 0)
        if dist_pts:
            breakdown["nearby_distance"] = dist_pts
            score += dist_pts

        if shared.get("_has_shared_city"):
            breakdown["shared_city"] = C.SCORE_SHARED_CITY
            score += C.SCORE_SHARED_CITY

        if shared.get("_has_shared_area_zone"):
            breakdown["shared_area_zone"] = C.SCORE_SHARED_AREA_OR_ZONE
            score += C.SCORE_SHARED_AREA_OR_ZONE

        # Personalized place matching
        if shared.get("_similar_attended_categories"):
            breakdown["similar_attended_categories"] = C.SCORE_SIMILAR_ATTENDED_CATEGORIES
            score += C.SCORE_SIMILAR_ATTENDED_CATEGORIES
        if shared.get("_similar_venue_types"):
            breakdown["similar_venue_types"] = C.SCORE_SIMILAR_VENUE_TYPES
            score += C.SCORE_SIMILAR_VENUE_TYPES
        if shared.get("_similar_host_types"):
            breakdown["similar_host_types"] = C.SCORE_SIMILAR_HOST_TYPES
            score += C.SCORE_SIMILAR_HOST_TYPES
        if shared.get("_often_same_area_city"):
            breakdown["often_same_area_city"] = C.SCORE_OFTEN_SAME_AREA_CITY
            score += C.SCORE_OFTEN_SAME_AREA_CITY
        if shared.get("_same_scene"):
            breakdown["same_scene"] = C.SCORE_SAME_SCENE
            score += C.SCORE_SAME_SCENE

        # Feedback
        if shared.get("_boost_similar_views"):
            breakdown["similar_profile_views"] = C.SCORE_SIMILAR_PROFILE_VIEWS
            score += C.SCORE_SIMILAR_PROFILE_VIEWS
        if shared.get("_boost_similar_connects"):
            breakdown["similar_profile_connects"] = C.SCORE_SIMILAR_PROFILE_CONNECTS
            score += C.SCORE_SIMILAR_PROFILE_CONNECTS
        if shared.get("_penalty_dismissed"):
            breakdown["dismissed"] = -C.SCORE_PENALTY_DISMISSED
            score -= C.SCORE_PENALTY_DISMISSED
        if shared.get("_penalty_repeatedly_ignored"):
            breakdown["repeatedly_ignored"] = -C.SCORE_PENALTY_REPEATEDLY_IGNORED
            score -= C.SCORE_PENALTY_REPEATEDLY_IGNORED

        if shared.get("_penalty_recently_declined"):
            breakdown["recently_declined"] = -C.SCORE_PENALTY_RECENTLY_DECLINED
            score -= C.SCORE_PENALTY_RECENTLY_DECLINED
        if shared.get("_penalty_too_many_outgoing"):
            breakdown["too_many_outgoing"] = -C.SCORE_PENALTY_TOO_MANY_OUTGOING
            score -= C.SCORE_PENALTY_TOO_MANY_OUTGOING
        if shared.get("_penalty_low_trust"):
            breakdown["low_trust"] = -C.SCORE_PENALTY_LOW_TRUST
            score -= C.SCORE_PENALTY_LOW_TRUST
        if shared.get("_penalty_report_risk"):
            breakdown["report_risk"] = -C.SCORE_PENALTY_REPORT_RISK
            score -= C.SCORE_PENALTY_REPORT_RISK

        clamped = max(0, min(C.SCORE_MAX, score))
        return clamped, breakdown

    def safe_reasons(self, db: Session | None, shared: dict) -> list[dict]:
        """Human-safe labels only — never VIP, spend, private, GPS, or hidden venue."""
        _ = db
        reasons: list[dict] = []

        for title in shared.get("_upcoming_event_titles") or []:
            reasons.append(
                {
                    "code": C.REASON_SHARED_UPCOMING_EVENT,
                    "label": f"You’re both going to {title}",
                }
            )
            break

        if shared.get("_has_shared_checked_in") and not shared.get("_has_shared_upcoming"):
            titles = shared.get("_checked_in_event_titles") or []
            if titles:
                reasons.append(
                    {
                        "code": C.REASON_SHARED_CHECKED_IN,
                        "label": f"You’re both checked in at {titles[0]}",
                    }
                )
            else:
                cats = shared.get("_checked_in_category_names") or []
                if cats:
                    reasons.append(
                        {
                            "code": C.REASON_SHARED_CHECKED_IN,
                            "label": (
                                f"You both have verified check-ins at {cats[0]} events"
                            ),
                        }
                    )
                else:
                    reasons.append(
                        {
                            "code": C.REASON_SHARED_PUBLIC_EVENT,
                            "label": "You share public event check-ins",
                        }
                    )

        if shared.get("_has_friend_of_friend"):
            n = int(shared.get("_mutual_connection_count") or 0)
            label = (
                f"Connected through {n} mutual fans"
                if n > 1
                else "Connected through someone you know"
            )
            reasons.append({"code": C.REASON_FRIEND_OF_FRIEND, "label": label})

        for name in shared.get("_shared_host_names") or []:
            reasons.append(
                {
                    "code": C.REASON_SHARED_HOST,
                    "label": f"You both follow {name}",
                }
            )
            break

        cats = shared.get("categories") or shared.get("_shared_categories") or []
        if cats:
            reasons.append(
                {
                    "code": C.REASON_SHARED_CATEGORY,
                    "label": f"You both like {cats[0]} events",
                }
            )
        elif shared.get("_similar_attended_category_label"):
            reasons.append(
                {
                    "code": C.REASON_SHARED_CATEGORY,
                    "label": shared["_similar_attended_category_label"],
                }
            )

        if shared.get("_distance_label"):
            reasons.append(
                {
                    "code": C.REASON_NEARBY,
                    "label": shared["_distance_label"],
                }
            )
        elif shared.get("_nearby_area_label"):
            reasons.append(
                {
                    "code": C.REASON_SHARED_PLACE,
                    "label": shared["_nearby_area_label"],
                }
            )

        if shared.get("_has_shared_city") and shared.get("_shared_cities"):
            city = shared["_shared_cities"][0]
            reasons.append(
                {
                    "code": C.REASON_SHARED_CITY,
                    "label": f"You’re both around {city}",
                }
            )
        elif shared.get("_has_shared_area_zone") and shared.get("_shared_areas"):
            area = shared["_shared_areas"][0]
            reasons.append(
                {
                    "code": C.REASON_SHARED_PLACE,
                    "label": f"You both go out around {area}",
                }
            )

        badges = shared.get("_shared_badges") or []
        if badges:
            reasons.append(
                {
                    "code": C.REASON_SHARED_BADGE,
                    "label": f"You both earned the {badges[0]['name']} badge",
                }
            )

        seen: set[str] = set()
        unique: list[dict] = []
        for r in reasons:
            code = r["code"]
            if code in seen or code not in C.SAFE_REASON_CODES:
                continue
            seen.add(code)
            unique.append(r)
        return unique

    def recommendation_label(self, score: int) -> str | None:
        if score >= C.SCORE_LABEL_STRONG:
            return C.LABEL_STRONG
        if score >= C.SCORE_LABEL_GOOD:
            return C.LABEL_GOOD
        if score >= C.SCORE_MIN_SHOW:
            return C.LABEL_SIMILAR
        return None

    def hard_exclusions(
        self,
        db: Session,
        *,
        actor: User,
        target: User,
        shared: dict,
        actor_passport: FanPassport | None,
        target_passport: FanPassport | None,
        actor_settings: FanConnectSettings | None,
        target_settings: FanConnectSettings | None,
    ) -> list[str]:
        denials: list[str] = []
        if has_serious_report(db, actor.id) or has_serious_report(db, target.id):
            denials.append("prior_serious_report")

        if shared.get("_dismiss_exclude"):
            denials.append("dismissed")

        has_safe = bool(
            shared.get("_has_shared_upcoming")
            or shared.get("_has_shared_checked_in")
            or shared.get("_has_shared_hosts")
            or shared.get("_has_shared_categories")
            or shared.get("_has_shared_badges")
            or shared.get("_has_shared_city")
            or shared.get("_has_friend_of_friend")
            or shared.get("_nearby_distance_points")
            or shared.get("_has_shared_area_zone")
            or shared.get("_similar_attended_categories")
            or shared.get("_similar_venue_types")
            or shared.get("_similar_host_types")
            or shared.get("_often_same_area_city")
            or shared.get("_same_scene")
        )
        if not has_safe:
            denials.append("no_safe_shared_reason")

        if actor_settings is not None and not actor_settings.fan_connect_enabled:
            denials.append("actor_connect_off")
        if target_settings is not None and not target_settings.fan_connect_enabled:
            denials.append("target_connect_off")
        if target_settings is not None and not target_settings.allow_connection_requests:
            denials.append("target_requests_off")
        if target_passport is None or target_passport.visibility != "public":
            denials.append("passport_not_public")
        if target_passport is not None and target_passport.admin_hidden_at is not None:
            denials.append("admin_hidden")
        if not actor.is_active or not target.is_active:
            denials.append("inactive")

        return denials


def score_from_shared(shared: dict) -> int:
    svc = FanConnectScoringService()
    score, _ = svc.compute_score(shared)
    return score


def reasons_from_shared(db: Session, shared: dict) -> list[dict]:
    return FanConnectScoringService().safe_reasons(db, shared)


def has_serious_report(db: Session, user_id: UUID) -> bool:
    open_statuses = {C.REPORT_OPEN, C.REPORT_REVIEWING, MC.REPORT_OPEN, MC.REPORT_REVIEWING}

    fc_reports = list(
        db.scalars(
            select(FanConnectionReport).where(
                FanConnectionReport.reported_user_id == user_id,
                FanConnectionReport.status.in_(tuple(open_statuses)),
            )
        ).all()
    )
    msg_reports = list(
        db.scalars(
            select(MessageReport).where(
                MessageReport.reported_user_id == user_id,
                MessageReport.status.in_(tuple(open_statuses)),
            )
        ).all()
    )
    all_open = fc_reports + msg_reports
    if len(all_open) >= C.SCORE_SERIOUS_REPORT_COUNT:
        return True
    for r in all_open:
        blob = f"{r.reason} {r.details or ''}".lower()
        if any(k in blob for k in C.SERIOUS_REPORT_KEYWORDS):
            return True

    resolved = list(
        db.scalars(
            select(FanConnectionReport).where(
                FanConnectionReport.reported_user_id == user_id,
                FanConnectionReport.status == C.REPORT_RESOLVED,
            )
        ).all()
    )
    for r in resolved:
        blob = f"{r.reason} {r.details or ''}".lower()
        if any(k in blob for k in C.SERIOUS_REPORT_KEYWORDS):
            return True
    return False


def _bucket_tags(shared: dict, score: int) -> list[str]:
    tags: list[str] = []
    if score >= C.SCORE_LABEL_STRONG:
        tags.append("strong")
    if shared.get("_nearby_distance_points") or shared.get("_has_shared_city"):
        tags.append("nearby")
    if shared.get("_has_friend_of_friend"):
        tags.append("fof")
    if shared.get("_has_shared_upcoming") or shared.get("_has_shared_checked_in"):
        tags.append("shared_event")
    if shared.get("_is_fresh_profile"):
        tags.append("fresh")
    if shared.get("_shared_category_count") or shared.get("_similar_attended_categories"):
        tags.append("interests")
    return tags


def _safe_upcoming_ticket_event_ids(db: Session, user_id: UUID) -> set[UUID]:
    now = _now()
    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user_id,
                Ticket.status == "active",
            )
        ).all()
    )
    if not tickets:
        return set()
    events = {
        e.id: e
        for e in db.scalars(
            select(Event).where(Event.id.in_({t.event_id for t in tickets}))
        ).all()
    }
    out: set[UUID] = set()
    for t in tickets:
        ev = events.get(t.event_id)
        if ev is None:
            continue
        if not event_is_safe_for_public_passport(ev, hide_private_events_always=True):
            continue
        start = _aware(ev.start_datetime)
        if start is None or start < now:
            continue
        out.add(ev.id)
    return out


def _public_safe_events_for_user(db: Session, user_id: UUID) -> list[Event]:
    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user_id,
                Ticket.status.in_(("checked_in", "active")),
            )
        ).all()
    )
    if not tickets:
        return []
    events = list(
        db.scalars(select(Event).where(Event.id.in_({t.event_id for t in tickets}))).all()
    )
    return [
        ev
        for ev in events
        if event_is_safe_for_public_passport(ev, hide_private_events_always=True)
    ]


def _public_cities(db: Session, user_id: UUID) -> set[str]:
    cities: set[str] = set()
    for ev in _public_safe_events_for_user(db, user_id):
        city = public_city_for_event(ev)
        if city and city.strip():
            cities.add(city.strip())
    return cities


def _public_areas(db: Session, user_id: UUID) -> set[str]:
    areas: set[str] = set()
    for ev in _public_safe_events_for_user(db, user_id):
        area = (ev.area or "").strip()
        if area:
            areas.add(area)
    return areas


def _place_affinity(db: Session, actor_id: UUID, target_id: UUID) -> dict:
    events_a = _public_safe_events_for_user(db, actor_id)
    events_b = _public_safe_events_for_user(db, target_id)
    out: dict = {
        "_similar_attended_categories": False,
        "_similar_venue_types": False,
        "_similar_host_types": False,
        "_often_same_area_city": False,
        "_same_scene": False,
        "_similar_attended_category_label": None,
    }
    if not events_a or not events_b:
        return out

    cat_ids_a = {e.category_id for e in events_a if e.category_id}
    cat_ids_b = {e.category_id for e in events_b if e.category_id}
    shared_cats = cat_ids_a & cat_ids_b
    if shared_cats:
        out["_similar_attended_categories"] = True
        cat = db.get(EventCategory, next(iter(shared_cats)))
        if cat:
            out["_similar_attended_category_label"] = (
                f"You both attend {cat.name} events"
            )

    venues_a = {(e.venue_type or "").strip().lower() for e in events_a if e.venue_type}
    venues_b = {(e.venue_type or "").strip().lower() for e in events_b if e.venue_type}
    if venues_a & venues_b:
        out["_similar_venue_types"] = True

    cities_a = {public_city_for_event(e) for e in events_a}
    cities_b = {public_city_for_event(e) for e in events_b}
    cities_a = {c.strip() for c in cities_a if c and c.strip()}
    cities_b = {c.strip() for c in cities_b if c and c.strip()}
    areas_a = {(e.area or "").strip() for e in events_a if e.area}
    areas_b = {(e.area or "").strip() for e in events_b if e.area}
    if (cities_a & cities_b) or (areas_a & areas_b):
        out["_often_same_area_city"] = True
        shared_area = sorted(areas_a & areas_b)
        shared_city = sorted(cities_a & cities_b)
        place = (shared_area or shared_city or [None])[0]
        if place:
            out["_nearby_area_label"] = f"You both attend events near {place}"

    hosts_a = {e.host_id for e in events_a if e.host_id}
    hosts_b = {e.host_id for e in events_b if e.host_id}
    types_a = _host_type_slugs(db, hosts_a)
    types_b = _host_type_slugs(db, hosts_b)
    if types_a & types_b:
        out["_similar_host_types"] = True

    # Scene ≈ shared public category names from attendance
    if shared_cats or (venues_a & venues_b):
        out["_same_scene"] = True

    return out


def _host_type_slugs(db: Session, host_ids: set[UUID]) -> set[str]:
    if not host_ids:
        return set()
    rows = list(
        db.scalars(
            select(HostTaxonomyLink).where(
                HostTaxonomyLink.host_id.in_(host_ids),
                HostTaxonomyLink.link_type == "host_type",
            )
        ).all()
    )
    return {r.taxonomy_slug for r in rows if r.taxonomy_slug}


def _nearby_signals(
    db: Session,
    *,
    target_id: UUID,
    upcoming_ids: set[UUID],
    actor_lat: float | None,
    actor_lng: float | None,
    radius_km: float | None,
    show_city: bool,
    target_cities: set[str],
) -> dict:
    out: dict = {
        "_nearby_distance_points": 0,
        "_distance_km": None,
        "_distance_label": None,
        "_nearby_area_label": None,
    }
    if actor_lat is None or actor_lng is None:
        return out

    radius = float(radius_km or C.NEARBY_DEFAULT_RADIUS_KM)
    best: float | None = None
    approx = False

    if upcoming_ids:
        events = list(db.scalars(select(Event).where(Event.id.in_(upcoming_ids))).all())
        for ev in events:
            if not event_is_safe_for_public_passport(ev, hide_private_events_always=True):
                continue
            point = discovery_point(ev)
            if point is None:
                continue
            elat, elng, mode = point
            d = haversine_km(actor_lat, actor_lng, elat, elng)
            if best is None or d < best:
                best = d
                approx = mode == "approximate"

    if show_city and target_cities and (best is None or best > 25):
        for city in target_cities:
            centroid = city_centroid(city, None)
            if not centroid:
                continue
            clat = parse_coord(centroid[0])
            clng = parse_coord(centroid[1])
            if clat is None or clng is None:
                continue
            d = haversine_km(actor_lat, actor_lng, clat, clng)
            if best is None or d < best:
                best = d
                approx = True

    if best is None or best > radius:
        return out

    out["_distance_km"] = round(best, 1)
    pts = _distance_points(best)
    out["_nearby_distance_points"] = pts
    out["_distance_label"] = _format_distance_label(best, approximate=approx)
    return out


def _distance_points(km: float) -> int:
    if km <= 2:
        return C.SCORE_NEARBY_WITHIN_2KM
    if km <= 5:
        return C.SCORE_NEARBY_WITHIN_5KM
    if km <= 10:
        return C.SCORE_NEARBY_WITHIN_10KM
    if km <= 25:
        return C.SCORE_NEARBY_WITHIN_25KM
    return 0


def _format_distance_label(km: float, *, approximate: bool) -> str:
    if km < 0.1:
        return "Nearby"
    if km < 10:
        label = f"{km:.1f} km away"
    else:
        label = f"{km:.0f} km away"
    if approximate:
        return f"About {label}"
    return label


def _dismissal_state(db: Session, actor_id: UUID, target_id: UUID) -> dict:
    row = db.scalar(
        select(FanConnectSuggestionDismissal).where(
            FanConnectSuggestionDismissal.actor_user_id == actor_id,
            FanConnectSuggestionDismissal.target_user_id == target_id,
        )
    )
    if row is None:
        return {"exclude": False, "penalty": False}
    expires = _aware(row.expires_at)
    if expires is not None and expires > _now():
        return {"exclude": True, "penalty": False}
    # Expired exclusion window — soft penalty if still recorded
    return {"exclude": False, "penalty": True}


def _feedback_signals(
    db: Session, actor_id: UUID, target_id: UUID, shared: dict
) -> dict:
    """Personalization from feedback history — category/host similarity only."""
    out = {
        "_boost_similar_views": False,
        "_boost_similar_connects": False,
        "_penalty_repeatedly_ignored": False,
    }
    liked = list(
        db.scalars(
            select(FanConnectSuggestionFeedback).where(
                FanConnectSuggestionFeedback.actor_user_id == actor_id,
                FanConnectSuggestionFeedback.action.in_(
                    (C.FEEDBACK_MORE_LIKE_THIS, C.FEEDBACK_CLICK)
                ),
            ).limit(40)
        ).all()
    )
    connected = list(
        db.scalars(
            select(FanConnectSuggestionFeedback).where(
                FanConnectSuggestionFeedback.actor_user_id == actor_id,
                FanConnectSuggestionFeedback.action == C.FEEDBACK_CONNECT_REQUEST,
            ).limit(40)
        ).all()
    )
    # Similar if target shares category/host signals with previously liked targets
    if liked and (
        shared.get("_shared_category_count")
        or shared.get("_similar_attended_categories")
        or shared.get("_shared_host_count")
    ):
        # Boost when actor has engaged similar profiles before
        out["_boost_similar_views"] = True

    if connected and (
        shared.get("_shared_category_count")
        or shared.get("_has_shared_upcoming")
        or shared.get("_shared_host_count")
    ):
        out["_boost_similar_connects"] = True

    impressions = int(
        db.scalar(
            select(func.count())
            .select_from(FanConnectSuggestionFeedback)
            .where(
                FanConnectSuggestionFeedback.actor_user_id == actor_id,
                FanConnectSuggestionFeedback.target_user_id == target_id,
                FanConnectSuggestionFeedback.action == C.FEEDBACK_IMPRESSION,
            )
        )
        or 0
    )
    engaged = int(
        db.scalar(
            select(func.count())
            .select_from(FanConnectSuggestionFeedback)
            .where(
                FanConnectSuggestionFeedback.actor_user_id == actor_id,
                FanConnectSuggestionFeedback.target_user_id == target_id,
                FanConnectSuggestionFeedback.action.in_(
                    (
                        C.FEEDBACK_CLICK,
                        C.FEEDBACK_CONNECT_REQUEST,
                        C.FEEDBACK_MORE_LIKE_THIS,
                    )
                ),
            )
        )
        or 0
    )
    if impressions >= C.FEEDBACK_IGNORE_THRESHOLD and engaged == 0:
        out["_penalty_repeatedly_ignored"] = True

    return out


def _passport_complete(
    passport: FanPassport | None, settings: FanConnectSettings | None
) -> bool:
    if passport is None:
        return False
    has_avatar = bool(passport.avatar_url)
    has_bio = bool((passport.tagline or passport.bio or "").strip())
    has_cats = bool(passport.favorite_categories)
    has_username = bool(passport.username)
    city_ok = settings is None or settings.show_public_city is not None
    return bool(has_username and has_avatar and has_bio and has_cats and city_ok)


def _is_fresh_profile(passport: FanPassport | None) -> bool:
    if passport is None:
        return False
    created = _aware(passport.created_at)
    if created is None:
        return False
    return (_now() - created) <= timedelta(days=C.NEW_PASSPORT_DAYS)


def _shared_public_badges(
    db: Session,
    actor_passport: FanPassport | None,
    target_passport: FanPassport | None,
) -> list[dict]:
    if (
        actor_passport is None
        or target_passport is None
        or not actor_passport.show_badges
        or not target_passport.show_badges
    ):
        return []
    a_ids = set(
        db.scalars(
            select(UserBadge.badge_id).where(UserBadge.user_id == actor_passport.user_id)
        ).all()
    )
    b_ids = set(
        db.scalars(
            select(UserBadge.badge_id).where(UserBadge.user_id == target_passport.user_id)
        ).all()
    )
    shared_ids = a_ids & b_ids
    if not shared_ids:
        return []
    badges = list(
        db.scalars(
            select(FanBadge).where(
                FanBadge.id.in_(shared_ids),
                FanBadge.is_active.is_(True),
            )
        ).all()
    )
    return [
        {"slug": b.slug, "name": b.name, "criteria_key": b.criteria_key}
        for b in badges
    ]


def _both_recently_active(
    db: Session,
    actor: User,
    target: User,
    actor_passport: FanPassport | None,
    target_passport: FanPassport | None,
) -> bool:
    cutoff = _now() - timedelta(days=C.SCORE_RECENT_ACTIVE_DAYS)

    def active(user: User, passport: FanPassport | None) -> bool:
        updated = _aware(passport.updated_at if passport else None)
        if updated and updated >= cutoff:
            return True
        recent = db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.buyer_user_id == user.id,
                Ticket.status.in_(("checked_in", "active")),
                Ticket.updated_at >= cutoff,
            )
        )
        return bool(recent and recent > 0)

    return active(actor, actor_passport) and active(target, target_passport)


def _mutual_connection_count(db: Session, actor_id: UUID, target_id: UUID) -> int:
    actor_others = _connected_user_ids(db, actor_id)
    target_others = _connected_user_ids(db, target_id)
    return len(actor_others & target_others)


def _connected_user_ids(db: Session, user_id: UUID) -> set[UUID]:
    rows = list(
        db.scalars(
            select(FanConnection).where(
                FanConnection.status == C.STATUS_CONNECTED,
                FanConnection.removed_at.is_(None),
                or_(
                    FanConnection.user_low_id == user_id,
                    FanConnection.user_high_id == user_id,
                ),
            )
        ).all()
    )
    out: set[UUID] = set()
    for c in rows:
        other = c.user_high_id if c.user_low_id == user_id else c.user_low_id
        out.add(other)
    return out


def _recently_declined(connection: FanConnection | None) -> bool:
    if connection is None:
        return False
    if connection.status == C.STATUS_DECLINED:
        return True
    declined = _aware(connection.declined_at)
    if declined is None:
        return False
    window = timedelta(days=C.DECLINE_COOLDOWN_DAYS * 2)
    return _now() - declined < window


def _outgoing_request_count(db: Session, user_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(FanConnection)
            .where(
                FanConnection.requester_user_id == user_id,
                FanConnection.status == C.STATUS_REQUEST_SENT,
            )
        )
        or 0
    )


def _low_trust(
    actor: User,
    target: User,
    actor_passport: FanPassport | None,
    target_passport: FanPassport | None,
) -> bool:
    del actor_passport, target_passport
    cutoff = _now() - timedelta(days=C.SCORE_NEW_ACCOUNT_DAYS)

    def newbie(user: User) -> bool:
        created = _aware(user.created_at)
        return bool(created and created >= cutoff)

    return newbie(actor) or newbie(target)


def _report_risk(db: Session, actor_id: UUID, target_id: UUID) -> bool:
    if has_serious_report(db, actor_id) or has_serious_report(db, target_id):
        return True
    open_statuses = (C.REPORT_OPEN, C.REPORT_REVIEWING)
    for uid in (actor_id, target_id):
        n = db.scalar(
            select(func.count())
            .select_from(FanConnectionReport)
            .where(
                FanConnectionReport.reported_user_id == uid,
                FanConnectionReport.status.in_(open_statuses),
            )
        )
        if n and n > 0:
            return True
        m = db.scalar(
            select(func.count())
            .select_from(MessageReport)
            .where(
                MessageReport.reported_user_id == uid,
                MessageReport.status.in_(open_statuses),
            )
        )
        if m and m > 0:
            return True
    return False
