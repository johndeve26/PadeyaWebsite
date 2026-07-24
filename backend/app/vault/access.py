"""Server-side Vault access evaluation."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.events.models import Event, TicketType
from app.tickets.models import Ticket
from app.users.models import User
from app.vault.models import VaultAccessRule, VaultItem, VaultPurchase

ACCESS_CODE_HASH_PREFIX = "sha256:"


def hash_access_code(code: str) -> str:
    digest = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()
    return f"{ACCESS_CODE_HASH_PREFIX}{digest}"


def access_code_is_set(rule: VaultAccessRule | None) -> bool:
    return bool(rule and (rule.access_code or "").strip())


def item_is_expired(item: VaultItem, *, now: datetime | None = None) -> bool:
    if item.expires_at is None:
        return False
    current = now or datetime.now(UTC)
    expires = item.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return expires <= current


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def access_window_state(
    rule: VaultAccessRule | None, *, now: datetime | None = None
) -> str | None:
    """Return None if open, else reason code."""
    if rule is None:
        return None
    current = now or datetime.now(UTC)
    starts = _aware(rule.starts_at)
    ends = _aware(rule.ends_at)
    if starts is not None and current < starts:
        return "not_started"
    if ends is not None and current > ends:
        return "access_ended"
    return None


def paid_unlock_count(db: Session, *, item_id: UUID) -> int:
    """Count entitled unlocks for cap checks — prefer grants, fall back to paid purchases."""
    from app.vault.models import VaultAccessGrant

    grant_count = db.scalar(
        select(func.count())
        .select_from(VaultAccessGrant)
        .where(VaultAccessGrant.vault_item_id == item_id)
    )
    if grant_count:
        return int(grant_count)
    count = db.scalar(
        select(func.count())
        .select_from(VaultPurchase)
        .where(
            VaultPurchase.vault_item_id == item_id,
            VaultPurchase.status == "paid",
        )
    )
    return int(count or 0)


def unlock_cap_reached(db: Session, *, item: VaultItem) -> bool:
    rule = item.access_rule
    if rule is None or rule.max_unlocks is None:
        return False
    return paid_unlock_count(db, item_id=item.id) >= int(rule.max_unlocks)


def user_has_vault_grant(db: Session, *, item_id: UUID, user_id: UUID) -> bool:
    from app.vault.models import VaultAccessGrant

    row = db.scalar(
        select(VaultAccessGrant.id).where(
            VaultAccessGrant.vault_item_id == item_id,
            VaultAccessGrant.user_id == user_id,
        )
    )
    return row is not None


def user_has_paid_unlock(db: Session, *, item_id: UUID, user_id: UUID) -> bool:
    """True when the user holds an idempotent grant or a legacy paid purchase."""
    if user_has_vault_grant(db, item_id=item_id, user_id=user_id):
        return True
    row = db.scalar(
        select(VaultPurchase).where(
            VaultPurchase.vault_item_id == item_id,
            VaultPurchase.user_id == user_id,
            VaultPurchase.status == "paid",
        )
    )
    return row is not None


def user_follows_host(db: Session, *, host_id: UUID, user_id: UUID) -> bool:
    row = db.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host_id,
            HostFollower.user_id == user_id,
        )
    )
    return row is not None


def user_holds_host_ticket(
    db: Session,
    *,
    host_id: UUID,
    user_id: UUID,
    vip_only: bool = False,
    event_id: UUID | None = None,
    ticket_type_ids: list[UUID] | None = None,
    require_check_in: bool = False,
) -> bool:
    statuses = ["checked_in"] if require_check_in else ["active", "checked_in"]
    q = (
        select(Ticket.id)
        .join(Event, Event.id == Ticket.event_id)
        .where(
            Event.host_id == host_id,
            Ticket.buyer_user_id == user_id,
            Ticket.status.in_(statuses),
        )
    )
    if event_id is not None:
        q = q.where(Ticket.event_id == event_id)
    if ticket_type_ids:
        q = q.where(Ticket.ticket_type_id.in_(ticket_type_ids))
    if vip_only:
        q = q.join(TicketType, TicketType.id == Ticket.ticket_type_id).where(
            TicketType.type.in_(["vip", "vvip"])
        )
    return db.scalar(q.limit(1)) is not None


def resolve_required_event_id(rule: VaultAccessRule | None, item: VaultItem) -> UUID | None:
    if rule and rule.event_id is not None:
        return rule.event_id
    return item.related_event_id


def resolve_ticket_type_ids(rule: VaultAccessRule | None) -> list[UUID] | None:
    if rule is None:
        return None
    if rule.required_ticket_type_id is not None:
        return [rule.required_ticket_type_id]
    return _parse_ticket_type_ids(rule)


def access_code_matches(rule: VaultAccessRule | None, submitted: str | None) -> bool:
    if rule is None or not rule.access_code or not submitted:
        return False
    expected = rule.access_code.strip()
    got = submitted.strip()
    if not expected or not got:
        return False
    if expected.startswith(ACCESS_CODE_HASH_PREFIX):
        return hmac.compare_digest(expected, hash_access_code(got))
    # Legacy plaintext codes (pre-hash) — compare in constant time
    return hmac.compare_digest(expected, got)


LOCK_REASON_LABELS = {
    "login_required": "Sign in to unlock this drop.",
    "followers_only": "Follow this host to unlock.",
    "ticket_required": "Buy a ticket to this event to unlock.",
    "check_in_required": "Checked-in attendees only.",
    "vip_ticket_required": "VIP ticket holders only.",
    "purchase_required": "Unlock this drop with a one-time purchase.",
    "invite_only": "Invite-only drop.",
    "admin_hidden": "This drop is not publicly available.",
    "expired": "This drop has expired.",
    "not_started": "Access has not started yet.",
    "access_ended": "The access window for this drop has ended.",
    "Item unavailable": "This drop is unavailable.",
    "Item not published": "This drop is not published.",
}


def lock_reason_label(reason: str | None) -> str | None:
    if not reason:
        return None
    return LOCK_REASON_LABELS.get(reason, reason.replace("_", " ").capitalize() + ".")


def evaluate_access(
    db: Session,
    *,
    item: VaultItem,
    user: User | None,
) -> tuple[bool, str]:
    """Return (has_access, reason). Host owner always has access."""
    from app.vault.lifecycle import normalize_item_status

    status = normalize_item_status(item.status)
    if status in {"archived", "hidden_by_admin"} or item.moderation_status == "removed":
        return False, "Item unavailable"
    if status != "published" and (
        user is None or not _is_host_owner(db, item=item, user=user)
    ):
        return False, "Item not published"

    if user is not None and _is_host_owner(db, item=item, user=user):
        return True, "host_owner"

    if item_is_expired(item):
        return False, "expired"

    rule = item.access_rule
    access_type = rule.access_type if rule else "free"

    if access_type == "admin_hidden":
        return False, "admin_hidden"

    window = access_window_state(rule)
    if window is not None:
        return False, window

    # Paid / invite grant always unlocks once recorded (within window)
    if user is not None and user_has_paid_unlock(db, item_id=item.id, user_id=user.id):
        return True, "purchased"

    if access_type == "free":
        return True, "free"

    if user is None:
        return False, "login_required"

    if access_type == "one_time_unlock":
        return False, "purchase_required"

    if access_type == "followers_only":
        if user_follows_host(db, host_id=item.host_id, user_id=user.id):
            return True, "follower"
        return False, "followers_only"

    if access_type == "ticket_holder_only":
        if user_holds_host_ticket(
            db,
            host_id=item.host_id,
            user_id=user.id,
            event_id=resolve_required_event_id(rule, item),
            ticket_type_ids=resolve_ticket_type_ids(rule),
            require_check_in=bool(rule.require_check_in) if rule else False,
        ):
            return True, "ticket_holder"
        return False, "ticket_required"

    if access_type == "checked_in_attendee_only":
        if user_holds_host_ticket(
            db,
            host_id=item.host_id,
            user_id=user.id,
            event_id=resolve_required_event_id(rule, item),
            ticket_type_ids=resolve_ticket_type_ids(rule),
            require_check_in=True,
        ):
            return True, "checked_in_attendee"
        return False, "check_in_required"

    if access_type == "vip_ticket_holder_only":
        if user_holds_host_ticket(
            db,
            host_id=item.host_id,
            user_id=user.id,
            vip_only=True,
            event_id=resolve_required_event_id(rule, item),
            ticket_type_ids=resolve_ticket_type_ids(rule),
            require_check_in=bool(rule.require_check_in) if rule else False,
        ):
            return True, "vip_ticket_holder"
        return False, "vip_ticket_required"

    if access_type == "invite_only":
        # Grant path: paid/invite purchase above, or redeem access code endpoint
        return False, "invite_only"

    return False, "locked"


def _is_host_owner(db: Session, *, item: VaultItem, user: User) -> bool:
    from app.hosts.models import Host

    host = db.get(Host, item.host_id)
    return host is not None and host.user_id == user.id


def _parse_ticket_type_ids(rule: VaultAccessRule | None) -> list[UUID] | None:
    if rule is None or not rule.ticket_type_ids:
        return None
    out: list[UUID] = []
    for value in rule.ticket_type_ids:
        try:
            out.append(UUID(str(value)))
        except ValueError:
            continue
    return out or None


def is_admin_hidden(item: VaultItem) -> bool:
    rule = item.access_rule
    return bool(rule and rule.access_type == "admin_hidden")
