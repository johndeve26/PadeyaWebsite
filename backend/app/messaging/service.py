"""Messaging service — fan ↔ host / fan ↔ fan inbox with privacy guards."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.messaging.attachment_privacy import serialize_attachment_public
from app.messaging.attachment_storage import (
    attachment_api_path,
    get_attachment_storage,
    verify_attachment_download_token,
)
from app.messaging.attachments import (
    ATT_STATUS_DELETED,
    ATT_STATUS_FAILED,
    ATT_STATUS_HIDDEN,
    ATT_STATUS_PENDING,
    ATT_STATUS_READY,
    ATT_STATUS_REJECTED,
    REASON_DISABLED_MODERATION,
    REASON_HIDDEN_MODERATION,
    REASON_HIDDEN_WITH_MESSAGE,
    AttachmentValidationError,
    get_attachment_limits,
    orphan_expiry_hours,
    preview_label_for_attachments,
    safe_filename_for,
    sanitize_original_filename,
    sha256_hex,
    validate_attachment_bytes,
)
from app.events.models import Event
from app.hosts.models import Host
from app.hosts.team_access import require_host_for_permission
from app.messaging import constants as C
from app.messaging.models import (
    InAppNotification,
    Message,
    MessageAttachment,
    MessageAttachmentDownload,
    MessageBlock,
    MessageReport,
    MessageSettings,
    MessageThread,
)
from app.messaging.relationships import (
    classify_fan_to_host,
    classify_host_to_fan,
    ensure_settings,
    existing_open_thread,
)
from app.passport.models import FanPassport
from app.users.models import User

logger = logging.getLogger("padeya.messaging")


def _now() -> datetime:
    return datetime.now(UTC)


def _preview(
    body: str,
    *,
    has_attachments: bool = False,
    attachment_content_types: list[str] | None = None,
) -> str:
    text = " ".join(body.strip().split())
    if text:
        return text[:220] + ("…" if len(text) > 220 else "")
    if has_attachments:
        return preview_label_for_attachments(attachment_content_types or [])
    return ""


def _soft_flag(body: str) -> str:
    lower = body.lower()
    link_count = lower.count("http://") + lower.count("https://") + lower.count("www.")
    if link_count >= 3:
        return C.MOD_FLAGGED
    for phrase in C.CONTACT_PRESSURE_PATTERNS:
        if phrase in lower:
            return C.MOD_FLAGGED
    return C.MOD_CLEAN


def _sanitize_filename(name: str | None) -> str | None:
    return sanitize_original_filename(name)


def _load_attachments(db: Session, message_id: UUID) -> list[MessageAttachment]:
    return list(
        db.scalars(
            select(MessageAttachment)
            .where(MessageAttachment.message_id == message_id)
            .order_by(MessageAttachment.created_at.asc())
        ).all()
    )


def _serialize_attachments(
    attachments: list[MessageAttachment],
    *,
    redact: bool,
    viewer_id: UUID | None = None,
    moderation_view: bool = False,
) -> list[dict]:
    """Allowlisted public metadata only — see attachment_privacy.py."""
    if redact and not moderation_view:
        return []
    out: list[dict] = []
    for a in attachments:
        item = serialize_attachment_public(
            a,
            viewer_id=viewer_id,
            ready_only=not moderation_view,
            moderation_view=moderation_view,
        )
        if item is not None:
            out.append(item)
    return out


def assert_user_may_attach(
    db: Session, user: User, thread_id: UUID
) -> MessageThread:
    """Upload/bind attachments only when send is allowed and thread is open.

    Product rules:
    - Fan↔host: valid participant thread; blocked users cannot attach.
    - Fan↔fan: accepted Fan Connect only; blocked/removed cannot attach.
    - Message requests: no attachments until accepted/active (safer default).
    """
    thread, as_host = _require_participant(db, thread_id, user)

    if thread.status == C.THREAD_STATUS_REQUEST:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Attachments are available after the message request is accepted.",
        )
    if thread.status in {C.THREAD_STATUS_BLOCKED, C.THREAD_STATUS_CLOSED}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Thread is closed.")

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        other = (
            thread.fan_b_user_id
            if thread.fan_user_id == user.id
            else thread.fan_user_id
        )
        if other is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid thread.")
        if is_blocked(db, a=user.id, b=other):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Messaging is blocked."
            )
        from app.fan_connect.service import connection_accepted

        if not connection_accepted(db, user.id, other):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Fan Connect required before messaging.",
            )
        return thread

    # Fan ↔ host — participant check already validated the pair.
    other = thread.host_user_id if not as_host else thread.fan_user_id
    if is_blocked(db, a=user.id, b=other):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Messaging is blocked."
        )
    return thread


def thread_allows_attachments(
    db: Session, user: User, thread: MessageThread, *, as_host: bool
) -> bool:
    """UI flag — same rules as assert_user_may_attach without raising."""
    if thread.status in {
        C.THREAD_STATUS_REQUEST,
        C.THREAD_STATUS_BLOCKED,
        C.THREAD_STATUS_CLOSED,
    }:
        return False

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        other = (
            thread.fan_b_user_id
            if thread.fan_user_id == user.id
            else thread.fan_user_id
        )
        if other is None or is_blocked(db, a=user.id, b=other):
            return False
        from app.fan_connect.service import connection_accepted

        return connection_accepted(db, user.id, other)

    other = thread.host_user_id if not as_host else thread.fan_user_id
    return not is_blocked(db, a=user.id, b=other)


def upload_message_attachment(
    db: Session,
    user: User,
    file: UploadFile,
    *,
    thread_id: UUID,
) -> MessageAttachment:
    """REST-only staged upload. Does not create a visible message until send.

    Flow: permission → validate → store → row status ready|rejected|failed.
    Orphan rows with message_id null expire via cleanup_orphan_attachments.
    """
    from app.messaging import ws_events

    # Opportunistic sweep on a separate session (never touch the request txn).
    try:
        from app.core.database import SessionLocal

        sweep = SessionLocal()
        try:
            cleanup_orphan_attachments(sweep, limit=50)
        finally:
            sweep.close()
    except Exception:
        pass

    thread = assert_user_may_attach(db, user, thread_id)
    limits = get_attachment_limits()
    # Read one byte past the largest allowed type so oversized files fail closed.
    max_read = max(limits.max_image_bytes, limits.max_doc_bytes) + 1
    data = file.file.read(max_read)
    original = _sanitize_filename(file.filename)

    # Staging row — never a chat message by itself.
    row = MessageAttachment(
        message_id=None,
        thread_id=thread.id,
        uploader_user_id=user.id,
        storage_key=None,
        url=None,
        original_filename=original,
        safe_filename=None,
        mime_type=(file.content_type or "application/octet-stream")[:120],
        file_size=len(data) if data else 0,
        file_extension=None,
        checksum_sha256=sha256_hex(data) if data else None,
        status=ATT_STATUS_PENDING,
        rejection_reason=None,
    )
    db.add(row)
    db.flush()

    try:
        validated = validate_attachment_bytes(
            filename=file.filename,
            declared_content_type=file.content_type,
            data=data,
        )
    except AttachmentValidationError as exc:
        row.status = ATT_STATUS_REJECTED
        row.rejection_reason = str(exc)[:300]
        db.commit()
        ws_events.publish_attachment_failed(user.id, detail=str(exc))
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Server-generated safe_filename + storage key — never user-controlled paths.
    safe_name = safe_filename_for(validated.extension)
    row.mime_type = validated.content_type
    row.file_size = validated.byte_size
    row.file_extension = validated.extension
    row.safe_filename = safe_name
    row.checksum_sha256 = validated.checksum_sha256
    row.width = validated.width
    row.height = validated.height
    store_data = validated.data

    try:
        stored = get_attachment_storage().store(
            data=store_data,
            extension=validated.extension,
            thread_id=thread.id,
            uploader_id=user.id,
            content_type=validated.content_type,
        )
    except ValueError as exc:
        row.status = ATT_STATUS_FAILED
        row.rejection_reason = str(exc)[:300]
        db.commit()
        ws_events.publish_attachment_failed(user.id, detail=str(exc))
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Persist opaque key only; client-facing URL is the authorized API path.
    row.storage_key = stored.key
    row.url = attachment_api_path(row.id)
    row.status = ATT_STATUS_READY
    row.rejection_reason = None
    db.commit()
    db.refresh(row)
    # Uploader-only ack — not a chat message; peers learn via message.created on send.
    ws_events.publish_attachment_ready(user.id, row)
    return row


def cleanup_orphan_attachments(
    db: Session, *, limit: int = 200
) -> int:
    """Expire unbound staged attachments (never sent) after the configured TTL.

    Soft-deletes rows and best-effort removes stored bytes. Safe to call often.
    """
    cutoff = _now() - timedelta(hours=orphan_expiry_hours())
    orphans = list(
        db.scalars(
            select(MessageAttachment)
            .where(
                MessageAttachment.message_id.is_(None),
                MessageAttachment.deleted_at.is_(None),
                MessageAttachment.status.in_(
                    (
                        ATT_STATUS_PENDING,
                        ATT_STATUS_READY,
                        ATT_STATUS_REJECTED,
                        ATT_STATUS_FAILED,
                    )
                ),
                MessageAttachment.created_at < cutoff,
            )
            .limit(max(1, min(limit, 500)))
        ).all()
    )
    if not orphans:
        return 0

    storage = get_attachment_storage()
    now = _now()
    for row in orphans:
        if row.storage_key:
            storage.delete(row.storage_key)
            row.storage_key = None
            row.url = None
        row.status = ATT_STATUS_DELETED
        row.deleted_at = now
        row.rejection_reason = row.rejection_reason or "Expired unused upload"
    db.commit()
    return len(orphans)


def serialize_attachment_upload(row: MessageAttachment) -> dict:
    """Uploader-only staging response — allowlisted fields, signed URL when ready."""
    item = serialize_attachment_public(
        row,
        viewer_id=row.uploader_user_id,
        ready_only=False,
    )
    if item is None:
        return {
            "id": str(row.id),
            "url": None,
            "content_type": row.mime_type,
            "byte_size": int(row.file_size or 0),
            "original_filename": row.original_filename,
            "status": row.status or "failed",
        }
    return item


def _admin_may_view_reported_attachment(
    db: Session, user: User, thread_id: UUID
) -> bool:
    """Admins may open attachments only for threads that have a message report."""
    from app.users.service import user_has_permission

    if not user_has_permission(user, "admin.full_access"):
        return False
    report_id = db.scalar(
        select(MessageReport.id)
        .where(MessageReport.thread_id == thread_id)
        .limit(1)
    )
    return report_id is not None


def get_attachment_for_download(
    db: Session,
    *,
    attachment_id: UUID,
    user: User | None = None,
    download_token: str | None = None,
) -> tuple[MessageAttachment, User]:
    """Authorize attachment download: login + thread access + ready + not deleted.

    Admins are not participants by default and cannot browse private files.
    They may download only when the thread appears in message-report moderation.
    """
    from app.users.service import get_user_by_id

    row = db.get(MessageAttachment, attachment_id)
    if row is None or not row.storage_key or row.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
    if row.status not in {ATT_STATUS_READY, ATT_STATUS_HIDDEN}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attachment not found.")

    viewer: User | None = user
    if viewer is None and download_token:
        uid = verify_attachment_download_token(
            download_token, attachment_id=attachment_id
        )
        if uid is not None:
            viewer = get_user_by_id(db, uid)
    if viewer is None or not viewer.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )

    try:
        _require_participant(db, row.thread_id, viewer)
        # Participants only download ready (not moderation-hidden) files.
        if row.status != ATT_STATUS_READY:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Attachment not found."
            )
    except HTTPException:
        if (
            row.status in {ATT_STATUS_READY, ATT_STATUS_HIDDEN}
            and _admin_may_view_reported_attachment(db, viewer, row.thread_id)
        ):
            return row, viewer
        raise
    return row, viewer


def stream_attachment_bytes(row: MessageAttachment) -> bytes:
    if not row.storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
    try:
        return get_attachment_storage().open_bytes(row.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Attachment not found."
        ) from exc


def record_attachment_download(
    db: Session, user: User, attachment_id: UUID
) -> MessageAttachmentDownload:
    """Audit download (caller must already authorize)."""
    log = MessageAttachmentDownload(attachment_id=attachment_id, user_id=user.id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _bind_attachments(
    db: Session,
    *,
    message: Message,
    uploader: User,
    attachment_ids: list[UUID],
) -> list[MessageAttachment]:
    if not attachment_ids:
        return []
    limits = get_attachment_limits()
    if len(attachment_ids) > limits.max_count:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"At most {limits.max_count} attachments allowed.",
        )
    # Preserve client order; reject duplicates / foreign / already-bound.
    seen: set[UUID] = set()
    bound: list[MessageAttachment] = []
    total_bytes = 0
    for aid in attachment_ids:
        if aid in seen:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Duplicate attachment id."
            )
        seen.add(aid)
        row = db.get(MessageAttachment, aid)
        if (
            row is None
            or row.uploader_user_id != uploader.id
            or row.thread_id != message.thread_id
            or row.message_id is not None
            or row.status != ATT_STATUS_READY
            or row.deleted_at is not None
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Invalid or unavailable attachment.",
            )
        total_bytes += int(row.file_size or 0)
        if total_bytes > limits.max_total_bytes:
            mb = limits.max_total_bytes // (1024 * 1024)
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Attachments for one message must total {mb}MB or less.",
            )
        row.message_id = message.id
        bound.append(row)
    db.flush()
    return bound


def _thread_participant_user_ids(thread: MessageThread) -> list[UUID]:
    from app.messaging.ws_events import participants

    return participants(thread)


def _publish_message_events(
    db: Session, *, thread: MessageThread, message: Message, sender_id: UUID
) -> None:
    """Push-only fan-out after REST send — never bypasses permission gates."""
    from app.messaging import ws_events

    try:
        ws_events.publish_new_message(
            db, thread=thread, message=message, sender_id=sender_id
        )
    except Exception:  # noqa: BLE001 — message is already committed; do not fail REST send
        logger.exception(
            "message WS fan-out failed thread=%s message=%s",
            thread.id,
            message.id,
        )


def is_blocked(db: Session, *, a: UUID, b: UUID) -> bool:
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


def _assert_active_sender(user: User, settings: MessageSettings) -> None:
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account inactive.")
    if settings.messaging_suspended_at is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Messaging is suspended for this account."
        )


def _rate_limit_thread_create(db: Session, user_id: UUID) -> None:
    since = _now() - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(MessageThread)
        .where(
            MessageThread.initiated_by_user_id == user_id,
            MessageThread.created_at >= since,
        )
    )
    if (count or 0) >= C.THREAD_CREATE_PER_HOUR:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many new conversations. Try again later.",
        )


def _rate_limit_send(db: Session, user_id: UUID) -> None:
    since = _now() - timedelta(minutes=1)
    count = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.sender_user_id == user_id, Message.created_at >= since)
    )
    if (count or 0) >= C.MESSAGES_PER_MINUTE:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Sending too quickly. Wait a moment.",
        )


def _notify(
    db: Session,
    *,
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    link_path: str | None,
    thread_id: UUID | None,
) -> None:
    from app.notifications.service import notify_user

    notify_user(
        db,
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        link_path=link_path,
        thread_id=thread_id,
        send_push=True,
    )


def _host_by_username(db: Session, username: str) -> Host | None:
    """Resolve host by Legacy username (= host slug)."""
    key = username.strip().lstrip("@").lower()
    return db.scalar(select(Host).where(func.lower(Host.slug) == key))


def _fan_by_username(db: Session, username: str) -> User | None:
    key = username.strip().lstrip("@").lower()
    passport = db.scalar(
        select(FanPassport).where(func.lower(FanPassport.username) == key)
    )
    if passport is None:
        return None
    return db.get(User, passport.user_id)


def _participant_for_host(
    db: Session, host: Host, *, viewer: User | None = None
) -> dict:
    avatar = None
    profile = host.profile
    if profile is not None:
        avatar = profile.avatar_url
    uname = host.slug
    from app.users.gender import (
        HIDDEN_GENDER_PAYLOAD,
        gender_display_payload,
        host_shows_personal_gender,
    )

    gender = dict(HIDDEN_GENDER_PAYLOAD)
    owner = db.get(User, host.user_id)
    if owner is not None:
        # Taxonomy-based individual vs org determination (never from host name).
        from app.taxonomy import service as taxonomy_service

        try:
            tax = taxonomy_service.get_host_taxonomy(db, host.id)
            type_slugs = list((tax or {}).get("host_type_slugs") or [])
        except Exception:  # noqa: BLE001
            type_slugs = []
        if host_shows_personal_gender(type_slugs):
            gender = gender_display_payload(
                db,
                viewer=viewer,
                profile_owner=owner,
                relationship_context="messaging",
            )
    return {
        "display_name": host.display_name,
        "username": uname,
        "role": "host",
        "legacy_path": f"/@{uname}" if uname else None,
        "passport_path": None,
        "avatar_url": avatar,
        **gender,
    }


def _participant_for_fan(
    db: Session, fan: User, *, viewer: User | None = None
) -> dict:
    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == fan.id))
    username = passport.username if passport else None
    public = bool(passport and passport.visibility == "public")
    unlisted = bool(passport and passport.visibility == "unlisted")
    # Messaging shows avatar when set — thread participants already share a conversation.
    avatar = passport.avatar_url if passport else None
    from app.users.gender import gender_display_payload

    gender = gender_display_payload(
        db,
        viewer=viewer,
        profile_owner=fan,
        relationship_context="messaging",
    )
    return {
        "display_name": (passport.display_name if passport else None)
        or fan.full_name
        or "Fan",
        "username": username if public or unlisted else username,
        "role": "fan",
        "legacy_path": None,
        "passport_path": f"/f/{username}" if username and (public or unlisted) else None,
        "avatar_url": avatar,
        **gender,
    }


def safe_typing_display_name(
    db: Session, user: User, thread: MessageThread
) -> str:
    """Public display name for ephemeral typing events — never email/phone/contact."""
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        return str(_participant_for_fan(db, user).get("display_name") or "Fan")
    host = db.scalar(select(Host).where(Host.user_id == user.id))
    if host is not None and (
        thread.host_id == host.id or thread.host_user_id == user.id
    ):
        return host.display_name or "Host"
    return str(_participant_for_fan(db, user).get("display_name") or "Fan")


def _related_event_chip(db: Session, event_id: UUID | None) -> dict | None:
    if not event_id:
        return None
    event = db.get(Event, event_id)
    if event is None:
        return None
    # Never expose private location here
    return {
        "id": str(event.id),
        "title": event.title,
        "slug": event.slug,
        "path": f"/events/{event.slug}",
        "banner_url": event.banner_url or event.mobile_banner_url,
    }


def _thread_unread(thread: MessageThread, *, as_fan: bool) -> bool:
    if thread.last_message_at is None:
        return False
    cursor = thread.fan_last_read_at if as_fan else thread.host_last_read_at
    if cursor is None:
        return True
    return thread.last_message_at > cursor


def _sender_display_name(db: Session, msg: Message) -> str:
    sender = db.get(User, msg.sender_user_id)
    if msg.message_type == C.MESSAGE_TYPE_SYSTEM or msg.sender_role == "system":
        return "Pàdéyá"
    if msg.sender_role == C.SENDER_HOST:
        host = db.scalar(select(Host).where(Host.user_id == msg.sender_user_id))
        return host.display_name if host else (sender.full_name if sender else "Host")
    if msg.sender_role == C.SENDER_FAN:
        part = _participant_for_fan(db, sender) if sender else {"display_name": "Fan"}
        return part["display_name"]
    if sender:
        return sender.full_name or "User"
    return "User"


def _unavailable_reply(
    *,
    reply_message_id: UUID | str,
    preview: str = "Original message unavailable",
    created_at=None,
) -> dict:
    return {
        "reply_message_id": str(reply_message_id),
        "reply_author_display_name": "",
        "reply_body_preview": preview,
        "reply_attachment_preview": None,
        "reply_created_at": created_at,
        "reply_is_unavailable": True,
    }


def _sanitize_reply_body_preview(body: str | None) -> str | None:
    """Truncate reply quote — never include storage paths or private system fields."""
    if not body:
        return None
    text = " ".join(body.strip().split())
    if not text:
        return None
    # Defense: strip path-like segments that must never appear in previews.
    if "/" in text or "\\" in text:
        # Keep human chat text; only drop obvious absolute/storage-looking paths.
        lowered = text.lower()
        if any(
            marker in lowered
            for marker in (
                "storage_key",
                "/var/",
                "/tmp/",
                "s3://",
                "file://",
            )
        ):
            return "Message unavailable"
    if len(text) > 120:
        return text[:117] + "…"
    return text


def _reply_to_public(db: Session, msg: Message, *, viewer_id: UUID) -> dict | None:
    """Safe reply quote for serializers + WS (no private contact / storage data)."""
    if msg.reply_to_message_id is None:
        return None
    parent = db.get(Message, msg.reply_to_message_id)
    if parent is None:
        return _unavailable_reply(reply_message_id=msg.reply_to_message_id)
    # Never quote across threads (stale/bad FK).
    if parent.thread_id != msg.thread_id:
        return _unavailable_reply(
            reply_message_id=parent.id, created_at=parent.created_at
        )
    from app.messaging.chat_actions import is_deleted_for_user

    if is_deleted_for_user(db, parent.id, viewer_id):
        return _unavailable_reply(
            reply_message_id=parent.id, created_at=parent.created_at
        )
    if parent.status == C.MESSAGE_STATUS_DELETED or parent.deleted_at is not None:
        return _unavailable_reply(
            reply_message_id=parent.id, created_at=parent.created_at
        )
    if (
        parent.status == C.MESSAGE_STATUS_HIDDEN
        or parent.moderation_status == C.MOD_HIDDEN
    ):
        return _unavailable_reply(
            reply_message_id=parent.id,
            preview="Message unavailable",
            created_at=parent.created_at,
        )

    from app.messaging.attachments import (
        ATT_STATUS_READY,
        preview_label_for_attachments,
    )

    atts = [
        a
        for a in _load_attachments(db, parent.id)
        if a.status == ATT_STATUS_READY and a.deleted_at is None
    ]
    body_preview = _sanitize_reply_body_preview(parent.body)
    att_preview = None
    if atts:
        att_preview = preview_label_for_attachments([a.mime_type for a in atts])
        # Prefer a sanitized display filename when a single file is attached.
        if len(atts) == 1:
            name = _sanitize_filename(atts[0].original_filename)
            if name:
                att_preview = name[:80]
    return {
        "reply_message_id": str(parent.id),
        "reply_author_display_name": _sender_display_name(db, parent),
        "reply_body_preview": body_preview,
        "reply_attachment_preview": att_preview,
        "reply_created_at": parent.created_at,
        "reply_is_unavailable": False,
    }


def serialize_message(
    db: Session,
    msg: Message,
    *,
    viewer_id: UUID,
    hide_body: bool = False,
    moderation_view: bool = False,
    pinned_ids: set[UUID] | None = None,
    starred_ids: set[UUID] | None = None,
    deleted_for_me_ids: set[UUID] | None = None,
) -> dict:
    from app.messaging.chat_actions import (
        message_deleted_for_user_ids,
        pinned_message_ids,
        starred_message_ids,
    )

    name = _sender_display_name(db, msg)

    if deleted_for_me_ids is None:
        deleted_for_me_ids = message_deleted_for_user_ids(db, viewer_id, [msg.id])
    deleted_for_me = msg.id in deleted_for_me_ids

    redact = False
    body = msg.body
    if deleted_for_me and not moderation_view:
        body = C.DELETED_FOR_ME_BODY
        redact = True
    elif msg.status == C.MESSAGE_STATUS_HIDDEN or msg.moderation_status == C.MOD_HIDDEN:
        body = "[Message hidden by moderation]"
        redact = True
    elif msg.status == C.MESSAGE_STATUS_DELETED:
        body = "[Message removed]"
        redact = True
    elif hide_body:
        body = "[Unavailable]"
        redact = True

    attachments = _serialize_attachments(
        _load_attachments(db, msg.id),
        redact=redact,
        viewer_id=viewer_id,
        moderation_view=moderation_view,
    )

    if pinned_ids is None:
        pinned_ids = pinned_message_ids(db, msg.thread_id)
    if starred_ids is None:
        starred_ids = starred_message_ids(db, viewer_id, [msg.id])

    return {
        "id": str(msg.id),
        "thread_id": str(msg.thread_id),
        "sender_role": msg.sender_role,
        "sender_display_name": name,
        "body": body,
        "message_type": msg.message_type,
        "status": msg.status,
        "moderation_status": msg.moderation_status,
        "created_at": msg.created_at,
        "is_mine": msg.sender_user_id == viewer_id,
        "attachments": attachments,
        "edited_at": None if deleted_for_me else msg.edited_at,
        "reply_to": None if redact else _reply_to_public(db, msg, viewer_id=viewer_id),
        "is_pinned": False if deleted_for_me else msg.id in pinned_ids,
        "is_starred": False if deleted_for_me else msg.id in starred_ids,
        "deleted_for_me": deleted_for_me,
    }

def _viewer_last_message_preview(
    db: Session, thread: MessageThread, *, viewer_id: UUID
) -> str | None:
    """Thread preview for this viewer — never expose deleted/hidden bodies."""
    from app.messaging.chat_actions import is_deleted_for_user

    if not thread.last_message_id:
        return thread.last_message_preview
    if is_deleted_for_user(db, thread.last_message_id, viewer_id):
        return C.DELETED_FOR_ME_BODY
    last = db.get(Message, thread.last_message_id)
    if last is None:
        return thread.last_message_preview
    if (
        last.status == C.MESSAGE_STATUS_HIDDEN
        or last.moderation_status == C.MOD_HIDDEN
    ):
        return "[Message hidden by moderation]"
    if last.status == C.MESSAGE_STATUS_DELETED or last.deleted_at is not None:
        return "[Message removed]"
    return thread.last_message_preview


def serialize_thread_list_item(
    db: Session, thread: MessageThread, *, viewer: User, as_host: bool
) -> dict:
    preview = _viewer_last_message_preview(db, thread, viewer_id=viewer.id)
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        other_id = (
            thread.fan_b_user_id
            if thread.fan_user_id == viewer.id
            else thread.fan_user_id
        )
        other = db.get(User, other_id) if other_id else None
        counterpart = (
            _participant_for_fan(db, other, viewer=viewer)
            if other
            else {"display_name": "Fan", "role": "fan"}
        )
        # Canonical low UUID uses fan_* read/archive columns; high uses host_*.
        as_low = thread.fan_user_id == viewer.id
        archived = bool(
            thread.fan_archived_at if as_low else thread.host_archived_at
        )
        blocked = thread.status == C.THREAD_STATUS_BLOCKED or is_blocked(
            db, a=viewer.id, b=other_id  # type: ignore[arg-type]
        )
        connect_ctx = (
            fan_connect_context_payload(db, viewer.id, other_id)
            if other_id
            else None
        )
        return {
            "id": str(thread.id),
            "status": thread.status,
            "subject": thread.subject,
            "last_message_preview": preview,
            "last_message_at": thread.last_message_at,
            "unread": _thread_unread(thread, as_fan=as_low),
            "is_request": False,
            "archived": archived,
            "blocked": blocked,
            "related_event": _related_event_chip(db, thread.related_event_id),
            "counterpart": counterpart,
            "thread_type": C.THREAD_TYPE_FAN_FAN,
            "connect_context": connect_ctx,
            "created_at": thread.created_at,
        }

    fan = db.get(User, thread.fan_user_id)
    host = db.get(Host, thread.host_id) if thread.host_id else None
    counterpart = (
        _participant_for_fan(db, fan, viewer=viewer)
        if as_host and fan
        else _participant_for_host(db, host, viewer=viewer)  # type: ignore[arg-type]
    )
    other_id = thread.fan_user_id if as_host else thread.host_user_id
    archived = bool(
        thread.host_archived_at if as_host else thread.fan_archived_at
    )
    blocked = thread.status == C.THREAD_STATUS_BLOCKED or is_blocked(
        db, a=viewer.id, b=other_id
    )
    return {
        "id": str(thread.id),
        "status": thread.status,
        "subject": thread.subject,
        "last_message_preview": preview,
        "last_message_at": thread.last_message_at,
        "unread": _thread_unread(thread, as_fan=not as_host),
        "is_request": thread.status == C.THREAD_STATUS_REQUEST,
        "archived": archived,
        "blocked": blocked,
        "related_event": _related_event_chip(db, thread.related_event_id),
        "counterpart": counterpart,
        "thread_type": thread.thread_type,
        "connect_context": None,
        "created_at": thread.created_at,
    }


def list_blocked_users(db: Session, user: User) -> list[dict]:
    """Privacy-safe blocked list for the settings screen (no emails/phones)."""
    rows = list(
        db.scalars(
            select(MessageBlock)
            .where(MessageBlock.blocker_user_id == user.id)
            .order_by(MessageBlock.created_at.desc())
        ).all()
    )
    items: list[dict] = []
    for row in rows:
        blocked = db.get(User, row.blocked_user_id)
        host = db.scalar(select(Host).where(Host.user_id == row.blocked_user_id))
        if host is not None:
            part = _participant_for_host(db, host)
        elif blocked is not None:
            part = _participant_for_fan(db, blocked)
        else:
            part = {"display_name": "User", "username": None, "role": "user"}
        items.append(
            {
                "user_id": str(row.blocked_user_id),
                "display_name": part.get("display_name") or "User",
                "username": part.get("username"),
                "role": part.get("role") or "user",
                "reason": row.reason,
                "created_at": row.created_at,
            }
        )
    return items


def get_settings_payload(db: Session, user: User) -> dict:
    s = ensure_settings(db, user)
    return {
        "allow_messages_from_hosts_i_follow": s.allow_messages_from_hosts_i_follow,
        "allow_messages_from_hosts_i_attended": s.allow_messages_from_hosts_i_attended,
        "allow_messages_from_public": s.allow_messages_from_public,
        "message_requests_enabled": s.message_requests_enabled,
        "allow_messages_from_followers": s.allow_messages_from_followers,
        "allow_messages_from_ticket_buyers": s.allow_messages_from_ticket_buyers,
        "allow_messages_from_public_host": s.allow_messages_from_public_host,
        "allow_event_inquiries": s.allow_event_inquiries,
        "auto_reply_enabled": s.auto_reply_enabled,
        "auto_reply_message": s.auto_reply_message,
        "blocked_users": list_blocked_users(db, user),
    }


def update_settings(db: Session, user: User, payload) -> MessageSettings:
    s = ensure_settings(db, user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if hasattr(s, key):
            setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return s


def unread_count_for_user(db: Session, user: User) -> int:
    fan_threads = list(
        db.scalars(
            select(MessageThread).where(
                or_(
                    MessageThread.fan_user_id == user.id,
                    MessageThread.fan_b_user_id == user.id,
                )
            )
        ).all()
    )
    host = db.scalar(select(Host).where(Host.user_id == user.id))
    host_threads: list[MessageThread] = []
    if host:
        host_threads = list(
            db.scalars(
                select(MessageThread).where(
                    MessageThread.host_id == host.id,
                    MessageThread.thread_type == C.THREAD_TYPE_FAN_HOST,
                )
            ).all()
        )
    n = 0
    for t in fan_threads:
        as_low = t.fan_user_id == user.id
        archived = t.fan_archived_at if as_low else t.host_archived_at
        if archived is None and _thread_unread(t, as_fan=as_low):
            n += 1
    for t in host_threads:
        if t.host_archived_at is None and _thread_unread(t, as_fan=False):
            n += 1
    return n


def list_threads_for_fan(
    db: Session,
    user: User,
    *,
    filter_key: str = "all",
    q: str | None = None,
    page: int = 1,
    limit: int = 30,
) -> dict:
    page = max(1, page)
    limit = min(max(1, limit), 50)
    stmt = select(MessageThread).where(
        or_(
            MessageThread.fan_user_id == user.id,
            MessageThread.fan_b_user_id == user.id,
        )
    )
    rows = list(db.scalars(stmt).all())

    def _archived(t: MessageThread) -> bool:
        as_low = t.fan_user_id == user.id
        return bool(t.fan_archived_at if as_low else t.host_archived_at)

    if filter_key == "archived":
        rows = [t for t in rows if _archived(t)]
    else:
        rows = [t for t in rows if not _archived(t)]
    if filter_key == "requests":
        rows = [
            t
            for t in rows
            if t.status == C.THREAD_STATUS_REQUEST
            and t.thread_type != C.THREAD_TYPE_FAN_FAN
        ]
    elif filter_key == "event":
        rows = [t for t in rows if t.related_event_id is not None]
    rows.sort(
        key=lambda t: (t.last_message_at or t.created_at or datetime.min.replace(tzinfo=UTC)),
        reverse=True,
    )
    if filter_key == "unread":
        rows = [
            t
            for t in rows
            if _thread_unread(t, as_fan=t.fan_user_id == user.id)
        ]
    if q:
        needle = q.strip().lower()
        filtered = []
        for t in rows:
            item = serialize_thread_list_item(db, t, viewer=user, as_host=False)
            part = item.get("counterpart") or {}
            hay = " ".join(
                [
                    str(part.get("display_name") or ""),
                    str(part.get("username") or ""),
                    t.subject or "",
                    t.last_message_preview or "",
                ]
            ).lower()
            if needle in hay:
                filtered.append(t)
        rows = filtered
    total = len(rows)
    start = (page - 1) * limit
    page_rows = rows[start : start + limit]
    items = [
        serialize_thread_list_item(db, t, viewer=user, as_host=False) for t in page_rows
    ]
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "unread_count": unread_count_for_user(db, user),
    }


def list_threads_for_host(
    db: Session,
    user: User,
    *,
    filter_key: str = "all",
    q: str | None = None,
    page: int = 1,
    limit: int = 30,
) -> dict:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="messages.view"
    )
    page = max(1, page)
    limit = min(max(1, limit), 50)
    stmt = select(MessageThread).where(MessageThread.host_id == host.id)
    if filter_key == "archived":
        stmt = stmt.where(MessageThread.host_archived_at.is_not(None))
    else:
        stmt = stmt.where(MessageThread.host_archived_at.is_(None))
    if filter_key == "requests":
        stmt = stmt.where(MessageThread.status == C.THREAD_STATUS_REQUEST)
    elif filter_key == "event":
        stmt = stmt.where(MessageThread.related_event_id.is_not(None))
    stmt = stmt.order_by(
        MessageThread.last_message_at.desc().nullslast(),
        MessageThread.created_at.desc(),
    )
    rows = list(db.scalars(stmt).all())
    if filter_key == "unread":
        rows = [t for t in rows if _thread_unread(t, as_fan=False)]
    if q:
        needle = q.strip().lower()
        filtered = []
        for t in rows:
            fan = db.get(User, t.fan_user_id)
            part = _participant_for_fan(db, fan) if fan else {}
            hay = " ".join(
                [
                    str(part.get("display_name") or ""),
                    str(part.get("username") or ""),
                    t.subject or "",
                    t.last_message_preview or "",
                ]
            ).lower()
            if needle in hay:
                filtered.append(t)
        rows = filtered
    total = len(rows)
    start = (page - 1) * limit
    page_rows = rows[start : start + limit]
    items = [
        serialize_thread_list_item(db, t, viewer=user, as_host=True) for t in page_rows
    ]
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "unread_count": unread_count_for_user(db, user),
    }


def _require_participant(
    db: Session, thread_id: UUID, user: User
) -> tuple[MessageThread, bool]:
    from app.teams.permissions import host_team_or_owner_allows

    thread = db.get(MessageThread, thread_id)
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    as_host = False
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        if user.id not in {thread.fan_user_id, thread.fan_b_user_id}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        # as_host True means "high" participant (host_* columns)
        as_host = thread.fan_user_id != user.id
        return thread, as_host
    if thread.fan_user_id == user.id:
        as_host = False
    elif thread.host_user_id == user.id:
        as_host = True
    elif thread.host_id is not None and host_team_or_owner_allows(
        db, user.id, thread.host_id, "messages.view", "messages.reply"
    ):
        as_host = True
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    return thread, as_host


def get_thread_detail(db: Session, user: User, thread_id: UUID) -> dict:
    from app.messaging.chat_actions import (
        list_pinned_messages,
        message_deleted_for_user_ids,
        pinned_message_ids,
        starred_message_ids,
    )

    thread, as_host = _require_participant(db, thread_id, user)
    msgs = list(
        db.scalars(
            select(Message)
            .where(Message.thread_id == thread.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    msg_ids = [m.id for m in msgs]
    pin_ids = pinned_message_ids(db, thread.id)
    star_ids = starred_message_ids(db, user.id, msg_ids)
    deleted_for_me_ids = message_deleted_for_user_ids(db, user.id, msg_ids)
    serialized = [
        serialize_message(
            db,
            m,
            viewer_id=user.id,
            pinned_ids=pin_ids,
            starred_ids=star_ids,
            deleted_for_me_ids=deleted_for_me_ids,
        )
        for m in msgs
    ]
    pinned_msgs = [
        m
        for m in list_pinned_messages(db, thread.id)
        if m.id not in deleted_for_me_ids
    ]
    pinned_public = [
        serialize_message(
            db,
            m,
            viewer_id=user.id,
            pinned_ids=pin_ids,
            starred_ids=star_ids,
            deleted_for_me_ids=deleted_for_me_ids,
        )
        for m in pinned_msgs
    ]

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        other_id = (
            thread.fan_b_user_id
            if thread.fan_user_id == user.id
            else thread.fan_user_id
        )
        other = db.get(User, other_id) if other_id else None
        counterpart = (
            _participant_for_fan(db, other, viewer=user)
            if other
            else {"display_name": "Fan", "role": "fan"}
        )
        blocked = thread.status == C.THREAD_STATUS_BLOCKED or is_blocked(
            db, a=user.id, b=other_id  # type: ignore[arg-type]
        )
        archived = bool(
            thread.host_archived_at if as_host else thread.fan_archived_at
        )
        from app.messaging.permissions import can_send_message

        can_reply = can_send_message(db, user, thread)
        can_attach = thread_allows_attachments(
            db, user, thread, as_host=as_host
        )
        connect_ctx = (
            fan_connect_context_payload(db, user.id, other_id)
            if other_id
            else None
        )
        return {
            "id": str(thread.id),
            "status": thread.status,
            "subject": thread.subject,
            "is_request": False,
            "can_reply": can_reply,
            "can_attach": can_attach,
            "blocked": blocked,
            "archived": archived,
            "counterpart_user_id": str(other_id) if other_id else None,
            "related_event": _related_event_chip(db, thread.related_event_id),
            "counterpart": counterpart,
            "thread_type": C.THREAD_TYPE_FAN_FAN,
            "connect_context": connect_ctx,
            "messages": serialized,
            "pinned_messages": pinned_public,
            "privacy_reminder": C.PRIVACY_REMINDER,
            "peer_read_at": peer_read_at_for_viewer(thread, as_host=as_host),
            "created_at": thread.created_at,
        }

    fan = db.get(User, thread.fan_user_id)
    host = db.get(Host, thread.host_id) if thread.host_id else None
    counterpart = (
        _participant_for_fan(db, fan, viewer=user)
        if as_host and fan
        else _participant_for_host(db, host, viewer=user)  # type: ignore[arg-type]
    )
    other_id = thread.host_user_id if not as_host else thread.fan_user_id
    blocked = thread.status == C.THREAD_STATUS_BLOCKED or is_blocked(
        db, a=user.id, b=other_id
    )
    archived = bool(
        thread.host_archived_at if as_host else thread.fan_archived_at
    )
    from app.messaging.permissions import can_send_message

    can_reply = can_send_message(db, user, thread)
    can_attach = thread_allows_attachments(db, user, thread, as_host=as_host)
    return {
        "id": str(thread.id),
        "status": thread.status,
        "subject": thread.subject,
        "is_request": thread.status == C.THREAD_STATUS_REQUEST,
        "can_reply": can_reply,
        "can_attach": can_attach,
        "blocked": blocked,
        "archived": archived,
        "counterpart_user_id": str(other_id),
        "related_event": _related_event_chip(db, thread.related_event_id),
        "counterpart": counterpart,
        "thread_type": thread.thread_type,
        "connect_context": None,
        "messages": serialized,
        "pinned_messages": pinned_public,
        "privacy_reminder": C.PRIVACY_REMINDER,
        "peer_read_at": peer_read_at_for_viewer(thread, as_host=as_host),
        "created_at": thread.created_at,
    }


def peer_read_at_for_viewer(
    thread: MessageThread, *, as_host: bool
) -> datetime | None:
    """Counterpart's read cursor for Seen UI (thread-level receipt)."""
    if as_host:
        return thread.fan_last_read_at
    return thread.host_last_read_at


