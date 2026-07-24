"""Admin API for platform fee settings and host fee overrides."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.core.database import get_db
from app.finance.fees.constants import (
    PERMISSION_MANAGE_FEES,
    PERMISSION_MANAGE_HOST_OVERRIDES,
    PERMISSION_VIEW_FEES,
)
from app.finance.fees.fee_settings_service import FeeSettingsService
from app.finance.fees.host_fee_override_service import HostFeeOverrideService
from app.finance.fees.schemas import (
    HostFeeOverrideCreate,
    HostFeeOverridePublic,
    HostFeeOverrideUpdate,
    PlatformFeeSettingCreate,
    PlatformFeeSettingPublic,
    PlatformFeeSettingUpdate,
)

router = APIRouter(prefix="/finance/admin/fees", tags=["finance-fees"])


@router.get(
    "/settings",
    response_model=list[PlatformFeeSettingPublic],
    dependencies=[Depends(require_permission(PERMISSION_VIEW_FEES, "admin.full_access"))],
)
def list_fee_settings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    category: str | None = None,
    fee_key: str | None = None,
    include_disabled: bool = Query(default=True),
) -> list[PlatformFeeSettingPublic]:
    rows = FeeSettingsService(db).list_settings(
        user=user,
        category=category,
        fee_key=fee_key,
        include_disabled=include_disabled,
    )
    return [PlatformFeeSettingPublic.model_validate(r) for r in rows]


@router.post(
    "/settings",
    response_model=PlatformFeeSettingPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PERMISSION_MANAGE_FEES, "admin.full_access"))],
)
def create_fee_setting(
    payload: PlatformFeeSettingCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PlatformFeeSettingPublic:
    row = FeeSettingsService(db).create_setting(payload, admin=user)
    db.commit()
    db.refresh(row)
    return PlatformFeeSettingPublic.model_validate(row)


@router.patch(
    "/settings/{setting_id}",
    response_model=PlatformFeeSettingPublic,
    dependencies=[Depends(require_permission(PERMISSION_MANAGE_FEES, "admin.full_access"))],
)
def update_fee_setting(
    setting_id: UUID,
    payload: PlatformFeeSettingUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PlatformFeeSettingPublic:
    row = FeeSettingsService(db).update_setting(setting_id, payload, admin=user)
    db.commit()
    db.refresh(row)
    return PlatformFeeSettingPublic.model_validate(row)


@router.get(
    "/overrides",
    response_model=list[HostFeeOverridePublic],
    dependencies=[
        Depends(
            require_permission(
                PERMISSION_VIEW_FEES,
                PERMISSION_MANAGE_HOST_OVERRIDES,
                "admin.full_access",
            )
        )
    ],
)
def list_host_overrides(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: UUID | None = None,
    fee_key: str | None = None,
    include_disabled: bool = Query(default=True),
) -> list[HostFeeOverridePublic]:
    rows = HostFeeOverrideService(db).list_overrides(
        user=user,
        host_id=host_id,
        fee_key=fee_key,
        include_disabled=include_disabled,
    )
    return [HostFeeOverridePublic.model_validate(r) for r in rows]


@router.post(
    "/overrides",
    response_model=HostFeeOverridePublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permission(PERMISSION_MANAGE_HOST_OVERRIDES, "admin.full_access"))
    ],
)
def create_host_override(
    payload: HostFeeOverrideCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostFeeOverridePublic:
    row = HostFeeOverrideService(db).create_override(payload, admin=user)
    db.commit()
    db.refresh(row)
    return HostFeeOverridePublic.model_validate(row)


@router.patch(
    "/overrides/{override_id}",
    response_model=HostFeeOverridePublic,
    dependencies=[
        Depends(require_permission(PERMISSION_MANAGE_HOST_OVERRIDES, "admin.full_access"))
    ],
)
def update_host_override(
    override_id: UUID,
    payload: HostFeeOverrideUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostFeeOverridePublic:
    row = HostFeeOverrideService(db).update_override(override_id, payload, admin=user)
    db.commit()
    db.refresh(row)
    return HostFeeOverridePublic.model_validate(row)
