"""CRUD and resolution for global platform fee settings."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.finance.fees.constants import (
    FEE_CATEGORIES,
    PERMISSION_MANAGE_FEES,
    PERMISSION_VIEW_FEES,
)
from app.finance.fees.models import PlatformFeeSetting
from app.finance.fees.schemas import PlatformFeeSettingCreate, PlatformFeeSettingUpdate
from app.users.models import User
from app.users.service import user_has_permission


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _now() -> datetime:
    return datetime.now(UTC)


def _is_effective(row: PlatformFeeSetting, at: datetime) -> bool:
    start = _aware(row.effective_from)
    if start > at:
        return False
    if row.effective_to is not None and _aware(row.effective_to) <= at:
        return False
    return True


def _require_view(user: User) -> None:
    if user_has_permission(user, PERMISSION_VIEW_FEES) or user_has_permission(
        user, PERMISSION_MANAGE_FEES
    ) or user_has_permission(user, "admin.full_access"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")


def _require_manage(user: User) -> None:
    if user_has_permission(user, PERMISSION_MANAGE_FEES) or user_has_permission(
        user, "admin.full_access"
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")


def _audit_payload(row: PlatformFeeSetting) -> dict:
    return {
        "fee_key": row.fee_key,
        "label": row.label,
        "category": row.category,
        "fee_type": row.fee_type,
        "percentage_value": str(row.percentage_value) if row.percentage_value is not None else None,
        "fixed_value": row.fixed_value,
        "currency": row.currency,
        "payer": row.payer,
        "enabled": row.enabled,
        "applies_to": row.applies_to,
        "notes": row.notes,
        "effective_from": row.effective_from.isoformat() if row.effective_from else None,
        "effective_to": row.effective_to.isoformat() if row.effective_to else None,
    }


class FeeSettingsService:
    """Admin-managed global fee schedule."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_settings(
        self,
        *,
        user: User | None = None,
        category: str | None = None,
        fee_key: str | None = None,
        include_disabled: bool = True,
    ) -> list[PlatformFeeSetting]:
        if user is not None:
            _require_view(user)
        stmt = select(PlatformFeeSetting).order_by(
            PlatformFeeSetting.fee_key.asc(),
            PlatformFeeSetting.effective_from.desc(),
        )
        if category is not None:
            if category not in FEE_CATEGORIES:
                raise HTTPException(status_code=400, detail="Invalid category")
            stmt = stmt.where(PlatformFeeSetting.category == category)
        if fee_key is not None:
            stmt = stmt.where(PlatformFeeSetting.fee_key == fee_key)
        if not include_disabled:
            stmt = stmt.where(PlatformFeeSetting.enabled.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_setting(self, setting_id: UUID, *, user: User | None = None) -> PlatformFeeSetting:
        if user is not None:
            _require_view(user)
        row = self.db.get(PlatformFeeSetting, setting_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Fee setting not found")
        return row

    def create_setting(
        self,
        payload: PlatformFeeSettingCreate,
        *,
        admin: User,
    ) -> PlatformFeeSetting:
        _require_manage(admin)
        row = PlatformFeeSetting(
            fee_key=payload.fee_key.strip(),
            label=payload.label.strip(),
            category=payload.category,
            fee_type=payload.fee_type,
            percentage_value=payload.percentage_value,
            fixed_value=payload.fixed_value,
            currency=payload.currency.upper(),
            payer=payload.payer,
            enabled=payload.enabled,
            applies_to=payload.applies_to.strip() or "all",
            notes=payload.notes.strip() if payload.notes else None,
            effective_from=_aware(payload.effective_from),
            effective_to=_aware(payload.effective_to) if payload.effective_to else None,
            created_by_admin_id=admin.id,
            updated_by_admin_id=admin.id,
        )
        self.db.add(row)
        self.db.flush()
        write_audit_log(
            self.db,
            action="finance.fee_setting_create",
            actor_user_id=admin.id,
            resource_type="platform_fee_setting",
            resource_id=str(row.id),
            details=_audit_payload(row),
        )
        return row

    def update_setting(
        self,
        setting_id: UUID,
        payload: PlatformFeeSettingUpdate,
        *,
        admin: User,
    ) -> PlatformFeeSetting:
        _require_manage(admin)
        row = self.get_setting(setting_id)
        before = _audit_payload(row)
        data = payload.model_dump(exclude_unset=True)
        if "label" in data and data["label"] is not None:
            row.label = data["label"].strip()
        if "fee_type" in data and data["fee_type"] is not None:
            row.fee_type = data["fee_type"]
        if "percentage_value" in data:
            row.percentage_value = data["percentage_value"]
        if "fixed_value" in data:
            row.fixed_value = data["fixed_value"]
        if "currency" in data and data["currency"] is not None:
            row.currency = data["currency"].upper()
        if "payer" in data and data["payer"] is not None:
            row.payer = data["payer"]
        if "enabled" in data and data["enabled"] is not None:
            row.enabled = data["enabled"]
        if "applies_to" in data and data["applies_to"] is not None:
            row.applies_to = data["applies_to"].strip() or "all"
        if "notes" in data:
            row.notes = data["notes"].strip() if data["notes"] else None
        if "effective_from" in data and data["effective_from"] is not None:
            row.effective_from = _aware(data["effective_from"])
        if "effective_to" in data:
            row.effective_to = (
                _aware(data["effective_to"]) if data["effective_to"] is not None else None
            )
        if row.effective_to is not None and row.effective_to <= row.effective_from:
            raise HTTPException(
                status_code=400, detail="effective_to must be after effective_from"
            )
        row.updated_by_admin_id = admin.id
        self.db.flush()
        write_audit_log(
            self.db,
            action="finance.fee_setting_update",
            actor_user_id=admin.id,
            resource_type="platform_fee_setting",
            resource_id=str(row.id),
            details={"before": before, "after": _audit_payload(row)},
        )
        return row

    def get_active_global_settings(
        self,
        *,
        category: str | None = None,
        at: datetime | None = None,
        fee_keys: list[str] | None = None,
    ) -> list[PlatformFeeSetting]:
        """Return enabled global settings effective at `at`, latest per fee_key."""
        moment = _aware(at or _now())
        stmt = select(PlatformFeeSetting).where(PlatformFeeSetting.enabled.is_(True))
        if category is not None:
            stmt = stmt.where(PlatformFeeSetting.category == category)
        if fee_keys is not None:
            stmt = stmt.where(PlatformFeeSetting.fee_key.in_(fee_keys))
        rows = list(self.db.scalars(stmt).all())
        by_key: dict[str, PlatformFeeSetting] = {}
        for row in rows:
            if not _is_effective(row, moment):
                continue
            existing = by_key.get(row.fee_key)
            if existing is None or _aware(row.effective_from) > _aware(existing.effective_from):
                by_key[row.fee_key] = row
        return list(by_key.values())


def percentage_as_decimal(value: Decimal | str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
