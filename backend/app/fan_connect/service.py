"""Fan Connect service — settings, requests, connections, suggestions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.fan_connect import constants as C
from app.fan_connect.context import compute_shared_context, public_shared_context
from app.fan_connect.eligibility import (
    assert_not_self_fan_connect,
    canonical_pair,
    classify_fan_connect,
    ensure_connect_settings,
    get_connection_pair,
    is_connect_blocked,
    resolve_target_by_username,
    viewer_status,
)
from app.fan_connect.lifecycle import can_suggest, messaging_allowed
from app.fan_connect.models import (
    FanConnectLocationPreference,
    FanConnectSettings,
    FanConnectSuggestion,
    FanConnectSuggestionDismissal,
    FanConnectSuggestionFeedback,
    FanConnection,
    FanConnectionBlock,
    FanConnectionReport,
)
from app.fan_connect.scoring import FanConnectScoringService
from app.fan_connect.diversity import empty_state_copy, filter_by_mode, mix_suggestions
from app.messaging import service as messaging_svc
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PUBLIC
from app.passport.service import ensure_passport
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _counterpart_chip(
    db: Session,
    user_id: UUID,
    *,
    viewer: User | None = None,
    relationship_context: str = "profile",
) -> dict:
    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    user = db.get(User, user_id)
    from app.users.gender import HIDDEN_GENDER_PAYLOAD, gender_display_payload

    gender = (
        gender_display_payload(
            db,
            viewer=viewer,
            profile_owner=user,
            relationship_context=relationship_context,
        )
        if user is not None
        else dict(HIDDEN_GENDER_PAYLOAD)
    )
    if passport is None:
        return {
            "user_id": str(user_id),
            "display_name": (user.full_name if user else "Fan") or "Fan",
            "username": None,
            "avatar_url": None,
            "tagline": None,
            **gender,
        }
    return {
        "user_id": str(user_id),
        "display_name": passport.display_name,
        "username": passport.username,
        "avatar_url": passport.avatar_url,
        "tagline": passport.tagline,
        **gender,
    }


def settings_payload(db: Session, user: User) -> dict:
    s = ensure_connect_settings(db, user)
    return {
        "fan_connect_enabled": s.fan_connect_enabled,
        "discoverable_for_same_events": s.discoverable_for_same_events,
        "discoverable_for_similar_interests": s.discoverable_for_similar_interests,
        "allow_connection_requests": s.allow_connection_requests,
        "show_shared_hosts": s.show_shared_hosts,
        "show_shared_categories": s.show_shared_categories,
        "show_shared_public_events": s.show_shared_public_events,
        "show_public_city": s.show_public_city,
        "hide_private_events_always": True,
        "request_policy": s.request_policy,
        "request_policies": list(s.request_policies or []),
    }


def update_settings(db: Session, user: User, payload) -> FanConnectSettings:
    from app.fan_connect.policies import (
        normalize_request_policies,
        primary_request_policy,
    )

    ensure_passport(db, user)
    s = ensure_connect_settings(db, user)
    was_enabled = bool(s.fan_connect_enabled)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "hide_private_events_always":
            continue
        if key == "request_policies":
            policies = normalize_request_policies(value)
            s.request_policies = policies
            s.request_policy = primary_request_policy(policies)
            continue
        if key == "request_policy":
            # Legacy single-value writes still accepted.
            if "request_policies" not in data and value in C.REQUEST_POLICIES:
                policies = normalize_request_policies([value])
                s.request_policies = policies
                s.request_policy = primary_request_policy(policies)
            continue
        if hasattr(s, key) and value is not None:
            setattr(s, key, bool(value))
    s.hide_private_events_always = True
    db.commit()
    db.refresh(s)
    from app.fan_connect import analytics as fc_analytics

    if not was_enabled and s.fan_connect_enabled:
        fc_analytics.emit_fan_connect_enabled(db, user_id=user.id)
    elif was_enabled and not s.fan_connect_enabled:
        fc_analytics.emit_fan_connect_disabled(db, user_id=user.id)
    return s


def can_connect(db: Session, actor: User, username: str) -> dict:
    target, _ = resolve_target_by_username(db, username)
    result = classify_fan_connect(
        db, actor=actor, target=target, for_new_request=True
    )
    payload = {
        "allowed": result["allowed"],
        "reasons": result["reasons"],
        "denials": result["denials"],
        "shared_context": result["shared_context"],
        "connection_status": result["connection_status"],
        "connection_id": result["connection_id"],
        "thread_id": result["thread_id"],
        "relationship_status": result.get("relationship_status"),
        "can_send_connect_request": result.get("can_send_connect_request"),
        "cannot_connect_reason": result.get("cannot_connect_reason"),
        "cooldown_until": result.get("cooldown_until"),
        "viewer_declined_target": result.get("viewer_declined_target"),
        "target_declined_viewer": result.get("target_declined_viewer"),
        "has_incoming_request": result.get("has_incoming_request"),
        "has_outgoing_request": result.get("has_outgoing_request"),
    }
    if "self" in result["denials"]:
        payload["message"] = C.SELF_CONNECT_DETAIL
    return payload


def _validate_intro(message: str | None) -> str | None:
    if message is None:
        return None
    text = " ".join(message.strip().split())
    if not text:
        return None
    if len(text) > C.MAX_INTRO_LENGTH:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Intro message is too long."
        )
    lower = text.lower()
    for phrase in C.CONTACT_PATTERNS:
        if phrase in lower:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Keep contact details off Pàdéyá Connect intros.",
            )
    return text


def _rate_limit_requests(db: Session, user_id: UUID) -> None:
    since = _now() - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(FanConnection)
        .where(
            FanConnection.requester_user_id == user_id,
            FanConnection.created_at >= since,
        )
    )
    if (count or 0) >= C.REQUESTS_PER_HOUR:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many connection requests. Try again later.",
        )


def create_request(
    db: Session,
    actor: User,
    *,
    username: str,
    message: str | None,
    context_event_id: UUID | None,
) -> FanConnection:
    from app.users.restrictions import assert_can_use_fan_connect

    assert_can_use_fan_connect(db, actor)

    ensure_passport(db, actor)
    target, _ = resolve_target_by_username(db, username)
    assert_not_self_fan_connect(actor_id=actor.id, target_id=target.id)
    result = classify_fan_connect(
        db, actor=actor, target=target, for_new_request=True
    )
    if not result["allowed"]:
        if "self" in result["denials"]:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=C.SELF_CONNECT_DETAIL
            )
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Cannot send a connection request.",
                "denials": result["denials"],
            },
        )

    existing = result["connection"]
    if existing and existing.status in C.OPEN_REQUEST_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="A request is already pending."
        )
    if existing and existing.status == C.STATUS_CONNECTED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Already connected."
        )

    intro = _validate_intro(message)
    related_host_id = None
    if context_event_id is not None:
        shared_ids = {
            e["event_id"] for e in result["shared_context"].get("events", [])
        }
        from app.fan_connect.context import (
            _safe_attended_event_ids,
            _safe_upcoming_ticket_event_ids,
        )

        raw = (
            _safe_attended_event_ids(db, actor.id)
            & _safe_attended_event_ids(db, target.id)
        ) | (
            _safe_upcoming_ticket_event_ids(db, actor.id)
            & _safe_upcoming_ticket_event_ids(db, target.id)
        )
        if context_event_id not in raw and context_event_id not in shared_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="context_event_id must be a shared public event.",
            )
        ev = db.get(Event, context_event_id)
        if ev is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid context event."
            )
        related_host_id = ev.host_id

    _rate_limit_requests(db, actor.id)
    low, high = canonical_pair(actor.id, target.id)
    shared_raw = result.get("shared_raw") or {}
    actor_passport = db.scalar(select(FanPassport).where(FanPassport.user_id == actor.id))
    target_passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == target.id)
    )
    scored = FanConnectScoringService().evaluate(
        db,
        actor=actor,
        target=target,
        shared=shared_raw,
        connection=existing,
        actor_passport=actor_passport,
        target_passport=target_passport,
        actor_settings=ensure_connect_settings(db, actor),
        target_settings=ensure_connect_settings(db, target),
        eligible=True,
    )
    reasons = scored.reasons
    score = float(scored.score)
    now = _now()

    if existing is not None:
        existing.requester_user_id = actor.id
        existing.recipient_user_id = target.id
        existing.status = C.STATUS_REQUEST_SENT
        existing.request_message = intro
        existing.related_event_id = context_event_id
        existing.related_host_id = related_host_id
        existing.reasons_json = reasons
        existing.score = score
        existing.requested_at = now
        existing.accepted_at = None
        existing.declined_at = None
        existing.declined_by_user_id = None
        existing.requester_cooldown_until = None
        existing.removed_at = None
        # Messaging stays gated until accept; keep prior thread id for unlock reuse.
        conn = existing
    else:
        conn = FanConnection(
            user_low_id=low,
            user_high_id=high,
            requester_user_id=actor.id,
            recipient_user_id=target.id,
            status=C.STATUS_REQUEST_SENT,
            request_message=intro,
            related_event_id=context_event_id,
            related_host_id=related_host_id,
            reasons_json=reasons,
            score=score,
            requested_at=now,
        )
        db.add(conn)

    db.flush()
    write_audit_log(
        db,
        action="fan_connect.request",
        actor_user_id=actor.id,
        resource_type="fan_connection",
        resource_id=str(conn.id),
        details={"recipient": str(target.id)},
    )
    from app.fan_connect import analytics as fc_analytics

    target_pp = db.scalar(
        select(FanPassport).where(FanPassport.user_id == target.id)
    )
    fc_analytics.emit_request_sent(
        db,
        user_id=actor.id,
        connection_id=conn.id,
        counterpart_username=target_pp.username if target_pp else username,
        target_event_id=context_event_id,
        reasons=reasons,
    )
    _record_feedback(
        db,
        actor_id=actor.id,
        target_id=target.id,
        action=C.FEEDBACK_CONNECT_REQUEST,
        context={"connection_id": str(conn.id)},
    )
    # Persist the request before notifications so a notify failure cannot
    # roll back the connection (and leave the sender UI stuck on Connect).
    db.commit()
    db.refresh(conn)

    try:
        from app.fan_connect.notifications import notify_connection_request

        notify_connection_request(
            db,
            recipient_user_id=target.id,
            requester_user_id=actor.id,
            connection_id=conn.id,
        )
        db.commit()
    except Exception:  # noqa: BLE001 — request already saved
        import logging

        logging.getLogger("padeya.fan_connect").exception(
            "fan_connect request notify failed for connection %s", conn.id
        )
        db.rollback()

    return conn


def _require_party(conn: FanConnection, user: User) -> None:
    if user.id not in {conn.requester_user_id, conn.recipient_user_id}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")


def serialize_connection(db: Session, conn: FanConnection, viewer: User) -> dict:
    other_id = (
        conn.recipient_user_id
        if conn.requester_user_id == viewer.id
        else conn.requester_user_id
    )
    direction = (
        "outgoing" if conn.requester_user_id == viewer.id else "incoming"
    )
    actor_settings = ensure_connect_settings(db, viewer)
    other = db.get(User, other_id)
    shared = {"events": [], "hosts": [], "categories": []}
    if other:
        other_settings = ensure_connect_settings(db, other)
        actor_passport = db.scalar(
            select(FanPassport).where(FanPassport.user_id == viewer.id)
        )
        other_passport = db.scalar(
            select(FanPassport).where(FanPassport.user_id == other_id)
        )
        raw = compute_shared_context(
            db,
            actor_id=viewer.id,
            target_id=other_id,
            actor_settings=actor_settings,
            target_settings=other_settings,
            actor_passport=actor_passport,
            target_passport=other_passport,
        )
        shared = public_shared_context(raw)

    from app.fan_connect import constants as FC

    # Pending connect requests use the explicit connect_request visibility rule.
    # Accepted connections use standard connections_only / public / private rules.
    rel_ctx = (
        "connect_request"
        if conn.status == FC.STATUS_REQUEST_SENT
        else "profile"
    )

    return {
        "id": conn.id,
        "status": viewer_status(conn, viewer.id) or conn.status,
        "direction": direction,
        "counterpart": _counterpart_chip(
            db, other_id, viewer=viewer, relationship_context=rel_ctx
        ),
        "message": conn.request_message,
        "score": conn.score,
        "reasons": _public_reasons(conn.reasons_json),
        "shared_context": shared,
        "thread_id": conn.message_thread_id,
        "created_at": conn.created_at,
        "requested_at": conn.requested_at,
        "accepted_at": conn.accepted_at,
        "responded_at": conn.accepted_at or conn.declined_at or conn.removed_at,
    }


def _public_reasons(raw: list | None) -> list[dict]:
    out: list[dict] = []
    for item in raw or []:
        if isinstance(item, dict):
            code = str(item.get("code") or "").strip()
            label = str(item.get("label") or code).strip()
            if code:
                out.append({"code": code, "label": label or code})
        elif isinstance(item, str) and item.strip():
            out.append({"code": item.strip(), "label": item.strip()})
    return out


def list_requests(db: Session, user: User, *, box: str) -> dict:
    if box == "outgoing":
        stmt = select(FanConnection).where(
            FanConnection.requester_user_id == user.id,
            FanConnection.status == C.STATUS_REQUEST_SENT,
        )
    else:
        stmt = select(FanConnection).where(
            FanConnection.recipient_user_id == user.id,
            FanConnection.status == C.STATUS_REQUEST_SENT,
        )
    rows = list(
        db.scalars(stmt.order_by(FanConnection.created_at.desc())).all()
    )
    return {"items": [serialize_connection(db, r, user) for r in rows]}


def list_connections(db: Session, user: User) -> dict:
    rows = list(
        db.scalars(
            select(FanConnection)
            .where(
                FanConnection.status == C.STATUS_CONNECTED,
                FanConnection.user_low_id != FanConnection.user_high_id,
                or_(
                    FanConnection.user_low_id == user.id,
                    FanConnection.user_high_id == user.id,
                ),
                FanConnection.removed_at.is_(None),
            )
            .order_by(FanConnection.accepted_at.desc().nullslast())
        ).all()
    )
    return {"items": [serialize_connection(db, r, user) for r in rows]}


def accept_request(db: Session, user: User, connection_id: UUID) -> FanConnection:
    conn = db.get(FanConnection, connection_id)
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    if conn.recipient_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the recipient.")
    if conn.status not in C.OPEN_REQUEST_STATUSES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Request is not pending."
        )

    other = db.get(User, conn.requester_user_id)
    if other is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    # Malformed self-rows or self-accept attempts.
    assert_not_self_fan_connect(actor_id=user.id, target_id=other.id)
    if conn.user_low_id == conn.user_high_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=C.SELF_CONNECT_DETAIL
        )

    result = classify_fan_connect(
        db, actor=user, target=other, for_new_request=False
    )
    if "self" in result["denials"]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=C.SELF_CONNECT_DETAIL
        )
    if "blocked" in result["denials"] or "messaging_suspended" in result["denials"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot accept this request."
        )

    thread = messaging_svc.ensure_fan_fan_thread(
        db, user_a=user.id, user_b=other.id, for_accept=True
    )
    conn.status = C.STATUS_CONNECTED
    conn.accepted_at = _now()
    conn.removed_at = None
    conn.declined_at = None
    conn.message_thread_id = thread.id
    system_msg = messaging_svc.append_fan_connect_system_message(
        db,
        thread=thread,
        actor=user,
        reasons=conn.reasons_json,
    )
    from app.fan_connect.notifications import notify_request_accepted

    notify_request_accepted(
        db,
        requester_user_id=other.id,
        acceptor_user_id=user.id,
        thread_id=thread.id,
    )
    write_audit_log(
        db,
        action="fan_connect.accept",
        actor_user_id=user.id,
        resource_type="fan_connection",
        resource_id=str(conn.id),
        details={"thread_id": str(thread.id)},
    )
    from app.fan_connect import analytics as fc_analytics

    fc_analytics.emit_request_accepted(
        db,
        user_id=user.id,
        connection_id=conn.id,
        thread_id=thread.id,
    )
    db.commit()
    db.refresh(conn)
    db.refresh(thread)
    if system_msg is not None:
        db.refresh(system_msg)
    from app.messaging import ws_events

    ws_events.publish_connection_accepted(
        thread=thread,
        connection_id=conn.id,
        user_ids=[user.id, other.id],
        system_message=system_msg,
        db=db,
    )
    return conn


def decline_request(
    db: Session,
    user: User,
    connection_id: UUID,
    *,
    cooldown_days: int | None = None,
) -> FanConnection:
    from app.fan_connect.platform_settings import (
        get_default_decline_cooldown_days,
        validate_decline_cooldown_days,
    )

    conn = db.get(FanConnection, connection_id)
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    if conn.recipient_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the recipient.")
    if conn.status not in C.OPEN_REQUEST_STATUSES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Request is not pending."
        )
    requester_id = conn.requester_user_id
    if cooldown_days is None:
        days = get_default_decline_cooldown_days(db)
    else:
        try:
            days = validate_decline_cooldown_days(int(cooldown_days))
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc

    now = _now()
    conn.status = C.STATUS_DECLINED
    conn.declined_at = now
    conn.declined_by_user_id = user.id
    if days <= 0:
        conn.requester_cooldown_until = now
    else:
        conn.requester_cooldown_until = now + timedelta(days=days)

    from app.core.audit import write_audit_log

    write_audit_log(
        db,
        action="fan_connect.decline",
        actor_user_id=user.id,
        resource_type="fan_connection",
        resource_id=str(conn.id),
        details={"requester_cooldown_days": days},
    )
    from app.fan_connect.notifications import notify_request_declined

    notify_request_declined(
        db,
        requester_user_id=requester_id,
        decliner_user_id=user.id,
    )
    from app.fan_connect import analytics as fc_analytics

    fc_analytics.emit_request_declined(
        db, user_id=user.id, connection_id=conn.id
    )
    db.commit()
    db.refresh(conn)
    return conn


def cancel_request(db: Session, user: User, connection_id: UUID) -> FanConnection:
    conn = db.get(FanConnection, connection_id)
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    if conn.requester_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the requester.")
    if conn.status not in C.OPEN_REQUEST_STATUSES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Request is not pending."
        )
    conn.status = C.STATUS_REMOVED
    conn.removed_at = _now()
    db.commit()
    db.refresh(conn)
    return conn


def disconnect(db: Session, user: User, connection_id: UUID) -> FanConnection:
    """Remove connection — messaging disabled until reconnected."""
    from app.messaging import constants as MC
    from app.messaging.models import MessageThread

    conn = db.get(FanConnection, connection_id)
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_party(conn, user)
    if conn.status != C.STATUS_CONNECTED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Not an active connection."
        )
    other_id = (
        conn.recipient_user_id
        if conn.requester_user_id == user.id
        else conn.requester_user_id
    )
    conn.status = C.STATUS_REMOVED
    conn.removed_at = _now()
    closed_thread = None
    if conn.message_thread_id:
        thread = db.get(MessageThread, conn.message_thread_id)
        if thread is not None and thread.thread_type == MC.THREAD_TYPE_FAN_FAN:
            thread.status = MC.THREAD_STATUS_CLOSED
            closed_thread = thread
    from app.fan_connect.notifications import notify_connection_removed

    notify_connection_removed(
        db,
        other_user_id=other_id,
        actor_user_id=user.id,
    )
    write_audit_log(
        db,
        action="fan_connect.remove",
        actor_user_id=user.id,
        resource_type="fan_connection",
        resource_id=str(conn.id),
    )
    from app.fan_connect import analytics as fc_analytics

    fc_analytics.emit_connection_removed(
        db, user_id=user.id, connection_id=conn.id
    )
    db.commit()
    db.refresh(conn)
    if closed_thread is not None:
        db.refresh(closed_thread)
        from app.messaging import ws_events

        ws_events.publish_thread_disabled(closed_thread, reason="removed", db=db)
        ws_events.publish_connection_removed(
            user_ids=[user.id, other_id],
            connection_id=conn.id,
            reason="removed",
        )
    return conn


def report_fan(
    db: Session,
    user: User,
    *,
    username: str,
    reason: str,
    details: str | None = None,
    connection_id: UUID | None = None,
    thread_id: UUID | None = None,
) -> FanConnectionReport:
    target, _ = resolve_target_by_username(db, username)
    if target.id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=C.SELF_REPORT_DETAIL
        )
    text = (reason or "").strip()
    if len(text) < 3:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Reason is required."
        )
    conn = get_connection_pair(db, user.id, target.id)
    if connection_id and conn and conn.id != connection_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="connection_id mismatch."
        )
    from app.messaging import constants as MC
    from app.messaging.models import MessageThread

    report = FanConnectionReport(
        reporter_user_id=user.id,
        reported_user_id=target.id,
        connection_id=(connection_id or (conn.id if conn else None)),
        thread_id=thread_id or (conn.message_thread_id if conn else None),
        reason=text[:120],
        details=(details or "").strip()[:2000] or None,
        status=C.REPORT_OPEN,
    )
    db.add(report)
    disabled_thread = None
    linked_tid = report.thread_id
    if linked_tid:
        linked = db.get(MessageThread, linked_tid)
        if linked is not None and linked.thread_type == MC.THREAD_TYPE_FAN_FAN:
            linked.status = MC.THREAD_STATUS_REPORTED
            disabled_thread = linked
    write_audit_log(
        db,
        action="fan_connect.report",
        actor_user_id=user.id,
        resource_type="fan_connection_report",
        resource_id=str(target.id),
        details={"reason": text[:120]},
    )
    from app.fan_connect import analytics as fc_analytics

    fc_analytics.emit_reported(
        db,
        user_id=user.id,
        counterpart_username=username,
        connection_id=report.connection_id,
    )
    db.commit()
    db.refresh(report)
    if disabled_thread is not None:
        db.refresh(disabled_thread)
        from app.messaging import ws_events

        ws_events.publish_thread_disabled(disabled_thread, reason="reported", db=db)
    return report


def block_fan(db: Session, user: User, *, username: str, reason: str | None) -> None:
    target, _ = resolve_target_by_username(db, username)
    if target.id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=C.SELF_BLOCK_DETAIL
        )

    existing_block = db.scalar(
        select(FanConnectionBlock).where(
            FanConnectionBlock.blocker_user_id == user.id,
            FanConnectionBlock.blocked_user_id == target.id,
        )
    )
    if existing_block is None:
        db.add(
            FanConnectionBlock(
                blocker_user_id=user.id,
                blocked_user_id=target.id,
                reason=(reason or "")[:300] or None,
            )
        )

    messaging_svc.block_user(
        db,
        user,
        blocked_user_id=target.id,
        reason=reason,
    )
    # block_user already emits thread_disabled for messaging threads.

    conn = get_connection_pair(db, user.id, target.id)
    low, high = canonical_pair(user.id, target.id)
    now = _now()
    if conn is None:
        conn = FanConnection(
            user_low_id=low,
            user_high_id=high,
            requester_user_id=user.id,
            recipient_user_id=target.id,
            status=C.STATUS_BLOCKED,
            removed_at=now,
        )
        db.add(conn)
    else:
        conn.status = C.STATUS_BLOCKED
        conn.removed_at = now

    write_audit_log(
        db,
        action="fan_connect.block",
        actor_user_id=user.id,
        resource_type="fan_connection",
        resource_id=str(conn.id if conn.id else target.id),
        details={"blocked_user_id": str(target.id)},
    )
    from app.fan_connect import analytics as fc_analytics

    fc_analytics.emit_blocked(
        db, user_id=user.id, counterpart_username=username
    )
    db.commit()
    # Notify both parties Connect is blocked (thread events already sent).
    from app.messaging import ws_events

    ws_events.publish_connection_removed(
        user_ids=[user.id, target.id],
        connection_id=conn.id if conn.id else None,
        reason="blocked",
    )


def _actor_knows_public_event(db: Session, user_id: UUID, event_id: UUID) -> bool:
    """Checked-in or active ticket on a public-safe event — never private lists."""
    from app.fan_connect.context import (
        _safe_attended_event_ids,
        _safe_upcoming_ticket_event_ids,
    )

    return event_id in _safe_attended_event_ids(
        db, user_id
    ) or event_id in _safe_upcoming_ticket_event_ids(db, user_id)


def score_band(score: int) -> str:
    if score >= C.SCORE_LABEL_STRONG:
        return C.SCORE_BAND_STRONG
    if score >= C.SCORE_LABEL_GOOD:
        return C.SCORE_BAND_GOOD
    if score >= C.SCORE_MIN_SHOW:
        return C.SCORE_BAND_SIMILAR
    return C.SCORE_BAND_HIDDEN


def cta_state_for(
    connection_status: str | None,
    *,
    can_connect: bool,
    denials: list[str] | None = None,
) -> str:
    if connection_status == C.STATUS_CONNECTED:
        return C.CTA_MESSAGE
    if connection_status in C.OPEN_REQUEST_STATUSES:
        return C.CTA_REQUEST_PENDING
    if connection_status == C.STATUS_BLOCKED:
        return C.CTA_BLOCKED
    if denials and "decline_cooldown" in denials:
        return C.CTA_DECLINE_COOLDOWN
    if can_connect:
        return C.CTA_CONNECT
    return C.CTA_UNAVAILABLE


def _suggestion_public_city(
    db: Session,
    *,
    passport: FanPassport,
    target_settings: FanConnectSettings,
    actor_settings: FanConnectSettings,
) -> str | None:
    """Safe public city only when both Connect settings allow city."""
    if not (actor_settings.show_public_city and target_settings.show_public_city):
        return None
    if not passport.show_city_category_stats:
        return None
    from app.passport.public_service import favorite_cities_for_user

    cities = favorite_cities_for_user(db, passport.user_id)
    return cities[0] if cities else None


def _suggestion_badges(db: Session, passport: FanPassport) -> list[dict]:
    from app.passport.public_service import public_badges

    return [
        {"slug": b["slug"], "name": b["name"]}
        for b in public_badges(db, passport)[:6]
    ]


def _serialize_suggestion_card(
    db: Session,
    *,
    passport: FanPassport,
    actor_settings: FanConnectSettings,
    target_settings: FanConnectSettings,
    scored,
    connection_status: str | None,
    shared_context: dict,
    eligibility: dict | None = None,
) -> dict:
    label = scored.recommendation_label
    denials = list((eligibility or {}).get("denials") or [])
    can_send = bool((eligibility or {}).get("can_send_connect_request"))
    return {
        "user_id": passport.user_id,
        "display_name": passport.display_name,
        "username": passport.username,
        "avatar_url": passport.avatar_url,
        "tagline": passport.tagline,
        "public_city": _suggestion_public_city(
            db,
            passport=passport,
            target_settings=target_settings,
            actor_settings=actor_settings,
        ),
        "badges": _suggestion_badges(db, passport),
        "match_label": label,
        "recommendation_label": label,
        "score": scored.score,
        "score_band": score_band(scored.score),
        "reasons": scored.reasons,
        "distance_label": scored.distance_label,
        "mutual_connection_count": scored.mutual_connection_count or None,
        "connection_status": connection_status or C.STATUS_SUGGESTED,
        "cta_state": cta_state_for(
            connection_status,
            can_connect=can_send,
            denials=denials,
        ),
        "cooldown_until": (eligibility or {}).get("cooldown_until"),
        "viewer_declined_target": (eligibility or {}).get("viewer_declined_target"),
        "can_send_connect_request": can_send,
        "shared_context": shared_context,
    }


def suggestions(
    db: Session,
    user: User,
    *,
    event_id: UUID | None = None,
    category: str | None = None,
    city: str | None = None,
    area: str | None = None,
    mode: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
    limit: int = C.SUGGESTIONS_CAP,
    page: int = 1,
) -> dict:
    """Opt-in suggestions with optional filters + pagination.

    lat/lng are one-time matching only — never persisted from this endpoint.
    Never returns phone/email, payments, hidden venues, private attendance, or GPS.
    """
    from app.passport.privacy import event_is_safe_for_public_passport
    from app.passport.public_service import favorite_cities_for_user

    actor_settings = ensure_connect_settings(db, user)
    mode_key = (mode or C.MODE_MIXED).strip().lower()
    if mode_key not in C.SUGGESTION_MODES:
        mode_key = C.MODE_MIXED
    empty_copy = empty_state_copy(mode_key)
    empty = {
        "items": [],
        "page": 1,
        "limit": limit,
        "total": 0,
        "next_cursor": None,
        "mode": mode_key,
        "empty_title": empty_copy["title"],
        "empty_description": empty_copy["description"],
    }
    if not actor_settings.fan_connect_enabled:
        return empty

    limit = min(max(1, limit), 50)
    page = max(1, page)

    # Resolve actor location: explicit query params win; else saved approx preference.
    actor_lat, actor_lng, actor_radius = _resolve_actor_geo(
        db, user, lat=lat, lng=lng, radius_km=radius_km
    )

    if event_id is not None:
        event = db.get(Event, event_id)
        if event is None or not event_is_safe_for_public_passport(
            event, hide_private_events_always=True
        ):
            return empty
        if not _actor_knows_public_event(db, user.id, event_id):
            return empty

    ensure_passport(db, user)
    actor_passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user.id))
    candidates = list(
        db.scalars(
            select(FanPassport)
            .where(
                FanPassport.visibility == VISIBILITY_PUBLIC,
                FanPassport.admin_hidden_at.is_(None),
                FanPassport.username.is_not(None),
                FanPassport.user_id != user.id,
            )
            .order_by(FanPassport.updated_at.desc())
            .limit(120)
        ).all()
    )

    scored_items: list[tuple[int, dict, list[str]]] = []
    scorer = FanConnectScoringService()
    cat_filter = (category or "").strip().lower() or None
    city_filter = (city or "").strip().lower() or None
    area_filter = (area or "").strip().lower() or None

    for passport in candidates:
        target = db.get(User, passport.user_id)
        if target is None or not target.is_active:
            continue
        if event_id is not None and not _actor_knows_public_event(
            db, target.id, event_id
        ):
            continue
        if cat_filter:
            cats = [str(c).lower() for c in (passport.favorite_categories or [])]
            if cat_filter not in cats:
                continue
        if city_filter:
            cities = {c.lower() for c in favorite_cities_for_user(db, passport.user_id)}
            if city_filter not in cities:
                continue
        if area_filter:
            from app.fan_connect.scoring import _public_areas

            areas = {a.lower() for a in _public_areas(db, passport.user_id)}
            if area_filter not in areas:
                continue

        result = classify_fan_connect(
            db,
            actor=user,
            target=target,
            for_discovery=True,
            for_new_request=True,
        )
        discovery_denials = [
            d for d in result["denials"] if d != "decline_cooldown"
        ]
        if discovery_denials:
            continue

        target_settings = ensure_connect_settings(db, target)
        scored = scorer.evaluate(
            db,
            actor=user,
            target=target,
            shared=result.get("shared_raw") or {},
            connection=result.get("connection"),
            actor_passport=actor_passport,
            target_passport=passport,
            actor_settings=actor_settings,
            target_settings=target_settings,
            eligible=True,
            actor_lat=actor_lat,
            actor_lng=actor_lng,
            radius_km=actor_radius,
        )
        show_card = scored.show or (
            result.get("connection_status") == C.STATUS_DECLINED
        )
        if not show_card:
            continue

        _upsert_suggested(
            db,
            actor=user,
            target=target,
            score=float(scored.score),
            reasons=scored.reasons,
        )
        ctx = result["shared_context"]
        if event_id is not None:
            scoped_events = [
                e for e in (ctx.get("events") or []) if e.get("event_id") == event_id
            ]
            if not scoped_events:
                ev = db.get(Event, event_id)
                if ev is None:
                    continue
                from app.passport.privacy import public_city_for_event

                scoped_events = [
                    {
                        "event_id": ev.id,
                        "title": ev.title,
                        "slug": ev.slug,
                        "path": f"/events/{ev.slug}",
                        "city": public_city_for_event(ev),
                    }
                ]
            ctx = {
                "events": scoped_events,
                "hosts": [],
                "categories": [],
            }
        card = _serialize_suggestion_card(
            db,
            passport=passport,
            actor_settings=actor_settings,
            target_settings=target_settings,
            scored=scored,
            connection_status=result.get("connection_status") or C.STATUS_SUGGESTED,
            shared_context=ctx,
            eligibility=result,
        )
        scored_items.append((scored.score, card, scored.buckets))

    filtered = filter_by_mode(scored_items, mode=mode_key)
    # For mixed: diversity mixer on full sorted pool then paginate conceptually
    # by building a diversified ordered list first.
    if mode_key == C.MODE_MIXED:
        mixed_all = mix_suggestions(filtered, limit=max(len(filtered), limit), mode=mode_key)
        # Reattach scores for pagination stability via card order from mixer
        total = len(mixed_all)
        start = (page - 1) * limit
        page_items = mixed_all[start : start + limit]
    else:
        filtered.sort(key=lambda t: t[0], reverse=True)
        total = len(filtered)
        start = (page - 1) * limit
        page_items = [card for _, card, _ in filtered[start : start + limit]]

    next_cursor = str(page + 1) if start + limit < total else None
    db.commit()
    return {
        "items": page_items,
        "page": page,
        "limit": limit,
        "total": total,
        "next_cursor": next_cursor,
        "mode": mode_key,
        "empty_title": empty_copy["title"],
        "empty_description": empty_copy["description"],
    }


def _resolve_actor_geo(
    db: Session,
    user: User,
    *,
    lat: float | None,
    lng: float | None,
    radius_km: float | None,
) -> tuple[float | None, float | None, float | None]:
    """One-time query lat/lng preferred; else approximate saved preference. Never raw GPS persist."""
    radius = radius_km if radius_km is not None else float(C.NEARBY_DEFAULT_RADIUS_KM)
    if lat is not None and lng is not None:
        return float(lat), float(lng), float(radius)

    pref = db.scalar(
        select(FanConnectLocationPreference).where(
            FanConnectLocationPreference.user_id == user.id
        )
    )
    if pref is None:
        return None, None, None
    if pref.precision == C.LOCATION_PRECISION_APPROXIMATE:
        from app.events.geo import parse_coord

        plat = parse_coord(pref.latitude_approx)
        plng = parse_coord(pref.longitude_approx)
        if plat is not None and plng is not None:
            return plat, plng, float(radius)
    # City/area preference → coarse centroid for scoring only
    from app.events.maps import city_centroid
    from app.events.geo import parse_coord

    centroid = city_centroid(pref.city, pref.area)
    if centroid:
        plat = parse_coord(centroid[0])
        plng = parse_coord(centroid[1])
        if plat is not None and plng is not None:
            return plat, plng, float(radius)
    return None, None, None


def dismiss_suggestion(
    db: Session,
    user: User,
    target_user_id: UUID,
    *,
    reason: str | None = None,
) -> dict:
    """Persist dismissal — hard-exclude while expires_at active."""
    if user.id == target_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=C.SELF_CONNECT_DETAIL)
    target = db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    expires = _now() + timedelta(days=C.DISMISS_EXCLUDE_DAYS)
    row = db.scalar(
        select(FanConnectSuggestionDismissal).where(
            FanConnectSuggestionDismissal.actor_user_id == user.id,
            FanConnectSuggestionDismissal.target_user_id == target_user_id,
        )
    )
    if row is None:
        row = FanConnectSuggestionDismissal(
            actor_user_id=user.id,
            target_user_id=target_user_id,
            reason=(reason or None),
            dismissed_at=_now(),
            expires_at=expires,
        )
        db.add(row)
    else:
        row.reason = reason or row.reason
        row.dismissed_at = _now()
        row.expires_at = expires

    _record_feedback(
        db,
        actor_id=user.id,
        target_id=target_user_id,
        action=C.FEEDBACK_DISMISS,
        context={"reason": reason} if reason else None,
    )
    db.commit()
    return {"ok": True, "target_user_id": target_user_id, "expires_at": expires}


def more_like_this(
    db: Session,
    user: User,
    target_user_id: UUID,
) -> dict:
    """Record more-like-this — boosts similar profiles (+5 views signal)."""
    if user.id == target_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=C.SELF_CONNECT_DETAIL)
    target = db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    _record_feedback(
        db,
        actor_id=user.id,
        target_id=target_user_id,
        action=C.FEEDBACK_MORE_LIKE_THIS,
        context=None,
    )
    db.commit()
    return {"ok": True, "target_user_id": target_user_id}


def save_location_preference(
    db: Session,
    user: User,
    *,
    city: str | None = None,
    area: str | None = None,
    country: str | None = None,
    latitude_approx: str | None = None,
    longitude_approx: str | None = None,
    precision: str = C.LOCATION_PRECISION_CITY,
) -> dict:
    """Explicit save only — city/area preferred; approx coords only when precision=approximate."""
    precision = (precision or C.LOCATION_PRECISION_CITY).strip().lower()
    if precision not in C.LOCATION_PRECISIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"precision must be one of: {sorted(C.LOCATION_PRECISIONS)}",
        )
    city = (city or "").strip() or None
    area = (area or "").strip() or None
    country = (country or "").strip() or None
    if not city and not area:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="city or area is required to save a location preference.",
        )

    lat_a = None
    lng_a = None
    if precision == C.LOCATION_PRECISION_APPROXIMATE:
        lat_a = (latitude_approx or "").strip() or None
        lng_a = (longitude_approx or "").strip() or None
        # Never accept high-precision browser dumps — round to ~2 decimals (~1km)
        if lat_a and lng_a:
            try:
                lat_a = f"{round(float(lat_a), 2)}"
                lng_a = f"{round(float(lng_a), 2)}"
            except ValueError as exc:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, detail="Invalid approximate coordinates."
                ) from exc
    # city/area precision: never store lat/lng

    row = db.scalar(
        select(FanConnectLocationPreference).where(
            FanConnectLocationPreference.user_id == user.id
        )
    )
    now = _now()
    if row is None:
        row = FanConnectLocationPreference(
            user_id=user.id,
            city=city,
            area=area,
            country=country,
            latitude_approx=lat_a,
            longitude_approx=lng_a,
            precision=precision,
            consented_at=now,
        )
        db.add(row)
    else:
        row.city = city
        row.area = area
        row.country = country
        row.latitude_approx = lat_a
        row.longitude_approx = lng_a
        row.precision = precision
        row.consented_at = now
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return location_preference_payload(row)


def get_location_preference(db: Session, user: User) -> dict | None:
    row = db.scalar(
        select(FanConnectLocationPreference).where(
            FanConnectLocationPreference.user_id == user.id
        )
    )
    if row is None:
        return None
    return location_preference_payload(row)


def clear_location_preference(db: Session, user: User) -> dict:
    row = db.scalar(
        select(FanConnectLocationPreference).where(
            FanConnectLocationPreference.user_id == user.id
        )
    )
    if row is not None:
        db.delete(row)
        db.commit()
    return {"ok": True}


def location_preference_payload(row: FanConnectLocationPreference) -> dict:
    return {
        "city": row.city,
        "area": row.area,
        "country": row.country,
        "precision": row.precision,
        # Approx coords only when user explicitly saved approximate precision
        "latitude_approx": row.latitude_approx
        if row.precision == C.LOCATION_PRECISION_APPROXIMATE
        else None,
        "longitude_approx": row.longitude_approx
        if row.precision == C.LOCATION_PRECISION_APPROXIMATE
        else None,
        "consented_at": row.consented_at,
        "updated_at": row.updated_at,
    }


def _record_feedback(
    db: Session,
    *,
    actor_id: UUID,
    target_id: UUID,
    action: str,
    context: dict | None,
) -> None:
    if action not in C.FEEDBACK_ACTIONS:
        return
    db.add(
        FanConnectSuggestionFeedback(
            actor_user_id=actor_id,
            target_user_id=target_id,
            action=action,
            context=context,
        )
    )
    db.flush()


def record_suggestion_feedback(
    db: Session,
    user: User,
    *,
    target_user_id: UUID,
    action: str,
    context: dict | None = None,
) -> dict:
    if action not in C.FEEDBACK_ACTIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid feedback action")
    if user.id == target_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=C.SELF_CONNECT_DETAIL)
    _record_feedback(
        db,
        actor_id=user.id,
        target_id=target_user_id,
        action=action,
        context=context,
    )
    db.commit()
    return {"ok": True}


def debug_score(
    db: Session,
    *,
    actor_user_id: UUID,
    target_user_id: UUID,
) -> dict:
    """Admin-only breakdown — no raw user GPS; bands/keys only."""
    actor = db.get(User, actor_user_id)
    target = db.get(User, target_user_id)
    if actor is None or target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    actor_settings = ensure_connect_settings(db, actor)
    target_settings = ensure_connect_settings(db, target)
    actor_passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == actor.id)
    )
    target_passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == target.id)
    )
    result = classify_fan_connect(
        db,
        actor=actor,
        target=target,
        for_discovery=True,
        for_new_request=True,
    )
    scorer = FanConnectScoringService()
    scored = scorer.evaluate(
        db,
        actor=actor,
        target=target,
        shared=result.get("shared_raw") or {},
        connection=result.get("connection"),
        actor_passport=actor_passport,
        target_passport=target_passport,
        actor_settings=actor_settings,
        target_settings=target_settings,
        eligible=bool(result.get("allowed")),
    )
    return {
        "actor_user_id": actor_user_id,
        "target_user_id": target_user_id,
        "score": scored.score,
        "score_band": score_band(scored.score),
        "show": scored.show,
        "hard_exclusions": scored.hard_exclusions,
        "breakdown": scored.breakdown,
        "reasons": scored.reasons,
        "distance_label": scored.distance_label,
        "buckets": scored.buckets,
        "connection_status": result.get("connection_status"),
        "eligible": bool(result.get("allowed")),
    }


def suggestions_for_event_slug(
    db: Session,
    user: User,
    *,
    event_slug: str,
    limit: int = C.SUGGESTIONS_CAP,
    page: int = 1,
) -> dict:
    """Event-scoped Fan Connect suggestions — public-safe event only."""
    from app.passport.privacy import event_is_safe_for_public_passport

    event = db.scalar(select(Event).where(Event.slug == event_slug))
    if event is None or not event_is_safe_for_public_passport(
        event, hide_private_events_always=True
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")
    return suggestions(
        db, user, event_id=event.id, limit=limit, page=page
    )


def _upsert_suggested(
    db: Session,
    *,
    actor: User,
    target: User,
    score: float,
    reasons: list[dict],
) -> FanConnection | None:
    """Mark pair as suggested when system recommends — no messaging."""
    if actor.id == target.id:
        return None

    ok, _ = can_suggest(get_connection_pair(db, actor.id, target.id))
    if not ok:
        return None

    low, high = canonical_pair(actor.id, target.id)
    if low == high:
        return None

    conn = get_connection_pair(db, actor.id, target.id)

    if conn is None:
        conn = FanConnection(
            user_low_id=low,
            user_high_id=high,
            requester_user_id=actor.id,
            recipient_user_id=target.id,
            status=C.STATUS_SUGGESTED,
            score=score,
            reasons_json=reasons,
        )
        db.add(conn)
    elif conn.status in {C.STATUS_SUGGESTED, C.STATUS_REMOVED}:
        conn.status = C.STATUS_SUGGESTED
        conn.score = score
        conn.reasons_json = reasons
        conn.removed_at = None
    elif conn.status == C.STATUS_DECLINED:
        # Keep decline history + requester cooldown; suggestion cache still updates.
        pass

    cache = db.scalar(
        select(FanConnectSuggestion).where(
            FanConnectSuggestion.user_id == actor.id,
            FanConnectSuggestion.suggested_user_id == target.id,
        )
    )
    expires = _now() + timedelta(hours=24)
    if cache is None:
        db.add(
            FanConnectSuggestion(
                user_id=actor.id,
                suggested_user_id=target.id,
                score=score,
                reasons_json=reasons,
                expires_at=expires,
            )
        )
    else:
        cache.score = score
        cache.reasons_json = reasons
        cache.expires_at = expires
    db.flush()
    return conn


def list_connect_events(db: Session, user: User) -> dict:
    """Public-safe nights the viewer can use for Connect (no attendee lists)."""
    from app.fan_connect.context import _safe_attended_event_ids
    from app.passport.privacy import public_city_for_event

    actor_settings = ensure_connect_settings(db, user)
    if not actor_settings.fan_connect_enabled:
        return {"items": []}

    event_ids = _safe_attended_event_ids(db, user.id)
    if not event_ids:
        return {"items": []}

    events = list(db.scalars(select(Event).where(Event.id.in_(event_ids))).all())
    events.sort(key=lambda e: e.start_datetime or e.created_at, reverse=True)
    items: list[dict] = []
    for ev in events[:40]:
        # Count eligible suggestions without exposing who — privacy-safe aggregate only.
        sug = suggestions(db, user, event_id=ev.id, limit=50, page=1)
        count = int(sug.get("total") or len(sug["items"]))
        items.append(
            {
                "event_id": ev.id,
                "title": ev.title,
                "slug": ev.slug,
                "path": f"/events/{ev.slug}",
                "city": public_city_for_event(ev),
                "start_datetime": ev.start_datetime,
                "suggestion_count": count,
            }
        )
    return {"items": items}


def _safe_admin_reason_labels(reasons: list | None) -> list[str]:
    """Public reason labels only — never VIP/spend/private venue/order IDs."""
    labels: list[str] = []
    for raw in reasons or []:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or "").strip()
        code = str(raw.get("code") or "").strip()
        if not label:
            continue
        low = label.lower()
        if any(
            bad in low
            for bad in (
                "vip",
                "spend",
                "payment",
                "order",
                "ticket type",
                "secret",
                "private",
                "street",
            )
        ):
            continue
        if code and code not in C.SAFE_REASON_CODES:
            continue
        labels.append(label[:160])
        if len(labels) >= 5:
            break
    return labels


def _message_report_id_for_thread(db: Session, thread_id: UUID | None) -> UUID | None:
    if thread_id is None:
        return None
    from app.messaging.models import MessageReport

    return db.scalar(
        select(MessageReport.id)
        .where(MessageReport.thread_id == thread_id)
        .order_by(MessageReport.created_at.desc())
        .limit(1)
    )


def _serialize_admin_block_item(db: Session, row: FanConnectionBlock) -> dict:
    blocker_pp = db.scalar(
        select(FanPassport).where(FanPassport.user_id == row.blocker_user_id)
    )
    blocked_pp = db.scalar(
        select(FanPassport).where(FanPassport.user_id == row.blocked_user_id)
    )
    return {
        "id": str(row.id),
        "blocker_user_id": str(row.blocker_user_id),
        "blocked_user_id": str(row.blocked_user_id),
        "blocker_display_name": (
            blocker_pp.display_name if blocker_pp else "User"
        ),
        "blocker_username": blocker_pp.username if blocker_pp else None,
        "blocked_display_name": (
            blocked_pp.display_name if blocked_pp else "User"
        ),
        "blocked_username": blocked_pp.username if blocked_pp else None,
        "reason": row.reason,
        "created_at": row.created_at,
    }


def serialize_admin_report(
    db: Session, row: FanConnectionReport, *, as_list_item: bool = False
) -> dict:
    """Admin report payload — display names + safe connection context only."""
    from app.messaging.constants import THREAD_TYPE_FAN_FAN
    from app.messaging.models import MessageThread

    reporter_pp = db.scalar(
        select(FanPassport).where(FanPassport.user_id == row.reporter_user_id)
    )
    reported_pp = db.scalar(
        select(FanPassport).where(FanPassport.user_id == row.reported_user_id)
    )
    reported_settings = db.scalar(
        select(FanConnectSettings).where(
            FanConnectSettings.user_id == row.reported_user_id
        )
    )
    conn = (
        db.get(FanConnection, row.connection_id)
        if row.connection_id
        else get_connection_pair(db, row.reporter_user_id, row.reported_user_id)
    )
    thread = db.get(MessageThread, row.thread_id) if row.thread_id else None
    thread_type = thread.thread_type if thread else None
    if thread_type is None and row.thread_id is None and conn and conn.message_thread_id:
        thread = db.get(MessageThread, conn.message_thread_id)
        thread_type = thread.thread_type if thread else None
    message_report_id = _message_report_id_for_thread(
        db, row.thread_id or (conn.message_thread_id if conn else None)
    )
    pair_blocked = is_connect_blocked(
        db, row.reporter_user_id, row.reported_user_id
    )
    context = {
        "connection_status": conn.status if conn else None,
        "reason_labels": _safe_admin_reason_labels(
            conn.reasons_json if conn else None
        ),
        "pair_blocked": pair_blocked,
    }
    # Only surface fan_fan thread type — never invent host/commerce context.
    if thread_type and thread_type != THREAD_TYPE_FAN_FAN:
        thread_type = None
        message_report_id = None

    base = {
        "id": str(row.id) if as_list_item else row.id,
        "status": row.status,
        "reason": row.reason,
        "details": row.details,
        "admin_notes": row.admin_notes,
        "reporter_user_id": (
            str(row.reporter_user_id) if as_list_item else row.reporter_user_id
        ),
        "reported_user_id": (
            str(row.reported_user_id) if as_list_item else row.reported_user_id
        ),
        "reporter_display_name": (
            reporter_pp.display_name if reporter_pp else "Fan"
        ),
        "reported_display_name": (
            reported_pp.display_name if reported_pp else "Fan"
        ),
        "reporter_username": reporter_pp.username if reporter_pp else None,
        "reported_username": reported_pp.username if reported_pp else None,
        "reported_connect_enabled": bool(
            reported_settings.fan_connect_enabled if reported_settings else False
        ),
        "connection_id": (
            str(conn.id)
            if as_list_item and conn
            else (conn.id if conn else None)
        ),
        "thread_id": (
            str(row.thread_id)
            if as_list_item and row.thread_id
            else row.thread_id
        ),
        "thread_type": thread_type,
        "message_report_id": (
            str(message_report_id)
            if as_list_item and message_report_id
            else message_report_id
        ),
        "connection_context": context,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        # Full message bodies stay on /admin/message-reports when reported there.
        "message_preview": None,
    }
    if as_list_item:
        base.pop("admin_notes", None)
        base.pop("updated_at", None)
        base.pop("connection_id", None)
    return base


def decline_cooldown_options(db: Session) -> dict:
    from app.fan_connect.platform_settings import (
        DECLINE_COOLDOWN_USER_OPTIONS,
        get_default_decline_cooldown_days,
    )

    return {
        "default_cooldown_days": get_default_decline_cooldown_days(db),
        "selectable_days": sorted(DECLINE_COOLDOWN_USER_OPTIONS),
    }


def admin_platform_settings(db: Session) -> dict:
    from app.fan_connect.platform_settings import (
        DECLINE_COOLDOWN_MAX_DAYS,
        DECLINE_COOLDOWN_MIN_DAYS,
        DECLINE_COOLDOWN_USER_OPTIONS,
        get_default_decline_cooldown_days,
    )

    return {
        "decline_cooldown_days_default": get_default_decline_cooldown_days(db),
        "decline_cooldown_days_min": DECLINE_COOLDOWN_MIN_DAYS,
        "decline_cooldown_days_max": DECLINE_COOLDOWN_MAX_DAYS,
        "decline_cooldown_user_options": sorted(DECLINE_COOLDOWN_USER_OPTIONS),
    }


def admin_update_platform_settings(
    db: Session,
    actor: User,
    *,
    decline_cooldown_days_default: int,
) -> dict:
    from app.fan_connect.platform_settings import (
        DECLINE_COOLDOWN_DAYS_KEY,
        validate_decline_cooldown_days,
    )
    from app.runtime_settings.service import runtime_settings_service

    days = validate_decline_cooldown_days(decline_cooldown_days_default)
    runtime_settings_service.upsert(
        db,
        category="fan_connect",
        key=DECLINE_COOLDOWN_DAYS_KEY,
        value=days,
        actor_user_id=actor.id,
        reason="Admin updated Fan Connect decline cooldown default",
        commit=False,
    )
    write_audit_log(
        db,
        action="fan_connect.admin.settings_update",
        actor_user_id=actor.id,
        resource_type="fan_connect_platform_settings",
        resource_id=DECLINE_COOLDOWN_DAYS_KEY,
        details={"decline_cooldown_days_default": days},
    )
    db.commit()
    return admin_platform_settings(db)


def admin_overview(db: Session) -> dict:
    from app.messaging.constants import THREAD_TYPE_FAN_FAN
    from app.messaging.models import MessageThread

    settings_on = db.scalar(
        select(func.count())
        .select_from(FanConnectSettings)
        .where(FanConnectSettings.fan_connect_enabled.is_(True))
    )
    pending = db.scalar(
        select(func.count())
        .select_from(FanConnection)
        .where(FanConnection.status == C.STATUS_REQUEST_SENT)
    )
    accepted = db.scalar(
        select(func.count())
        .select_from(FanConnection)
        .where(FanConnection.status == C.STATUS_CONNECTED)
    )
    blocked_conn = db.scalar(
        select(func.count())
        .select_from(FanConnection)
        .where(FanConnection.status == C.STATUS_BLOCKED)
    )
    fan_threads = db.scalar(
        select(func.count())
        .select_from(MessageThread)
        .where(MessageThread.thread_type == THREAD_TYPE_FAN_FAN)
    )
    reports = db.scalar(
        select(func.count()).select_from(FanConnectionReport)
    )
    open_reports = db.scalar(
        select(func.count())
        .select_from(FanConnectionReport)
        .where(FanConnectionReport.status.in_([C.REPORT_OPEN, C.REPORT_REVIEWING]))
    )
    blocks = db.scalar(select(func.count()).select_from(FanConnectionBlock))
    return {
        "connect_enabled_users": int(settings_on or 0),
        "pending_requests": int(pending or 0),
        "accepted_connections": int(accepted or 0),
        "blocked_connections": int(blocked_conn or 0),
        "fan_fan_threads": int(fan_threads or 0),
        "fan_fan_reports": int(reports or 0),
        "message_blocks": int(blocks or 0),
        "open_reports": int(open_reports or 0),
    }


def admin_list_blocks(db: Session, *, page: int = 1, limit: int = 50) -> dict:
    page = max(1, page)
    limit = min(max(1, limit), 100)
    rows = list(
        db.scalars(
            select(FanConnectionBlock).order_by(FanConnectionBlock.created_at.desc())
        ).all()
    )
    total = len(rows)
    start = (page - 1) * limit
    items = [
        _serialize_admin_block_item(db, row) for row in rows[start : start + limit]
    ]
    return {"items": items, "page": page, "limit": limit, "total": total}


def admin_list_reports(
    db: Session,
    *,
    page: int = 1,
    limit: int = 50,
    status_filter: str | None = None,
) -> dict:
    page = max(1, page)
    limit = min(max(1, limit), 100)
    stmt = select(FanConnectionReport).order_by(
        FanConnectionReport.created_at.desc()
    )
    if status_filter:
        stmt = stmt.where(FanConnectionReport.status == status_filter)
    rows = list(db.scalars(stmt).all())
    total = len(rows)
    start = (page - 1) * limit
    items = [
        serialize_admin_report(db, row, as_list_item=True)
        for row in rows[start : start + limit]
    ]
    return {"items": items, "page": page, "limit": limit, "total": total}


def admin_get_report(db: Session, report_id: UUID) -> dict:
    row = db.get(FanConnectionReport, report_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    return serialize_admin_report(db, row, as_list_item=False)


def admin_user_moderation_history(db: Session, user_id: UUID) -> dict:
    """Block + report history for a fan — display names only, no finance."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    pp = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    settings = ensure_connect_settings(db, target)
    reports_about = list(
        db.scalars(
            select(FanConnectionReport)
            .where(FanConnectionReport.reported_user_id == user_id)
            .order_by(FanConnectionReport.created_at.desc())
            .limit(50)
        ).all()
    )
    reports_filed = list(
        db.scalars(
            select(FanConnectionReport)
            .where(FanConnectionReport.reporter_user_id == user_id)
            .order_by(FanConnectionReport.created_at.desc())
            .limit(50)
        ).all()
    )
    as_blocker = list(
        db.scalars(
            select(FanConnectionBlock)
            .where(FanConnectionBlock.blocker_user_id == user_id)
            .order_by(FanConnectionBlock.created_at.desc())
            .limit(50)
        ).all()
    )
    as_blocked = list(
        db.scalars(
            select(FanConnectionBlock)
            .where(FanConnectionBlock.blocked_user_id == user_id)
            .order_by(FanConnectionBlock.created_at.desc())
            .limit(50)
        ).all()
    )
    return {
        "user_id": target.id,
        "display_name": (pp.display_name if pp else target.full_name) or "Fan",
        "username": pp.username if pp else None,
        "fan_connect_enabled": settings.fan_connect_enabled,
        "reports_about": [
            serialize_admin_report(db, r, as_list_item=True) for r in reports_about
        ],
        "reports_filed": [
            serialize_admin_report(db, r, as_list_item=True) for r in reports_filed
        ],
        "blocks_as_blocker": [
            _serialize_admin_block_item(db, b) for b in as_blocker
        ],
        "blocks_as_blocked": [
            _serialize_admin_block_item(db, b) for b in as_blocked
        ],
    }


