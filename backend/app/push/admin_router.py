"""Admin push settings, test send, outbox + delivery inspection."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.notifications.delivery_admin import (
    delivery_summary,
    list_deliveries,
    serialize_delivery,
)
from app.notifications.settings_service import (
    disable_push,
    get_or_create_active_push_settings,
    serialize_push_settings,
    update_push_settings,
)
from app.push.models import PushEvent
from app.push.schemas import (
    PushDeliveryEventPublic,
    PushDeliveryListResponse,
    PushEventListResponse,
    PushEventPublic,
    PushProviderSettingsPublic,
    PushProviderSettingsUpdate,
    PushTestByEmailRequest,
    PushTestRequest,
    PushUserSubscriptionStatus,
)
from app.push.service import (
    cleanup_failed_subscriptions,
    count_by_status,
    send_test_push,
    serialize_push_event,
    user_push_subscription_status,
)
from app.users.models import User

router = APIRouter(tags=["push-admin"])


@router.get("/admin/push/settings", response_model=PushProviderSettingsPublic)
def admin_get_push_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> PushProviderSettingsPublic:
    row = get_or_create_active_push_settings(db)
    db.commit()
    return PushProviderSettingsPublic.model_validate(serialize_push_settings(row))


@router.patch("/admin/push/settings", response_model=PushProviderSettingsPublic)
def admin_patch_push_settings(
    payload: PushProviderSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> PushProviderSettingsPublic:
    try:
        row = update_push_settings(
            db,
            updates=payload.model_dump(exclude_unset=True),
            actor_user_id=admin.id,
            commit=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PushProviderSettingsPublic.model_validate(serialize_push_settings(row))


@router.post("/admin/push/settings/disable", response_model=PushProviderSettingsPublic)
def admin_disable_push(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> PushProviderSettingsPublic:
    row = disable_push(db, actor_user_id=admin.id)
    return PushProviderSettingsPublic.model_validate(serialize_push_settings(row))


@router.get(
    "/admin/push/subscriptions/lookup",
    response_model=PushUserSubscriptionStatus,
)
def admin_lookup_push_subscriptions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    email: Annotated[str | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
) -> PushUserSubscriptionStatus:
    if not email and user_id is None:
        raise HTTPException(
            status_code=400, detail="Provide email or user_id to look up devices"
        )
    try:
        status = user_push_subscription_status(db, user_id=user_id, email=email)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PushUserSubscriptionStatus.model_validate(status)


@router.post("/admin/push/settings/test")
def admin_test_push(
    payload: PushTestRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    del payload  # Fixed copy server-side
    try:
        result = send_test_push(
            db,
            user_id=admin.id,
            actor_user_id=admin.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/admin/push/settings/test-user")
def admin_test_push_user(
    payload: PushTestByEmailRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    if not payload.email and payload.user_id is None:
        raise HTTPException(
            status_code=400, detail="Provide email or user_id for the test recipient"
        )
    try:
        result = send_test_push(
            db,
            user_id=payload.user_id,
            email=payload.email,
            actor_user_id=admin.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.get("/admin/push/deliveries", response_model=PushDeliveryListResponse)
def admin_list_push_deliveries(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PushDeliveryListResponse:
    rows, total = list_deliveries(db, status=status, limit=limit, offset=offset)
    summary = delivery_summary(db)
    return PushDeliveryListResponse(
        items=[
            PushDeliveryEventPublic.model_validate(serialize_delivery(r)) for r in rows
        ],
        total=total,
        summary=summary,
    )


@router.get("/admin/push/events", response_model=PushEventListResponse)
def admin_list_push_events(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PushEventListResponse:
    stmt = select(PushEvent)
    count_stmt = select(func.count()).select_from(PushEvent)
    if status:
        stmt = stmt.where(PushEvent.status == status.strip().lower())
        count_stmt = count_stmt.where(PushEvent.status == status.strip().lower())
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(PushEvent.created_at.desc()).offset(offset).limit(limit)
        )
    )
    summary = {
        "pending": count_by_status(db, "pending"),
        "sent": count_by_status(db, "sent"),
        "failed": count_by_status(db, "failed"),
        "skipped": count_by_status(db, "skipped"),
        "total": sum(
            count_by_status(db, s) for s in ("pending", "sent", "failed", "skipped")
        ),
    }
    return PushEventListResponse(
        items=[PushEventPublic.model_validate(serialize_push_event(r)) for r in rows],
        total=total,
        summary=summary,
    )


@router.post("/admin/push/cleanup-subscriptions")
def admin_cleanup_subscriptions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict[str, int]:
    n = cleanup_failed_subscriptions(db)
    db.commit()
    return {"deactivated": n}
