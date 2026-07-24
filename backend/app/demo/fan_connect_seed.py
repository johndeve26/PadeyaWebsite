"""Rich Fan Connect demo — settings, relationships, fan↔fan thread.

Idempotent. Privacy-safe reasons and messages only (no private venues,
VIP/spend signals, or contact off-platform).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.models import HostFollower
from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_EVENT_SLUG_PREFIX
from app.demo.messaging_privacy import assert_safe_demo_copy
from app.events.models import Event
from app.fan_connect import constants as C
from app.fan_connect.eligibility import canonical_pair, ensure_connect_settings
from app.fan_connect.models import (
    FanConnection,
    FanConnectionBlock,
    FanConnectionReport,
    FanConnectSuggestion,
)
from app.hosts.models import Host
from app.messaging import constants as MC
from app.messaging import service as messaging_svc
from app.messaging.models import Message, MessageBlock, MessageThread
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PRIVATE
from app.passport.service import ensure_passport
from app.users.models import User
from app.users.service import get_user_by_email


def _now() -> datetime:
    return datetime.now(UTC)


def _fan(db: Session, n: int) -> User | None:
    return get_user_by_email(db, f"fan{n}@{DEMO_EMAIL_DOMAIN}")


def _host(db: Session, hosts: dict[str, Host] | None, slug: str) -> Host | None:
    if hosts and slug in hosts:
        return hosts[slug]
    return db.scalar(select(Host).where(Host.slug == slug))


def _event(
    db: Session, events: dict[str, Event] | None, key: str
) -> Event | None:
    if events and key in events:
        return events[key]
    slug = key if key.startswith(DEMO_EVENT_SLUG_PREFIX) else f"{DEMO_EVENT_SLUG_PREFIX}{key}"
    return db.scalar(select(Event).where(Event.slug == slug))


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


def _apply_settings(row, *, enabled: bool, **flags: Any) -> None:
    from app.fan_connect.policies import (
        normalize_request_policies,
        primary_request_policy,
    )

    row.fan_connect_enabled = enabled
    for key, value in flags.items():
        setattr(row, key, value)
    if "request_policies" in flags:
        policies = normalize_request_policies(flags["request_policies"])
        row.request_policies = policies
        row.request_policy = primary_request_policy(policies)
    elif "request_policy" in flags:
        policies = normalize_request_policies([flags["request_policy"]])
        row.request_policies = policies
        row.request_policy = primary_request_policy(policies)


def _get_pair(db: Session, a: UUID, b: UUID) -> FanConnection | None:
    low, high = canonical_pair(a, b)
    return db.scalar(
        select(FanConnection).where(
            FanConnection.user_low_id == low,
            FanConnection.user_high_id == high,
        )
    )


def _upsert_connection(
    db: Session,
    *,
    requester: User,
    recipient: User,
    status: str,
    score: float,
    reasons: list[dict[str, str]],
    request_message: str | None = None,
    related_event_id: UUID | None = None,
    related_host_id: UUID | None = None,
    message_thread_id: UUID | None = None,
    requested_at: datetime | None = None,
    accepted_at: datetime | None = None,
    removed_at: datetime | None = None,
) -> FanConnection:
    low, high = canonical_pair(requester.id, recipient.id)
    conn = _get_pair(db, requester.id, recipient.id)
    now = _now()
    if conn is None:
        conn = FanConnection(
            user_low_id=low,
            user_high_id=high,
            requester_user_id=requester.id,
            recipient_user_id=recipient.id,
            status=status,
            score=score,
            reasons_json=reasons,
            request_message=request_message,
            related_event_id=related_event_id,
            related_host_id=related_host_id,
            message_thread_id=message_thread_id,
            requested_at=requested_at,
            accepted_at=accepted_at,
            removed_at=removed_at,
        )
        db.add(conn)
    else:
        conn.requester_user_id = requester.id
        conn.recipient_user_id = recipient.id
        conn.status = status
        conn.score = score
        conn.reasons_json = reasons
        conn.request_message = request_message
        conn.related_event_id = related_event_id
        conn.related_host_id = related_host_id
        conn.message_thread_id = message_thread_id
        conn.requested_at = requested_at
        conn.accepted_at = accepted_at
        conn.declined_at = None
        conn.removed_at = removed_at
        conn.updated_at = now
    db.flush()
    return conn


def _close_fan_fan_thread(db: Session, user_a: UUID, user_b: UUID) -> None:
    low, high = (user_a, user_b) if str(user_a) < str(user_b) else (user_b, user_a)
    thread = db.scalar(
        select(MessageThread).where(
            MessageThread.thread_type == MC.THREAD_TYPE_FAN_FAN,
            MessageThread.fan_user_id == low,
            MessageThread.fan_b_user_id == high,
        )
    )
    if thread is not None and thread.status != MC.THREAD_STATUS_CLOSED:
        thread.status = MC.THREAD_STATUS_CLOSED
        db.flush()


def _seed_fan_fan_script(
    db: Session,
    *,
    thread: MessageThread,
    chidi: User,
    bayo: User,
    reasons: list[dict[str, str]],
) -> int:
    """Replace thread messages with the Chidi ↔ Bayo demo script."""
    for msg in db.scalars(select(Message).where(Message.thread_id == thread.id)).all():
        db.delete(msg)
    db.flush()
    thread.last_message_id = None
    thread.last_message_at = None
    thread.last_message_preview = None

    messaging_svc.append_fan_connect_system_message(
        db, thread=thread, actor=chidi, reasons=reasons
    )

    script: list[tuple[User, str, int]] = [
        (
            chidi,
            "Hey Bayo, I saw we’re both going to Product Demo Night. "
            "Are you planning to join the demo circle?",
            50,
        ),
        (
            bayo,
            "Yes, I want to watch first and maybe pitch next time.",
            40,
        ),
        (
            chidi,
            # Final edited body — history applied in chat features seed.
            "Same here. I’m mostly going to meet other builders.",
            30,
        ),
        (
            bayo,
            "Cool. See you there.",
            20,
        ),
        (
            chidi,
            # Reply to Bayo’s “watch first” tip (wired in chat features seed).
            "Perfect — I’ll look for you near the demo circle.",
            10,
        ),
    ]
    last: Message | None = None
    for sender, body, mins_ago in script:
        assert_safe_demo_copy(body, context="fan_fan message body")
        created = _now() - timedelta(minutes=mins_ago)
        msg = Message(
            thread_id=thread.id,
            sender_user_id=sender.id,
            sender_role=MC.SENDER_FAN,
            body=body,
            message_type=MC.MESSAGE_TYPE_TEXT,
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
        thread.status = MC.THREAD_STATUS_ACTIVE
    db.flush()
    return len(script) + 1


def _ensure_suggestion_cache(
    db: Session,
    *,
    user: User,
    suggested: User,
    score: float,
    reasons: list[dict[str, str]],
) -> None:
    row = db.scalar(
        select(FanConnectSuggestion).where(
            FanConnectSuggestion.user_id == user.id,
            FanConnectSuggestion.suggested_user_id == suggested.id,
        )
    )
    expires = _now() + timedelta(days=7)
    if row is None:
        db.add(
            FanConnectSuggestion(
                user_id=user.id,
                suggested_user_id=suggested.id,
                score=score,
                reasons_json=reasons,
                expires_at=expires,
            )
        )
    else:
        row.score = score
        row.reasons_json = reasons
        row.expires_at = expires
    db.flush()


def _ensure_block(db: Session, *, blocker: User, blocked: User, reason: str) -> None:
    fc_block = db.scalar(
        select(FanConnectionBlock).where(
            FanConnectionBlock.blocker_user_id == blocker.id,
            FanConnectionBlock.blocked_user_id == blocked.id,
        )
    )
    if fc_block is None:
        db.add(
            FanConnectionBlock(
                blocker_user_id=blocker.id,
                blocked_user_id=blocked.id,
                reason=reason[:300],
            )
        )
    msg_block = db.scalar(
        select(MessageBlock).where(
            MessageBlock.blocker_user_id == blocker.id,
            MessageBlock.blocked_user_id == blocked.id,
        )
    )
    if msg_block is None:
        db.add(
            MessageBlock(
                blocker_user_id=blocker.id,
                blocked_user_id=blocked.id,
                reason=reason[:300],
            )
        )
    db.flush()


def _ensure_report(
    db: Session,
    *,
    reporter: User,
    reported: User,
    connection: FanConnection | None,
    reason: str,
    details: str,
) -> None:
    existing = db.scalar(
        select(FanConnectionReport).where(
            FanConnectionReport.reporter_user_id == reporter.id,
            FanConnectionReport.reported_user_id == reported.id,
            FanConnectionReport.status == C.REPORT_OPEN,
        )
    )
    if existing is not None:
        return
    assert_safe_demo_copy(details, context="fan connect report")
    db.add(
        FanConnectionReport(
            reporter_user_id=reporter.id,
            reported_user_id=reported.id,
            connection_id=connection.id if connection else None,
            reason=reason[:120],
            details=details[:500],
            status=C.REPORT_OPEN,
        )
    )
    db.flush()


def seed_fan_connect_demo(
    db: Session,
    *,
    hosts: dict[str, Host] | None = None,
    events: dict[str, Event] | None = None,
) -> dict[str, int]:
    """Seed Fan Connect personas, relationships, and Chidi↔Bayo chat."""
    tolu = _fan(db, 1)
    amaka = _fan(db, 2)
    chidi = _fan(db, 3)
    sade = _fan(db, 4)
    kunle = _fan(db, 5)
    mira = _fan(db, 6)
    ada = _fan(db, 7)
    bayo = _fan(db, 8)
    bode = _fan(db, 12)

    required = [tolu, amaka, chidi, sade, kunle, mira, ada, bayo]
    if any(u is None for u in required):
        return {"fan_connect_enabled": 0}

    assert tolu and amaka and chidi and sade and kunle and mira and ada and bayo

    djmaze = _host(db, hosts, "djmaze")
    comedy = _host(db, hosts, "lagoscomedyhub")
    tech = _host(db, hosts, "techconnectafrica")
    afrobeats = _event(db, events, "afrobeats-night-live")
    detty = _event(db, events, "detty-friday-live")
    product_demo = _event(db, events, "startup-demo-evening")

    # Shared public follows for suggestion / request reasons
    if djmaze:
        _ensure_follow(db, fan=tolu, host=djmaze)
        _ensure_follow(db, fan=amaka, host=djmaze)
    if comedy:
        _ensure_follow(db, fan=tolu, host=comedy)
        _ensure_follow(db, fan=sade, host=comedy)
    if tech:
        _ensure_follow(db, fan=chidi, host=tech)
        _ensure_follow(db, fan=bayo, host=tech)

    # --- Settings ---------------------------------------------------------
    enabled = 0

    s_tolu = ensure_connect_settings(db, tolu)
    _apply_settings(
        s_tolu,
        enabled=True,
        allow_connection_requests=True,
        discoverable_for_same_events=True,
        discoverable_for_similar_interests=True,
        show_shared_hosts=True,
        show_shared_categories=True,
        show_shared_public_events=True,
        show_public_city=False,
        hide_private_events_always=True,
        request_policy=C.POLICY_SAME_EVENT,
    )
    enabled += 1

    s_amaka = ensure_connect_settings(db, amaka)
    _apply_settings(
        s_amaka,
        enabled=True,
        allow_connection_requests=True,
        discoverable_for_same_events=True,
        discoverable_for_similar_interests=True,
        show_shared_hosts=True,
        show_shared_categories=True,
        show_shared_public_events=True,
        hide_private_events_always=True,
        request_policy=C.POLICY_SAME_EVENT,
    )
    enabled += 1

    s_chidi = ensure_connect_settings(db, chidi)
    _apply_settings(
        s_chidi,
        enabled=True,
        allow_connection_requests=True,
        discoverable_for_same_events=True,
        discoverable_for_similar_interests=True,
        show_shared_hosts=True,
        show_shared_categories=True,
        show_shared_public_events=True,
        hide_private_events_always=True,
        request_policy=C.POLICY_SAME_HOST,
    )
    enabled += 1

    s_sade = ensure_connect_settings(db, sade)
    _apply_settings(
        s_sade,
        enabled=True,
        allow_connection_requests=True,
        discoverable_for_same_events=True,
        discoverable_for_similar_interests=True,
        show_shared_hosts=True,
        show_shared_categories=True,
        show_shared_public_events=True,
        hide_private_events_always=True,
        request_policy=C.POLICY_SAME_HOST,
    )
    enabled += 1
    sade_pp = ensure_passport(db, sade)
    sade_pp.favorite_categories = ["Comedy"]

    s_kunle = ensure_connect_settings(db, kunle)
    _apply_settings(
        s_kunle,
        enabled=True,
        allow_connection_requests=True,
        discoverable_for_same_events=True,
        discoverable_for_similar_interests=True,
        show_shared_hosts=True,
        show_shared_categories=True,
        show_shared_public_events=True,
        hide_private_events_always=True,
        request_policy=C.POLICY_SAME_EVENT,
    )
    enabled += 1
    kunle_pp = ensure_passport(db, kunle)
    # Public-safe interest labels only — never VIP spend signals in Connect reasons.
    kunle_pp.favorite_categories = ["Nightlife", "Music"]

    # Mira: private Passport → excluded from Connect discovery
    s_mira = ensure_connect_settings(db, mira)
    _apply_settings(
        s_mira,
        enabled=False,
        allow_connection_requests=False,
        discoverable_for_same_events=False,
        discoverable_for_similar_interests=False,
        request_policy=C.POLICY_NOBODY,
    )
    mira_pp = ensure_passport(db, mira)
    mira_pp.visibility = VISIBILITY_PRIVATE
    mira_pp.appear_in_directory = False

    # Ada: Fan Connect disabled → must not appear
    s_ada = ensure_connect_settings(db, ada)
    _apply_settings(
        s_ada,
        enabled=False,
        allow_connection_requests=False,
        discoverable_for_same_events=False,
        discoverable_for_similar_interests=False,
        request_policy=C.POLICY_NOBODY,
    )

    s_bayo = ensure_connect_settings(db, bayo)
    _apply_settings(
        s_bayo,
        enabled=True,
        allow_connection_requests=True,
        discoverable_for_same_events=True,
        discoverable_for_similar_interests=True,
        show_shared_hosts=True,
        show_shared_categories=True,
        show_shared_public_events=True,
        hide_private_events_always=True,
        request_policy=C.POLICY_SAME_HOST,
    )
    enabled += 1
    bayo_pp = ensure_passport(db, bayo)
    cats = list(bayo_pp.favorite_categories or [])
    if "Tech" not in cats:
        bayo_pp.favorite_categories = [*cats, "Tech"]

    if bode is not None:
        s_bode = ensure_connect_settings(db, bode)
        _apply_settings(
            s_bode,
            enabled=True,
            allow_connection_requests=True,
            discoverable_for_same_events=True,
            discoverable_for_similar_interests=True,
            request_policy=C.POLICY_PUBLIC_PASSPORTS,
        )
        enabled += 1

    # Drop obsolete stub pair (Chidi → Tolu pending from earlier seed)
    obsolete = _get_pair(db, chidi.id, tolu.id)
    if obsolete is not None:
        db.delete(obsolete)
        db.flush()

    counts: dict[str, object] = {
        "fan_connect_enabled": enabled,
        "fan_connect_suggested": 0,
        "fan_connect_pending": 0,
        "fan_connect_accepted": 0,
        "fan_connect_blocked": 0,
        "fan_connect_messages": 0,
        "fan_connect_attachments": 0,
        "fan_connect_chat_features": {},
        "fan_connect_reports": 0,
        "fan_connect_excluded": 2,  # Mira + Ada
    }

    # 1) Tolu ↔ Amaka suggested
    tolu_amaka_reasons = [
        {
            "code": C.REASON_SHARED_UPCOMING_EVENT,
            "label": "You’re both going to Afrobeats Night Live",
        },
        {
            "code": C.REASON_SHARED_HOST,
            "label": "You both follow DJ Maze",
        },
    ]
    _upsert_connection(
        db,
        requester=tolu,
        recipient=amaka,
        status=C.STATUS_SUGGESTED,
        score=82.0,
        reasons=tolu_amaka_reasons,
        related_event_id=afrobeats.id if afrobeats else None,
        related_host_id=djmaze.id if djmaze else None,
        message_thread_id=None,
        requested_at=None,
        accepted_at=None,
        removed_at=None,
    )
    _close_fan_fan_thread(db, tolu.id, amaka.id)
    _ensure_suggestion_cache(
        db, user=tolu, suggested=amaka, score=82.0, reasons=tolu_amaka_reasons
    )
    _ensure_suggestion_cache(
        db, user=amaka, suggested=tolu, score=82.0, reasons=tolu_amaka_reasons
    )
    counts["fan_connect_suggested"] = 1

    # 2) Tolu → Sade pending request
    tolu_sade_msg = (
        "Hi Sade, I saw we both follow Lagos Comedy Hub. "
        "Are you going for Sunday Comedy Room?"
    )
    assert_safe_demo_copy(tolu_sade_msg, context="fan connect request")
    tolu_sade_reasons = [
        {
            "code": C.REASON_SHARED_HOST,
            "label": "You both follow Lagos Comedy Hub",
        },
        {
            "code": C.REASON_SHARED_PUBLIC_EVENT,
            "label": "You’re both checked in at Sunday Comedy Room",
        },
    ]
    _upsert_connection(
        db,
        requester=tolu,
        recipient=sade,
        status=C.STATUS_REQUEST_SENT,
        score=68.0,
        reasons=tolu_sade_reasons,
        request_message=tolu_sade_msg[:280],
        related_host_id=comedy.id if comedy else None,
        requested_at=_now() - timedelta(hours=6),
        accepted_at=None,
        message_thread_id=None,
    )
    counts["fan_connect_pending"] += 1

    # 3) Chidi ↔ Bayo connected + fan_fan thread
    chidi_bayo_reasons = [
        {
            "code": C.REASON_SHARED_PUBLIC_EVENT,
            "label": "You’re both going to Product Demo Night",
        },
        {
            "code": C.REASON_SHARED_HOST,
            "label": "You both follow Tech Connect Africa",
        },
    ]
    thread = messaging_svc.ensure_fan_fan_thread(
        db, user_a=chidi.id, user_b=bayo.id, for_accept=True
    )
    conn_cb = _upsert_connection(
        db,
        requester=chidi,
        recipient=bayo,
        status=C.STATUS_CONNECTED,
        score=88.0,
        reasons=chidi_bayo_reasons,
        related_event_id=product_demo.id if product_demo else None,
        related_host_id=tech.id if tech else None,
        message_thread_id=thread.id,
        requested_at=_now() - timedelta(days=3),
        accepted_at=_now() - timedelta(days=2),
    )
    counts["fan_connect_accepted"] = 1
    counts["fan_connect_messages"] = _seed_fan_fan_script(
        db,
        thread=thread,
        chidi=chidi,
        bayo=bayo,
        reasons=chidi_bayo_reasons,
    )
    from app.demo.messaging_attachments_seed import seed_chidi_bayo_attachments
    from app.demo.messaging_chat_features_seed import (
        enrich_chidi_bayo_chat_features,
    )

    counts["fan_connect_attachments"] = seed_chidi_bayo_attachments(
        db, thread=thread, chidi=chidi, bayo=bayo
    )
    counts["fan_connect_chat_features"] = enrich_chidi_bayo_chat_features(
        db, thread=thread, chidi=chidi, bayo=bayo
    )
    # Keep message_thread_id in sync after script rewrite
    conn_cb.message_thread_id = thread.id

    # 4) Amaka → Kunle pending (Detty Friday / premium nightlife interest)
    amaka_kunle_msg = (
        "Hi Kunle — saw we both caught Detty Friday Rooftop. "
        "Want to connect on Pàdéyá?"
    )
    assert_safe_demo_copy(amaka_kunle_msg, context="fan connect request")
    amaka_kunle_reasons = [
        {
            "code": C.REASON_SHARED_PUBLIC_EVENT,
            "label": "You’re both checked in at Detty Friday Rooftop",
        },
        {
            "code": C.REASON_SHARED_CATEGORY,
            "label": "You both like Nightlife",
        },
    ]
    _upsert_connection(
        db,
        requester=amaka,
        recipient=kunle,
        status=C.STATUS_REQUEST_SENT,
        score=72.0,
        reasons=amaka_kunle_reasons,
        request_message=amaka_kunle_msg[:280],
        related_event_id=detty.id if detty else None,
        related_host_id=djmaze.id if djmaze else None,
        requested_at=_now() - timedelta(hours=18),
        accepted_at=None,
        message_thread_id=None,
    )
    counts["fan_connect_pending"] += 1

    # 5) Ada ↔ Mira excluded — no connection rows; settings already off
    pair_am = _get_pair(db, ada.id, mira.id)
    if pair_am is not None:
        db.delete(pair_am)
        db.flush()

    # 6) Tolu ↔ Bode blocked
    if bode is not None:
        blocked_conn = _upsert_connection(
            db,
            requester=tolu,
            recipient=bode,
            status=C.STATUS_BLOCKED,
            score=0.0,
            reasons=[],
            removed_at=_now() - timedelta(days=1),
            message_thread_id=None,
            accepted_at=None,
            requested_at=_now() - timedelta(days=4),
        )
        _ensure_block(
            db,
            blocker=tolu,
            blocked=bode,
            reason="Demo block — excluded from suggestions and messaging.",
        )
        _close_fan_fan_thread(db, tolu.id, bode.id)
        _ensure_report(
            db,
            reporter=tolu,
            reported=bode,
            connection=blocked_conn,
            reason="unwanted_contact",
            details=(
                "Demo Fan Connect report — Bode kept sending requests after I declined. "
                "No private event details included."
            ),
        )
        counts["fan_connect_blocked"] = 1
        counts["fan_connect_reports"] = 1

    db.commit()
    return counts