def mark_read(db: Session, user: User, thread_id: UUID) -> MessageThread:
    """Mark the caller's side of the thread as read (thread-level cursor).

    Uses fan_last_read_at / host_last_read_at — no per-message receipt table.
    Only the authenticated participant can advance their own cursor; peers are
    notified over WebSocket and cannot forge another user's read receipt.
    """
    from app.messaging import ws_events

    thread, as_host = _require_participant(db, thread_id, user)
    now = _now()
    if as_host:
        thread.host_last_read_at = now
    else:
        thread.fan_last_read_at = now
    db.commit()
    db.refresh(thread)
    ws_events.publish_thread_read(db, thread, reader_id=user.id, read_at=now)
    return thread


def archive_thread(db: Session, user: User, thread_id: UUID) -> MessageThread:
    thread, as_host = _require_participant(db, thread_id, user)
    now = _now()
    if as_host:
        thread.host_archived_at = now
    else:
        thread.fan_archived_at = now
    db.commit()
    db.refresh(thread)
    return thread


def accept_request(db: Session, user: User, thread_id: UUID) -> MessageThread:
    from app.messaging import ws_events

    thread, as_host = _require_participant(db, thread_id, user)
    if thread.status != C.THREAD_STATUS_REQUEST:
        return thread
    # Only the non-initiator (recipient) accepts
    if thread.initiated_by_user_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Waiting for the other party to accept."
        )

    # Defense in depth: never accept a self message request / self fan_fan row.
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        assert_not_self_message(
            sender_user_id=thread.fan_user_id,
            recipient_user_id=thread.fan_b_user_id or thread.fan_user_id,
        )
    elif thread.fan_user_id == thread.host_user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=C.SELF_MESSAGE_DETAIL,
        )

    thread.status = C.THREAD_STATUS_ACTIVE
    thread.accepted_at = _now()
    _notify(
        db,
        user_id=thread.initiated_by_user_id,
        kind="message_request_accepted",
        title="Message request accepted",
        body="You can continue the conversation on Pàdéyá.",
        link_path=f"/messages/{thread.id}",
        thread_id=thread.id,
    )
    db.commit()
    db.refresh(thread)
    ws_events.publish_message_request(
        thread,
        event="accepted",
        notify_user_ids=_thread_participant_user_ids(thread),
        db=db,
    )
    return thread


