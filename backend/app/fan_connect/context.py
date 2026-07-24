"""Safe shared public context between two fans."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event
from app.fan_connect import constants as C
from app.fan_connect.models import FanConnectSettings
from app.hosts.models import Host
from app.passport.models import FanPassport
from app.passport.privacy import event_is_safe_for_public_passport, public_city_for_event
from app.tickets.models import Ticket


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _safe_attended_event_ids(db: Session, user_id: UUID) -> set[UUID]:
    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.buyer_user_id == user_id,
                Ticket.status == "checked_in",
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
        if ev and event_is_safe_for_public_passport(
            ev, hide_private_events_always=True
        ):
            out.add(ev.id)
    return out


def _safe_upcoming_ticket_event_ids(db: Session, user_id: UUID) -> set[UUID]:
    """Public-safe upcoming events the fan holds an active ticket for."""
    now = datetime.now(UTC)
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


def _followed_host_ids(db: Session, user_id: UUID) -> set[UUID]:
    return set(
        db.scalars(
            select(HostFollower.host_id).where(HostFollower.user_id == user_id)
        ).all()
    )


def _category_set(passport: FanPassport | None) -> set[str]:
    if passport is None:
        return set()
    return {
        str(c).strip()
        for c in (passport.favorite_categories or [])
        if str(c).strip()
    }


def compute_shared_context(
    db: Session,
    *,
    actor_id: UUID,
    target_id: UUID,
    actor_settings: FanConnectSettings | None = None,
    target_settings: FanConnectSettings | None = None,
    actor_passport: FanPassport | None = None,
    target_passport: FanPassport | None = None,
) -> dict:
    """Return privacy-safe shared chips. Never includes venue/ticket/order."""
    show_events = True
    show_hosts = True
    show_cats = True
    show_city = False
    if actor_settings is not None:
        show_events = show_events and actor_settings.show_shared_public_events
        show_hosts = show_hosts and actor_settings.show_shared_hosts
        show_cats = show_cats and actor_settings.show_shared_categories
        show_city = show_city or actor_settings.show_public_city
    if target_settings is not None:
        show_events = show_events and target_settings.show_shared_public_events
        show_hosts = show_hosts and target_settings.show_shared_hosts
        show_cats = show_cats and target_settings.show_shared_categories
        if actor_settings is not None:
            show_city = bool(
                actor_settings.show_public_city and target_settings.show_public_city
            )
        else:
            show_city = bool(target_settings.show_public_city)

    checked_ids = _safe_attended_event_ids(db, actor_id) & _safe_attended_event_ids(
        db, target_id
    )
    upcoming_ids = _safe_upcoming_ticket_event_ids(
        db, actor_id
    ) & _safe_upcoming_ticket_event_ids(db, target_id)
    # Chip set: upcoming first, then checked-in (public titles only).
    chip_event_ids = list(upcoming_ids) + [i for i in checked_ids if i not in upcoming_ids]

    shared_host_ids = _followed_host_ids(db, actor_id) & _followed_host_ids(
        db, target_id
    )
    shared_cats = sorted(
        _category_set(actor_passport) & _category_set(target_passport)
    )

    events_out: list[dict] = []
    if show_events and chip_event_ids:
        events = {
            e.id: e
            for e in db.scalars(select(Event).where(Event.id.in_(chip_event_ids))).all()
        }
        ordered = [events[i] for i in chip_event_ids if i in events]
        # Upcoming by soonest; checked-in already appended after.
        upcoming_sorted = sorted(
            [e for e in ordered if e.id in upcoming_ids],
            key=lambda e: e.start_datetime or e.created_at,
        )
        checked_sorted = sorted(
            [e for e in ordered if e.id in checked_ids and e.id not in upcoming_ids],
            key=lambda e: e.start_datetime or e.created_at,
            reverse=True,
        )
        for ev in (upcoming_sorted + checked_sorted)[:8]:
            events_out.append(
                {
                    "event_id": ev.id,
                    "title": ev.title,
                    "slug": ev.slug,
                    "path": f"/events/{ev.slug}",
                    "city": public_city_for_event(ev) if show_city else None,
                }
            )

    hosts_out: list[dict] = []
    if show_hosts and shared_host_ids:
        hosts = list(db.scalars(select(Host).where(Host.id.in_(shared_host_ids))).all())
        for h in hosts[:8]:
            hosts_out.append(
                {
                    "host_id": str(h.id),
                    "display_name": h.display_name,
                    "username": h.slug,
                }
            )

    categories_out = shared_cats[:8] if show_cats else []

    return {
        "events": events_out,
        "hosts": hosts_out,
        "categories": categories_out,
        "_has_shared_events": bool(checked_ids or upcoming_ids),
        "_has_shared_hosts": bool(shared_host_ids),
        "_has_shared_categories": bool(shared_cats),
        "_has_shared_upcoming": bool(upcoming_ids),
        "_has_shared_checked_in": bool(checked_ids),
        "_shared_event_ids": list(checked_ids),
        "_shared_upcoming_event_ids": list(upcoming_ids),
        "_shared_host_ids": [str(h) for h in shared_host_ids],
        "_shared_categories": shared_cats,
    }


def has_safe_shared_reason(shared: dict) -> bool:
    return bool(
        shared.get("_has_shared_events")
        or shared.get("_has_shared_upcoming")
        or shared.get("_has_shared_hosts")
        or shared.get("_has_shared_categories")
        or shared.get("_has_shared_badges")
        or shared.get("_has_shared_city")
    )


def public_shared_context(shared: dict) -> dict:
    return {
        "events": shared.get("events") or [],
        "hosts": shared.get("hosts") or [],
        "categories": shared.get("categories") or [],
    }


def safe_reasons_json(shared: dict, db: Session | None = None) -> list[dict]:
    """Store only safe public explanation codes — never private details."""
    if db is not None:
        from app.fan_connect.scoring import FanConnectScoringService

        return FanConnectScoringService().safe_reasons(db, shared)

    # Fallback without DB (generic labels only)
    reasons: list[dict] = []
    if shared.get("_has_shared_upcoming") or shared.get("_has_shared_events"):
        reasons.append(
            {
                "code": C.REASON_SHARED_PUBLIC_EVENT,
                "label": "Shared public events",
            }
        )
    if shared.get("_has_shared_hosts"):
        reasons.append(
            {
                "code": C.REASON_SHARED_HOST,
                "label": "Shared hosts",
            }
        )
    if shared.get("_has_shared_categories"):
        reasons.append(
            {
                "code": C.REASON_SHARED_CATEGORY,
                "label": "Shared categories",
            }
        )
    return reasons


def compute_score(shared: dict) -> float:
    """Delegate to FanConnectScoringService (0–100)."""
    from app.fan_connect.scoring import FanConnectScoringService

    score, _ = FanConnectScoringService().compute_score(shared)
    return float(score)


def policy_allows_shared(policy: str, shared: dict) -> bool:
    """Whether target request_policy is satisfied by safe shared context."""
    if policy == C.POLICY_NOBODY:
        return False
    if policy == C.POLICY_SAME_EVENT:
        return bool(
            shared.get("_has_shared_events") or shared.get("_has_shared_upcoming")
        )
    if policy == C.POLICY_SAME_HOST:
        return bool(
            shared.get("_has_shared_hosts")
            or shared.get("_has_shared_events")
            or shared.get("_has_shared_upcoming")
        )
    return has_safe_shared_reason(shared)
