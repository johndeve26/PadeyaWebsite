"""Email preferences, unsubscribe, and admin email event APIs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.core.config import get_settings
from app.core.database import get_db
from app.email.models import EmailEvent
from app.email.prefs import (
    get_or_create_preferences,
    serialize_prefs,
    unsubscribe_marketing,
    update_preferences,
)
from app.email.queue import process_pending_emails, resend_email_event
from app.email.schemas import (
    EmailEventListResponse,
    EmailEventPublic,
    EmailPreferencesPublic,
    EmailPreferencesUpdate,
    EmailProviderSettingsPublic,
    EmailProviderSettingsUpdate,
    EmailSettingsActivateRequest,
    EmailSettingsTestResponse,
    EmailSettingsTestSendRequest,
    ResendResponse,
    UnsubscribeRequest,
)
from app.email.service import send_template
from app.email.settings_service import (
    activate_provider_settings,
    disable_email_sending,
    get_or_create_active_settings,
    outbox_counts,
    send_test_email,
    serialize_provider_settings,
    test_smtp_connection,
    update_provider_settings,
)
from app.email.tokens import make_prefs_token, parse_prefs_token
from app.users.models import User

router = APIRouter(tags=["email"])


@router.get("/email/health")
async def email_module_health() -> dict[str, str]:
    return {"module": "email", "status": "ok"}


@router.get(
    "/email/preferences",
    response_model=EmailPreferencesPublic,
)
def get_my_email_preferences(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EmailPreferencesPublic:
    prefs = get_or_create_preferences(db, user.id)
    db.commit()
    return EmailPreferencesPublic.model_validate(serialize_prefs(prefs))


@router.patch(
    "/email/preferences",
    response_model=EmailPreferencesPublic,
)
def patch_my_email_preferences(
    payload: EmailPreferencesUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EmailPreferencesPublic:
    data = payload.model_dump(exclude_unset=True)
    prefs = update_preferences(db, user_id=user.id, updates=data)
    send_template(
        db,
        template="email_preferences_updated",
        to=user.email,
        recipient_user_id=user.id,
        context={"full_name": user.full_name},
        dedupe_key=None,
        deliver_now=True,
    )
    db.commit()
    return EmailPreferencesPublic.model_validate(serialize_prefs(prefs))


@router.get("/email/preferences/token")
def get_prefs_token(user: CurrentUser) -> dict[str, str]:
    return {
        "token": make_prefs_token(user.id, purpose="preferences"),
        "unsubscribe_token": make_prefs_token(user.id, purpose="unsubscribe"),
    }


@router.post("/email/unsubscribe", response_model=EmailPreferencesPublic)
def unsubscribe_via_token(
    payload: UnsubscribeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> EmailPreferencesPublic:
    try:
        user_id = parse_prefs_token(payload.token, purpose="unsubscribe")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.marketing_only:
        prefs = unsubscribe_marketing(db, user_id=user_id)
    else:
        prefs = update_preferences(
            db,
            user_id=user_id,
            updates={
                "email_marketing": False,
                "email_messages": False,
                "email_fan_connect": False,
            },
        )
    db.commit()
    return EmailPreferencesPublic.model_validate(serialize_prefs(prefs))


@router.get(
    "/email/preferences/by-token",
    response_model=EmailPreferencesPublic,
)
def get_prefs_by_token(
    db: Annotated[Session, Depends(get_db)],
    token: str = Query(...),
) -> EmailPreferencesPublic:
    try:
        user_id = parse_prefs_token(token, purpose="preferences")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prefs = get_or_create_preferences(db, user_id)
    db.commit()
    return EmailPreferencesPublic.model_validate(serialize_prefs(prefs))


@router.patch(
    "/email/preferences/by-token",
    response_model=EmailPreferencesPublic,
)
def patch_prefs_by_token(
    payload: EmailPreferencesUpdate,
    db: Annotated[Session, Depends(get_db)],
    token: str = Query(...),
) -> EmailPreferencesPublic:
    try:
        user_id = parse_prefs_token(token, purpose="preferences")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prefs = update_preferences(
        db, user_id=user_id, updates=payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return EmailPreferencesPublic.model_validate(serialize_prefs(prefs))


def _serialize_event(row: EmailEvent, *, include_body: bool) -> EmailEventPublic:
    data = {
        "id": row.id,
        "template": row.template,
        "recipient_email": row.recipient_email,
        "recipient_user_id": row.recipient_user_id,
        "subject": row.subject,
        "status": row.status,
        "provider": row.provider,
        "provider_message_id": row.provider_message_id,
        "error_message": row.error_message,
        "attempts": row.attempts,
        "last_attempt_at": row.last_attempt_at,
        "sent_at": row.sent_at,
        "dedupe_key": row.dedupe_key,
        "preference_key": row.preference_key,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "body_text": row.body_text if include_body else None,
        "body_html": row.body_html if include_body else None,
    }
    return EmailEventPublic.model_validate(data)


def _settings_public(db: Session, row) -> EmailProviderSettingsPublic:
    pending, failed = outbox_counts(db)
    return EmailProviderSettingsPublic.model_validate(
        serialize_provider_settings(row, pending_count=pending, failed_count=failed)
    )


@router.get("/admin/email/settings", response_model=EmailProviderSettingsPublic)
@router.get("/admin/emails/settings", response_model=EmailProviderSettingsPublic, include_in_schema=False)
def admin_get_email_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailProviderSettingsPublic:
    row = get_or_create_active_settings(db)
    db.commit()
    return _settings_public(db, row)


@router.patch("/admin/email/settings", response_model=EmailProviderSettingsPublic)
@router.patch("/admin/emails/settings", response_model=EmailProviderSettingsPublic, include_in_schema=False)
def admin_patch_email_settings(
    payload: EmailProviderSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailProviderSettingsPublic:
    updates = payload.model_dump(exclude_unset=True)
    try:
        row = update_provider_settings(
            db, updates=updates, actor_user_id=admin.id, commit=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _settings_public(db, row)


@router.post("/admin/email/settings/test", response_model=EmailSettingsTestResponse)
def admin_test_email_settings(
    payload: EmailSettingsTestSendRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailSettingsTestResponse:
    recipient = payload.test_recipient_email or payload.to
    if not recipient:
        # Connection-only test when no recipient
        result = test_smtp_connection(db, actor_user_id=admin.id)
        return EmailSettingsTestResponse.model_validate(result)
    try:
        result = send_test_email(db, to=recipient, actor_user_id=admin.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EmailSettingsTestResponse.model_validate(result)


@router.post(
    "/admin/emails/settings/test-connection",
    response_model=EmailSettingsTestResponse,
    include_in_schema=False,
)
def admin_test_email_connection_legacy(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailSettingsTestResponse:
    result = test_smtp_connection(db, actor_user_id=admin.id)
    return EmailSettingsTestResponse.model_validate(result)


@router.post(
    "/admin/emails/settings/test-send",
    response_model=EmailSettingsTestResponse,
    include_in_schema=False,
)
def admin_test_email_send_legacy(
    payload: EmailSettingsTestSendRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailSettingsTestResponse:
    recipient = payload.test_recipient_email or payload.to
    if not recipient:
        raise HTTPException(status_code=400, detail="test_recipient_email is required")
    try:
        result = send_test_email(db, to=recipient, actor_user_id=admin.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EmailSettingsTestResponse.model_validate(result)


@router.post("/admin/email/settings/activate", response_model=EmailProviderSettingsPublic)
def admin_activate_email_settings(
    payload: EmailSettingsActivateRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailProviderSettingsPublic:
    try:
        row = activate_provider_settings(
            db, settings_id=payload.settings_id, actor_user_id=admin.id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _settings_public(db, row)


@router.post("/admin/email/settings/disable", response_model=EmailProviderSettingsPublic)
def admin_disable_email_settings(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailProviderSettingsPublic:
    row = disable_email_sending(db, actor_user_id=admin.id)
    return _settings_public(db, row)


@router.post("/admin/emails/process-pending")
def admin_process_pending(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, int]:
    processed = process_pending_emails(db, limit=limit)
    return {"processed": processed}


@router.get("/admin/emails", response_model=EmailEventListResponse)
def admin_list_emails(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status_filter: str | None = Query(default=None, alias="status"),
    template: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EmailEventListResponse:
    stmt = select(EmailEvent)
    count_stmt = select(func.count()).select_from(EmailEvent)
    if status_filter:
        stmt = stmt.where(EmailEvent.status == status_filter)
        count_stmt = count_stmt.where(EmailEvent.status == status_filter)
    if template:
        stmt = stmt.where(EmailEvent.template == template)
        count_stmt = count_stmt.where(EmailEvent.template == template)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(EmailEvent.created_at.desc()).offset(offset).limit(limit)
        )
    )
    settings = get_settings()
    include_body = settings.app_env in {"development", "dev", "local", "test"} or bool(
        settings.email_dev_mode
    )
    return EmailEventListResponse(
        items=[_serialize_event(r, include_body=include_body) for r in rows],
        total=total,
    )


@router.get("/admin/emails/{email_id}", response_model=EmailEventPublic)
def admin_get_email(
    email_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EmailEventPublic:
    row = db.get(EmailEvent, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Email event not found")
    settings = get_settings()
    include_body = settings.app_env in {"development", "dev", "local", "test"} or bool(
        settings.email_dev_mode
    )
    return _serialize_event(row, include_body=include_body)


@router.post("/admin/emails/{email_id}/resend", response_model=ResendResponse)
def admin_resend_email(
    email_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> ResendResponse:
    try:
        event = resend_email_event(db, event_id=email_id, actor_user_id=admin.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResendResponse(id=event.id, status=event.status)