def _append_message(
    db: Session,
    *,
    thread: MessageThread,
    sender: User,
    sender_role: str,
    body: str,
    attachment_ids: list[UUID] | None = None,
    fan_fan_as_high: bool = False,
    reply_to_message_id: UUID | None = None,
) -> Message:
    from app.messaging.chat_actions import validate_reply_target

    body = (body or "").strip()
    attachment_ids = list(attachment_ids or [])
    if len(body) > C.MAX_BODY_LENGTH:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid message body.")
    if not body and not attachment_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Message body or attachments required."
        )
    settings = ensure_settings(db, sender)
    _assert_active_sender(sender, settings)
    _rate_limit_send(db, sender.id)

    reply_id = None
    if reply_to_message_id is not None:
        validate_reply_target(
            db,
            sender,
            thread_id=thread.id,
            reply_to_message_id=reply_to_message_id,
        )
        reply_id = reply_to_message_id

    mod = _soft_flag(body) if body else C.MOD_CLEAN
    msg = Message(
        thread_id=thread.id,
        sender_user_id=sender.id,
        sender_role=sender_role,
        body=body or "",
        message_type=C.MESSAGE_TYPE_TEXT,
        status=C.MESSAGE_STATUS_SENT,
        moderation_status=mod,
        reply_to_message_id=reply_id,
    )
    db.add(msg)
    db.flush()
    bound = _bind_attachments(
        db, message=msg, uploader=sender, attachment_ids=attachment_ids
    )
    if bound and not body:
        if all(
            (a.content_type or "").startswith("image/") for a in bound
        ):
            msg.message_type = C.MESSAGE_TYPE_IMAGE
        else:
            msg.message_type = C.MESSAGE_TYPE_ATTACHMENT
    thread.last_message_id = msg.id
    thread.last_message_at = msg.created_at or _now()
    thread.last_message_preview = _preview(
        body,
        has_attachments=bool(bound),
        attachment_content_types=[a.mime_type for a in bound],
    )

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        if fan_fan_as_high:
            thread.host_last_read_at = _now()
            thread.host_archived_at = None
        else:
            thread.fan_last_read_at = _now()
            thread.fan_archived_at = None
        recipient_id = (
            thread.fan_b_user_id
            if thread.fan_user_id == sender.id
            else thread.fan_user_id
        )
        if recipient_id:
            from app.fan_connect.notifications import notify_connected_fan_message

            notify_connected_fan_message(
                db,
                recipient_user_id=recipient_id,
                thread_id=thread.id,
                has_attachments=bool(bound),
                sender_user_id=sender.id,
            )
        return msg

    if sender_role == C.SENDER_FAN:
        thread.fan_last_read_at = _now()
        thread.fan_archived_at = None
    else:
        thread.host_last_read_at = _now()
        thread.host_archived_at = None

    recipient_id = (
        thread.host_user_id if sender_role == C.SENDER_FAN else thread.fan_user_id
    )
    kind = "host_reply" if sender_role == C.SENDER_HOST else "fan_reply"
    if thread.status == C.THREAD_STATUS_REQUEST and sender.id == thread.initiated_by_user_id:
        kind = "message_request"
    from app.messaging.notifications import notify_new_chat_message

    notify_new_chat_message(
        db,
        recipient_user_id=recipient_id,
        thread_id=thread.id,
        kind=kind,
        link_path=(
            f"/host/messages/{thread.id}"
            if sender_role == C.SENDER_FAN
            else f"/dashboard/messages/{thread.id}"
        ),
        has_attachments=bool(bound),
        sender_user_id=sender.id,
    )
    return msg


