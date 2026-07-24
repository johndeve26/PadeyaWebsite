"""Admin editable platform email templates API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.email.admin_schemas import (
    AdminEmailNotificationSettingsPublic,
    AdminEmailNotificationSettingsUpdate,
    AdminEmailTemplateListResponse,
    AdminEmailTemplatePreviewRequest,
    AdminEmailTemplatePreviewResponse,
    AdminEmailTemplatePublic,
    AdminEmailTemplateTestSendResponse,
    AdminEmailTemplateUpdate,
)
from app.email.admin_template_service import (
    get_global_admin_email_settings,
    list_admin_templates,
    preview_admin_template,
    restore_admin_template_default,
    serialize_admin_template,
    test_send_admin_template,
    update_admin_template,
)
from app.users.models import User
from app.users.service import user_has_permission

router = APIRouter(prefix="/admin/emails", tags=["admin-emails"])


def _mask_recipients(user: User) -> bool:
    return not user_has_permission(user, "admin.emails.manage_recipients")


@router.get("/templates", response_model=AdminEmailTemplateListResponse)
def admin_list_email_templates(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.emails.view"))],
    category: str | None = Query(None),
    q: str | None = Query(None),
) -> AdminEmailTemplateListResponse:
    mask = _mask_recipients(admin)
    items = list_admin_templates(db, category=category, q=q, mask_recipient_emails=mask)
    db.commit()
    return AdminEmailTemplateListResponse(
        items=[AdminEmailTemplatePublic.model_validate(i) for i in items]
    )


@router.get("/templates/{template_key}", response_model=AdminEmailTemplatePublic)
def admin_get_email_template(
    template_key: str,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.emails.view"))],
) -> AdminEmailTemplatePublic:
    mask = _mask_recipients(admin)
    data = serialize_admin_template(
        db, template_key, include_bodies=True, mask_recipient_emails=mask
    )
    db.commit()
    return AdminEmailTemplatePublic.model_validate(data)


@router.patch("/templates/{template_key}", response_model=AdminEmailTemplatePublic)
def admin_patch_email_template(
    template_key: str,
    payload: AdminEmailTemplateUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.emails.edit_templates"))],
) -> AdminEmailTemplatePublic:
    data = update_admin_template(
        db,
        key=template_key,
        admin_id=admin.id,
        updates=payload.model_dump(exclude_unset=True),
        actor=admin,
    )
    db.commit()
    return AdminEmailTemplatePublic.model_validate(data)


@router.post("/templates/{template_key}/restore-default", response_model=AdminEmailTemplatePublic)
def admin_restore_email_template(
    template_key: str,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.emails.edit_templates"))],
) -> AdminEmailTemplatePublic:
    data = restore_admin_template_default(db, key=template_key, admin_id=admin.id)
    db.commit()
    return AdminEmailTemplatePublic.model_validate(data)


@router.post("/templates/{template_key}/preview", response_model=AdminEmailTemplatePreviewResponse)
def admin_preview_email_template(
    template_key: str,
    payload: AdminEmailTemplatePreviewRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.emails.view"))],
) -> AdminEmailTemplatePreviewResponse:
    result = preview_admin_template(db, template_key, payload.context)
    db.commit()
    return AdminEmailTemplatePreviewResponse.model_validate(result)


@router.post("/templates/{template_key}/test-send", response_model=AdminEmailTemplateTestSendResponse)
def admin_test_send_email_template(
    template_key: str,
    payload: AdminEmailTemplatePreviewRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.emails.test_send"))],
) -> AdminEmailTemplateTestSendResponse:
    count = test_send_admin_template(
        db,
        key=template_key,
        admin=admin,
        context=payload.context,
        test_recipient_emails=payload.test_recipient_emails,
    )
    db.commit()
    return AdminEmailTemplateTestSendResponse(recipient_count=count)


@router.get("/notification-settings", response_model=AdminEmailNotificationSettingsPublic)
@router.get("/settings/notifications", response_model=AdminEmailNotificationSettingsPublic, include_in_schema=False)
def admin_get_notification_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.notifications.manage_settings"))],
) -> AdminEmailNotificationSettingsPublic:
    row = get_global_admin_email_settings(db)
    db.commit()
    return AdminEmailNotificationSettingsPublic(
        master_enabled=row.master_enabled,
        digest_enabled=row.digest_enabled,
        digest_hour_utc=row.digest_hour_utc,
        updated_at=row.updated_at,
    )


@router.patch("/notification-settings", response_model=AdminEmailNotificationSettingsPublic)
@router.patch("/settings/notifications", response_model=AdminEmailNotificationSettingsPublic, include_in_schema=False)
def admin_patch_notification_settings(
    payload: AdminEmailNotificationSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.notifications.manage_settings"))],
) -> AdminEmailNotificationSettingsPublic:
    row = get_global_admin_email_settings(db)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_by_admin_id = admin.id
    write_audit_log(
        db,
        action="admin.emails.notification_settings_updated",
        actor_user_id=admin.id,
        resource_type="email_admin_notification_settings",
        resource_id=str(row.id),
    )
    db.commit()
    return AdminEmailNotificationSettingsPublic(
        master_enabled=row.master_enabled,
        digest_enabled=row.digest_enabled,
        digest_hour_utc=row.digest_hour_utc,
        updated_at=row.updated_at,
    )
