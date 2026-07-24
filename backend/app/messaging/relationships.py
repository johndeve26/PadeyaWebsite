"""Who may message whom — relationship checks (privacy-first)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event
from app.hosts.models import Host
from app.messaging.models import MessageSettings, MessageThread
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.users.models import User


def ensure_settings(db: Session, user: User) -> MessageSettings:
    row = db.scalar(
        select(MessageSettings).where(MessageSettings.user_id == user.id)
    )
    if row is None:
        row = MessageSettings(user_id=user.id)
        db.add(row)
        db.flush()
    return row


def fan_follows_host(db: Session, *, fan_user_id: UUID, host_id: UUID) -> bool:
    return (
        db.scalar(
            select(HostFollower.id).where(
                HostFollower.user_id == fan_user_id,
                HostFollower.host_id == host_id,
            )
        )
        is not None
    )


def fan_bought_from_host(db: Session, *, fan_user_id: UUID, host_id: UUID) -> bool:
    return (
        db.scalar(
            select(Ticket.id)
            .join(Event, Event.id == Ticket.event_id)
            .where(
                Ticket.buyer_user_id == fan_user_id,
                Event.host_id == host_id,
                Ticket.status.in_(["active", "checked_in"]),
            )
            .limit(1)
        )
        is not None
    )


def fan_checked_in_with_host(
    db: Session, *, fan_user_id: UUID, host_id: UUID
) -> bool:
    return (
        db.scalar(
            select(Ticket.id)
            .join(Event, Event.id == Ticket.event_id)
            .where(
                Ticket.buyer_user_id == fan_user_id,
                Event.host_id == host_id,
                Ticket.status == "checked_in",
            )
            .limit(1)
        )
        is not None
    )


def fan_reviewed_host(db: Session, *, fan_user_id: UUID, host_id: UUID) -> bool:
    return (
        db.scalar(
            select(VerifiedReview.id)
            .join(Event, Event.id == VerifiedReview.event_id)
            .where(
                VerifiedReview.reviewer_user_id == fan_user_id,
                Event.host_id == host_id,
            )
            .limit(1)
        )
        is not None
    )


def existing_open_thread(
    db: Session, *, fan_user_id: UUID, host_id: UUID
) -> MessageThread | None:
    return db.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == fan_user_id,
            MessageThread.host_id == host_id,
        )
    )


def host_is_messageable(host: Host) -> bool:
    return host.status not in {"suspended", "banned", "rejected", "inactive"}


def classify_fan_to_host(
    db: Session,
    *,
    fan: User,
    host: Host,
    related_event_id: UUID | None,
) -> tuple[str, str]:
    """
    Returns (access, thread_status_hint).
    access: allowed | request | denied
    """
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    # Host owner must not message their own workspace as an external fan.
    if is_user_owner_of_host(db, user_id=fan.id, host_profile_id=host.id):
        return "denied", "closed"

    host_settings = ensure_settings(db, db.get(User, host.user_id))  # type: ignore[arg-type]
    if host_settings.messaging_suspended_at is not None:
        return "denied", "closed"
    if not fan.is_active or not host_is_messageable(host):
        return "denied", "closed"

    follows = fan_follows_host(db, fan_user_id=fan.id, host_id=host.id)
    buyer = fan_bought_from_host(db, fan_user_id=fan.id, host_id=host.id)
    checked = fan_checked_in_with_host(db, fan_user_id=fan.id, host_id=host.id)
    prior = existing_open_thread(db, fan_user_id=fan.id, host_id=host.id)

    if prior and prior.status not in {"blocked", "closed"}:
        return "allowed", prior.status

    if related_event_id and host_settings.allow_event_inquiries:
        event = db.get(Event, related_event_id)
        if event and event.host_id == host.id:
            if follows or buyer or checked:
                return "allowed", "active"
            if host_settings.allow_messages_from_public_host:
                return "request", "request"

    if follows and host_settings.allow_messages_from_followers:
        return "allowed", "active"
    if buyer and host_settings.allow_messages_from_ticket_buyers:
        return "allowed", "active"
    if checked and host_settings.allow_messages_from_ticket_buyers:
        return "allowed", "active"

    if (
        host_settings.allow_messages_from_public_host
        and host_settings.message_requests_enabled
    ):
        return "request", "request"
    return "denied", "closed"


def classify_host_to_fan(
    db: Session,
    *,
    host: Host,
    fan: User,
) -> tuple[str, str]:
    """Host may only message fans with a real relationship — never directory-only."""
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    # Do not treat the host owner as an external fan inbox target for this host.
    if is_user_owner_of_host(db, user_id=fan.id, host_profile_id=host.id):
        return "denied", "closed"

    fan_settings = ensure_settings(db, fan)
    if fan_settings.messaging_suspended_at is not None:
        return "denied", "closed"
    if not fan.is_active or not host_is_messageable(host):
        return "denied", "closed"

    prior = existing_open_thread(db, fan_user_id=fan.id, host_id=host.id)
    if prior and prior.status not in {"blocked", "closed"}:
        return "allowed", prior.status

    follows = fan_follows_host(db, fan_user_id=fan.id, host_id=host.id)
    buyer = fan_bought_from_host(db, fan_user_id=fan.id, host_id=host.id)
    checked = fan_checked_in_with_host(db, fan_user_id=fan.id, host_id=host.id)
    reviewed = fan_reviewed_host(db, fan_user_id=fan.id, host_id=host.id)

    if follows and fan_settings.allow_messages_from_hosts_i_follow:
        return "allowed", "active"
    if (buyer or checked) and fan_settings.allow_messages_from_hosts_i_attended:
        return "allowed", "active"
    if reviewed and fan_settings.allow_messages_from_hosts_i_attended:
        return "allowed", "active"
    if fan_settings.allow_messages_from_public and fan_settings.message_requests_enabled:
        return "request", "request"
    return "denied", "closed"