def assert_not_self_message(*, sender_user_id: UUID, recipient_user_id: UUID) -> None:
    """Block fan↔fan / direct threads where both parties are the same user."""
    if sender_user_id == recipient_user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=C.SELF_MESSAGE_DETAIL,
        )


def ensure_fan_fan_thread(
    db: Session,
    *,
    user_a: UUID,
    user_b: UUID,
    for_accept: bool = False,
) -> MessageThread:
    """Create or unlock fan↔fan thread.

    Threads are only created at Fan Connect accept (`for_accept=True`).
    Afterwards, callers must already have an accepted connection.
    """
    assert_not_self_message(sender_user_id=user_a, recipient_user_id=user_b)
    if is_blocked(db, a=user_a, b=user_b):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Messaging is blocked."
        )
    if not for_accept:
        from app.fan_connect.service import connection_accepted

        if not connection_accepted(db, user_a, user_b):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Fan Connect required before messaging.",
            )

    low, high = (user_a, user_b) if str(user_a) < str(user_b) else (user_b, user_a)
    existing = db.scalar(
        select(MessageThread).where(
            MessageThread.thread_type == C.THREAD_TYPE_FAN_FAN,
            MessageThread.fan_user_id == low,
            MessageThread.fan_b_user_id == high,
        )
    )
    if existing is not None:
        if existing.status == C.THREAD_STATUS_BLOCKED:
            # Never silently reopen blocked threads.
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Messaging is blocked."
            )
        if existing.status == C.THREAD_STATUS_CLOSED and for_accept:
            existing.status = C.THREAD_STATUS_ACTIVE
            existing.accepted_at = _now()
        existing.fan_archived_at = None
        existing.host_archived_at = None
        db.flush()
        return existing

    if not for_accept:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Fan Connect required before messaging.",
        )

    thread = MessageThread(
        thread_type=C.THREAD_TYPE_FAN_FAN,
        fan_user_id=low,
        fan_b_user_id=high,
        host_id=None,
        host_user_id=high,
        status=C.THREAD_STATUS_ACTIVE,
        initiated_by_user_id=user_a,
        accepted_at=_now(),
        subject="Fan Connect",
    )
    db.add(thread)
    db.flush()
    from app.fan_connect import analytics as fc_analytics

    fc_analytics.emit_fan_fan_thread_created(
        db, user_id=user_a, thread_id=thread.id
    )
    return thread


