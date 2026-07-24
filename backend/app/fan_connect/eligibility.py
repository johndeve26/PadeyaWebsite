"""Fan Connect eligibility — opt-in + safe shared public context."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.fan_connect import constants as C
from app.fan_connect.context import (
    compute_shared_context,
    has_safe_shared_reason,
    public_shared_context,
)
from app.fan_connect.lifecycle import (
    can_send_request,
    can_suggest,
    requester_cooldown_until,
)
from app.fan_connect.models import (
    FanConnectSettings,
    FanConnection,
    FanConnectionBlock,
)
from app.fan_connect.policies import (
    normalize_request_policies,
    policies_allow_shared,
    primary_request_policy,
)
from app.fan_connect.scoring import has_serious_report
from app.messaging.models import MessageBlock
from app.messaging.relationships import ensure_settings as ensure_message_settings
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PUBLIC, normalize_username
from app.users.models import User


def ensure_connect_settings(db: Session, user: User) -> FanConnectSettings:
    row = db.scalar(
        select(FanConnectSettings).where(FanConnectSettings.user_id == user.id)
    )
    if row is None:
        row = FanConnectSettings(user_id=user.id)
        db.add(row)
        db.flush()
    row.hide_private_events_always = True
    policies = normalize_request_policies(
        list(row.request_policies or []),
        fallback=row.request_policy,
    )
    row.request_policies = policies
    row.request_policy = primary_request_policy(policies)
    return row


def canonical_pair(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    return (a, b) if str(a) < str(b) else (b, a)


def get_connection_pair(
    db: Session, user_a: UUID, user_b: UUID
) -> FanConnection | None:
    low, high = canonical_pair(user_a, user_b)
    return db.scalar(
        select(FanConnection).where(
            FanConnection.user_low_id == low,
            FanConnection.user_high_id == high,
        )
    )


def is_connect_blocked(db: Session, a: UUID, b: UUID) -> bool:
    if (
        db.scalar(
            select(FanConnectionBlock.id).where(
                or_(
                    (FanConnectionBlock.blocker_user_id == a)
                    & (FanConnectionBlock.blocked_user_id == b),
                    (FanConnectionBlock.blocker_user_id == b)
                    & (FanConnectionBlock.blocked_user_id == a),
                )
            )
        )
        is not None
    ):
        return True
    return (
        db.scalar(
            select(MessageBlock.id).where(
                or_(
                    (MessageBlock.blocker_user_id == a)
                    & (MessageBlock.blocked_user_id == b),
                    (MessageBlock.blocker_user_id == b)
                    & (MessageBlock.blocked_user_id == a),
                )
            )
        )
        is not None
    )


def is_messaging_blocked(db: Session, a: UUID, b: UUID) -> bool:
    return is_connect_blocked(db, a, b)


def assert_not_self_fan_connect(*, actor_id: UUID, target_id: UUID) -> None:
    """Block Fan Connect request / accept / suggest / row creation to self."""
    if actor_id == target_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=C.SELF_CONNECT_DETAIL,
        )


def _messaging_suspended(db: Session, user: User) -> bool:
    s = ensure_message_settings(db, user)
    return s.messaging_suspended_at is not None


def viewer_status(conn: FanConnection | None, viewer_id: UUID) -> str | None:
    """Map stored status to viewer-facing status (request_received for recipient)."""
    if conn is None:
        return None
    if conn.status == C.STATUS_REQUEST_SENT:
        if conn.recipient_user_id == viewer_id:
            return C.STATUS_REQUEST_RECEIVED
        return C.STATUS_REQUEST_SENT
    return conn.status


def classify_fan_connect(
    db: Session,
    *,
    actor: User,
    target: User,
    for_discovery: bool = False,
    for_new_request: bool = True,
) -> dict:
    """Eligibility for actor → target."""
    denials: list[str] = []
    reasons: list[str] = []

    if actor.id == target.id:
        return _pack(False, ["self"], [], {}, None, actor.id, db=db)

    if not actor.is_active or not target.is_active:
        denials.append("inactive")

    if is_connect_blocked(db, actor.id, target.id):
        denials.append("blocked")

    if _messaging_suspended(db, actor) or _messaging_suspended(db, target):
        denials.append("messaging_suspended")

    if has_serious_report(db, actor.id) or has_serious_report(db, target.id):
        denials.append("prior_serious_report")

    actor_settings = ensure_connect_settings(db, actor)
    target_settings = ensure_connect_settings(db, target)

    if not actor_settings.fan_connect_enabled:
        denials.append("actor_connect_off")
    if not target_settings.fan_connect_enabled:
        denials.append("target_connect_off")

    actor_passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == actor.id)
    )
    target_passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == target.id)
    )

    if actor_passport is None or not actor_passport.username:
        denials.append("actor_passport_missing")
    if target_passport is None or not target_passport.username:
        denials.append("passport_missing")
    elif target_passport.admin_hidden_at is not None:
        denials.append("admin_hidden")
    elif target_passport.visibility != VISIBILITY_PUBLIC:
        denials.append("passport_not_public")

    connection = get_connection_pair(db, actor.id, target.id)

    if connection and connection.status == C.STATUS_BLOCKED:
        denials.append("connection_blocked")

    if connection and connection.status == C.STATUS_CONNECTED:
        reasons.append("already_connected")
        hard = {"inactive", "blocked", "messaging_suspended", "connection_blocked"}
        hard_denials = [d for d in denials if d in hard]
        shared = compute_shared_context(
            db,
            actor_id=actor.id,
            target_id=target.id,
            actor_settings=actor_settings,
            target_settings=target_settings,
            actor_passport=actor_passport,
            target_passport=target_passport,
        )
        return _pack(
            len(hard_denials) == 0,
            hard_denials,
            reasons,
            shared,
            connection,
            actor.id,
            db=db,
        )

    if connection and connection.status in C.OPEN_REQUEST_STATUSES:
        reasons.append("request_pending")

    if for_new_request:
        ok_send, deny_send = can_send_request(connection, actor.id, db=db)
        if not ok_send and deny_send:
            denials.append(deny_send)

    if for_discovery:
        ok_sug, deny_sug = can_suggest(connection)
        if not ok_sug and deny_sug:
            denials.append(deny_sug)

    if for_new_request or for_discovery:
        if not target_settings.allow_connection_requests:
            denials.append("target_requests_off")
        target_policies = normalize_request_policies(
            list(target_settings.request_policies or []),
            fallback=target_settings.request_policy,
        )
        if C.POLICY_NOBODY in target_policies:
            denials.append("target_policy_nobody")

    if for_discovery:
        disco_ok = (
            target_settings.discoverable_for_same_events
            or target_settings.discoverable_for_similar_interests
        )
        if not disco_ok:
            denials.append("target_not_discoverable")

    shared = compute_shared_context(
        db,
        actor_id=actor.id,
        target_id=target.id,
        actor_settings=actor_settings,
        target_settings=target_settings,
        actor_passport=actor_passport,
        target_passport=target_passport,
    )

    open_request = bool(
        connection and connection.status in C.OPEN_REQUEST_STATUSES
    )

    if for_new_request and not open_request and "decline_cooldown" not in denials:
        target_policies = normalize_request_policies(
            list(target_settings.request_policies or []),
            fallback=target_settings.request_policy,
        )
        if not policies_allow_shared(target_policies, shared):
            if target_policies == [C.POLICY_SAME_EVENT]:
                denials.append("policy_requires_shared_event")
            elif set(target_policies) <= {
                C.POLICY_SAME_EVENT,
                C.POLICY_SAME_HOST,
            }:
                denials.append("policy_requires_shared_host")
            elif not has_safe_shared_reason(shared):
                denials.append("no_shared_public_context")
            else:
                denials.append("no_shared_public_context")
        elif not has_safe_shared_reason(shared):
            denials.append("no_shared_public_context")

    if has_safe_shared_reason(shared):
        if shared.get("_has_shared_events"):
            reasons.append("shared_public_events")
        if shared.get("_has_shared_hosts"):
            reasons.append("shared_hosts")
        if shared.get("_has_shared_categories"):
            reasons.append("shared_categories")

    return _pack(
        len(denials) == 0, denials, reasons, shared, connection, actor.id, db=db
    )


def _relationship_fields(
    connection: FanConnection | None,
    viewer_id: UUID,
    denials: list[str],
    *,
    db: Session,
) -> dict:
    conn = connection
    cooldown = requester_cooldown_until(conn, db=db)
    has_outgoing = bool(
        conn
        and conn.status in C.OPEN_REQUEST_STATUSES
        and conn.requester_user_id == viewer_id
    )
    has_incoming = bool(
        conn
        and conn.status in C.OPEN_REQUEST_STATUSES
        and conn.recipient_user_id == viewer_id
    )
    viewer_declined_target = bool(
        conn
        and conn.status == C.STATUS_DECLINED
        and conn.declined_by_user_id == viewer_id
    )
    target_declined_viewer = bool(
        conn
        and conn.status == C.STATUS_DECLINED
        and conn.requester_user_id == viewer_id
        and conn.declined_by_user_id is not None
        and conn.declined_by_user_id != viewer_id
    )
    if conn and conn.status == C.STATUS_CONNECTED:
        rel_status = "connected"
    elif has_outgoing:
        rel_status = "outgoing_pending"
    elif has_incoming:
        rel_status = "incoming_pending"
    elif conn and conn.status == C.STATUS_DECLINED:
        rel_status = "declined"
    elif conn and conn.status == C.STATUS_BLOCKED:
        rel_status = "blocked"
    else:
        rel_status = "none"

    can_send = "decline_cooldown" not in denials and not has_outgoing
    if "blocked" in denials or "connection_blocked" in denials:
        can_send = False
    if has_incoming or has_outgoing:
        can_send = False
    if conn and conn.status == C.STATUS_CONNECTED:
        can_send = False

    cannot_reason = None
    if "decline_cooldown" in denials:
        cannot_reason = "decline_cooldown"
    elif not can_send and has_outgoing:
        cannot_reason = "request_pending"
    elif not can_send and has_incoming:
        cannot_reason = "incoming_request"

    ok_send, _ = can_send_request(connection, viewer_id, db=db)
    send_blockers = [
        d
        for d in denials
        if d not in ("target_not_discoverable", "decline_cooldown")
    ]
    can_send_connect = ok_send and len(send_blockers) == 0

    return {
        "relationship_status": rel_status,
        "can_send_connect_request": can_send_connect,
        "cannot_connect_reason": cannot_reason,
        "cooldown_until": cooldown,
        "viewer_declined_target": viewer_declined_target,
        "target_declined_viewer": target_declined_viewer,
        "has_incoming_request": has_incoming,
        "has_outgoing_request": has_outgoing,
    }


def _pack(
    allowed: bool,
    denials: list[str],
    reasons: list[str],
    shared: dict,
    connection: FanConnection | None,
    viewer_id: UUID,
    *,
    db: Session,
) -> dict:
    seen: set[str] = set()
    clean: list[str] = []
    for d in denials:
        if d not in seen:
            seen.add(d)
            clean.append(d)
    rel = _relationship_fields(connection, viewer_id, clean, db=db)
    return {
        "allowed": allowed and len(clean) == 0,
        "denials": clean,
        "reasons": reasons,
        "shared_context": public_shared_context(shared)
        if shared
        else {"events": [], "hosts": [], "categories": []},
        "shared_raw": shared,
        "connection": connection,
        "connection_status": viewer_status(connection, viewer_id),
        "connection_id": connection.id if connection else None,
        "thread_id": connection.message_thread_id if connection else None,
        **rel,
    }


def resolve_target_by_username(db: Session, username: str) -> tuple[User, FanPassport]:
    uname = normalize_username(username)
    passport = db.scalar(select(FanPassport).where(FanPassport.username == uname))
    if passport is None or passport.admin_hidden_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fan not found")
    user = db.get(User, passport.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fan not found")
    return user, passport
