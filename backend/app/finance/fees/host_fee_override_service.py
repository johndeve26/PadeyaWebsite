"""CRUD for host-specific fee overrides."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.finance.fees.constants import (
    PERMISSION_MANAGE_HOST_OVERRIDES,
    PERMISSION_VIEW_FEES,
)
from app.finance.fees.models import HostFeeOverride
from app.finance.fees.schemas import HostFeeOverrideCreate, HostFeeOverrideUpdate
from app.hosts.models import Host
from app.users.models import User
from app.users.service import user_has_permission


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _now() -> datetime:
    return datetime.now(UTC)


def _is_effective(row: HostFeeOverride, at: datetime) -> bool:
    start = _aware(row.effective_from)
    if start > at:
        return False
    if row.effective_to is not None and _aware(row.effective_to) <= at:
        return False
    return True


def _require_view(user: User) -> None:
    if (
        user_has_permission(user, PERMISSION_VIEW_FEES)
        or user_has_permission(user, PERMISSION_MANAGE_HOST_OVERRIDES)
        or user_has_permission(user, "admin.full_access")
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")


def _require_manage(user: User) -> None:
    if user_has_permission(user, PERMISSION_MANAGE_HOST_OVERRIDES) or user_has_permission(
        user, "admin.full_access"
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")

def _audit_payload(row: HostFeeOverride) -> dict:
    return {
        "host_id": str(row.host_id),
        "fee_key": row.fee_key,
        "percentage_value": str(row.percentage_value) if row.percentage_value is not None else None,
        "fixed_value": row.fixed_value,
        "payer": row.payer,
        "enabled": row.enabled,
        "effective_from": row.effective_from.isoformat() if row.effective_from else None,
        "effective_to": row.effective_to.isoformat() if row.effective_to else None,
        "reason": row.reason,
    }


class HostFeeOverrideService:
    """Admin-managed per-host fee overrides (beat global settings)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_overrides(
        self,
        *,
        user: User | None = None,
        host_id: UUID | None = None,
        fee_key: str | None = None,
        include_disabled: bool = True,
    ) -> list[HostFeeOverride]:
        if user is not None:
            _require_view(user)
        stmt = select(HostFeeOverride).order_by(
            HostFeeOverride.host_id.asc(),
            HostFeeOverride.fee_key.asc(),
            HostFeeOverride.effective_from.desc(),
        )
        if host_id is not None:
            stmt = stmt.where(HostFeeOverride.host_id == host_id)
        if fee_key is not None:
            stmt = stmt.where(HostFeeOverride.fee_key == fee_key)
        if not include_disabled:
            stmt = stmt.where(HostFeeOverride.enabled.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_override(self, override_id: UUID, *, user: User | None = None) -> HostFeeOverride:
        if user is not None:
            _require_view(user)
        row = self.db.get(HostFeeOverride, override_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Host fee override not found")
        return row

    def create_override(
        self,
        payload: HostFeeOverrideCreate,
        *,
        admin: User,
    ) -> HostFeeOverride:
        _require_manage(admin)
        host = self.db.get(Host, payload.host_id)
        if host is None:
            raise HTTPException(status_code=404, detail="Host not found")
        row = HostFeeOverride(
            host_id=payload.host_id,
            fee_key=payload.fee_key.strip(),
            percentage_value=payload.percentage_value,
            fixed_value=payload.fixed_value,
            payer=payload.payer,
            enabled=payload.enabled,
            effective_from=_aware(payload.effective_from),
            effective_to=_aware(payload.effective_to) if payload.effective_to else None,
            reason=payload.reason.strip() if payload.reason else None,
            created_by_admin_id=admin.id,
            updated_by_admin_id=admin.id,
        )
        self.db.add(row)
        self.db.flush()
        write_audit_log(
            self.db,
            action="finance.host_fee_override_create",
            actor_user_id=admin.id,
            resource_type="host_fee_override",
            resource_id=str(row.id),
            details=_audit_payload(row),
        )
        return row

    def update_override(
        self,
        override_id: UUID,
        payload: HostFeeOverrideUpdate,
        *,
        admin: User,
    ) -> HostFeeOverride:
        _require_manage(admin)
        row = self.get_override(override_id)
        before = _audit_payload(row)
        data = payload.model_dump(exclude_unset=True)
        if "percentage_value" in data:
            row.percentage_value = data["percentage_value"]
        if "fixed_value" in data:
            row.fixed_value = data["fixed_value"]
        if "payer" in data and data["payer"] is not None:
            row.payer = data["payer"]
        if "enabled" in data and data["enabled"] is not None:
            row.enabled = data["enabled"]
        if "effective_from" in data and data["effective_from"] is not None:
            row.effective_from = _aware(data["effective_from"])
        if "effective_to" in data:
            row.effective_to = (
                _aware(data["effective_to"]) if data["effective_to"] is not None else None
            )
        if "reason" in data:
            row.reason = data["reason"].strip() if data["reason"] else None
        if row.effective_to is not None and row.effective_to <= row.effective_from:
            raise HTTPException(
                status_code=400, detail="effective_to must be after effective_from"
            )
        row.updated_by_admin_id = admin.id
        self.db.flush()
        write_audit_log(
            self.db,
            action="finance.host_fee_override_update",
            actor_user_id=admin.id,
            resource_type="host_fee_override",
            resource_id=str(row.id),
            details={"before": before, "after": _audit_payload(row)},
        )
        return row

    def get_active_overrides(
        self,
        host_id: UUID,
        *,
        at: datetime | None = None,
        fee_keys: list[str] | None = None,
    ) -> dict[str, HostFeeOverride]:
        """Return enabled overrides for host effective at `at`, latest per fee_key."""
        moment = _aware(at or _now())
        stmt = select(HostFeeOverride).where(
            HostFeeOverride.host_id == host_id,
            HostFeeOverride.enabled.is_(True),
        )
        if fee_keys is not None:
            stmt = stmt.where(HostFeeOverride.fee_key.in_(fee_keys))
        rows = list(self.db.scalars(stmt).all())
        by_key: dict[str, HostFeeOverride] = {}
        for row in rows:
            if not _is_effective(row, moment):
                continue
            existing = by_key.get(row.fee_key)
            if existing is None or _aware(row.effective_from) > _aware(existing.effective_from):
                by_key[row.fee_key] = row
        return by_key