def _safe_connect_reason_phrase(reasons: list | None) -> str:
    """Short safe phrase for system copy — never VIP/spend/private venue."""
    if not reasons:
        return "Fan Connect"
    first = reasons[0] if isinstance(reasons[0], dict) else {}
    label = str(first.get("label") or "").strip()
    if not label:
        return "Fan Connect"
    prefixes = (
        "You’re both going to ",
        "You're both going to ",
        "You’re both checked in at ",
        "You're both checked in at ",
        "You both follow ",
        "You both like ",
        "You’re both around ",
        "You're both around ",
        "You both earned ",
        "You both have verified check-ins at ",
    )
    for prefix in prefixes:
        if label.startswith(prefix):
            return label[len(prefix) :].rstrip(".")
    return label


def fan_connect_context_payload(db: Session, user_a: UUID, user_b: UUID) -> dict | None:
    """Safe connection context for inbox UI — public reason labels only."""
    from app.fan_connect import constants as FC
    from app.fan_connect.eligibility import get_connection_pair

    conn = get_connection_pair(db, user_a, user_b)
    if conn is None or conn.status != FC.STATUS_CONNECTED or conn.removed_at is not None:
        return None
    reasons_raw = conn.reasons_json or []
    reasons = [
        {"code": str(r.get("code") or ""), "label": str(r.get("label") or "")}
        for r in reasons_raw
        if isinstance(r, dict) and r.get("label")
    ][:3]
    phrase = _safe_connect_reason_phrase(reasons_raw)
    context_label = (
        reasons[0]["label"]
        if reasons
        else f"Connected through {phrase}"
    )
    # Prefer short “Connected through …” when label is the long reason form.
    if reasons and reasons[0]["label"].startswith(("You both", "You’re both", "You're both")):
        context_label = f"Connected through {phrase}"
    return {
        "badge": C.FAN_CONNECT_BADGE,
        "context_label": context_label,
        "reasons": reasons,
    }