def admin_resolve_report(
    db: Session,
    actor: User,
    report_id: UUID,
    *,
    resolution: str,
    admin_notes: str | None = None,
) -> FanConnectionReport:
    if resolution not in {C.REPORT_RESOLVED, C.REPORT_DISMISSED}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="resolution must be resolved or dismissed.",
        )
    row = db.get(FanConnectionReport, report_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    row.status = resolution
    if admin_notes is not None:
        row.admin_notes = admin_notes.strip()[:2000] or None
    write_audit_log(
        db,
        action="fan_connect.admin.resolve_report",
        actor_user_id=actor.id,
        resource_type="fan_connection_report",
        resource_id=str(row.id),
        details={"resolution": resolution},
    )
    db.commit()
    db.refresh(row)
    return row


def admin_disable_user(
    db: Session,
    actor: User,
    user_id: UUID,
    *,
    reason: str | None = None,
) -> dict:
    """Soft-disable Fan Connect for a user (settings off — no hard delete)."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    settings = ensure_connect_settings(db, target)
    settings.fan_connect_enabled = False
    settings.allow_connection_requests = False
    settings.discoverable_for_same_events = False
    settings.discoverable_for_similar_interests = False
    write_audit_log(
        db,
        action="fan_connect.admin.disable_user",
        actor_user_id=actor.id,
        resource_type="fan_connect_settings",
        resource_id=str(target.id),
        details={"reason": (reason or "")[:500] or None},
    )
    from app.fan_connect import analytics as fc_analytics

    fc_analytics.emit_fan_connect_disabled(db, user_id=target.id)
    db.commit()
    return {
        "user_id": target.id,
        "fan_connect_enabled": False,
        "allow_connection_requests": False,
        "disabled": True,
    }


def connection_accepted(db: Session, user_a: UUID, user_b: UUID) -> bool:
    conn = get_connection_pair(db, user_a, user_b)
    return messaging_allowed(conn)
