"""Fan Connect in-app notifications — no private events or message bodies."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.passport.models import FanPassport
from app.users.models import User

KIND_REQUEST = "fan_connect.request"
KIND_ACCEPTED = "fan_connect.accepted"
KIND_DECLINED = "fan_connect.declined"
KIND_REMOVED = "fan_connect.removed"
KIND_MESSAGE = "fan_connect.message"


def _safe_short_name(db: Session, user_id: UUID) -> str:
    """Public display first name only — never email/phone."""
    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    if passport and passport.display_name:
        return passport.display_name.strip().split()[0]
    user = db.get(User, user_id)
    if user and user.full_name:
        return user.full_name.strip().split()[0]
    return "A fan"


def _push_context_for(
    db: Session,
    *,
    recipient_user_id: UUID,
    display_name: str | None,
) -> dict:
    from app.email.prefs import get_or_create_preferences
    from app.push.privacy import safe_sender_display_name

    prefs = get_or_create_preferences(db, recipient_user_id)
    allow = bool(getattr(prefs, "push_message_previews", False))
    ctx: dict = {"allow_message_preview": allow}
    if allow:
        safe = safe_sender_display_name(display_name)
        if safe:
            ctx["sender_name"] = safe
            ctx["name"] = safe
            ctx["requester_name"] = safe
            ctx["acceptor_name"] = safe
    return ctx


def _add(
    db: Session,
    *,
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    link_path: str,
    thread_id: UUID | None = None,
    display_name: str | None = None,
    dedupe_key: str | None = None,
) -> None:
    from app.notifications.service import notify_user

    notify_user(
        db,
        user_id=user_id,
        kind=kind,
        title=title[:160],
        body=body[:240],
        link_path=link_path,
        thread_id=thread_id,
        dedupe_key=dedupe_key,
        send_push=True,
        push_context=_push_context_for(
            db,
            recipient_user_id=user_id,
            display_name=display_name,
        ),
    )


def notify_connection_request(
    db: Session,
    *,
    recipient_user_id: UUID,
    requester_user_id: UUID,
    connection_id: UUID | None = None,
) -> None:
    name = _safe_short_name(db, requester_user_id)
    title = f"{name} sent you a Fan Connect request."
    dedupe = (
        f"fan_connect:request:{connection_id}"
        if connection_id
        else f"fan_connect:request:{requester_user_id}:{recipient_user_id}"
    )
    _add(
        db,
        user_id=recipient_user_id,
        kind=KIND_REQUEST,
        title=title,
        body="Review the request on Pàdéyá — chat unlocks only if you both accept.",
        link_path="/connect/requests",
        display_name=name,
        dedupe_key=dedupe,
    )
    recipient = db.get(User, recipient_user_id)
    if recipient and recipient.email:
        from app.email.service import enqueue_template

        enqueue_template(
            db,
            template="fan_connect_request",
            to=recipient.email,
            recipient_user_id=recipient.id,
            dedupe_key=f"fan_connect:request:{requester_user_id}:{recipient_user_id}",
            context={"requester_name": name},
        )


def notify_request_accepted(
    db: Session,
    *,
    requester_user_id: UUID,
    acceptor_user_id: UUID,
    thread_id: UUID | None,
) -> None:
    name = _safe_short_name(db, acceptor_user_id)
    title = f"{name} accepted your Fan Connect request."
    link = (
        f"/dashboard/messages/{thread_id}"
        if thread_id
        else "/connect/connections"
    )
    _add(
        db,
        user_id=requester_user_id,
        kind=KIND_ACCEPTED,
        title=title,
        body="You can message on Pàdéyá — no phone numbers needed.",
        link_path=link,
        thread_id=thread_id,
        display_name=name,
    )
    requester = db.get(User, requester_user_id)
    if requester and requester.email:
        from app.email.service import enqueue_template

        enqueue_template(
            db,
            template="fan_connect_accepted",
            to=requester.email,
            recipient_user_id=requester.id,
            dedupe_key=f"fan_connect:accepted:{requester_user_id}:{acceptor_user_id}",
            context={"acceptor_name": name},
        )


def notify_request_declined(
    db: Session,
    *,
    requester_user_id: UUID,
    decliner_user_id: UUID,
) -> None:
    name = _safe_short_name(db, decliner_user_id)
    title = "Connect request update"
    _add(
        db,
        user_id=requester_user_id,
        kind=KIND_DECLINED,
        title=title,
        body="Your connect request was not accepted. You can explore other fans on Pàdéyá.",
        link_path="/connect",
    )


def notify_connection_removed(
    db: Session,
    *,
    other_user_id: UUID,
    actor_user_id: UUID,
) -> None:
    name = _safe_short_name(db, actor_user_id)
    title = f"{name} removed your Fan Connect connection."
    _add(
        db,
        user_id=other_user_id,
        kind=KIND_REMOVED,
        title=title,
        body="Messaging for that connection is turned off on Pàdéyá.",
        link_path="/connect/connections",
    )


def notify_connected_fan_message(
    db: Session,
    *,
    recipient_user_id: UUID,
    thread_id: UUID,
    has_attachments: bool = False,
    sender_user_id: UUID | None = None,
) -> None:
    """New message from a connected fan — no full message content or file URLs."""
    from app.messaging.notifications import notify_new_chat_message

    notify_new_chat_message(
        db,
        recipient_user_id=recipient_user_id,
        thread_id=thread_id,
        kind=KIND_MESSAGE,
        link_path=f"/dashboard/messages/{thread_id}",
        has_attachments=has_attachments,
        sender_user_id=sender_user_id,
    )