def append_fan_connect_system_message(
    db: Session,
    *,
    thread: MessageThread,
    actor: User,
    reasons: list | None,
) -> Message | None:
    """System line on accept: “You connected through [safe reason] on Pàdéyá.”"""
    existing = db.scalar(
        select(Message.id).where(
            Message.thread_id == thread.id,
            Message.message_type == C.MESSAGE_TYPE_SYSTEM,
            Message.body.like(f"{C.FAN_CONNECT_SYSTEM_PREFIX}%"),
        )
    )
    if existing is not None:
        return None
    phrase = _safe_connect_reason_phrase(reasons)
    body = f"{C.FAN_CONNECT_SYSTEM_PREFIX}{phrase} on Pàdéyá."
    msg = Message(
        thread_id=thread.id,
        sender_user_id=actor.id,
        sender_role="system",
        body=body,
        message_type=C.MESSAGE_TYPE_SYSTEM,
        status=C.MESSAGE_STATUS_SENT,
        moderation_status=C.MOD_CLEAN,
    )
    db.add(msg)
    thread.last_message_preview = body[:240]
    thread.last_message_at = _now()
    db.flush()
    return msg


def _merch_product_name(db: Session, order_item_id: UUID | None) -> str | None:
    if order_item_id is None:
        return None
    from app.payments.models import OrderItem

    item = db.get(OrderItem, order_item_id)
    if item is None:
        return None
    name = getattr(item, "product_name", None) or None
    return (name or "").strip() or None


def _append_merch_context_system(
    db: Session,
    *,
    thread: MessageThread,
    actor: User,
    order_item_id: UUID | None,
) -> None:
    """System line when a thread is about a merch line — no email/phone."""
    product_name = _merch_product_name(db, order_item_id)
    if not product_name:
        return
    existing = db.scalar(
        select(Message.id).where(
            Message.thread_id == thread.id,
            Message.message_type == C.MESSAGE_TYPE_SYSTEM,
            Message.body.like("This conversation is about %"),
        )
    )
    if existing is not None:
        return
    msg = Message(
        thread_id=thread.id,
        sender_user_id=actor.id,
        sender_role="system",
        body=f"This conversation is about {product_name}.",
        message_type=C.MESSAGE_TYPE_SYSTEM,
        status=C.MESSAGE_STATUS_SENT,
        moderation_status=C.MOD_CLEAN,
    )
    db.add(msg)
    db.flush()


def create_thread_as_fan(
    db: Session,
    user: User,
    *,
    host_id: UUID | None,
    host_username: str | None,
    related_event_id: UUID | None,
    related_merch_order_item_id: UUID | None = None,
    subject: str | None,
    body: str,
) -> MessageThread:
    settings = ensure_settings(db, user)
    _assert_active_sender(user, settings)
    _rate_limit_thread_create(db, user.id)

    host: Host | None = None
    if host_id:
        host = db.get(Host, host_id)
    elif host_username:
        host = _host_by_username(db, host_username)
    if host is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Host not found")

    from app.hosts.fan_self_abuse import assert_not_own_host_fan_messaging

    assert_not_own_host_fan_messaging(db, user_id=user.id, host_id=host.id)

    if is_blocked(db, a=user.id, b=host.user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Messaging is blocked.")

    access, status_hint = classify_fan_to_host(
        db, fan=user, host=host, related_event_id=related_event_id
    )
    if access == "denied":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot message this host right now.",
        )

    thread = existing_open_thread(db, fan_user_id=user.id, host_id=host.id)
    created = False
    if thread is None:
        thread = MessageThread(
            thread_type=C.THREAD_TYPE_FAN_HOST,
            fan_user_id=user.id,
            host_id=host.id,
            host_user_id=host.user_id,
            related_event_id=related_event_id,
            related_merch_order_item_id=related_merch_order_item_id,
            subject=subject,
            status=status_hint,
            initiated_by_user_id=user.id,
            accepted_at=_now() if status_hint == C.THREAD_STATUS_ACTIVE else None,
        )
        db.add(thread)
        db.flush()
        created = True
    else:
        if thread.status == C.THREAD_STATUS_BLOCKED:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Thread is blocked.")
        if related_event_id and thread.related_event_id is None:
            thread.related_event_id = related_event_id
        if (
            related_merch_order_item_id
            and getattr(thread, "related_merch_order_item_id", None) is None
        ):
            thread.related_merch_order_item_id = related_merch_order_item_id
        if subject and not thread.subject:
            thread.subject = subject
        thread.fan_archived_at = None

    if related_merch_order_item_id:
        _append_merch_context_system(
            db,
            thread=thread,
            actor=user,
            order_item_id=related_merch_order_item_id,
        )

    first_msg = _append_message(
        db, thread=thread, sender=user, sender_role=C.SENDER_FAN, body=body
    )

    # Auto-reply once for new active threads
    auto_msg: Message | None = None
    host_settings = ensure_settings(db, db.get(User, host.user_id))  # type: ignore[arg-type]
    if (
        created
        and host_settings.auto_reply_enabled
        and host_settings.auto_reply_message
        and thread.status == C.THREAD_STATUS_ACTIVE
    ):
        host_user = db.get(User, host.user_id)
        if host_user:
            auto_msg = _append_message(
                db,
                thread=thread,
                sender=host_user,
                sender_role=C.SENDER_HOST,
                body=host_settings.auto_reply_message,
            )

    db.commit()
    db.refresh(thread)
    db.refresh(first_msg)
    _publish_message_events(db, thread=thread, message=first_msg, sender_id=user.id)
    if auto_msg is not None:
        db.refresh(auto_msg)
        _publish_message_events(
            db, thread=thread, message=auto_msg, sender_id=host.user_id
        )
    if created and thread.status == C.THREAD_STATUS_REQUEST:
        from app.messaging import ws_events

        ws_events.publish_message_request(
            thread,
            event="created",
            notify_user_ids=_thread_participant_user_ids(thread),
            db=db,
        )
    return thread


def create_thread_as_host(
    db: Session,
    user: User,
    *,
    fan_user_id: UUID | None,
    fan_username: str | None,
    related_event_id: UUID | None,
    related_merch_order_item_id: UUID | None = None,
    subject: str | None,
    body: str,
) -> MessageThread:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="messages.reply"
    )
    settings = ensure_settings(db, user)
    _assert_active_sender(user, settings)
    _rate_limit_thread_create(db, user.id)

    fan: User | None = None
    if fan_user_id:
        fan = db.get(User, fan_user_id)
    elif fan_username:
        fan = _fan_by_username(db, fan_username)
    if fan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fan not found")

    assert_not_self_message(sender_user_id=user.id, recipient_user_id=fan.id)

    from app.hosts.fan_self_abuse import (
        MESSAGING_OWN_HOST_DETAIL,
        is_user_owner_of_host,
    )

    # Host desk must not open a fan↔host thread with the host owner as the fan.
    if is_user_owner_of_host(
        db, user_id=fan.id, host_profile_id=host.id
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=MESSAGING_OWN_HOST_DETAIL,
        )

    if is_blocked(db, a=user.id, b=fan.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Messaging is blocked.")

    access, status_hint = classify_host_to_fan(db, host=host, fan=fan)
    if access == "denied":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You can only message fans who follow you, bought tickets, checked in, reviewed you, or already messaged you.",
        )

    thread = existing_open_thread(db, fan_user_id=fan.id, host_id=host.id)
    if thread is None:
        thread = MessageThread(
            thread_type=C.THREAD_TYPE_FAN_HOST,
            fan_user_id=fan.id,
            host_id=host.id,
            host_user_id=host.user_id,
            related_event_id=related_event_id,
            related_merch_order_item_id=related_merch_order_item_id,
            subject=subject,
            status=status_hint,
            initiated_by_user_id=user.id,
            accepted_at=_now() if status_hint == C.THREAD_STATUS_ACTIVE else None,
        )
        db.add(thread)
        db.flush()
    else:
        if thread.status == C.THREAD_STATUS_BLOCKED:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Thread is blocked.")
        if related_event_id and thread.related_event_id is None:
            thread.related_event_id = related_event_id
        if (
            related_merch_order_item_id
            and getattr(thread, "related_merch_order_item_id", None) is None
        ):
            thread.related_merch_order_item_id = related_merch_order_item_id
        thread.host_archived_at = None

    if related_merch_order_item_id:
        _append_merch_context_system(
            db,
            thread=thread,
            actor=user,
            order_item_id=related_merch_order_item_id,
        )

    first_msg = _append_message(
        db, thread=thread, sender=user, sender_role=C.SENDER_HOST, body=body
    )
    db.commit()
    db.refresh(thread)
    db.refresh(first_msg)
    _publish_message_events(db, thread=thread, message=first_msg, sender_id=user.id)
    if thread.status == C.THREAD_STATUS_REQUEST:
        from app.messaging import ws_events

        ws_events.publish_message_request(
            thread,
            event="created",
            notify_user_ids=_thread_participant_user_ids(thread),
            db=db,
        )
    return thread


