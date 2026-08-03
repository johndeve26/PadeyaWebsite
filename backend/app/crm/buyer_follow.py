"""Auto-follow hosts for paid buyers with host notifications on."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.crm.models import HostFollower
from app.events.models import Event
from app.hosts.models import Host
from app.payments.models import Order
from app.users.models import User

logger = logging.getLogger("padeya.crm.buyer_follow")


def resolve_order_host_id(db: Session, order: Order) -> uuid.UUID | None:
    """Prefer denormalized order.host_id; fall back to the event host."""
    if order.host_id is not None:
        return order.host_id
    if order.event_id is None:
        return None
    event = db.get(Event, order.event_id)
    return event.host_id if event is not None else None


def ensure_buyer_follows_host(
    db: Session,
    *,
    user_id: uuid.UUID,
    host_id: uuid.UUID,
    source: str = "purchase",
) -> HostFollower | None:
    """Ensure a buyer follows the host with marketing notifications on.

    Idempotent. Does not commit. Skips own-host follows, inactive hosts, and
    users restricted from following. Quiet — does not ping the host as a
    "new follower" (purchase-origin).
    """
    from app.hosts.fan_self_abuse import is_user_owner_of_host
    from app.users.restrictions import user_has_restriction

    if is_user_owner_of_host(db, user_id=user_id, host_profile_id=host_id):
        return None
    if user_has_restriction(db, user_id, "cannot_follow_hosts"):
        return None

    host = db.get(Host, host_id)
    if host is None or host.status != "active":
        return None

    existing = db.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host_id,
            HostFollower.user_id == user_id,
        )
    )
    if existing is not None:
        if not existing.marketing_opt_in:
            existing.marketing_opt_in = True
            write_audit_log(
                db,
                action="crm.buyer_follow_notify_on",
                actor_user_id=user_id,
                resource_type="host_follower",
                resource_id=str(existing.id),
                details={"host_id": str(host_id), "source": source},
            )
        return existing

    row = HostFollower(
        host_id=host_id,
        user_id=user_id,
        marketing_opt_in=True,
    )
    db.add(row)
    write_audit_log(
        db,
        action="crm.buyer_follow",
        actor_user_id=user_id,
        resource_type="host",
        resource_id=str(host_id),
        details={"source": source, "marketing_opt_in": True},
    )
    db.flush()
    from app.crm.follower_count import sync_legacy_follower_count

    sync_legacy_follower_count(db, host_id)
    return row


def ensure_paid_order_buyer_follows_host(db: Session, order: Order) -> None:
    """After a paid order has a buyer user, follow the host with notify on."""
    if order.status != "paid":
        return
    if order.buyer_user_id is None:
        return
    host_id = resolve_order_host_id(db, order)
    if host_id is None:
        return
    try:
        ensure_buyer_follows_host(
            db,
            user_id=order.buyer_user_id,
            host_id=host_id,
            source="purchase",
        )
    except Exception:  # noqa: BLE001 — never block paid finalize / claim
        logger.exception(
            "buyer auto-follow failed order=%s buyer=%s host=%s",
            order.id,
            order.buyer_user_id,
            host_id,
        )


def backfill_buyer_follows(db: Session) -> dict[str, int]:
    """Create/opt-in follows for every distinct paid buyer↔host pair.

    Intended for migrations and one-off repair. Does not commit.
    """
    created = 0
    opted_in = 0

    # Event-linked paid orders
    event_pairs = db.execute(
        select(Order.buyer_user_id, Event.host_id)
        .join(Event, Event.id == Order.event_id)
        .where(
            Order.status == "paid",
            Order.buyer_user_id.is_not(None),
            Order.event_id.is_not(None),
        )
        .distinct()
    ).all()

    # Host-shop / merch-only (host_id on order, possibly no event)
    host_pairs = db.execute(
        select(Order.buyer_user_id, Order.host_id)
        .where(
            Order.status == "paid",
            Order.buyer_user_id.is_not(None),
            Order.host_id.is_not(None),
        )
        .distinct()
    ).all()

    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for buyer_id, host_id in [*event_pairs, *host_pairs]:
        if buyer_id is None or host_id is None:
            continue
        key = (buyer_id, host_id)
        if key in seen:
            continue
        seen.add(key)
        before = db.scalar(
            select(HostFollower).where(
                HostFollower.host_id == host_id,
                HostFollower.user_id == buyer_id,
            )
        )
        had = before is not None
        was_on = bool(before.marketing_opt_in) if before is not None else False
        row = ensure_buyer_follows_host(
            db,
            user_id=buyer_id,
            host_id=host_id,
            source="backfill",
        )
        if row is None:
            continue
        if not had:
            created += 1
        elif not was_on and row.marketing_opt_in:
            opted_in += 1

    return {"pairs": len(seen), "created": created, "opted_in": opted_in}
