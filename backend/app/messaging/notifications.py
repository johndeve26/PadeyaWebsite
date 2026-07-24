"""Messaging notifications — presence-aware channels (no file contents/URLs).

WebSocket ``message.created`` remains the live channel.

Channel policy for new messages:
- In-app: always (inbox); toast via WS only reaches online clients
- Push: only when recipient is offline/inactive (and push prefs allow)
- Email: preference-gated, and only when offline/inactive
- Push copy: generic by default; optional safer sender-name preview
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.messaging.models import InAppNotification
from app.users.models import User

# Safe in-app copy — never include message bodies, filenames, or private file URLs.
TITLE_NEW_MESSAGE = "You have a new message."
BODY_NEW_MESSAGE = "Open Pàdéyá to read it — message bodies are never sent in alerts."
BODY_NEW_MESSAGE_WITH_ATTACHMENT = (
    "You have a new message with an attachment. Open Pàdéyá to view it."
)

# Coalesce rapid back-to-back notifies on the same thread (same kind).
_COALESCE_SECONDS = 45


def notification_copy(*, has_attachments: bool) -> tuple[str, str]:
    if has_attachments:
        return TITLE_NEW_MESSAGE, BODY_NEW_MESSAGE_WITH_ATTACHMENT
    return TITLE_NEW_MESSAGE, BODY_NEW_MESSAGE


def _normalize_kind(kind: str) -> str:
    k = (kind or "").strip()
    if not k:
        return "message.new"
    if k.startswith("message.") or k.startswith("messaging."):
        return k
    if k.startswith("fan_connect"):
        return k
    return f"message.{k}"


def _recent_duplicate(
    db: Session,
    *,
    user_id: UUID,
    thread_id: UUID,
    kind: str,
) -> bool:
    cutoff = datetime.now(UTC) - timedelta(seconds=_COALESCE_SECONDS)
    existing = db.scalar(
        select(InAppNotification.id)
        .where(
            InAppNotification.user_id == user_id,
            InAppNotification.thread_id == thread_id,
            InAppNotification.kind == kind,
            InAppNotification.created_at >= cutoff,
        )
        .limit(1)
    )
    return existing is not None


def _recipient_away(*, user_id: UUID, thread_id: UUID) -> bool:
    """True when push/email away-channels should fire."""
    from app.messaging.presence import is_user_active_on_thread, is_user_present

    if is_user_active_on_thread(user_id, thread_id):
        return False
    if is_user_present(user_id):
        return False
    return True


def _safe_sender_name(db: Session, sender_user_id: UUID | None) -> str | None:
    if sender_user_id is None:
        return None
    from app.push.privacy import safe_sender_display_name

    try:
        from app.passport.models import FanPassport

        passport = db.scalar(
            select(FanPassport).where(FanPassport.user_id == sender_user_id)
        )
        if passport and passport.display_name:
            return safe_sender_display_name(passport.display_name)
    except Exception:  # noqa: BLE001
        pass
    user = db.get(User, sender_user_id)
    if user and user.full_name:
        return safe_sender_display_name(user.full_name)
    return None


def _push_preview_context(
    db: Session,
    *,
    recipient_user_id: UUID,
    sender_user_id: UUID | None,
) -> dict:
    from app.email.prefs import get_or_create_preferences

    prefs = get_or_create_preferences(db, recipient_user_id)
    allow = bool(getattr(prefs, "push_message_previews", False))
    ctx: dict = {"allow_message_preview": allow}
    if allow:
        name = _safe_sender_name(db, sender_user_id)
        if name:
            ctx["sender_name"] = name
    return ctx


def _maybe_email_new_message(
    db: Session,
    *,
    recipient_user_id: UUID,
    thread_id: UUID,
    has_attachments: bool,
    kind: str,
) -> None:
    """Email channel — preference-gated; never includes attachment URLs/contents."""
    user = db.get(User, recipient_user_id)
    if user is None or not user.email:
        return
    from app.email.service import enqueue_template

    if kind.startswith("fan_connect"):
        template = "fan_connect_message"
    elif has_attachments:
        template = "attachment_received"
    elif "request" in kind:
        template = "message_request"
    else:
        template = "new_message"
    enqueue_template(
        db,
        template=template,
        to=user.email,
        recipient_user_id=user.id,
        context={"thread_id": str(thread_id)},
    )


def notify_new_chat_message(
    db: Session,
    *,
    recipient_user_id: UUID,
    thread_id: UUID,
    kind: str,
    link_path: str,
    has_attachments: bool = False,
    sender_user_id: UUID | None = None,
) -> bool:
    """Create in-app notification; push/email only when recipient is away.

    Returns True when a new in-app row was created.
    """
    stored_kind = _normalize_kind(kind)
    if _recent_duplicate(
        db, user_id=recipient_user_id, thread_id=thread_id, kind=stored_kind
    ):
        return False

    title, body = notification_copy(has_attachments=has_attachments)
    away = _recipient_away(user_id=recipient_user_id, thread_id=thread_id)
    from app.notifications.service import notify_user

    notify_user(
        db,
        user_id=recipient_user_id,
        kind=stored_kind,
        title=title[:160],
        body=body[:240],
        link_path=link_path,
        send_push=away,
        thread_id=thread_id,
        push_context=_push_preview_context(
            db,
            recipient_user_id=recipient_user_id,
            sender_user_id=sender_user_id,
        )
        if away
        else None,
    )
    if away:
        _maybe_email_new_message(
            db,
            recipient_user_id=recipient_user_id,
            thread_id=thread_id,
            has_attachments=has_attachments,
            kind=stored_kind,
        )
    return True