def send_in_thread(
    db: Session,
    user: User,
    thread_id: UUID,
    body: str,
    attachment_ids: list[UUID] | None = None,
    reply_to_message_id: UUID | None = None,
) -> Message:
    from app.messaging.permissions import assert_can_send_message
    from app.users.restrictions import assert_can_message

    assert_can_message(db, user)

    thread, as_host = _require_participant(db, thread_id, user)
    assert_can_send_message(db, user, thread)
    attachment_ids = list(attachment_ids or [])
    # Attachments follow the same gates as upload (no request-state files).
    if attachment_ids:
        assert_user_may_attach(db, user, thread_id)

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        assert_not_self_message(
            sender_user_id=thread.fan_user_id,
            recipient_user_id=thread.fan_b_user_id or thread.fan_user_id,
        )
        # Both fans send as fan; as_host only selects read-receipt columns.
        role = C.SENDER_FAN
        msg = _append_message(
            db,
            thread=thread,
            sender=user,
            sender_role=role,
            body=body,
            attachment_ids=attachment_ids,
            fan_fan_as_high=as_host,
            reply_to_message_id=reply_to_message_id,
        )
        from app.fan_connect import analytics as fc_analytics

        fc_analytics.emit_fan_fan_message_sent(
            db, user_id=user.id, thread_id=thread.id
        )
        db.commit()
        db.refresh(msg)
        _publish_message_events(db, thread=thread, message=msg, sender_id=user.id)
        return msg

    # Accept request implicitly when recipient replies
    accepted_request = False
    if (
        thread.status == C.THREAD_STATUS_REQUEST
        and thread.initiated_by_user_id != user.id
    ):
        thread.status = C.THREAD_STATUS_ACTIVE
        thread.accepted_at = _now()
        accepted_request = True

    role = C.SENDER_HOST if as_host else C.SENDER_FAN
    msg = _append_message(
        db,
        thread=thread,
        sender=user,
        sender_role=role,
        body=body,
        attachment_ids=attachment_ids,
        reply_to_message_id=reply_to_message_id,
    )
    db.commit()
    db.refresh(msg)
    db.refresh(thread)
    _publish_message_events(db, thread=thread, message=msg, sender_id=user.id)
    if accepted_request:
        from app.messaging import ws_events

        ws_events.publish_message_request(
            thread,
            event="accepted",
            notify_user_ids=_thread_participant_user_ids(thread),
            db=db,
        )
    return msg


def block_user(
    db: Session,
    user: User,
    *,
    blocked_user_id: UUID,
    reason: str | None,
    host_id: UUID | None = None,
) -> None:
    from app.messaging import ws_events

    if blocked_user_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=C.SELF_BLOCK_DETAIL
        )
    existing = db.scalar(
        select(MessageBlock).where(
            MessageBlock.blocker_user_id == user.id,
            MessageBlock.blocked_user_id == blocked_user_id,
        )
    )
    if existing is None:
        db.add(
            MessageBlock(
                blocker_user_id=user.id,
                blocked_user_id=blocked_user_id,
                host_id=host_id,
                reason=(reason or "")[:300] or None,
            )
        )
    # Mark related threads blocked (fan↔host and fan↔fan)
    host = db.scalar(select(Host).where(Host.user_id == user.id))
    clauses = [
        (MessageThread.fan_user_id == user.id)
        & (MessageThread.host_user_id == blocked_user_id),
        (MessageThread.host_user_id == user.id)
        & (MessageThread.fan_user_id == blocked_user_id),
        (MessageThread.thread_type == C.THREAD_TYPE_FAN_FAN)
        & (
            (
                (MessageThread.fan_user_id == user.id)
                & (MessageThread.fan_b_user_id == blocked_user_id)
            )
            | (
                (MessageThread.fan_user_id == blocked_user_id)
                & (MessageThread.fan_b_user_id == user.id)
            )
        ),
    ]
    if host:
        clauses.append(
            (MessageThread.host_id == host.id)
            & (MessageThread.fan_user_id == blocked_user_id)
        )
    affected = list(db.scalars(select(MessageThread).where(or_(*clauses))).all())
    for t in affected:
        t.status = C.THREAD_STATUS_BLOCKED
    write_audit_log(
        db,
        action="messaging.block",
        actor_user_id=user.id,
        resource_type="message_block",
        resource_id=str(blocked_user_id),
        details={"reason": (reason or "")[:120] or None},
    )
    db.commit()
    for t in affected:
        db.refresh(t)
        ws_events.publish_thread_disabled(t, reason="blocked", db=db)


def unblock_user(db: Session, user: User, blocked_user_id: UUID) -> None:
    row = db.scalar(
        select(MessageBlock).where(
            MessageBlock.blocker_user_id == user.id,
            MessageBlock.blocked_user_id == blocked_user_id,
        )
    )
    if row:
        db.delete(row)
        db.commit()


def report_thread(
    db: Session,
    user: User,
    thread_id: UUID,
    *,
    reason: str,
    details: str | None,
    message_id: UUID | None,
) -> MessageReport:
    from app.messaging import ws_events

    thread, as_host = _require_participant(db, thread_id, user)
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        reported = (
            thread.fan_b_user_id
            if thread.fan_user_id == user.id
            else thread.fan_user_id
        )
    else:
        reported = thread.host_user_id if not as_host else thread.fan_user_id
    if reported is None or reported == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=C.SELF_REPORT_DETAIL,
        )
    report = MessageReport(
        thread_id=thread.id,
        message_id=message_id,
        reporter_user_id=user.id,
        reported_user_id=reported,
        reason=reason.strip()[:120],
        details=(details or "")[:2000] or None,
        status=C.REPORT_OPEN,
    )
    db.add(report)
    thread.status = C.THREAD_STATUS_REPORTED
    write_audit_log(
        db,
        action="messaging.report",
        actor_user_id=user.id,
        resource_type="message_report",
        resource_id=str(thread.id),
        details={"reason": reason[:120]},
    )
    from app.notifications.triggers import notify_admins_report

    notify_admins_report(
        db,
        report_id=report.id,
        report_kind="message",
        title="New message report on Pàdéyá",
        body="A conversation was reported and needs moderation.",
        link_path="/admin/message-reports",
    )
    db.commit()
    db.refresh(report)
    db.refresh(thread)
    ws_events.publish_thread_disabled(thread, reason="reported", db=db)
    return report


def list_reports(
    db: Session, *, status_filter: str | None, page: int, limit: int
) -> dict:
    page = max(1, page)
    limit = min(max(1, limit), 100)
    stmt = select(MessageReport).order_by(MessageReport.created_at.desc())
    if status_filter:
        stmt = stmt.where(MessageReport.status == status_filter)
    rows = list(db.scalars(stmt).all())
    total = len(rows)
    start = (page - 1) * limit
    items = []
    for r in rows[start : start + limit]:
        reporter = db.get(User, r.reporter_user_id)
        reported = db.get(User, r.reported_user_id)
        thread = db.get(MessageThread, r.thread_id)
        host = (
            db.get(Host, thread.host_id)
            if thread is not None and thread.host_id is not None
            else None
        )
        preview = None
        if r.message_id:
            msg = db.get(Message, r.message_id)
            if msg:
                preview = _preview(msg.body)
                if not preview:
                    atts = _load_attachments(db, msg.id)
                    if atts:
                        preview = preview_label_for_attachments(
                            [a.mime_type for a in atts]
                        )
        elif thread:
            preview = thread.last_message_preview
        items.append(
            {
                "id": str(r.id),
                "thread_id": str(r.thread_id),
                "reason": r.reason,
                "status": r.status,
                "reporter_display_name": (reporter.full_name if reporter else "User"),
                "reported_display_name": (reported.full_name if reported else "User"),
                "host_display_name": host.display_name if host else None,
                "thread_type": thread.thread_type if thread else None,
                "created_at": r.created_at,
                "message_preview": preview,
            }
        )
    return {"items": items, "page": page, "limit": limit, "total": total}


