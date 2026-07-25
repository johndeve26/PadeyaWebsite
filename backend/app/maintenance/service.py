"""Maintenance business logic: mode, sections, schedules, bypass, audit."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.maintenance.models import (
    MaintenanceAuditLog,
    MaintenanceBypassSession,
    MaintenanceNotification,
    MaintenanceSchedule,
    MaintenanceSection,
    MaintenanceSettings,
)
from app.maintenance.sections import SECTION_BY_KEY, SECTION_DEFINITIONS

logger = logging.getLogger("padeya.maintenance")

GLOBAL_MODES = frozenset({"off", "scheduled", "active", "read_only", "section_only"})
SECTION_MODES = frozenset({"maintenance", "read_only"})
BYPASS_HEADER = "X-Maintenance-Bypass"
BYPASS_TTL_HOURS = 8

# Process-local short-circuit: middleware used to INSERT+flush without commit on
# every request when the table was empty, deadlocking Neon under load.
_SECTIONS_SEEDED = False


def _utcnow() -> datetime:
    return datetime.now(UTC)


def write_maintenance_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: UUID | None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        MaintenanceAuditLog(
            action=action,
            actor_user_id=actor_user_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=(user_agent or "")[:400] or None,
        )
    )


def get_or_create_settings(db: Session) -> MaintenanceSettings:
    row = db.scalar(select(MaintenanceSettings).limit(1))
    if row is None:
        row = MaintenanceSettings(mode="off")
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            row = db.scalar(select(MaintenanceSettings).limit(1))
            if row is None:
                raise
        else:
            db.refresh(row)
    return row


def ensure_section_rows(db: Session) -> list[MaintenanceSection]:
    """Idempotent seed of section rows. Commits when creating (safe for middleware)."""
    global _SECTIONS_SEEDED

    existing = {
        r.section_key: r
        for r in db.scalars(select(MaintenanceSection)).all()
    }
    if _SECTIONS_SEEDED and len(existing) >= len(SECTION_DEFINITIONS):
        return [existing[d.key] for d in SECTION_DEFINITIONS if d.key in existing]

    missing = [d for d in SECTION_DEFINITIONS if d.key not in existing]
    if missing:
        for defn in missing:
            db.add(
                MaintenanceSection(
                    section_key=defn.key,
                    enabled=False,
                    mode="maintenance",
                    title=defn.label,
                    message=f"{defn.label} is temporarily unavailable.",
                    affected_routes=list(defn.fe_prefixes),
                    affected_api_scopes=list(defn.api_prefixes),
                )
            )
        try:
            db.commit()
        except IntegrityError:
            # Concurrent middleware seeds — reload winners.
            db.rollback()
        existing = {
            r.section_key: r
            for r in db.scalars(select(MaintenanceSection)).all()
        }

    if len(existing) >= len(SECTION_DEFINITIONS):
        _SECTIONS_SEEDED = True

    return [existing[d.key] for d in SECTION_DEFINITIONS if d.key in existing]

def apply_due_schedules(db: Session) -> None:
    """Auto-enable/disable schedules based on wall clock (called from middleware)."""
    now = _utcnow()
    settings = get_or_create_settings(db)
    pending = db.scalars(
        select(MaintenanceSchedule).where(
            MaintenanceSchedule.status == "pending",
            MaintenanceSchedule.auto_enable.is_(True),
            MaintenanceSchedule.starts_at <= now,
        )
    ).all()
    for sched in pending:
        settings.mode = sched.target_mode
        settings.title = sched.title
        settings.message = sched.message or settings.message
        settings.expected_back_at = sched.ends_at
        settings.timezone = sched.timezone
        settings.show_countdown = sched.show_countdown
        if sched.target_mode == "section_only" and sched.section_keys:
            ensure_section_rows(db)
            for key in sched.section_keys:
                sec = db.scalar(
                    select(MaintenanceSection).where(
                        MaintenanceSection.section_key == key
                    )
                )
                if sec:
                    sec.enabled = True
                    sec.mode = "maintenance"
                    sec.starts_at = sched.starts_at
                    sec.ends_at = sched.ends_at
        sched.status = "active"
        sched.activated_at = now
        write_maintenance_audit(
            db,
            action="schedule_activated",
            actor_user_id=None,
            details={"schedule_id": str(sched.id), "mode": sched.target_mode},
        )

    active = db.scalars(
        select(MaintenanceSchedule).where(
            MaintenanceSchedule.status == "active",
            MaintenanceSchedule.auto_disable.is_(True),
            MaintenanceSchedule.ends_at.is_not(None),
            MaintenanceSchedule.ends_at <= now,
        )
    ).all()
    for sched in active:
        settings.mode = "off"
        settings.expected_back_at = None
        if sched.section_keys:
            for key in sched.section_keys:
                sec = db.scalar(
                    select(MaintenanceSection).where(
                        MaintenanceSection.section_key == key
                    )
                )
                if sec:
                    sec.enabled = False
        sched.status = "completed"
        sched.completed_at = now
        write_maintenance_audit(
            db,
            action="schedule_completed",
            actor_user_id=None,
            details={"schedule_id": str(sched.id)},
        )
    if pending or active:
        db.commit()
        try:
            from app.maintenance.decision_cache import (
                invalidate_maintenance_decision_cache,
            )

            invalidate_maintenance_decision_cache()
        except Exception:  # noqa: BLE001
            pass


def hash_bypass_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_bypass_session(
    db: Session,
    *,
    user_id: UUID,
    actor_user_id: UUID | None,
    hours: int = BYPASS_TTL_HOURS,
) -> tuple[MaintenanceBypassSession, str]:
    raw = secrets.token_urlsafe(32)
    row = MaintenanceBypassSession(
        user_id=user_id,
        token_hash=hash_bypass_token(raw),
        expires_at=_utcnow() + timedelta(hours=max(1, min(hours, 72))),
        created_by_admin_id=actor_user_id,
    )
    db.add(row)
    write_maintenance_audit(
        db,
        action="bypass_token_regenerated",
        actor_user_id=actor_user_id,
        details={"user_id": str(user_id), "expires_at": row.expires_at.isoformat()},
    )
    db.commit()
    db.refresh(row)
    return row, raw


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def validate_bypass_token(
    db: Session, *, token: str | None, user_id: UUID | None
) -> bool:
    if not token or not user_id:
        return False
    th = hash_bypass_token(token)
    row = db.scalar(
        select(MaintenanceBypassSession).where(
            MaintenanceBypassSession.token_hash == th,
            MaintenanceBypassSession.user_id == user_id,
            MaintenanceBypassSession.revoked_at.is_(None),
        )
    )
    if row is None or _as_utc(row.expires_at) <= _utcnow():
        return False
    row.last_used_at = _utcnow()
    write_maintenance_audit(
        db,
        action="bypass_used",
        actor_user_id=user_id,
        details={"session_id": str(row.id)},
    )
    db.commit()
    return True


def public_status_payload(db: Session) -> dict[str, Any]:
    apply_due_schedules(db)
    settings = get_or_create_settings(db)
    sections = ensure_section_rows(db)
    upcoming = db.scalar(
        select(MaintenanceSchedule)
        .where(
            MaintenanceSchedule.status == "pending",
            MaintenanceSchedule.starts_at > _utcnow(),
        )
        .order_by(MaintenanceSchedule.starts_at.asc())
        .limit(1)
    )
    active_sections = []
    for s in sections:
        if not (s.enabled and _section_window_active(s)):
            continue
        defn = SECTION_BY_KEY.get(s.section_key)
        active_sections.append(
            {
                "key": s.section_key,
                "label": defn.label if defn else s.section_key,
                "mode": s.mode,
                "title": s.title,
                "message": s.message,
                "starts_at": s.starts_at.isoformat() if s.starts_at else None,
                "ends_at": s.ends_at.isoformat() if s.ends_at else None,
            }
        )
    return {
        "mode": settings.mode,
        "maintenance": settings.mode in {"active", "read_only", "section_only"},
        "title": settings.title,
        "message": settings.message,
        "expected_back_at": settings.expected_back_at.isoformat()
        if settings.expected_back_at
        else None,
        "timezone": settings.timezone,
        "show_countdown": settings.show_countdown,
        "sections": active_sections,
        "upcoming_schedule": (
            {
                "id": str(upcoming.id),
                "title": upcoming.title,
                "starts_at": upcoming.starts_at.isoformat(),
                "ends_at": upcoming.ends_at.isoformat() if upcoming.ends_at else None,
                "show_countdown": upcoming.show_countdown,
            }
            if upcoming
            else None
        ),
    }


def _section_window_active(sec: MaintenanceSection) -> bool:
    now = _utcnow()
    if sec.starts_at and _as_utc(sec.starts_at) > now:
        return False
    if sec.ends_at and _as_utc(sec.ends_at) <= now:
        return False
    return True


def serialize_settings(row: MaintenanceSettings) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "mode": row.mode,
        "title": row.title,
        "message": row.message,
        "expected_back_at": row.expected_back_at.isoformat()
        if row.expected_back_at
        else None,
        "timezone": row.timezone,
        "show_countdown": row.show_countdown,
        "allow_admin_panel": row.allow_admin_panel,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_section(row: MaintenanceSection) -> dict[str, Any]:
    defn = SECTION_BY_KEY.get(row.section_key)
    return {
        "id": str(row.id),
        "section_key": row.section_key,
        "label": defn.label if defn else row.section_key,
        "description": defn.description if defn else "",
        "enabled": row.enabled,
        "mode": row.mode,
        "title": row.title,
        "message": row.message,
        "starts_at": row.starts_at.isoformat() if row.starts_at else None,
        "ends_at": row.ends_at.isoformat() if row.ends_at else None,
        "affected_routes": row.affected_routes or (list(defn.fe_prefixes) if defn else []),
        "affected_api_scopes": row.affected_api_scopes
        or (list(defn.api_prefixes) if defn else []),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
