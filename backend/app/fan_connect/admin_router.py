"""Admin Fan Connect routes — /api/v1/admin/fan-connect/..."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.fan_connect import service as svc
from app.fan_connect.schemas import (
    AdminBlockListPublic,
    AdminDebugScorePublic,
    AdminDisableUserBody,
    AdminDisableUserPublic,
    AdminFanConnectSettingsPublic,
    AdminFanConnectSettingsUpdate,
    AdminOverviewPublic,
    AdminReportListPublic,
    AdminReportPublic,
    AdminResolveReportBody,
    AdminUserModerationHistoryPublic,
)
from app.users.models import User

router = APIRouter(prefix="/admin/fan-connect", tags=["fan-connect-admin"])


@router.get("/overview", response_model=AdminOverviewPublic)
def overview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminOverviewPublic:
    return AdminOverviewPublic.model_validate(svc.admin_overview(db))


@router.get("/blocks", response_model=AdminBlockListPublic)
def list_blocks(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> AdminBlockListPublic:
    return AdminBlockListPublic.model_validate(
        svc.admin_list_blocks(db, page=page, limit=limit)
    )


@router.get("/reports", response_model=AdminReportListPublic)
def list_reports(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> AdminReportListPublic:
    return AdminReportListPublic.model_validate(
        svc.admin_list_reports(
            db, page=page, limit=limit, status_filter=status_filter
        )
    )


@router.get("/reports/{report_id}", response_model=AdminReportPublic)
def get_report(
    report_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminReportPublic:
    return AdminReportPublic.model_validate(svc.admin_get_report(db, report_id))


@router.post("/reports/{report_id}/resolve", response_model=AdminReportPublic)
def resolve_report(
    report_id: UUID,
    payload: AdminResolveReportBody,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminReportPublic:
    row = svc.admin_resolve_report(
        db,
        user,
        report_id,
        resolution=payload.resolution,
        admin_notes=payload.admin_notes,
    )
    return AdminReportPublic.model_validate(svc.serialize_admin_report(db, row))


@router.get(
    "/users/{user_id}/moderation",
    response_model=AdminUserModerationHistoryPublic,
)
def user_moderation_history(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminUserModerationHistoryPublic:
    return AdminUserModerationHistoryPublic.model_validate(
        svc.admin_user_moderation_history(db, user_id)
    )


@router.post("/users/{user_id}/disable", response_model=AdminDisableUserPublic)
def disable_user(
    user_id: UUID,
    payload: AdminDisableUserBody,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminDisableUserPublic:
    return AdminDisableUserPublic.model_validate(
        svc.admin_disable_user(db, user, user_id, reason=payload.reason)
    )


@router.get("/debug/score", response_model=AdminDebugScorePublic)
def debug_score(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    actor: UUID = Query(..., description="Actor user id"),
    target: UUID = Query(..., description="Target user id"),
) -> AdminDebugScorePublic:
    """Admin score breakdown — bands/keys only; no raw user GPS."""
    return AdminDebugScorePublic.model_validate(
        svc.debug_score(db, actor_user_id=actor, target_user_id=target)
    )


@router.get("/settings", response_model=AdminFanConnectSettingsPublic)
def get_platform_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminFanConnectSettingsPublic:
    return AdminFanConnectSettingsPublic.model_validate(svc.admin_platform_settings(db))


@router.patch("/settings", response_model=AdminFanConnectSettingsPublic)
def patch_platform_settings(
    payload: AdminFanConnectSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminFanConnectSettingsPublic:
    return AdminFanConnectSettingsPublic.model_validate(
        svc.admin_update_platform_settings(
            db,
            user,
            decline_cooldown_days_default=payload.decline_cooldown_days_default,
        )
    )