def get_report_detail(
    db: Session, report_id: UUID, *, admin: User | None = None
) -> dict:
    """Moderation-only thread view. Attachment URLs are signed for the admin.

    Admins must use report-scoped download (not a private-attachment browser).
    """
    r = db.get(MessageReport, report_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    thread = db.get(MessageThread, r.thread_id)
    reporter = db.get(User, r.reporter_user_id)
    reported = db.get(User, r.reported_user_id)
    # Host label only for fan↔host threads — never invent host for fan_fan.
    host = None
    if thread and thread.thread_type != C.THREAD_TYPE_FAN_FAN and thread.host_id:
        host = db.get(Host, thread.host_id)
    msgs = []
    if thread:
        msgs = list(
            db.scalars(
                select(Message)
                .where(Message.thread_id == thread.id)
                .order_by(Message.created_at.asc())
            ).all()
        )
    # Prefer admin viewer so signed download tokens authorize via report scope.
    admin_viewer = (
        admin.id
        if admin is not None
        else (reported.id if reported else UUID(int=0))
    )
    connect_context = None
    if (
        thread
        and thread.thread_type == C.THREAD_TYPE_FAN_FAN
        and thread.fan_user_id
        and thread.fan_b_user_id
    ):
        connect_context = fan_connect_context_payload(
            db, thread.fan_user_id, thread.fan_b_user_id
        )
    return {
        "id": str(r.id),
        "thread_id": str(r.thread_id),
        "reason": r.reason,
        "details": r.details,
        "status": r.status,
        "admin_notes": r.admin_notes,
        "reporter_display_name": reporter.full_name if reporter else "User",
        "reported_display_name": reported.full_name if reported else "User",
        "host_display_name": host.display_name if host else None,
        "thread_type": thread.thread_type if thread else None,
        "connect_context": connect_context,
        "messages": [
            serialize_message(
                db, m, viewer_id=admin_viewer, moderation_view=True
            )
            for m in msgs
        ],
        "created_at": r.created_at,
    }


def _require_admin_moderatable_attachment(
    db: Session, admin: User, attachment_id: UUID
) -> MessageAttachment:
    from app.users.service import user_has_permission

    if not user_has_permission(admin, "admin.full_access"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")
    row = db.get(MessageAttachment, attachment_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
    if not _admin_may_view_reported_attachment(db, admin, row.thread_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Attachments can only be moderated on reported threads.",
        )
    return row


def _publish_attachment_message_update(
    db: Session, row: MessageAttachment
) -> None:
    from app.messaging import ws_events

    if row.message_id is None:
        return
    msg = db.get(Message, row.message_id)
    thread = db.get(MessageThread, row.thread_id)
    if msg is None or thread is None:
        return
    ws_events.publish_message_updated(db, thread=thread, message=msg)


def serialize_attachment_admin(row: MessageAttachment, *, admin_id: UUID) -> dict:
    item = serialize_attachment_public(
        row,
        viewer_id=admin_id,
        ready_only=False,
        moderation_view=True,
    )
    return item or {
        "id": str(row.id),
        "url": None,
        "content_type": row.mime_type,
        "byte_size": int(row.file_size or 0),
        "original_filename": row.original_filename,
        "status": row.status,
    }


def hide_attachment(db: Session, admin: User, attachment_id: UUID) -> MessageAttachment:
    row = _require_admin_moderatable_attachment(db, admin, attachment_id)
    row.status = ATT_STATUS_HIDDEN
    row.deleted_at = None
    row.rejection_reason = REASON_HIDDEN_MODERATION
    write_audit_log(
        db,
        action="messaging.attachment.hide",
        actor_user_id=admin.id,
        resource_type="message_attachment",
        resource_id=str(row.id),
        details={"thread_id": str(row.thread_id)},
    )
    db.commit()
    db.refresh(row)
    _publish_attachment_message_update(db, row)
    return row


def restore_attachment(
    db: Session, admin: User, attachment_id: UUID
) -> MessageAttachment:
    row = _require_admin_moderatable_attachment(db, admin, attachment_id)
    if not row.storage_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Attachment file is no longer available to restore.",
        )
    if row.status not in {
        ATT_STATUS_HIDDEN,
        ATT_STATUS_DELETED,
        ATT_STATUS_REJECTED,
    }:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Attachment is not in a restorable moderation state.",
        )
    row.status = ATT_STATUS_READY
    row.deleted_at = None
    row.rejection_reason = None
    write_audit_log(
        db,
        action="messaging.attachment.restore",
        actor_user_id=admin.id,
        resource_type="message_attachment",
        resource_id=str(row.id),
        details={"thread_id": str(row.thread_id)},
    )
    db.commit()
    db.refresh(row)
    _publish_attachment_message_update(db, row)
    return row


def soft_delete_attachment(
    db: Session, admin: User, attachment_id: UUID
) -> MessageAttachment:
    """Disable access via soft-delete — keeps storage_key (no hard delete)."""
    row = _require_admin_moderatable_attachment(db, admin, attachment_id)
    row.status = ATT_STATUS_DELETED
    row.deleted_at = _now()
    row.rejection_reason = REASON_DISABLED_MODERATION
    # Intentionally keep storage_key for retention / possible restore.
    write_audit_log(
        db,
        action="messaging.attachment.delete",
        actor_user_id=admin.id,
        resource_type="message_attachment",
        resource_id=str(row.id),
        details={"thread_id": str(row.thread_id), "soft": True},
    )
    db.commit()
    db.refresh(row)
    _publish_attachment_message_update(db, row)
    return row


def review_attachment(
    db: Session, admin: User, attachment_id: UUID
) -> MessageAttachment:
    row = _require_admin_moderatable_attachment(db, admin, attachment_id)
    row.reviewed_at = _now()
    write_audit_log(
        db,
        action="messaging.attachment.review",
        actor_user_id=admin.id,
        resource_type="message_attachment",
        resource_id=str(row.id),
        details={"thread_id": str(row.thread_id)},
    )
    db.commit()
    db.refresh(row)
    return row


def patch_report(
    db: Session, admin: User, report_id: UUID, *, status_value: str | None, notes: str | None
) -> MessageReport:
    r = db.get(MessageReport, report_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    if status_value:
        if status_value not in {
            C.REPORT_OPEN,
            C.REPORT_REVIEWING,
            C.REPORT_RESOLVED,
            C.REPORT_DISMISSED,
        }:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        r.status = status_value
        if status_value in {C.REPORT_RESOLVED, C.REPORT_DISMISSED}:
            r.resolved_by_user_id = admin.id
            _notify(
                db,
                user_id=r.reporter_user_id,
                kind="report_resolved",
                title="Message report updated",
                body="Your message report was reviewed on Pàdéyá.",
                link_path="/messages",
                thread_id=r.thread_id,
            )
    if notes is not None:
        r.admin_notes = notes[:2000]
    write_audit_log(
        db,
        action="messaging.report.moderate",
        actor_user_id=admin.id,
        resource_type="message_report",
        resource_id=str(r.id),
        details={"status": r.status},
    )
    db.commit()
    db.refresh(r)
    return r


def _require_admin_moderatable_message(
    db: Session, admin: User, message_id: UUID
) -> Message:
    """Admins may hide/restore only on threads that have a message report."""
    from app.users.service import user_has_permission

    if not user_has_permission(admin, "admin.full_access"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")
    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    if not _admin_may_view_reported_attachment(db, admin, msg.thread_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Messages can only be moderated on reported threads.",
        )
    return msg


def hide_message(db: Session, admin: User, message_id: UUID) -> Message:
    from app.messaging import ws_events
    from app.messaging.chat_actions import clear_pins_for_message

    msg = _require_admin_moderatable_message(db, admin, message_id)
    msg.status = C.MESSAGE_STATUS_HIDDEN
    msg.moderation_status = C.MOD_HIDDEN
    clear_pins_for_message(db, msg.id)
    # Soft-hide bound attachments with the message (no hard file delete).
    for att in _load_attachments(db, msg.id):
        if att.status == ATT_STATUS_READY and att.deleted_at is None:
            att.status = ATT_STATUS_HIDDEN
            att.rejection_reason = REASON_HIDDEN_WITH_MESSAGE
    thread = db.get(MessageThread, msg.thread_id)
    if thread is not None and thread.last_message_id == msg.id:
        # Keep inbox preview aligned with participant serializers.
        thread.last_message_preview = "[Message hidden by moderation]"
    write_audit_log(
        db,
        action="messaging.message.hide",
        actor_user_id=admin.id,
        resource_type="message",
        resource_id=str(msg.id),
        details={},
    )
    db.commit()
    db.refresh(msg)
    if thread is not None:
        ws_events.publish_message_deleted(db, thread=thread, message=msg)
        ws_events.publish_thread_updated(thread, db=db)
    return msg


def restore_message(db: Session, admin: User, message_id: UUID) -> Message:
    from app.messaging import ws_events

    msg = _require_admin_moderatable_message(db, admin, message_id)
    msg.status = C.MESSAGE_STATUS_SENT
    msg.moderation_status = C.MOD_CLEAN
    # Restore attachments that were auto-hidden with the message only.
    for att in _load_attachments(db, msg.id):
        if (
            att.status == ATT_STATUS_HIDDEN
            and att.rejection_reason == REASON_HIDDEN_WITH_MESSAGE
            and att.storage_key
            and att.deleted_at is None
        ):
            att.status = ATT_STATUS_READY
            att.rejection_reason = None
    thread = db.get(MessageThread, msg.thread_id)
    if thread is not None and thread.last_message_id == msg.id:
        atts = _load_attachments(db, msg.id)
        thread.last_message_preview = _preview(
            msg.body or "",
            has_attachments=any(
                a.status == ATT_STATUS_READY and a.deleted_at is None for a in atts
            ),
            attachment_content_types=[
                a.mime_type
                for a in atts
                if a.status == ATT_STATUS_READY and a.deleted_at is None
            ],
        )
    write_audit_log(
        db,
        action="messaging.message.restore",
        actor_user_id=admin.id,
        resource_type="message",
        resource_id=str(msg.id),
        details={},
    )
    db.commit()
    db.refresh(msg)
    if thread is not None:
        ws_events.publish_message_updated(db, thread=thread, message=msg)
        ws_events.publish_thread_updated(thread, db=db)
    return msg


def list_notifications(db: Session, user: User, *, limit: int = 30) -> dict:
    from app.notifications.categories import inbox_only_kinds_clause

    stmt = select(InAppNotification).where(InAppNotification.user_id == user.id)
    inbox_only = inbox_only_kinds_clause()
    if inbox_only is not None:
        stmt = stmt.where(inbox_only)
    rows = list(
        db.scalars(
            stmt.order_by(InAppNotification.created_at.desc())
            .limit(min(limit, 50))
        ).all()
    )
    return {
        "items": [
            {
                "id": str(n.id),
                "kind": n.kind,
                "title": n.title,
                "body": n.body,
                "link_path": n.link_path,
                "read_at": n.read_at,
                "created_at": n.created_at,
            }
            for n in rows
        ]
    }


def host_can_message_fan(db: Session, host_user: User, fan_user_id: UUID) -> bool:
    try:
        host, _ = require_host_for_permission(
            db, user=host_user, host_id=None, permission="messages.reply"
        )
    except HTTPException:
        return False
    fan = db.get(User, fan_user_id)
    if fan is None:
        return False
    if fan.id == host_user.id:
        return False
    access, _ = classify_host_to_fan(db, host=host, fan=fan)
    return access in {"allowed", "request"}


def host_can_message_fan_username(
    db: Session, host_user: User, username: str
) -> bool:
    fan = _fan_by_username(db, username)
    if fan is None:
        return False
    return host_can_message_fan(db, host_user, fan.id)
