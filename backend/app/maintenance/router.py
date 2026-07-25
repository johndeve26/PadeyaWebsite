"""Maintenance admin + public API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.maintenance.models import (
    MaintenanceAuditLog,
    MaintenanceNotification,
    MaintenanceSchedule,
)
from app.maintenance.notify import deliver_maintenance_notification, send_test_to_self
from app.maintenance.sections import SECTION_DEFINITIONS
from app.maintenance.decision_cache import invalidate_maintenance_decision_cache
from app.maintenance.service import (
    GLOBAL_MODES,
    SECTION_MODES,
    create_bypass_session,
    ensure_section_rows,
    get_or_create_settings,
    public_status_payload,
    serialize_section,
    serialize_settings,
    write_maintenance_audit,
)
from app.users.models import User

router = APIRouter(tags=["maintenance"])


class SettingsUpdate(BaseModel):
    mode: str | None = None
    title: str | None = Field(default=None, max_length=200)
    message: str | None = None
    expected_back_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    show_countdown: bool | None = None
    allow_admin_panel: bool | None = None


class SectionUpdate(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    title: str | None = Field(default=None, max_length=200)
    message: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    affected_routes: list[str] | None = None
    affected_api_scopes: list[str] | None = None


class ScheduleCreate(BaseModel):
    title: str = Field(max_length=200)
    message: str = ""
    target_mode: str = "active"
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str = "UTC"
    show_countdown: bool = True
    auto_enable: bool = True
    auto_disable: bool = True
    section_keys: list[str] | None = None


class NotificationCreate(BaseModel):
    title: str = Field(max_length=200)
    body: str
    channels: list[str] = Field(default_factory=lambda: ["in_app"])
    audience: str = "all_users"
    schedule_id: UUID | None = None
    send_at: datetime | None = None
    reminder_hours: int | None = None
    send_now: bool = False


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("/maintenance/status")
@router.get("/maintenance/public")
def public_maintenance_status(db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    return public_status_payload(db)


@router.get("/admin/platform/maintenance")
def admin_get_maintenance(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.maintenance.view"))],
) -> dict[str, Any]:
    settings = get_or_create_settings(db)
    sections = ensure_section_rows(db)
    db.commit()
    catalog = [
        {
            "key": d.key,
            "label": d.label,
            "description": d.description,
            "api_prefixes": list(d.api_prefixes),
            "fe_prefixes": list(d.fe_prefixes),
        }
        for d in SECTION_DEFINITIONS
    ]
    schedules = db.scalars(
        select(MaintenanceSchedule).order_by(MaintenanceSchedule.starts_at.desc()).limit(20)
    ).all()
    return {
        "settings": serialize_settings(settings),
        "sections": [serialize_section(s) for s in sections],
        "section_catalog": catalog,
        "modes": sorted(GLOBAL_MODES),
        "section_modes": sorted(SECTION_MODES),
        "schedules": [
            {
                "id": str(s.id),
                "status": s.status,
                "target_mode": s.target_mode,
                "title": s.title,
                "message": s.message,
                "starts_at": s.starts_at.isoformat(),
                "ends_at": s.ends_at.isoformat() if s.ends_at else None,
                "timezone": s.timezone,
                "show_countdown": s.show_countdown,
                "auto_enable": s.auto_enable,
                "auto_disable": s.auto_disable,
                "section_keys": s.section_keys or [],
            }
            for s in schedules
        ],
    }


@router.patch("/admin/platform/maintenance")
def admin_patch_maintenance(
    payload: SettingsUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.maintenance.manage"))],
) -> dict[str, Any]:
    settings = get_or_create_settings(db)
    before = settings.mode
    if payload.mode is not None:
        if payload.mode not in GLOBAL_MODES:
            raise HTTPException(400, detail=f"Invalid mode: {payload.mode}")
        settings.mode = payload.mode
    if payload.title is not None:
        settings.title = payload.title.strip() or settings.title
    if payload.message is not None:
        settings.message = payload.message
    if "expected_back_at" in payload.model_fields_set:
        settings.expected_back_at = payload.expected_back_at
    if payload.timezone is not None:
        settings.timezone = payload.timezone
    if payload.show_countdown is not None:
        settings.show_countdown = payload.show_countdown
    if payload.allow_admin_panel is not None:
        settings.allow_admin_panel = payload.allow_admin_panel
    settings.updated_by_admin_id = admin.id
    ip, ua = _client_meta(request)
    action = "maintenance_enabled" if settings.mode != "off" else "maintenance_disabled"
    if before != settings.mode:
        if settings.mode == "read_only":
            action = "read_only_mode_enabled"
        elif settings.mode == "off":
            action = "maintenance_disabled"
        else:
            action = "maintenance_enabled"
    write_maintenance_audit(
        db,
        action=action,
        actor_user_id=admin.id,
        details={"before": before, "after": settings.mode},
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    invalidate_maintenance_decision_cache()
    db.refresh(settings)
    return serialize_settings(settings)


@router.patch("/admin/platform/maintenance/sections/{section_key}")
def admin_patch_section(
    section_key: str,
    payload: SectionUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.maintenance.manage"))],
) -> dict[str, Any]:
    ensure_section_rows(db)
    from app.maintenance.models import MaintenanceSection

    row = db.scalar(
        select(MaintenanceSection).where(MaintenanceSection.section_key == section_key)
    )
    if row is None:
        raise HTTPException(404, detail="Unknown section")
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.mode is not None:
        if payload.mode not in SECTION_MODES:
            raise HTTPException(400, detail="Invalid section mode")
        row.mode = payload.mode
    if payload.title is not None:
        row.title = payload.title
    if payload.message is not None:
        row.message = payload.message
    if "starts_at" in payload.model_fields_set:
        row.starts_at = payload.starts_at
    if "ends_at" in payload.model_fields_set:
        row.ends_at = payload.ends_at
    if payload.affected_routes is not None:
        row.affected_routes = payload.affected_routes
    if payload.affected_api_scopes is not None:
        row.affected_api_scopes = payload.affected_api_scopes
    row.updated_by_admin_id = admin.id
    ip, ua = _client_meta(request)
    write_maintenance_audit(
        db,
        action="section_maintenance_changed",
        actor_user_id=admin.id,
        details={
            "section_key": section_key,
            "enabled": row.enabled,
            "mode": row.mode,
        },
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    invalidate_maintenance_decision_cache()
    db.refresh(row)
    return serialize_section(row)


@router.post("/admin/platform/maintenance/schedules")
def admin_create_schedule(
    payload: ScheduleCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.maintenance.schedule"))],
) -> dict[str, Any]:
    if payload.target_mode not in {"active", "read_only", "section_only"}:
        raise HTTPException(400, detail="Invalid target_mode")
    row = MaintenanceSchedule(
        title=payload.title.strip(),
        message=payload.message,
        target_mode=payload.target_mode,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        timezone=payload.timezone,
        show_countdown=payload.show_countdown,
        auto_enable=payload.auto_enable,
        auto_disable=payload.auto_disable,
        section_keys=payload.section_keys,
        created_by_admin_id=admin.id,
        status="pending",
    )
    db.add(row)
    # Mark global as scheduled if currently off
    settings = get_or_create_settings(db)
    if settings.mode == "off":
        settings.mode = "scheduled"
        settings.title = payload.title
        settings.message = payload.message or settings.message
        settings.expected_back_at = payload.ends_at
        settings.show_countdown = payload.show_countdown
    ip, ua = _client_meta(request)
    write_maintenance_audit(
        db,
        action="schedule_created",
        actor_user_id=admin.id,
        details={"title": row.title, "starts_at": row.starts_at.isoformat()},
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    invalidate_maintenance_decision_cache()
    db.refresh(row)
    return {"id": str(row.id), "status": row.status}


@router.post("/admin/platform/maintenance/schedules/{schedule_id}/cancel")
def admin_cancel_schedule(
    schedule_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.maintenance.schedule"))],
) -> dict[str, str]:
    row = db.get(MaintenanceSchedule, schedule_id)
    if row is None:
        raise HTTPException(404, detail="Schedule not found")
    row.status = "cancelled"
    row.cancelled_at = datetime.now(UTC)
    ip, ua = _client_meta(request)
    write_maintenance_audit(
        db,
        action="schedule_cancelled",
        actor_user_id=admin.id,
        details={"schedule_id": str(schedule_id)},
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    invalidate_maintenance_decision_cache()
    return {"status": "cancelled"}


@router.get("/admin/platform/maintenance/history")
def admin_history(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.maintenance.view"))],
    limit: int = 100,
) -> dict[str, Any]:
    rows = db.scalars(
        select(MaintenanceAuditLog)
        .order_by(MaintenanceAuditLog.created_at.desc())
        .limit(min(limit, 500))
    ).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "action": r.action,
                "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
                "details": r.details or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/admin/platform/maintenance/notifications")
def admin_list_notifications(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.maintenance.notify"))],
) -> dict[str, Any]:
    rows = db.scalars(
        select(MaintenanceNotification)
        .order_by(MaintenanceNotification.created_at.desc())
        .limit(50)
    ).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "status": r.status,
                "title": r.title,
                "body": r.body,
                "channels": r.channels,
                "audience": r.audience,
                "send_at": r.send_at.isoformat() if r.send_at else None,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "delivery_count": r.delivery_count,
            }
            for r in rows
        ]
    }


@router.post("/admin/platform/maintenance/notifications")
def admin_create_notification(
    payload: NotificationCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.maintenance.notify"))],
) -> dict[str, Any]:
    row = MaintenanceNotification(
        title=payload.title.strip(),
        body=payload.body,
        channels=payload.channels,
        audience=payload.audience,
        schedule_id=payload.schedule_id,
        send_at=payload.send_at,
        reminder_hours=payload.reminder_hours,
        created_by_admin_id=admin.id,
        status="scheduled" if payload.send_at and not payload.send_now else "draft",
    )
    db.add(row)
    db.flush()
    ip, ua = _client_meta(request)
    delivery = 0
    if payload.send_now:
        delivery = deliver_maintenance_notification(db, row=row, actor=admin)
        row.status = "sent"
        row.sent_at = datetime.now(UTC)
        row.delivery_count = delivery
        write_maintenance_audit(
            db,
            action="notification_sent",
            actor_user_id=admin.id,
            details={"notification_id": str(row.id), "delivery_count": delivery},
            ip_address=ip,
            user_agent=ua,
        )
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "status": row.status, "delivery_count": row.delivery_count}


@router.post("/admin/platform/maintenance/notifications/test")
def admin_test_notification(
    payload: NotificationCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.maintenance.notify"))],
) -> dict[str, Any]:
    count = send_test_to_self(
        db,
        actor=admin,
        title=payload.title,
        body=payload.body,
        channels=payload.channels,
    )
    db.commit()
    return {"ok": True, "delivery_count": count}


@router.post("/admin/platform/maintenance/bypass")
def admin_create_bypass(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.maintenance.bypass"))],
    hours: int = 8,
) -> dict[str, Any]:
    row, raw = create_bypass_session(
        db, user_id=admin.id, actor_user_id=admin.id, hours=hours
    )
    ip, ua = _client_meta(request)
    write_maintenance_audit(
        db,
        action="bypass_token_regenerated",
        actor_user_id=admin.id,
        details={"session_id": str(row.id)},
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return {
        "token": raw,
        "expires_at": row.expires_at.isoformat(),
        "header": "X-Maintenance-Bypass",
        "warning": "Store securely. Never expose publicly. Shown once.",
    }
