"""Audience resolution for admin notification fan-out."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event, TicketType
from app.hosts.models import Host
from app.merch.models import MerchFulfillment
from app.payments.models import Order
from app.tickets.models import Ticket
from app.users.models import User
from app.vault.models import VaultItem, VaultPurchase


def _active_users(db: Session, ids: list[uuid.UUID]) -> list[uuid.UUID]:
    if not ids:
        return []
    rows = db.scalars(
        select(User.id).where(
            User.id.in_(ids),
            User.is_active.is_(True),
            User.deactivated_at.is_(None),
        )
    ).all()
    return list(rows)


def resolve_notification_audience(
    db: Session,
    *,
    audience: str,
    context: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
    limit: int = 2000,
) -> list[uuid.UUID]:
    """Resolve recipient user ids. Never returns deactivated users."""
    ctx = context or {}
    flt = filters or {}
    audience = (audience or "context_recipients").strip()

    if audience == "selected_users" or audience == "context_recipients":
        raw = ctx.get("recipient_user_ids") or flt.get("user_ids") or []
        if ctx.get("recipient_user_id"):
            raw = list(raw) + [ctx["recipient_user_id"]]
        ids = []
        for item in raw:
            try:
                ids.append(uuid.UUID(str(item)))
            except (TypeError, ValueError):
                continue
        return _active_users(db, ids[:limit])

    if audience == "all_users":
        rows = db.scalars(
            select(User.id)
            .where(User.is_active.is_(True), User.deactivated_at.is_(None))
            .order_by(User.created_at.desc())
            .limit(limit)
        ).all()
        return list(rows)

    host_id = _as_uuid(ctx.get("host_id") or flt.get("host_id"))
    event_id = _as_uuid(ctx.get("event_id") or flt.get("event_id"))

    if audience == "host_followers":
        if host_id is None:
            return []
        rows = db.scalars(
            select(HostFollower.user_id)
            .where(HostFollower.host_id == host_id)
            .distinct()
            .limit(limit)
        ).all()
        host = db.get(Host, host_id)
        ids = [uid for uid in rows if host is None or uid != host.user_id]
        return _active_users(db, ids)

    if audience == "event_ticket_buyers":
        if event_id is None:
            return []
        rows = db.scalars(
            select(Ticket.buyer_user_id)
            .where(
                Ticket.event_id == event_id,
                Ticket.status.in_(("active", "checked_in")),
                Ticket.buyer_user_id.is_not(None),
            )
            .distinct()
            .limit(limit)
        ).all()
        return _active_users(db, [u for u in rows if u])

    if audience == "checked_in_attendees":
        if event_id is None:
            return []
        rows = db.scalars(
            select(Ticket.buyer_user_id)
            .where(
                Ticket.event_id == event_id,
                Ticket.status == "checked_in",
                Ticket.buyer_user_id.is_not(None),
            )
            .distinct()
            .limit(limit)
        ).all()
        return _active_users(db, [u for u in rows if u])

    if audience == "vip_ticket_holders":
        if event_id is None:
            return []
        rows = db.scalars(
            select(Ticket.buyer_user_id)
            .join(TicketType, TicketType.id == Ticket.ticket_type_id)
            .where(
                Ticket.event_id == event_id,
                Ticket.status.in_(("active", "checked_in")),
                Ticket.buyer_user_id.is_not(None),
                TicketType.type.in_(("vip", "vvip")),
            )
            .distinct()
            .limit(limit)
        ).all()
        return _active_users(db, [u for u in rows if u])

    if audience == "past_buyers":
        if host_id is None:
            return []
        event_ids = select(Event.id).where(Event.host_id == host_id)
        rows = db.scalars(
            select(Order.buyer_user_id)
            .where(
                Order.event_id.in_(event_ids),
                Order.status == "paid",
                Order.buyer_user_id.is_not(None),
            )
            .distinct()
            .limit(limit)
        ).all()
        return _active_users(db, [u for u in rows if u])

    if audience == "past_merch_buyers":
        if host_id is None:
            return []
        rows = db.scalars(
            select(MerchFulfillment.buyer_user_id)
            .where(
                MerchFulfillment.host_id == host_id,
                MerchFulfillment.buyer_user_id.is_not(None),
            )
            .distinct()
            .limit(limit)
        ).all()
        return _active_users(db, [u for u in rows if u])

    if audience == "vault_members":
        if host_id is None:
            return []
        host_items = select(VaultItem.id).where(VaultItem.host_id == host_id)
        rows = db.scalars(
            select(VaultPurchase.user_id)
            .where(
                VaultPurchase.status == "paid",
                VaultPurchase.vault_item_id.in_(host_items),
            )
            .distinct()
            .limit(limit)
        ).all()
        return _active_users(db, list(rows))

    if audience == "ambassadors":
        from app.promos.models import Ambassador

        q = select(Ambassador.user_id).where(Ambassador.status == "active")
        if host_id is not None:
            q = q.where(Ambassador.host_id == host_id)
        rows = db.scalars(q.distinct().limit(limit)).all()
        return _active_users(db, list(rows))

    if audience == "host_team_members":
        if host_id is None:
            return []
        from app.hosts.models import HostTeamMember

        rows = db.scalars(
            select(HostTeamMember.user_id)
            .where(
                HostTeamMember.host_id == host_id,
                HostTeamMember.status == "active",
            )
            .distinct()
            .limit(limit)
        ).all()
        return _active_users(db, list(rows))

    if audience == "role":
        role_name = str(flt.get("role") or ctx.get("role") or "").strip()
        if not role_name:
            return []
        from app.users.models import Role

        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            return []
        rows = db.scalars(
            select(User.id)
            .where(
                User.roles.any(Role.id == role.id),
                User.is_active.is_(True),
                User.deactivated_at.is_(None),
            )
            .limit(limit)
        ).all()
        return list(rows)

    if audience == "geo":
        # Soft geo filters on user profile fields when present.
        clauses = [User.is_active.is_(True), User.deactivated_at.is_(None)]
        city = (flt.get("city") or ctx.get("city") or "").strip()
        state = (flt.get("state") or ctx.get("state") or "").strip()
        country = (flt.get("country") or ctx.get("country") or "").strip()
        if city and hasattr(User, "city"):
            clauses.append(func.lower(User.city) == city.lower())
        if state and hasattr(User, "state"):
            clauses.append(func.lower(User.state) == state.lower())
        if country and hasattr(User, "country"):
            clauses.append(func.lower(User.country) == country.lower())
        if len(clauses) <= 2 and not any((city, state, country)):
            return []
        rows = db.scalars(select(User.id).where(*clauses).limit(limit)).all()
        return list(rows)

    return []


def preview_audience_count(
    db: Session,
    *,
    audience: str,
    context: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
) -> int:
    return len(
        resolve_notification_audience(
            db, audience=audience, context=context, filters=filters, limit=5000
        )
    )


def search_users_for_campaign(
    db: Session,
    *,
    q: str | None = None,
    role: str | None = None,
    limit: int = 30,
) -> list[dict]:
    """Safe admin recipient preview fields only."""
    stmt = select(User).where(User.is_active.is_(True), User.deactivated_at.is_(None))
    term = (q or "").strip()
    if term:
        like = f"%{term.lower()}%"
        clauses = [func.lower(User.email).like(like), func.lower(User.full_name).like(like)]
        if hasattr(User, "phone"):
            clauses.append(func.lower(User.phone).like(like))
        stmt = stmt.where(or_(*clauses))
    if role:
        from app.users.models import Role

        r = db.scalar(select(Role).where(Role.name == role))
        if r is not None:
            stmt = stmt.where(User.roles.any(Role.id == r.id))
    users = list(db.scalars(stmt.order_by(User.created_at.desc()).limit(limit)))
    return [
        {
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "roles": [r.name for r in (u.roles or [])],
        }
        for u in users
    ]


def _as_uuid(value: Any) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
