"""Messaging API routes — fan, host, and admin moderation."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from fastapi.responses import Response as RawResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CurrentUser,
    get_current_user_optional,
    require_permission,
)
from app.core.database import get_db
from app.messaging import chat_actions
from app.messaging import service as svc
from app.messaging.schemas import (
    AcceptRequestBody,
    AdminReportDetailPublic,
    AdminReportListPublic,
    AdminReportPatch,
    AttachmentUploadPublic,
    BlockUserBody,
    CreateThreadBody,
    DeleteMessageBody,
    EditMessageBody,
    MessagePublic,
    MessageSettingsPublic,
    MessageSettingsUpdate,
    NotificationListPublic,
    PinnedListPublic,
    ReportThreadBody,
    SendMessageBody,
    StarredListPublic,
    ThreadDetailPublic,
    ThreadListPublic,
    ThreadSearchPublic,
    UnreadCountPublic,
)
from app.messaging.models import Message
from app.users.models import User

router = APIRouter(tags=["messaging"])


@router.get("/messages/unread-count", response_model=UnreadCountPublic)
def unread_count(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> UnreadCountPublic:
    return UnreadCountPublic(unread_count=svc.unread_count_for_user(db, user))


@router.get("/messages/settings", response_model=MessageSettingsPublic)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageSettingsPublic:
    return MessageSettingsPublic.model_validate(svc.get_settings_payload(db, user))


@router.patch("/messages/settings", response_model=MessageSettingsPublic)
def patch_settings(
    payload: MessageSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageSettingsPublic:
    svc.update_settings(db, user, payload)
    return MessageSettingsPublic.model_validate(svc.get_settings_payload(db, user))


@router.get("/messages/notifications", response_model=NotificationListPublic)
def notifications(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> NotificationListPublic:
    return NotificationListPublic.model_validate(svc.list_notifications(db, user))


@router.get("/messages/attachments/{attachment_id}")
def download_attachment(
    attachment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    d: str | None = Query(
        default=None,
        description="Short-lived signed download token (optional if Bearer auth).",
    ),
) -> RawResponse:
    """Private attachment download — auth + thread access + ready status required."""
    row, viewer = svc.get_attachment_for_download(
        db,
        attachment_id=attachment_id,
        user=user,
        download_token=d,
    )
    from app.messaging.attachments import content_disposition_for

    data = svc.stream_attachment_bytes(row)
    # Best-effort audit (do not fail the download).
    try:
        svc.record_attachment_download(db, viewer, row.id)
    except Exception:
        pass
    filename = row.original_filename or row.safe_filename or "attachment"
    return RawResponse(
        content=data,
        media_type=row.mime_type or "application/octet-stream",
        headers={
            # Images: inline preview. PDF/docs: attachment (no unsafe inline render).
            "Content-Disposition": content_disposition_for(row.mime_type, filename),
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.post(
    "/messages/threads/{thread_id}/attachments",
    response_model=AttachmentUploadPublic,
    status_code=201,
)
def upload_thread_attachment(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
) -> AttachmentUploadPublic:
    """Stage a file on a thread (REST only). Does not create a chat message."""
    row = svc.upload_message_attachment(db, user, file, thread_id=thread_id)
    return AttachmentUploadPublic.model_validate(svc.serialize_attachment_upload(row))


@router.post("/messages/attachments", response_model=AttachmentUploadPublic, status_code=201)
def upload_attachment_legacy(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
    thread_id: Annotated[UUID, Form(...)],
) -> AttachmentUploadPublic:
    """Deprecated: prefer POST /messages/threads/{thread_id}/attachments."""
    row = svc.upload_message_attachment(db, user, file, thread_id=thread_id)
    return AttachmentUploadPublic.model_validate(svc.serialize_attachment_upload(row))


@router.get("/messages", response_model=ThreadListPublic)
def list_messages(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filter: str = Query(default="all", alias="filter"),
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=50),
) -> ThreadListPublic:
    return ThreadListPublic.model_validate(
        svc.list_threads_for_fan(
            db, user, filter_key=filter, q=q, page=page, limit=limit
        )
    )


@router.get("/messages/starred", response_model=StarredListPublic)
def list_starred(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=50),
) -> StarredListPublic:
    return StarredListPublic.model_validate(
        chat_actions.list_starred_for_user(db, user, page=page, limit=limit)
    )


@router.post("/messages/threads", response_model=ThreadDetailPublic)
def create_thread(
    payload: CreateThreadBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    thread = svc.create_thread_as_fan(
        db,
        user,
        host_id=payload.host_id,
        host_username=payload.host_username,
        related_event_id=payload.related_event_id,
        related_merch_order_item_id=payload.related_merch_order_item_id,
        subject=payload.subject,
        body=payload.body,
    )
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread.id)
    )


@router.get(
    "/messages/threads/{thread_id}/pins",
    response_model=PinnedListPublic,
)
def list_thread_pins(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PinnedListPublic:
    return PinnedListPublic.model_validate(
        chat_actions.list_pins_payload(db, user, thread_id)
    )


@router.get(
    "/messages/threads/{thread_id}/search",
    response_model=ThreadSearchPublic,
)
def search_thread_messages(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    q: str | None = Query(default=None, max_length=120),
    starred: bool = Query(default=False),
    pinned: bool = Query(default=False),
    has_attachments: bool = Query(default=False),
    limit: int = Query(default=40, ge=1, le=50),
) -> ThreadSearchPublic:
    """Simple in-thread body search + star/pin/attachment filters (no FTS index)."""
    return ThreadSearchPublic.model_validate(
        chat_actions.search_thread_messages(
            db,
            user,
            thread_id,
            q=q,
            starred=starred,
            pinned=pinned,
            has_attachments=has_attachments,
            limit=limit,
        )
    )


@router.get("/messages/{thread_id}", response_model=ThreadDetailPublic)
def get_thread(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.post("/messages/{thread_id}/send", response_model=MessagePublic)
def send_message(
    thread_id: UUID,
    payload: SendMessageBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    msg = svc.send_in_thread(
        db,
        user,
        thread_id,
        payload.body,
        attachment_ids=payload.attachment_ids,
        reply_to_message_id=payload.reply_to_message_id,
    )
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.patch("/messages/{message_id}", response_model=MessagePublic)
def edit_message(
    message_id: UUID,
    payload: EditMessageBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Edit own message body (24h window). Not an admin moderation path."""
    msg = chat_actions.edit_message(db, user, message_id, payload.body)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.patch(
    "/messages/{thread_id}/messages/{message_id}",
    response_model=MessagePublic,
    deprecated=True,
)
def edit_message_nested(
    thread_id: UUID,
    message_id: UUID,
    payload: EditMessageBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Deprecated: prefer PATCH /messages/{message_id}."""
    msg = chat_actions.edit_message(
        db, user, message_id, payload.body, thread_id=thread_id
    )
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post("/messages/{message_id}/pin", response_model=PinnedListPublic)
def pin_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PinnedListPublic:
    pinned = chat_actions.pin_message(db, user, message_id)
    msg = db.get(Message, message_id)
    assert msg is not None
    return PinnedListPublic.model_validate(
        chat_actions.list_pins_payload(db, user, msg.thread_id)
    )


@router.post("/messages/{message_id}/unpin", response_model=PinnedListPublic)
def unpin_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PinnedListPublic:
    chat_actions.unpin_message(db, user, message_id)
    msg = db.get(Message, message_id)
    assert msg is not None
    return PinnedListPublic.model_validate(
        chat_actions.list_pins_payload(db, user, msg.thread_id)
    )


@router.post(
    "/messages/{thread_id}/messages/{message_id}/pin",
    response_model=ThreadDetailPublic,
    deprecated=True,
)
def pin_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    """Deprecated: prefer POST /messages/{message_id}/pin."""
    chat_actions.pin_message(db, user, message_id, thread_id=thread_id)
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.delete(
    "/messages/{thread_id}/messages/{message_id}/pin",
    response_model=ThreadDetailPublic,
    deprecated=True,
)
def unpin_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    """Deprecated: prefer POST /messages/{message_id}/unpin."""
    chat_actions.unpin_message(db, user, message_id, thread_id=thread_id)
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.post("/messages/{message_id}/delete", response_model=MessagePublic)
def delete_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    payload: DeleteMessageBody = DeleteMessageBody(),
) -> MessagePublic:
    """Soft delete for the current user only (`for_me`). Peer still sees the message."""
    from fastapi import HTTPException

    from app.messaging import constants as msg_c

    if payload.scope != msg_c.DELETE_SCOPE_FOR_ME:
        raise HTTPException(
            status_code=400,
            detail="Only delete for me is supported.",
        )
    msg = chat_actions.delete_message_for_me(db, user, message_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post("/messages/{message_id}/star", response_model=MessagePublic)
def star_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    msg = chat_actions.star_message(db, user, message_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post("/messages/{message_id}/unstar", response_model=MessagePublic)
def unstar_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    msg = chat_actions.unstar_message(db, user, message_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post(
    "/messages/{thread_id}/messages/{message_id}/star",
    response_model=MessagePublic,
    deprecated=True,
)
def star_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Deprecated: prefer POST /messages/{message_id}/star."""
    msg = chat_actions.star_message(db, user, message_id, thread_id=thread_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.delete(
    "/messages/{thread_id}/messages/{message_id}/star",
    response_model=MessagePublic,
    deprecated=True,
)
def unstar_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Deprecated: prefer POST /messages/{message_id}/unstar."""
    msg = chat_actions.unstar_message(db, user, message_id, thread_id=thread_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.patch("/messages/{thread_id}/read", response_model=UnreadCountPublic)
def read_thread(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> UnreadCountPublic:
    svc.mark_read(db, user, thread_id)
    return UnreadCountPublic(unread_count=svc.unread_count_for_user(db, user))


@router.patch("/messages/{thread_id}/archive", response_model=ThreadDetailPublic)
def archive_thread(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    svc.archive_thread(db, user, thread_id)
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.post("/messages/{thread_id}/accept", response_model=ThreadDetailPublic)
def accept_request(
    thread_id: UUID,
    payload: AcceptRequestBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    if payload.accept:
        svc.accept_request(db, user, thread_id)
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.post("/messages/{thread_id}/report", status_code=201)
def report_thread(
    thread_id: UUID,
    payload: ReportThreadBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    report = svc.report_thread(
        db,
        user,
        thread_id,
        reason=payload.reason,
        details=payload.details,
        message_id=payload.message_id,
    )
    return {"id": str(report.id), "status": report.status}


@router.post("/messages/block", status_code=204, response_class=Response)
def block_user(
    payload: BlockUserBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    svc.block_user(
        db,
        user,
        blocked_user_id=payload.blocked_user_id,
        reason=payload.reason,
    )
    return Response(status_code=204)


@router.delete("/messages/block/{blocked_user_id}", status_code=204, response_class=Response)
def unblock_user(
    blocked_user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    svc.unblock_user(db, user, blocked_user_id)
    return Response(status_code=204)


# --- Host ---


@router.post(
    "/host/messages/threads/{thread_id}/attachments",
    response_model=AttachmentUploadPublic,
    status_code=201,
)
def host_upload_thread_attachment(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
) -> AttachmentUploadPublic:
    """Stage a file on a thread (REST only). Does not create a chat message."""
    from app.hosts.team_access import require_host_for_permission

    require_host_for_permission(
        db, user=user, host_id=None, permission="messages.reply"
    )
    row = svc.upload_message_attachment(db, user, file, thread_id=thread_id)
    return AttachmentUploadPublic.model_validate(svc.serialize_attachment_upload(row))


@router.post(
    "/host/messages/attachments",
    response_model=AttachmentUploadPublic,
    status_code=201,
)
def host_upload_attachment_legacy(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
    thread_id: Annotated[UUID, Form(...)],
) -> AttachmentUploadPublic:
    """Deprecated: prefer POST /host/messages/threads/{thread_id}/attachments."""
    from app.hosts.team_access import require_host_for_permission

    require_host_for_permission(
        db, user=user, host_id=None, permission="messages.reply"
    )
    row = svc.upload_message_attachment(db, user, file, thread_id=thread_id)
    return AttachmentUploadPublic.model_validate(svc.serialize_attachment_upload(row))


@router.get("/host/messages", response_model=ThreadListPublic)
def host_list(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filter: str = Query(default="all", alias="filter"),
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=50),
) -> ThreadListPublic:
    return ThreadListPublic.model_validate(
        svc.list_threads_for_host(
            db, user, filter_key=filter, q=q, page=page, limit=limit
        )
    )


@router.get("/host/messages/starred", response_model=StarredListPublic)
def host_list_starred(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=50),
) -> StarredListPublic:
    from app.hosts.service import require_user_host

    require_user_host(db, user)
    return StarredListPublic.model_validate(
        chat_actions.list_starred_for_user(db, user, page=page, limit=limit)
    )


@router.get("/host/messages/can-message/{fan_user_id}")
def host_can_message(
    fan_user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return {"allowed": svc.host_can_message_fan(db, user, fan_user_id)}


@router.get("/host/messages/can-message-by-username/{username}")
def host_can_message_username(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return {"allowed": svc.host_can_message_fan_username(db, user, username)}


@router.post("/host/messages/threads", response_model=ThreadDetailPublic)
def host_create(
    payload: CreateThreadBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    thread = svc.create_thread_as_host(
        db,
        user,
        fan_user_id=payload.fan_user_id,
        fan_username=payload.fan_username,
        related_event_id=payload.related_event_id,
        related_merch_order_item_id=payload.related_merch_order_item_id,
        subject=payload.subject,
        body=payload.body,
    )
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread.id)
    )


@router.get(
    "/host/messages/threads/{thread_id}/search",
    response_model=ThreadSearchPublic,
)
def host_search_thread_messages(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    q: str | None = Query(default=None, max_length=120),
    starred: bool = Query(default=False),
    pinned: bool = Query(default=False),
    has_attachments: bool = Query(default=False),
    limit: int = Query(default=40, ge=1, le=50),
) -> ThreadSearchPublic:
    return ThreadSearchPublic.model_validate(
        chat_actions.search_thread_messages(
            db,
            user,
            thread_id,
            q=q,
            starred=starred,
            pinned=pinned,
            has_attachments=has_attachments,
            limit=limit,
        )
    )


@router.get(
    "/host/messages/threads/{thread_id}/pins",
    response_model=PinnedListPublic,
)
def host_list_thread_pins(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PinnedListPublic:
    return PinnedListPublic.model_validate(
        chat_actions.list_pins_payload(db, user, thread_id)
    )


@router.get("/host/messages/{thread_id}", response_model=ThreadDetailPublic)
def host_get(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.post("/host/messages/{thread_id}/send", response_model=MessagePublic)
def host_send(
    thread_id: UUID,
    payload: SendMessageBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    msg = svc.send_in_thread(
        db,
        user,
        thread_id,
        payload.body,
        attachment_ids=payload.attachment_ids,
        reply_to_message_id=payload.reply_to_message_id,
    )
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.patch("/host/messages/{message_id}", response_model=MessagePublic)
def host_edit_message(
    message_id: UUID,
    payload: EditMessageBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Edit own message body (24h window). Not an admin moderation path."""
    msg = chat_actions.edit_message(db, user, message_id, payload.body)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.patch(
    "/host/messages/{thread_id}/messages/{message_id}",
    response_model=MessagePublic,
    deprecated=True,
)
def host_edit_message_nested(
    thread_id: UUID,
    message_id: UUID,
    payload: EditMessageBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Deprecated: prefer PATCH /host/messages/{message_id}."""
    msg = chat_actions.edit_message(
        db, user, message_id, payload.body, thread_id=thread_id
    )
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post("/host/messages/{message_id}/pin", response_model=PinnedListPublic)
def host_pin_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PinnedListPublic:
    chat_actions.pin_message(db, user, message_id)
    msg = db.get(Message, message_id)
    assert msg is not None
    return PinnedListPublic.model_validate(
        chat_actions.list_pins_payload(db, user, msg.thread_id)
    )


@router.post("/host/messages/{message_id}/unpin", response_model=PinnedListPublic)
def host_unpin_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PinnedListPublic:
    chat_actions.unpin_message(db, user, message_id)
    msg = db.get(Message, message_id)
    assert msg is not None
    return PinnedListPublic.model_validate(
        chat_actions.list_pins_payload(db, user, msg.thread_id)
    )


@router.post(
    "/host/messages/{thread_id}/messages/{message_id}/pin",
    response_model=ThreadDetailPublic,
    deprecated=True,
)
def host_pin_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    chat_actions.pin_message(db, user, message_id, thread_id=thread_id)
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.delete(
    "/host/messages/{thread_id}/messages/{message_id}/pin",
    response_model=ThreadDetailPublic,
    deprecated=True,
)
def host_unpin_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    chat_actions.unpin_message(db, user, message_id, thread_id=thread_id)
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.post("/host/messages/{message_id}/delete", response_model=MessagePublic)
def host_delete_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    payload: DeleteMessageBody = DeleteMessageBody(),
) -> MessagePublic:
    from fastapi import HTTPException

    from app.messaging import constants as msg_c

    if payload.scope != msg_c.DELETE_SCOPE_FOR_ME:
        raise HTTPException(
            status_code=400,
            detail="Only delete for me is supported.",
        )
    msg = chat_actions.delete_message_for_me(db, user, message_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post("/host/messages/{message_id}/star", response_model=MessagePublic)
def host_star_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    msg = chat_actions.star_message(db, user, message_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post("/host/messages/{message_id}/unstar", response_model=MessagePublic)
def host_unstar_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    msg = chat_actions.unstar_message(db, user, message_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.post(
    "/host/messages/{thread_id}/messages/{message_id}/star",
    response_model=MessagePublic,
    deprecated=True,
)
def host_star_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Deprecated: prefer POST /host/messages/{message_id}/star."""
    msg = chat_actions.star_message(db, user, message_id, thread_id=thread_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.delete(
    "/host/messages/{thread_id}/messages/{message_id}/star",
    response_model=MessagePublic,
    deprecated=True,
)
def host_unstar_message_nested(
    thread_id: UUID,
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessagePublic:
    """Deprecated: prefer POST /host/messages/{message_id}/unstar."""
    msg = chat_actions.unstar_message(db, user, message_id, thread_id=thread_id)
    return MessagePublic.model_validate(
        svc.serialize_message(db, msg, viewer_id=user.id)
    )


@router.patch("/host/messages/{thread_id}/read", response_model=UnreadCountPublic)
def host_read(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> UnreadCountPublic:
    svc.mark_read(db, user, thread_id)
    return UnreadCountPublic(unread_count=svc.unread_count_for_user(db, user))


@router.patch("/host/messages/{thread_id}/archive", response_model=ThreadDetailPublic)
def host_archive(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ThreadDetailPublic:
    svc.archive_thread(db, user, thread_id)
    return ThreadDetailPublic.model_validate(
        svc.get_thread_detail(db, user, thread_id)
    )


@router.post("/host/messages/{thread_id}/report", status_code=201)
def host_report(
    thread_id: UUID,
    payload: ReportThreadBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    report = svc.report_thread(
        db,
        user,
        thread_id,
        reason=payload.reason,
        details=payload.details,
        message_id=payload.message_id,
    )
    return {"id": str(report.id), "status": report.status}


@router.post("/host/messages/block", status_code=204, response_class=Response)
def host_block(
    payload: BlockUserBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    from app.hosts.service import require_user_host

    h = require_user_host(db, user)
    svc.block_user(
        db,
        user,
        blocked_user_id=payload.blocked_user_id,
        reason=payload.reason,
        host_id=h.id,
    )
    return Response(status_code=204)


@router.delete(
    "/host/messages/block/{blocked_user_id}",
    status_code=204,
    response_class=Response,
)
def host_unblock(
    blocked_user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    from app.hosts.service import require_user_host

    require_user_host(db, user)
    svc.unblock_user(db, user, blocked_user_id)
    return Response(status_code=204)


# --- Admin ---


@router.get(
    "/admin/message-reports",
    response_model=AdminReportListPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_reports(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=40, ge=1, le=100),
) -> AdminReportListPublic:
    return AdminReportListPublic.model_validate(
        svc.list_reports(db, status_filter=status, page=page, limit=limit)
    )


@router.get(
    "/admin/message-reports/{report_id}",
    response_model=AdminReportDetailPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_report_detail(
    report_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminReportDetailPublic:
    return AdminReportDetailPublic.model_validate(
        svc.get_report_detail(db, report_id, admin=admin)
    )


@router.patch(
    "/admin/message-reports/{report_id}",
    response_model=AdminReportDetailPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_report_patch(
    report_id: UUID,
    payload: AdminReportPatch,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminReportDetailPublic:
    svc.patch_report(
        db, admin, report_id, status_value=payload.status, notes=payload.admin_notes
    )
    return AdminReportDetailPublic.model_validate(
        svc.get_report_detail(db, report_id, admin=admin)
    )


@router.patch(
    "/admin/messages/{message_id}/hide",
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_hide_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    msg = svc.hide_message(db, admin, message_id)
    return {"id": str(msg.id), "status": msg.status}


@router.patch(
    "/admin/messages/{message_id}/restore",
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_restore_message(
    message_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    msg = svc.restore_message(db, admin, message_id)
    return {"id": str(msg.id), "status": msg.status}


@router.patch(
    "/admin/messages/attachments/{attachment_id}/hide",
    response_model=AttachmentUploadPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_hide_attachment(
    attachment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AttachmentUploadPublic:
    row = svc.hide_attachment(db, admin, attachment_id)
    return AttachmentUploadPublic.model_validate(
        svc.serialize_attachment_admin(row, admin_id=admin.id)
    )


@router.patch(
    "/admin/messages/attachments/{attachment_id}/restore",
    response_model=AttachmentUploadPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_restore_attachment(
    attachment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AttachmentUploadPublic:
    row = svc.restore_attachment(db, admin, attachment_id)
    return AttachmentUploadPublic.model_validate(
        svc.serialize_attachment_admin(row, admin_id=admin.id)
    )


@router.patch(
    "/admin/messages/attachments/{attachment_id}/delete",
    response_model=AttachmentUploadPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_soft_delete_attachment(
    attachment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AttachmentUploadPublic:
    """Soft-disable access — does not permanently remove stored bytes."""
    row = svc.soft_delete_attachment(db, admin, attachment_id)
    return AttachmentUploadPublic.model_validate(
        svc.serialize_attachment_admin(row, admin_id=admin.id)
    )


@router.patch(
    "/admin/messages/attachments/{attachment_id}/review",
    response_model=AttachmentUploadPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_review_attachment(
    attachment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AttachmentUploadPublic:
    row = svc.review_attachment(db, admin, attachment_id)
    return AttachmentUploadPublic.model_validate(
        svc.serialize_attachment_admin(row, admin_id=admin.id)
    )
