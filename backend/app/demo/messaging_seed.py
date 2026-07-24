"""Rich, privacy-safe demo content for in-app messaging.

Idempotent: skips fan↔host pairs that already have a thread.
Blocked in production via `seed_demo_data` → `assert_demo_ops_allowed`.

Never seeds: real phones, emails in bodies, WhatsApp, bank/payment links,
private street addresses, hidden venue names, locked Vault content,
order/payment IDs in public copy, or CRM notes. Prefer safe placeholders
(Open your Pàdéyá ticket / Check your dashboard / Use your QR code at
check-in / Your ticket-holder Vault access should unlock / Refresh your
Vault page). Do not encourage moving chats off Pàdéyá.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.demo.constants import (
    DEMO_EMAIL_DOMAIN,
    DEMO_FAN_PERSONAS,
    DEMO_SHOWCASE_EVENTS,
)
from app.demo.messaging_privacy import assert_safe_demo_copy
from app.events.models import Event
from app.hosts.models import Host
from app.messaging import constants as MC
from app.messaging.models import (
    InAppNotification,
    Message,
    MessageBlock,
    MessageReport,
    MessageThread,
)
from app.messaging.relationships import ensure_settings
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import get_user_by_email


def _now() -> datetime:
    return datetime.now(UTC)


def _fan(db: Session, n: int) -> User | None:
    return get_user_by_email(db, f"fan{n}@{DEMO_EMAIL_DOMAIN}")


def _ensure_follow(db: Session, *, fan: User, host: Host) -> None:
    exists = db.scalar(
        select(HostFollower.id).where(
            HostFollower.user_id == fan.id,
            HostFollower.host_id == host.id,
        )
    )
    if exists is None:
        db.add(HostFollower(host_id=host.id, user_id=fan.id, marketing_opt_in=False))
        db.flush()


def _ensure_unfollow(db: Session, *, fan: User, host: Host) -> None:
    """Remove follow so a thread can remain a true message request."""
    row = db.scalar(
        select(HostFollower).where(
            HostFollower.user_id == fan.id,
            HostFollower.host_id == host.id,
        )
    )
    if row is not None:
        db.delete(row)
        db.flush()


def _event(events: dict[str, Event], *keys: str) -> Event | None:
    for key in keys:
        if key in events:
            return events[key]
        prefixed = key if key.startswith("demo-") else None
        if prefixed and prefixed in events:
            return events[prefixed]
    # slug may include demo prefix from seed
    for key in keys:
        for slug, ev in events.items():
            if slug.endswith(key) or slug == key:
                return ev
    return None


def _get_or_skip_thread(
    db: Session, *, fan_id: UUID, host_id: UUID
) -> MessageThread | None:
    """Return existing thread (skip create) or None if we should create."""
    return db.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == fan_id,
            MessageThread.host_id == host_id,
        )
    )


def _ticket_for_event(db: Session, *, fan: User, event: Event | None) -> Ticket | None:
    if event is None:
        return None
    return db.scalar(
        select(Ticket)
        .where(
            Ticket.buyer_user_id == fan.id,
            Ticket.event_id == event.id,
            Ticket.status.in_(("active", "checked_in")),
        )
        .order_by(Ticket.created_at.asc())
        .limit(1)
    )


def _ensure_ticket_for_event(
    db: Session, *, fan: User, event: Event | None
) -> Ticket | None:
    """Return an existing ticket or create one via savepoint (never full-session rollback)."""
    if event is None:
        return None
    existing = _ticket_for_event(db, fan=fan, event=event)
    if existing is not None:
        return existing
    # Lazy imports — avoid circular import at module load; savepoint protects prior threads
    from sqlalchemy.orm import selectinload

    from app.demo.seed import _demo_checkout_answers, _pay_order
    from app.payments.schemas import OrderCreate, OrderItemCreate
    from app.payments.service import create_order

    loaded = db.scalar(
        select(Event)
        .where(Event.id == event.id)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.checkout_questions),
        )
    )
    if loaded is None:
        return None
    publics = [
        t
        for t in loaded.ticket_types
        if t.visibility == "public" and t.status == "active"
    ]
    if not publics:
        return None
    try:
        with db.begin_nested():
            order = create_order(
                db,
                user=fan,
                payload=OrderCreate(
                    event_id=loaded.id,
                    items=[OrderItemCreate(ticket_type_id=publics[0].id, quantity=1)],
                    checkout_answers=_demo_checkout_answers(loaded, buyer_index=920),
                ),
            )
            tickets = _pay_order(db, order, fan)
            return tickets[0] if tickets else None
    except Exception:
        return _ticket_for_event(db, fan=fan, event=event)


def _replace_thread_messages(
    db: Session,
    thread: MessageThread,
    *,
    fan: User,
    host: Host,
    messages: list[tuple[str, str, int]],
) -> Message | None:
    """Replace all messages on a thread (used for scripted demo conversations)."""
    thread.last_message_id = None
    thread.last_message_at = None
    thread.last_message_preview = None
    db.flush()
    for msg in db.scalars(select(Message).where(Message.thread_id == thread.id)).all():
        db.delete(msg)
    db.flush()
    last: Message | None = None
    for role, body, mins_ago in messages:
        assert_safe_demo_copy(body, context="message body")
        created = _now() - timedelta(minutes=mins_ago)
        is_system = role == "system"
        if is_system:
            sender_id = host.user_id
            sender_role = "system"
            msg_type = MC.MESSAGE_TYPE_SYSTEM
        elif role == "fan":
            sender_id = fan.id
            sender_role = "fan"
            msg_type = MC.MESSAGE_TYPE_TEXT
        else:
            sender_id = host.user_id
            sender_role = "host"
            msg_type = MC.MESSAGE_TYPE_TEXT
        msg = Message(
            thread_id=thread.id,
            sender_user_id=sender_id,
            sender_role=sender_role,
            body=body,
            message_type=msg_type,
            status=MC.MESSAGE_STATUS_SENT,
            moderation_status=MC.MOD_CLEAN,
            created_at=created,
            updated_at=created,
        )
        db.add(msg)
        db.flush()
        last = msg
    if last:
        thread.last_message_id = last.id
        thread.last_message_at = last.created_at
        thread.last_message_preview = " ".join(last.body.split())[:220]
    return last


def _upsert_scripted_thread(
    db: Session,
    *,
    fan: User,
    host: Host,
    subject: str,
    status: str,
    messages: list[tuple[str, str, int]],
    event: Event | None = None,
    ticket: Ticket | None = None,
    initiated_by: str = "fan",
    fan_archived: bool = False,
    host_archived: bool = False,
    fan_read_offset_min: int | None = None,
    host_read_offset_min: int | None = None,
    accepted: bool = True,
    script_key: str,
) -> tuple[MessageThread, bool]:
    """Create or refresh a named scripted conversation. Returns (thread, created_new)."""
    existing = _get_or_skip_thread(db, fan_id=fan.id, host_id=host.id)
    created_new = existing is None
    if existing is None:
        initiator = fan.id if initiated_by == "fan" else host.user_id
        thread = MessageThread(
            thread_type=MC.THREAD_TYPE_FAN_HOST,
            fan_user_id=fan.id,
            host_id=host.id,
            host_user_id=host.user_id,
            related_event_id=event.id if event else None,
            related_ticket_id=ticket.id if ticket else None,
            related_order_id=ticket.order_id if ticket else None,
            subject=subject,
            status=status,
            initiated_by_user_id=initiator,
            accepted_at=_now() - timedelta(days=2) if accepted else None,
        )
        db.add(thread)
        db.flush()
    else:
        thread = existing
        thread.subject = subject
        thread.status = status
        thread.related_event_id = event.id if event else None
        thread.related_ticket_id = ticket.id if ticket else None
        thread.related_order_id = ticket.order_id if ticket else None
        if accepted and thread.accepted_at is None:
            thread.accepted_at = _now() - timedelta(days=2)

    # Refresh bodies when missing, wrong count, or script marker mismatch
    current = list(
        db.scalars(
            select(Message)
            .where(Message.thread_id == thread.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    bodies = [m.body for m in current]
    expected = [b for _, b, _ in messages]
    needs_refresh = bodies != expected
    if needs_refresh:
        _replace_thread_messages(
            db, thread, fan=fan, host=host, messages=messages
        )
    last = db.get(Message, thread.last_message_id) if thread.last_message_id else None
    if last is None and messages:
        last = _replace_thread_messages(
            db, thread, fan=fan, host=host, messages=messages
        )

    thread.fan_archived_at = (
        _now() - timedelta(hours=6) if fan_archived else None
    )
    thread.host_archived_at = (
        _now() - timedelta(hours=6) if host_archived else None
    )

    if fan_read_offset_min is not None:
        thread.fan_last_read_at = _now() - timedelta(minutes=fan_read_offset_min)
    elif last and last.sender_role == "fan":
        thread.fan_last_read_at = last.created_at

    if host_read_offset_min is not None:
        thread.host_last_read_at = _now() - timedelta(minutes=host_read_offset_min)
    elif last and last.sender_role == "host":
        thread.host_last_read_at = last.created_at

    # Stash script identity in preview-safe subject already; keep meta via subject prefix if needed
    _ = script_key
    return thread, created_new


def _create_thread(
    db: Session,
    *,
    fan: User,
    host: Host,
    subject: str,
    status: str,
    messages: list[tuple[str, str, int]],
    # messages: (role, body, minutes_ago)
    event: Event | None = None,
    ticket: Ticket | None = None,
    initiated_by: str = "fan",
    fan_archived: bool = False,
    host_archived: bool = False,
    fan_read_offset_min: int | None = None,
    host_read_offset_min: int | None = None,
    accepted: bool = True,
) -> MessageThread | None:
    if _get_or_skip_thread(db, fan_id=fan.id, host_id=host.id) is not None:
        return None

    initiator = fan.id if initiated_by == "fan" else host.user_id
    thread = MessageThread(
        thread_type=MC.THREAD_TYPE_FAN_HOST,
        fan_user_id=fan.id,
        host_id=host.id,
        host_user_id=host.user_id,
        related_event_id=event.id if event else None,
        related_ticket_id=ticket.id if ticket else None,
        related_order_id=ticket.order_id if ticket else None,
        subject=subject,
        status=status,
        initiated_by_user_id=initiator,
        accepted_at=_now() - timedelta(days=2) if accepted else None,
    )
    db.add(thread)
    db.flush()

    last = _replace_thread_messages(
        db, thread, fan=fan, host=host, messages=messages
    )

    if fan_archived:
        thread.fan_archived_at = _now() - timedelta(hours=6)
    if host_archived:
        thread.host_archived_at = _now() - timedelta(hours=6)

    if fan_read_offset_min is not None:
        thread.fan_last_read_at = _now() - timedelta(minutes=fan_read_offset_min)
    elif last and last.sender_role == "fan":
        thread.fan_last_read_at = last.created_at

    if host_read_offset_min is not None:
        thread.host_last_read_at = _now() - timedelta(minutes=host_read_offset_min)
    elif last and last.sender_role == "host":
        thread.host_last_read_at = last.created_at

    return thread


def _notify(
    db: Session,
    *,
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    link_path: str,
    thread_id: UUID | None,
    hours_ago: int = 1,
    read: bool = False,
    read_hours_ago: int = 1,
) -> bool:
    """Create or refresh a safe in-app notification (no full message bodies).

    Returns True when a new row was inserted.
    """
    assert_safe_demo_copy(title, context="notification title")
    assert_safe_demo_copy(body, context="notification body")
    existing: InAppNotification | None = None
    if thread_id is not None:
        existing = db.scalar(
            select(InAppNotification).where(
                InAppNotification.user_id == user_id,
                InAppNotification.thread_id == thread_id,
                InAppNotification.kind == kind,
            )
        )
    read_at = (
        _now() - timedelta(hours=read_hours_ago) if read else None
    )
    if existing is not None:
        existing.title = title[:160]
        existing.body = body[:240]
        existing.link_path = link_path[:300] if link_path else None
        existing.read_at = read_at
        return False
    created = _now() - timedelta(hours=hours_ago)
    db.add(
        InAppNotification(
            user_id=user_id,
            kind=kind,
            title=title[:160],
            body=body[:240],
            link_path=link_path[:300] if link_path else None,
            thread_id=thread_id,
            read_at=read_at,
            created_at=created,
        )
    )
    return True


def _thread_for_pair(
    db: Session, *, fan: User | None, host: Host | None
) -> MessageThread | None:
    if fan is None or host is None:
        return None
    return db.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == fan.id,
            MessageThread.host_id == host.id,
        )
    )


def _seed_message_notifications(
    db: Session,
    *,
    hosts: dict[str, Host],
    fan_by_n: dict[int, User],
) -> int:
    """Seed read/unread message notifications with safe summaries + thread links."""
    maze = hosts.get("djmaze")
    comedy = hosts.get("lagoscomedyhub")
    tech = hosts.get("techconnectafrica")
    praise = hosts.get("praiseexperience")
    mainland = hosts.get("mainlandvibes")
    tolu = fan_by_n.get(1)
    amaka = fan_by_n.get(2)
    chidi = fan_by_n.get(3)
    sade = fan_by_n.get(4)
    ada = fan_by_n.get(7)
    bayo = fan_by_n.get(8)

    created = 0

    # Unread: Amaka — new message from DJ Maze (Vault / Detty thread)
    t_amaka_maze = _thread_for_pair(db, fan=amaka, host=maze)
    if amaka and t_amaka_maze and _notify(
        db,
        user_id=amaka.id,
        kind="host_reply",
        title="New message from DJ Maze",
        body="DJ Maze sent you a new message on Pàdéyá.",
        link_path=f"/dashboard/messages/{t_amaka_maze.id}",
        thread_id=t_amaka_maze.id,
        hours_ago=1,
        read=False,
    ):
        created += 1

    # Unread: Praise host — message request from Ada
    t_ada_praise = _thread_for_pair(db, fan=ada, host=praise)
    if praise and t_ada_praise and _notify(
        db,
        user_id=praise.user_id,
        kind="message_request",
        title="Message request from Ada First Timer",
        body="Ada First Timer sent a message request on Pàdéyá.",
        link_path=f"/host/messages/{t_ada_praise.id}",
        thread_id=t_ada_praise.id,
        hours_ago=0,
        read=False,
    ):
        created += 1

    # Read: Sade — host replied to event question (Maze / After Dark)
    t_sade_maze = _thread_for_pair(db, fan=sade, host=maze)
    if sade and t_sade_maze and _notify(
        db,
        user_id=sade.id,
        kind="host_reply",
        title="Host replied to your event question",
        body="DJ Maze replied to your event question on Pàdéyá.",
        link_path=f"/dashboard/messages/{t_sade_maze.id}",
        thread_id=t_sade_maze.id,
        hours_ago=6,
        read=True,
        read_hours_ago=3,
    ):
        created += 1

    # Unread: Maze host — new message about Afrobeats Night Live (Tolu)
    t_tolu_maze = _thread_for_pair(db, fan=tolu, host=maze)
    if maze and t_tolu_maze and _notify(
        db,
        user_id=maze.user_id,
        kind="fan_reply",
        title="New message about Afrobeats Night Live",
        body="You have a new message about Afrobeats Night Live.",
        link_path=f"/host/messages/{t_tolu_maze.id}",
        thread_id=t_tolu_maze.id,
        hours_ago=0,
        read=False,
    ):
        created += 1

    # Unread: Bayo — report under review (Tech reported thread)
    t_bayo_tech = _thread_for_pair(db, fan=bayo, host=tech)
    if bayo and t_bayo_tech and _notify(
        db,
        user_id=bayo.id,
        kind="report_reviewing",
        title="Your message report is being reviewed",
        body="Pàdéyá is reviewing your message report. We’ll update you here.",
        link_path=f"/dashboard/messages/{t_bayo_tech.id}",
        thread_id=t_bayo_tech.id,
        hours_ago=2,
        read=False,
    ):
        created += 1

    # Read: Tolu — conversation archived (Praise)
    t_tolu_praise = _thread_for_pair(db, fan=tolu, host=praise)
    if tolu and t_tolu_praise and _notify(
        db,
        user_id=tolu.id,
        kind="thread_archived",
        title="Your conversation was archived",
        body="This conversation was moved to your archived inbox on Pàdéyá.",
        link_path=f"/dashboard/messages/{t_tolu_praise.id}",
        thread_id=t_tolu_praise.id,
        hours_ago=12,
        read=True,
        read_hours_ago=10,
    ):
        created += 1

    # Unread: Chidi — Vault-related reply from Tech Connect
    t_chidi_tech = _thread_for_pair(db, fan=chidi, host=tech)
    if chidi and t_chidi_tech and _notify(
        db,
        user_id=chidi.id,
        kind="vault_reply",
        title="New Vault-related reply from Tech Connect Africa",
        body="Tech Connect Africa replied about your Vault access on Pàdéyá.",
        link_path=f"/dashboard/messages/{t_chidi_tech.id}",
        thread_id=t_chidi_tech.id,
        hours_ago=3,
        read=False,
    ):
        created += 1

    # Read: Chidi — Comedy host replied (extra read example)
    t_chidi_comedy = _thread_for_pair(db, fan=chidi, host=comedy)
    if chidi and t_chidi_comedy and _notify(
        db,
        user_id=chidi.id,
        kind="host_reply",
        title="Host replied to your event question",
        body="Lagos Comedy Hub replied to your event question on Pàdéyá.",
        link_path=f"/dashboard/messages/{t_chidi_comedy.id}",
        thread_id=t_chidi_comedy.id,
        hours_ago=8,
        read=True,
        read_hours_ago=4,
    ):
        created += 1

    # Read: Mainland host — Ada event inquiry reply acknowledgment (host-side read)
    t_ada_mainland = _thread_for_pair(db, fan=ada, host=mainland)
    if mainland and t_ada_mainland and _notify(
        db,
        user_id=mainland.user_id,
        kind="fan_reply",
        title="New message about Lagos Creative Market",
        body="You have a new message about Lagos Creative Market.",
        link_path=f"/host/messages/{t_ada_mainland.id}",
        thread_id=t_ada_mainland.id,
        hours_ago=5,
        read=True,
        read_hours_ago=2,
    ):
        created += 1

    return created


# Exact (fan_n, host_slug) pairs retained for inbox QA. All other demo threads
# for these hosts are pruned after seed so host/fan dashboards stay countable.
_INBOX_QA_PAIRS: frozenset[tuple[int, str]] = frozenset(
    {
        (1, "djmaze"),  # Tolu active / Maze ticket + host-unread
        (1, "lagoscomedyhub"),  # Tolu blocked
        (1, "techconnectafrica"),  # Tolu active / fan-unread ticket-holder
        (1, "mainlandvibes"),  # Tolu active
        (1, "praiseexperience"),  # Tolu fan-archived
        (2, "djmaze"),  # Amaka active / Vault + fan-unread
        (2, "lagoscomedyhub"),  # Amaka follower
        (3, "techconnectafrica"),  # Chidi Vault
        (3, "lagoscomedyhub"),  # Chidi event inquiry
        (3, "mainlandvibes"),  # Chidi reported
        (4, "djmaze"),  # Sade Maze event inquiry
        (6, "djmaze"),  # Mira host/fan archived
        (7, "praiseexperience"),  # Ada message request
        (7, "mainlandvibes"),  # Ada event discovery
        (8, "techconnectafrica"),  # Bayo reported (host reported slot)
    }
)


def _prune_to_inbox_qa(
    db: Session,
    *,
    hosts: dict[str, Host],
    fan_by_n: dict[int, User],
) -> int:
    """Delete demo threads outside the inbox QA allowlist for QA hosts."""
    qa_host_ids = {h.id for slug, h in hosts.items() if slug in {p[1] for p in _INBOX_QA_PAIRS}}
    if not qa_host_ids:
        return 0
    allowed: set[tuple[UUID, UUID]] = set()
    for fan_n, host_slug in _INBOX_QA_PAIRS:
        fan = fan_by_n.get(fan_n)
        host = hosts.get(host_slug)
        if fan is None or host is None:
            continue
        allowed.add((fan.id, host.id))

    removed = 0
    threads = list(
        db.scalars(
            select(MessageThread).where(MessageThread.host_id.in_(qa_host_ids))
        ).all()
    )
    for thread in threads:
        key = (thread.fan_user_id, thread.host_id)
        if key in allowed:
            continue
        db.delete(thread)
        removed += 1
    if removed:
        db.flush()
    return removed


# Per-host messaging flags for Legacy / event Message Host CTAs.
_HOST_MESSAGING_SPECS: dict[str, dict[str, object]] = {
    "djmaze": {
        "allow_messages_from_followers": True,
        "allow_messages_from_ticket_buyers": True,
        "allow_messages_from_public_host": True,
        "allow_event_inquiries": True,
        "message_requests_enabled": True,
        "auto_reply_enabled": False,
        "auto_reply_message": None,
    },
    "lagoscomedyhub": {
        "allow_messages_from_followers": True,
        "allow_messages_from_ticket_buyers": True,
        "allow_messages_from_public_host": True,
        "allow_event_inquiries": True,
        "message_requests_enabled": True,
        "auto_reply_enabled": True,
        "auto_reply_message": (
            "Thanks for messaging Lagos Comedy Hub on Pàdéyá. "
            "Keep this conversation here — we’ll reply soon. "
            "Check your dashboard for ticket updates."
        ),
    },
    "techconnectafrica": {
        # Ticket buyers + checked-in attendees (same flag); not cold followers
        "allow_messages_from_followers": False,
        "allow_messages_from_ticket_buyers": True,
        "allow_messages_from_public_host": True,
        "allow_event_inquiries": True,
        "message_requests_enabled": True,
        "auto_reply_enabled": False,
        "auto_reply_message": None,
    },
    "praiseexperience": {
        # Public cold messages become Message Requests
        "allow_messages_from_followers": True,
        "allow_messages_from_ticket_buyers": True,
        "allow_messages_from_public_host": True,
        "allow_event_inquiries": True,
        "message_requests_enabled": True,
        "auto_reply_enabled": False,
        "auto_reply_message": None,
    },
    "mainlandvibes": {
        "allow_messages_from_followers": True,
        "allow_messages_from_ticket_buyers": True,
        "allow_messages_from_public_host": True,
        "allow_event_inquiries": True,
        "message_requests_enabled": True,
        "auto_reply_enabled": False,
        "auto_reply_message": None,
    },
}


def _seed_settings(db: Session, hosts: dict[str, Host], fans: list[User]) -> None:
    for host in hosts.values():
        owner = db.get(User, host.user_id)
        if owner is None:
            continue
        s = ensure_settings(db, owner)
        spec = _HOST_MESSAGING_SPECS.get(host.slug)
        if spec is None:
            s.allow_messages_from_followers = True
            s.allow_messages_from_ticket_buyers = True
            s.allow_messages_from_public_host = True
            s.allow_event_inquiries = True
            s.message_requests_enabled = True
            s.auto_reply_enabled = False
            s.auto_reply_message = None
            continue
        s.allow_messages_from_followers = bool(spec["allow_messages_from_followers"])
        s.allow_messages_from_ticket_buyers = bool(
            spec["allow_messages_from_ticket_buyers"]
        )
        s.allow_messages_from_public_host = bool(spec["allow_messages_from_public_host"])
        s.allow_event_inquiries = bool(spec["allow_event_inquiries"])
        s.message_requests_enabled = bool(spec["message_requests_enabled"])
        s.auto_reply_enabled = bool(spec["auto_reply_enabled"])
        msg = spec.get("auto_reply_message")
        s.auto_reply_message = str(msg) if msg else None
        if s.auto_reply_message:
            assert_safe_demo_copy(s.auto_reply_message, context="auto-reply")

    persona_by_email = {
        str(p["email"]).lower(): p for p in DEMO_FAN_PERSONAS
    }
    for fan in fans:
        s = ensure_settings(db, fan)
        persona = persona_by_email.get((fan.email or "").lower())
        if persona is not None:
            s.allow_messages_from_hosts_i_follow = bool(
                persona.get("allow_messages_from_hosts_i_follow", True)
            )
            s.allow_messages_from_hosts_i_attended = bool(
                persona.get("allow_messages_from_hosts_i_attended", True)
            )
            s.allow_messages_from_public = bool(
                persona.get("allow_messages_from_public", False)
            )
            s.message_requests_enabled = bool(
                persona.get("message_requests_enabled", True)
            )
        else:
            # Volume fans: followed + attended hosts only (never cold public)
            s.allow_messages_from_hosts_i_follow = True
            s.allow_messages_from_hosts_i_attended = True
            s.allow_messages_from_public = False
            s.message_requests_enabled = True


def seed_messaging_demo(
    db: Session,
    *,
    users: dict[str, User],
    hosts: dict[str, Host],
    events: dict[str, Event],
) -> dict[str, Any]:
    """Populate messaging demo. Safe to rerun; returns counts of newly created rows."""
    maze = hosts.get("djmaze")
    comedy = hosts.get("lagoscomedyhub")
    mainland = hosts.get("mainlandvibes")
    tech = hosts.get("techconnectafrica")
    praise = hosts.get("praiseexperience")

    buyer = users.get(f"buyer@{DEMO_EMAIL_DOMAIN}") or get_user_by_email(
        db, f"buyer@{DEMO_EMAIL_DOMAIN}"
    )
    fans = [u for u in (_fan(db, i) for i in range(1, 21)) if u is not None]
    fan_by_n = {i: _fan(db, i) for i in range(1, 21)}

    if not any([maze, comedy, mainland, tech, praise]) or not fans:
        return {
            "threads": 0,
            "messages": 0,
            "reports": 0,
            "blocks": 0,
            "notifications": 0,
            "attachments": 0,
        }

    host_map = {
        k: v
        for k, v in {
            "djmaze": maze,
            "lagoscomedyhub": comedy,
            "mainlandvibes": mainland,
            "techconnectafrica": tech,
            "praiseexperience": praise,
        }.items()
        if v is not None
    }
    _seed_settings(db, host_map, fans + ([buyer] if buyer else []))

    created_threads = 0
    created_messages = 0
    created_reports = 0
    created_blocks = 0
    created_notes = 0
    created_attachments = 0
    tolu_maze_thread: MessageThread | None = None
    bayo_reported_thread: MessageThread | None = None
    f8_bayo: User | None = None

    def track(thread: MessageThread | None, n_msgs: int) -> MessageThread | None:
        nonlocal created_threads, created_messages
        if thread is None:
            return None
        created_threads += 1
        created_messages += n_msgs
        return thread

    detty = _event(events, "detty-friday-live")
    after_dark = _event(events, "mainland-after-dark")
    comedy_night = _event(events, "island-comedy-night")  # Sunday Comedy Room
    laugh_lagos = _event(events, "lagos-comedy-jam")  # Laugh Lagos Live
    food_fest = _event(events, "food-and-flow")
    creative_market = _event(events, "mainland-vibes-summer")
    founders = _event(events, "founders-mixer-lagos")
    product_demo = _event(events, "startup-demo-evening")
    choir_live = _event(events, "praise-experience-live")
    worship = _event(events, "worship-under-stars")
    afrobeats = _event(events, "afrobeats-night-live")

    # --- Conversation 1: Tolu ↔ DJ Maze — Afrobeats Night Live check-in ---
    # Fan read / host unread (latest fan message). Related ticket/order when present.
    f1 = fan_by_n.get(1)  # Tolu Nightlife Explorer (@toluwave)
    if maze and f1 and afrobeats:
        _ensure_follow(db, fan=f1, host=maze)
        ticket = _ticket_for_event(db, fan=f1, event=afrobeats)
        t, created = _upsert_scripted_thread(
            db,
            fan=f1,
            host=maze,
            subject="Check-in — Afrobeats Night Live",
            status=MC.THREAD_STATUS_ACTIVE,
            event=afrobeats,
            ticket=ticket,
            script_key="conv1_tolu_maze_afrobeats",
            # Fan has read latest; host has not (unread count contribution = 1)
            fan_read_offset_min=0,
            host_read_offset_min=45,
            messages=[
                (
                    "system",
                    "This conversation is connected to Afrobeats Night Live.",
                    125,
                ),
                (
                    "fan",
                    "Hi DJ Maze, I already got my ticket for Afrobeats Night Live. "
                    "What time should I arrive for smooth check-in?",
                    120,
                ),
                (
                    "host",
                    "Hey Tolu, thanks for getting your ticket. Doors open at 7 PM and "
                    "check-in is fastest before 8:30 PM.",
                    100,
                ),
                (
                    "fan",
                    "Perfect. Can I use my QR code at check-in from Pàdéyá?",
                    80,
                ),
                (
                    "host",
                    # Final edited body — history + edited_at applied in chat features seed.
                    "Yes — open your Pàdéyá ticket and use your QR code at check-in.",
                    60,
                ),
                (
                    "fan",
                    "Great, thank you. I’m coming with two friends too.",
                    40,
                ),
                (
                    "host",
                    "Nice. Tell them to get their own tickets early so entry is smooth.",
                    25,
                ),
                (
                    "fan",
                    "Done. They’ve both booked now.",
                    15,
                ),
                (
                    "fan",
                    # Reply target: doors / check-in host tip (wired in chat features seed).
                    "Thanks — I’ll aim for 7:15 PM so check-in is easy.",
                    5,
                ),
            ],
        )
        if created:
            track(t, 9)
        tolu_maze_thread = t

    # --- Conversation 2: Amaka ↔ DJ Maze — Detty Friday Rooftop (unread for fan) ---
    f2_amaka = fan_by_n.get(2)  # Amaka Concert Lover (@amakaconcerts)
    if maze and f2_amaka and detty:
        _ensure_follow(db, fan=f2_amaka, host=maze)
        amaka_ticket = _ensure_ticket_for_event(db, fan=f2_amaka, event=detty)
        t2, created2 = _upsert_scripted_thread(
            db,
            fan=f2_amaka,
            host=maze,
            subject="Early entry — Detty Friday Rooftop",
            status=MC.THREAD_STATUS_ACTIVE,
            event=detty,
            ticket=amaka_ticket,
            initiated_by="host",
            script_key="conv2_amaka_maze_detty",
            # Latest messages are from host → unread for fan (= 1 for this thread)
            fan_read_offset_min=9999,
            host_read_offset_min=0,
            messages=[
                (
                    "host",
                    "Hi Amaka, thanks for booking Detty Friday Rooftop. We just opened a "
                    "small early-entry window for ticket holders.",
                    90,
                ),
                (
                    "fan",
                    "That sounds good. Is it automatic with my Pàdéyá ticket?",
                    60,
                ),
                (
                    "host",
                    "Yes. Your ticket shows your entry type at check-in. No extra "
                    "confirmation needed.",
                    30,
                ),
                (
                    "host",
                    "Also, there will be a ticket-holder Vault drop after the event with "
                    "recap clips and photos.",
                    8,
                ),
            ],
        )
        if created2:
            track(t2, 4)

    # --- Conversation 3: Sade ↔ DJ Maze — Mainland After Dark (event inquiry, no ticket) ---
    f4_sade = fan_by_n.get(4)  # Sade Comedy Fan (@sadecomedy)
    if maze and f4_sade and after_dark:
        t3, created3 = _upsert_scripted_thread(
            db,
            fan=f4_sade,
            host=maze,
            subject="About Mainland After Dark",
            status=MC.THREAD_STATUS_ACTIVE,
            event=after_dark,
            ticket=None,
            script_key="conv3_sade_maze_after_dark",
            fan_read_offset_min=5,
            host_read_offset_min=5,
            messages=[
                (
                    "fan",
                    "Hi, I’m thinking of booking Mainland After Dark. Is it a good "
                    "first show if I’m new to the venue?",
                    180,
                ),
                (
                    "host",
                    "Hi Sade. Yes — it’s a relaxed night. Details stay on the Pàdéyá "
                    "event page, including the public area label.",
                    150,
                ),
                (
                    "fan",
                    "Okay, thanks. I’ll check the page and book from there.",
                    120,
                ),
                (
                    "host",
                    "Great. See you at check-in.",
                    90,
                ),
            ],
        )
        t3.related_ticket_id = None
        t3.related_order_id = None
        if created3:
            track(t3, 4)

    # --- Chidi ↔ Lagos Comedy Hub — Sunday Comedy Room (event inquiry) ---
    f3 = fan_by_n.get(3)  # Chidi
    if comedy and f3 and comedy_night:
        _ensure_follow(db, fan=f3, host=comedy)
        t_chidi_comedy, created_cc = _upsert_scripted_thread(
            db,
            fan=f3,
            host=comedy,
            subject="Seating — Sunday Comedy Room",
            status=MC.THREAD_STATUS_ACTIVE,
            event=comedy_night,
            ticket=None,
            script_key="inbox_chidi_comedy_inquiry",
            fan_read_offset_min=10,
            host_read_offset_min=10,
            messages=[
                (
                    "fan",
                    "Is seating assigned for Sunday Comedy Room, or first come first served?",
                    300,
                ),
                (
                    "host",
                    "General admission — arrive early for the best seats. "
                    "Details stay on the Pàdéyá event page.",
                    240,
                ),
                (
                    "fan",
                    "Got it — I’ll book and arrive early. Looking forward to it.",
                    200,
                ),
            ],
        )
        t_chidi_comedy.related_ticket_id = None
        t_chidi_comedy.related_order_id = None
        if created_cc:
            track(t_chidi_comedy, 3)

    # --- Conversation 11: Chidi ↔ Tech Connect — Product Demo Night (Vault access) ---
    # One thread per fan↔host: Chidi↔Tech owns Conv 11 (Vault). Founders Mixer
    # ticket-holder script lives on a volume fan below.
    f3_chidi = fan_by_n.get(3)  # Chidi Tech Regular (@chiditech)
    if tech and f3_chidi and product_demo:
        _ensure_follow(db, fan=f3_chidi, host=tech)
        chidi_demo_ticket = _ticket_for_event(db, fan=f3_chidi, event=product_demo)
        t11, created11 = _upsert_scripted_thread(
            db,
            fan=f3_chidi,
            host=tech,
            subject="Vault access — Product Demo Night",
            status=MC.THREAD_STATUS_ACTIVE,
            event=product_demo,
            ticket=chidi_demo_ticket,
            script_key="conv11_chidi_tech_vault",
            fan_read_offset_min=8,
            host_read_offset_min=8,
            messages=[
                (
                    "fan",
                    "I checked in at Product Demo Night. Should I have access to the "
                    "slide deck in Vault?",
                    200,
                ),
                (
                    "host",
                    "Your ticket-holder Vault access should unlock after check-in.",
                    170,
                ),
                (
                    "fan",
                    "I can see the replay card, but not the slide deck listing.",
                    140,
                ),
                (
                    "host",
                    "Thanks for flagging it. Refresh your Vault page. "
                    "Check your dashboard if access still looks incomplete.",
                    110,
                ),
                (
                    "system",
                    "Refresh your Vault page.",
                    70,
                ),
            ],
        )
        if created11:
            track(t11, 5)

    # --- Tolu ↔ Tech Connect — Founders Mixer (ticket-holder + unread host reply) ---
    f1_tolu_tech = fan_by_n.get(1)
    if tech and f1_tolu_tech and founders:
        _ensure_follow(db, fan=f1_tolu_tech, host=tech)
        tolu_founders_ticket = _ticket_for_event(db, fan=f1_tolu_tech, event=founders)
        t_tolu_tech, created_tt = _upsert_scripted_thread(
            db,
            fan=f1_tolu_tech,
            host=tech,
            subject="Demo circle — Founders Mixer Lagos",
            status=MC.THREAD_STATUS_ACTIVE,
            event=founders,
            ticket=tolu_founders_ticket,
            script_key="inbox_tolu_tech_founders",
            fan_read_offset_min=9999,  # unread host reply for Tolu
            host_read_offset_min=0,
            messages=[
                (
                    "fan",
                    "Hi Tech Connect Africa, will there be time for startup demos at "
                    "Founders Mixer?",
                    200,
                ),
                (
                    "host",
                    "Yes. We have a short demo circle after the first networking session.",
                    170,
                ),
                (
                    "fan",
                    "Do attendees need to apply before demoing?",
                    140,
                ),
                (
                    "host",
                    "For this edition, just arrive early and speak with the host desk "
                    "through your Pàdéyá check-in. Your ticket-holder badge will show "
                    "at the door.",
                    30,
                ),
            ],
        )
        if created_tt:
            track(t_tolu_tech, 4)

    # --- Tolu ↔ Mainland Vibes — Food & Culture Fest (active event inquiry) ---
    f1_tolu_mainland = fan_by_n.get(1)
    if mainland and f1_tolu_mainland and food_fest:
        _ensure_follow(db, fan=f1_tolu_mainland, host=mainland)
        t_tolu_ml, created_tml = _upsert_scripted_thread(
            db,
            fan=f1_tolu_mainland,
            host=mainland,
            subject="Premium experience — Mainland Food & Culture Fest",
            status=MC.THREAD_STATUS_ACTIVE,
            event=food_fest,
            ticket=None,
            script_key="inbox_tolu_mainland_food",
            fan_read_offset_min=10,
            host_read_offset_min=10,
            messages=[
                (
                    "fan",
                    "Hi Mainland Vibes, I saw the premium experience option. What does it include?",
                    160,
                ),
                (
                    "host",
                    "Hi Tolu. It includes priority entry, reserved seating area, and access "
                    "to the premium experience lane.",
                    130,
                ),
                (
                    "fan",
                    "Can I upgrade from a standard ticket?",
                    100,
                ),
                (
                    "host",
                    "Yes, if upgrades are still available. Open your Pàdéyá ticket and "
                    "check available upgrade options.",
                    70,
                ),
                (
                    "fan",
                    "Thanks. I’ll check my dashboard.",
                    40,
                ),
            ],
        )
        if created_tml:
            track(t_tolu_ml, 5)

    # --- Tolu ↔ Praise — fan-archived sample ---
    f1_tolu_praise = fan_by_n.get(1)
    if praise and f1_tolu_praise and choir_live:
        _ensure_follow(db, fan=f1_tolu_praise, host=praise)
        t_tolu_praise, created_tp = _upsert_scripted_thread(
            db,
            fan=f1_tolu_praise,
            host=praise,
            subject="Choir night follow-up (archived)",
            status=MC.THREAD_STATUS_ACTIVE,
            event=choir_live,
            ticket=None,
            fan_archived=True,
            script_key="inbox_tolu_praise_archived",
            fan_read_offset_min=5,
            host_read_offset_min=5,
            messages=[
                (
                    "fan",
                    "Thanks for the choir night info on Pàdéyá.",
                    5000,
                ),
                (
                    "host",
                    "You’re welcome — updates stay on our Legacy Page.",
                    4900,
                ),
                (
                    "system",
                    "This conversation was archived.",
                    4850,
                ),
            ],
        )
        if created_tp:
            track(t_tolu_praise, 3)

    # --- Conversation 7: Mira ↔ DJ Maze — archived for fan + host inbox ---
    f6_mira = fan_by_n.get(6)  # Mira Lagos Explorer (@miralagos)
    if maze and f6_mira and after_dark:
        _ensure_follow(db, fan=f6_mira, host=maze)
        t7, created7 = _upsert_scripted_thread(
            db,
            fan=f6_mira,
            host=maze,
            subject="Thanks — Mainland After Dark",
            status=MC.THREAD_STATUS_ACTIVE,
            event=after_dark,
            ticket=None,
            fan_archived=True,
            host_archived=True,
            script_key="conv7_mira_maze_after_dark",
            fan_read_offset_min=5,
            host_read_offset_min=5,
            messages=[
                (
                    "fan",
                    "Thanks for the last event. The check-in was smooth.",
                    4200,
                ),
                (
                    "host",
                    "Glad you enjoyed it. Your verified review really helps our Legacy Page.",
                    4100,
                ),
                (
                    "fan",
                    "I left a review already.",
                    4000,
                ),
                (
                    "host",
                    "Thank you. We appreciate it.",
                    3900,
                ),
                (
                    "system",
                    "This conversation was archived.",
                    3850,
                ),
            ],
        )
        if created7:
            track(t7, 5)

    # --- Conversation 8: Bayo ↔ Tech Connect — Product Demo Night (reported / admin) ---
    f8_bayo = fan_by_n.get(8)  # Bayo Campus Fan (@bayocampus)
    if tech and f8_bayo and product_demo:
        _ensure_follow(db, fan=f8_bayo, host=tech)
        t8, created8 = _upsert_scripted_thread(
            db,
            fan=f8_bayo,
            host=tech,
            subject="Demo night ticket — Product Demo Night",
            status=MC.THREAD_STATUS_REPORTED,
            event=product_demo,
            ticket=None,
            script_key="conv8_bayo_tech_product_demo",
            fan_read_offset_min=5,
            host_read_offset_min=5,
            messages=[
                (
                    "fan",
                    "Hi, I have a question about the demo night ticket.",
                    500,
                ),
                (
                    "host",
                    "Sure, what would you like to know?",
                    460,
                ),
                (
                    "fan",
                    # Reply to host question (wired in chat features seed); then hidden for QA.
                    "Can I still attend if I arrive late?",
                    420,
                ),
                (
                    "host",
                    "Yes, but check-in may be slower after the first session starts.",
                    380,
                ),
                (
                    "fan",
                    "Okay, thank you.",
                    340,
                ),
                (
                    "system",
                    "A report was submitted for this conversation.",
                    300,
                ),
            ],
        )
        if created8:
            track(t8, 6)
        report8 = db.scalar(
            select(MessageReport).where(
                MessageReport.thread_id == t8.id,
                MessageReport.reporter_user_id == f8_bayo.id,
            )
        )
        # Prefer linking report to the message that will be hidden (not the system notice)
        hide_target = db.scalar(
            select(Message)
            .where(
                Message.thread_id == t8.id,
                Message.body == "Can I still attend if I arrive late?",
            )
            .limit(1)
        )
        last8 = db.get(Message, t8.last_message_id) if t8.last_message_id else None
        report_msg_id = hide_target.id if hide_target else (last8.id if last8 else None)
        admin_notes_reviewing = (
            "Demo admin notes — reviewing for moderation QA. "
            "No private payment or contact data in this thread."
        )
        if report8 is None:
            db.add(
                MessageReport(
                    thread_id=t8.id,
                    message_id=report_msg_id,
                    reporter_user_id=f8_bayo.id,
                    reported_user_id=tech.user_id,
                    reason="other",
                    details="Demo report example for moderation testing.",
                    status=MC.REPORT_REVIEWING,
                    admin_notes=admin_notes_reviewing,
                )
            )
            created_reports += 1
        else:
            report8.message_id = report_msg_id
            report8.reported_user_id = tech.user_id
            report8.reason = "other"
            report8.details = "Demo report example for moderation testing."
            report8.status = MC.REPORT_REVIEWING
            report8.admin_notes = admin_notes_reviewing
        # Hidden message example — participants see moderation placeholder
        if hide_target is not None:
            hide_target.status = MC.MESSAGE_STATUS_HIDDEN
            hide_target.moderation_status = MC.MOD_HIDDEN
        bayo_reported_thread = t8

    # --- Chidi ↔ Mainland Vibes — reported demo thread (fan inbox QA) ---
    f3_chidi_ml = fan_by_n.get(3)
    if mainland and f3_chidi_ml and creative_market:
        _ensure_follow(db, fan=f3_chidi_ml, host=mainland)
        t_chidi_rep, created_cr = _upsert_scripted_thread(
            db,
            fan=f3_chidi_ml,
            host=mainland,
            subject="Vendor hours — Lagos Creative Market",
            status=MC.THREAD_STATUS_REPORTED,
            event=creative_market,
            ticket=None,
            script_key="inbox_chidi_mainland_reported",
            fan_read_offset_min=5,
            host_read_offset_min=5,
            messages=[
                (
                    "fan",
                    "Do market vendors stay open after the performances end?",
                    400,
                ),
                (
                    "host",
                    "Most stay through the closing hour posted on the Pàdéyá event page.",
                    360,
                ),
                (
                    "system",
                    "A report was submitted for this conversation.",
                    320,
                ),
            ],
        )
        if created_cr:
            track(t_chidi_rep, 3)
        report_chidi = db.scalar(
            select(MessageReport).where(
                MessageReport.thread_id == t_chidi_rep.id,
                MessageReport.reporter_user_id == f3_chidi_ml.id,
            )
        )
        last_cr = (
            db.get(Message, t_chidi_rep.last_message_id)
            if t_chidi_rep.last_message_id
            else None
        )
        if report_chidi is None:
            db.add(
                MessageReport(
                    thread_id=t_chidi_rep.id,
                    message_id=last_cr.id if last_cr else None,
                    reporter_user_id=f3_chidi_ml.id,
                    reported_user_id=mainland.user_id,
                    reason="other",
                    details="Demo report example for fan inbox QA.",
                    status=MC.REPORT_OPEN,
                )
            )
            created_reports += 1
        else:
            report_chidi.reason = "other"
            report_chidi.details = "Demo report example for fan inbox QA."
            report_chidi.status = MC.REPORT_OPEN

    # --- Conversation 9: Tolu ↔ Lagos Comedy Hub — Sunday Comedy Room (blocked) ---
    f1_tolu = fan_by_n.get(1)  # Tolu Nightlife Explorer (@toluwave)
    if comedy and f1_tolu and comedy_night:
        _ensure_follow(db, fan=f1_tolu, host=comedy)
        t9, created9 = _upsert_scripted_thread(
            db,
            fan=f1_tolu,
            host=comedy,
            subject="Sunday Comedy Room (blocked)",
            status=MC.THREAD_STATUS_BLOCKED,
            event=comedy_night,
            ticket=None,
            script_key="conv9_tolu_comedy_blocked",
            fan_read_offset_min=5,
            host_read_offset_min=5,
            messages=[
                (
                    "fan",
                    "Can I ask about Sunday Comedy Room?",
                    800,
                ),
                (
                    "host",
                    "Sure. What would you like to know?",
                    760,
                ),
                (
                    "system",
                    "This user has been blocked.",
                    720,
                ),
            ],
        )
        if created9:
            track(t9, 3)
        # This pair used to host the open spam report — drop those so Conv 9 owns the thread
        for stale in db.scalars(
            select(MessageReport).where(MessageReport.thread_id == t9.id)
        ).all():
            db.delete(stale)
        block9 = db.scalar(
            select(MessageBlock).where(
                MessageBlock.blocker_user_id == f1_tolu.id,
                MessageBlock.blocked_user_id == comedy.user_id,
            )
        )
        if block9 is None:
            db.add(
                MessageBlock(
                    blocker_user_id=f1_tolu.id,
                    blocked_user_id=comedy.user_id,
                    host_id=comedy.id,
                    reason="Demo blocked conversation",
                )
            )
            created_blocks += 1
        else:
            block9.host_id = comedy.id
            block9.reason = "Demo blocked conversation"

    # --- Conversation 10: Amaka ↔ Lagos Comedy Hub — Legacy Page (follower, no event) ---
    f2_amaka_comedy = fan_by_n.get(2)  # Amaka Concert Lover (@amakaconcerts)
    if comedy and f2_amaka_comedy:
        _ensure_follow(db, fan=f2_amaka_comedy, host=comedy)
        t10, created10 = _upsert_scripted_thread(
            db,
            fan=f2_amaka_comedy,
            host=comedy,
            subject="Legacy Page — upcoming comedy nights",
            status=MC.THREAD_STATUS_ACTIVE,
            event=None,
            ticket=None,
            script_key="conv10_amaka_comedy_legacy",
            fan_read_offset_min=10,
            host_read_offset_min=10,
            messages=[
                (
                    "fan",
                    "I followed your Legacy Page. Do you post upcoming comedy nights there first?",
                    300,
                ),
                (
                    "host",
                    "Yes. Our Legacy Page shows upcoming shows, reviews, and Vault drops.",
                    260,
                ),
                (
                    "fan",
                    "Nice. I’ll keep checking.",
                    220,
                ),
            ],
        )
        if created10:
            track(t10, 3)
        # Resolved admin report example (thread stays active for inbox QA)
        admin = get_user_by_email(db, f"admin@{DEMO_EMAIL_DOMAIN}")
        if admin is not None:
            resolved = db.scalar(
                select(MessageReport).where(
                    MessageReport.thread_id == t10.id,
                    MessageReport.reporter_user_id == comedy.user_id,
                )
            )
            last10 = db.get(Message, t10.last_message_id) if t10.last_message_id else None
            if resolved is None:
                db.add(
                    MessageReport(
                        thread_id=t10.id,
                        message_id=last10.id if last10 else None,
                        reporter_user_id=comedy.user_id,
                        reported_user_id=f2_amaka_comedy.id,
                        reason="other",
                        details="Earlier misunderstanding — demo resolved case.",
                        status=MC.REPORT_RESOLVED,
                        admin_notes="Demo resolved report.",
                        resolved_by_user_id=admin.id,
                    )
                )
                created_reports += 1
            else:
                resolved.message_id = last10.id if last10 else resolved.message_id
                resolved.reported_user_id = f2_amaka_comedy.id
                resolved.reason = "other"
                resolved.details = "Earlier misunderstanding — demo resolved case."
                resolved.status = MC.REPORT_RESOLVED
                resolved.admin_notes = "Demo resolved report."
                resolved.resolved_by_user_id = admin.id

    # --- Conversation 12: Ada ↔ Mainland Vibes — Lagos Creative Market (event discovery) ---
    f7_ada_mainland = fan_by_n.get(7)  # Ada First Timer (@adafirsttimer)
    if mainland and f7_ada_mainland and creative_market:
        _ensure_follow(db, fan=f7_ada_mainland, host=mainland)
        t12, created12 = _upsert_scripted_thread(
            db,
            fan=f7_ada_mainland,
            host=mainland,
            subject="Attending alone — Lagos Creative Market",
            status=MC.THREAD_STATUS_ACTIVE,
            event=creative_market,
            ticket=None,
            script_key="conv12_ada_mainland_creative",
            fan_read_offset_min=10,
            host_read_offset_min=10,
            messages=[
                (
                    "fan",
                    "Hi, is Lagos Creative Market okay for someone attending alone?",
                    280,
                ),
                (
                    "host",
                    "Yes. It’s a relaxed daytime event with food, vendors, creators, "
                    "and small performances.",
                    240,
                ),
                (
                    "fan",
                    "Great. I’ll book one ticket.",
                    200,
                ),
                (
                    "host",
                    "Nice. Check your dashboard after booking. "
                    "Open your Pàdéyá ticket when you’re ready.",
                    160,
                ),
            ],
        )
        if created12:
            track(t12, 4)

    # --- Conversation 5: Ada ↔ Praise — Worship Night Ibadan (message request / pending) ---
    f7_ada = fan_by_n.get(7)  # Ada First Timer (@adafirsttimer)
    if praise and f7_ada and worship:
        # No follow / no ticket — first-time public inquiry → message request
        _ensure_unfollow(db, fan=f7_ada, host=praise)
        t5, created5 = _upsert_scripted_thread(
            db,
            fan=f7_ada,
            host=praise,
            subject="First event — Worship Night Ibadan",
            status=MC.THREAD_STATUS_REQUEST,
            event=worship,
            ticket=None,
            accepted=False,
            script_key="conv5_ada_praise_worship",
            fan_read_offset_min=5,
            host_read_offset_min=9999,  # unread in host Message Requests
            messages=[
                (
                    "fan",
                    "Hello, this will be my first Pàdéyá event. How does check-in work?",
                    40,
                ),
                (
                    "system",
                    "This conversation is a message request.",
                    39,
                ),
            ],
        )
        t5.related_ticket_id = None
        t5.related_order_id = None
        t5.accepted_at = None
        t5.status = MC.THREAD_STATUS_REQUEST
        if created5:
            track(t5, 2)

    # Guarantee every showcase event is attached to an existing QA thread when possible
    # (never create extra pairs — inbox caps are enforced by prune below).
    _ensure_showcase_event_threads(
        db,
        events=events,
        hosts=host_map,
        fans=fans + ([buyer] if buyer else []),
        track=track,
        create_missing=False,
    )

    created_notes += _seed_message_notifications(
        db, hosts=host_map, fan_by_n=fan_by_n
    )

    # Host-side blocked user for settings screen (no inbox QA thread required)
    f12 = fan_by_n.get(12)
    if maze and f12:
        host_block = db.scalar(
            select(MessageBlock).where(
                MessageBlock.blocker_user_id == maze.user_id,
                MessageBlock.blocked_user_id == f12.id,
            )
        )
        if host_block is None:
            db.add(
                MessageBlock(
                    blocker_user_id=maze.user_id,
                    blocked_user_id=f12.id,
                    host_id=maze.id,
                    reason="Demo blocked user for host message settings QA",
                )
            )
            created_blocks += 1
        else:
            host_block.reason = "Demo blocked user for host message settings QA"
            host_block.host_id = maze.id

    _prune_to_inbox_qa(db, hosts=host_map, fan_by_n=fan_by_n)

    from app.demo.messaging_attachments_seed import (
        seed_reported_thread_attachments,
        seed_tolu_maze_attachments,
    )
    from app.demo.messaging_chat_features_seed import (
        enrich_reported_thread_chat_features,
        enrich_tolu_maze_chat_features,
    )

    chat_feature_counts: dict[str, int] = {
        "edits": 0,
        "replies": 0,
        "pins": 0,
        "stars": 0,
    }

    if tolu_maze_thread is not None and maze is not None and f1 is not None:
        maze_user = db.get(User, maze.user_id)
        if maze_user is not None:
            created_attachments += seed_tolu_maze_attachments(
                db, thread=tolu_maze_thread, maze_user=maze_user
            )
            for key, value in enrich_tolu_maze_chat_features(
                db,
                thread=tolu_maze_thread,
                tolu=f1,
                maze_user=maze_user,
            ).items():
                chat_feature_counts[key] = chat_feature_counts.get(key, 0) + value
    if bayo_reported_thread is not None and f8_bayo is not None:
        created_attachments += seed_reported_thread_attachments(
            db, thread=bayo_reported_thread, uploader=f8_bayo
        )
        for key, value in enrich_reported_thread_chat_features(
            db, thread=bayo_reported_thread
        ).items():
            chat_feature_counts[key] = chat_feature_counts.get(key, 0) + value

    db.commit()
    return {
        "threads": created_threads,
        "messages": created_messages,
        "reports": created_reports,
        "blocks": created_blocks,
        "notifications": created_notes,
        "attachments": created_attachments,
        "chat_features": chat_feature_counts,
    }


def _ensure_showcase_event_threads(
    db: Session,
    *,
    events: dict[str, Event],
    hosts: dict[str, Host],
    fans: list[User],
    track,
    create_missing: bool = True,
) -> None:
    """Attach each DEMO_SHOWCASE_EVENTS row to a fan↔host thread (idempotent)."""
    for row in DEMO_SHOWCASE_EVENTS:
        event = _event(events, row["key"])
        host = hosts.get(row["host_slug"])
        if event is None or host is None:
            continue

        already = db.scalar(
            select(MessageThread.id).where(
                MessageThread.host_id == host.id,
                MessageThread.related_event_id == event.id,
            )
        )
        if already:
            continue

        # Prefer attaching to an existing bare thread for this host
        bare = db.scalar(
            select(MessageThread)
            .where(
                MessageThread.host_id == host.id,
                MessageThread.related_event_id.is_(None),
                MessageThread.status != MC.THREAD_STATUS_BLOCKED,
            )
            .order_by(MessageThread.created_at.asc())
            .limit(1)
        )
        if bare is not None:
            bare.related_event_id = event.id
            if not bare.subject:
                bare.subject = row["title"]
            continue

        if not create_missing:
            continue

        # Otherwise create with a fan who does not yet message this host
        for fan in fans:
            if fan is None:
                continue
            if _get_or_skip_thread(db, fan_id=fan.id, host_id=host.id) is not None:
                continue
            _ensure_follow(db, fan=fan, host=host)
            title = str(row["title"])
            track(
                _create_thread(
                    db,
                    fan=fan,
                    host=host,
                    subject=f"About {title}",
                    status=MC.THREAD_STATUS_ACTIVE,
                    event=event,
                    fan_read_offset_min=15,
                    host_read_offset_min=15,
                    messages=[
                        (
                            "fan",
                            f"Quick question about {title} on Pàdéyá — "
                            "is general admission still available?",
                            90,
                        ),
                        (
                            "host",
                            f"Yes — tickets for {title} are on Pàdéyá. "
                            "See you at check-in!",
                            60,
                        ),
                    ],
                ),
                2,
            )
            break
