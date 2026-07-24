"""Admin notification system APIs."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.admin_notifications.audience import search_users_for_campaign
from app.admin_notifications.campaigns import (
    cancel_campaign,
    create_campaign,
    get_campaign,
    list_campaign_deliveries,
    list_campaigns,
    preview_recipients,
    send_custom_admin_notification,
    test_campaign_to_self,
)
from app.admin_notifications.schemas import (
    AudiencePreviewRequest,
    CampaignCreate,
    NotificationSettingUpdate,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
)
from app.admin_notifications.settings_service import (
    create_template,
    ensure_default_settings,
    list_settings,
    list_templates,
    update_setting,
    update_template,
)
from app.auth.dependencies import get_current_user, get_db, require_permission
from app.users.models import User
from app.users.service import user_has_permission

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


def _is_super(user: User) -> bool:
    return user_has_permission(user, "admin.full_access")


@router.get("/settings")
def admin_list_notification_settings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.notifications.view", "admin.full_access"))
    ],
) -> list[dict[str, Any]]:
    del user
    ensure_default_settings(db)
    db.commit()
    return list_settings(db)


@router.put("/settings/{type_key}")
def admin_update_notification_setting(
    type_key: str,
    payload: NotificationSettingUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.notifications.manage_settings", "admin.full_access"
            )
        ),
    ],
) -> dict[str, Any]:
    try:
        data = payload.model_dump(exclude_unset=True)
        if "channels" in data and data["channels"] is not None:
            data["channels"] = payload.channels.model_dump(exclude_unset=True)  # type: ignore[union-attr]
        result = update_setting(
            db,
            type_key=type_key,
            updates=data,
            actor_user_id=user.id,
            actor_is_super_admin=_is_super(user),
        )
        db.commit()
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/templates")
def admin_list_templates(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.notifications.view", "admin.full_access"))
    ],
) -> list[dict[str, Any]]:
    del user
    ensure_default_settings(db)
    db.commit()
    return list_templates(db)


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def admin_create_template(
    payload: NotificationTemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.notifications.manage_settings", "admin.full_access"
            )
        ),
    ],
) -> dict[str, Any]:
    row = create_template(
        db, payload=payload.model_dump(), actor_user_id=user.id
    )
    db.commit()
    return row


@router.patch("/templates/{template_id}")
def admin_update_template(
    template_id: UUID,
    payload: NotificationTemplateUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.notifications.manage_settings", "admin.full_access"
            )
        ),
    ],
) -> dict[str, Any]:
    try:
        row = update_template(
            db,
            template_id=template_id,
            payload=payload.model_dump(exclude_unset=True),
            actor_user_id=user.id,
        )
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/campaigns")
def admin_list_campaigns(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.notifications.view", "admin.full_access"))
    ],
) -> list[dict[str, Any]]:
    del user
    return list_campaigns(db)


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
def admin_create_campaign(
    payload: CampaignCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.notifications.send_custom", "admin.full_access")
        ),
    ],
) -> dict[str, Any]:
    try:
        data = payload.model_dump()
        if payload.channels is not None:
            data["channels"] = payload.channels.model_dump(exclude_unset=True)
        if payload.user_ids:
            data["user_ids"] = [str(u) for u in payload.user_ids]
        row = create_campaign(db, payload=data, actor_user_id=user.id)
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}")
def admin_get_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.notifications.view", "admin.full_access"))
    ],
) -> dict[str, Any]:
    del user
    from app.admin_notifications.campaigns import serialize_campaign

    row = get_campaign(db, campaign_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return serialize_campaign(row)


@router.post("/campaigns/{campaign_id}/send")
def admin_send_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.notifications.send_custom", "admin.full_access")
        ),
    ],
) -> dict[str, Any]:
    try:
        result = send_custom_admin_notification(
            db, campaign_id=campaign_id, actor_user_id=user.id
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/test")
def admin_test_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.notifications.send_custom", "admin.full_access")
        ),
    ],
) -> dict[str, Any]:
    try:
        result = test_campaign_to_self(
            db, campaign_id=campaign_id, actor_user_id=user.id
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/cancel")
def admin_cancel_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.notifications.send_custom", "admin.full_access")
        ),
    ],
) -> dict[str, Any]:
    try:
        result = cancel_campaign(
            db, campaign_id=campaign_id, actor_user_id=user.id
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}/deliveries")
def admin_campaign_deliveries(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.notifications.view_delivery_logs", "admin.full_access"
            )
        ),
    ],
) -> list[dict[str, Any]]:
    del user
    return list_campaign_deliveries(db, campaign_id=campaign_id)


@router.post("/audience/preview")
def admin_preview_audience(
    payload: AudiencePreviewRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.notifications.send_custom", "admin.full_access")
        ),
    ],
) -> dict[str, Any]:
    del user
    return preview_recipients(
        db,
        audience_mode=payload.audience_mode,
        audience_filters=payload.audience_filters,
        user_ids=[str(u) for u in (payload.user_ids or [])],
    )


@router.get("/users/search")
def admin_search_notification_users(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.notifications.send_custom", "admin.full_access")
        ),
    ],
    q: str | None = Query(default=None),
    role: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[dict[str, Any]]:
    del user
    return search_users_for_campaign(db, q=q, role=role, limit=limit)
