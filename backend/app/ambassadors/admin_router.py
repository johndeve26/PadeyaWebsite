"""Admin Ambassadors routes — /api/v1/admin/ambassadors/..."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ambassadors import admin_service as svc
from app.ambassadors.fraud import list_fraud_flags
from app.ambassadors.reward_audit import list_admin_reward_audits
from app.ambassadors.schemas import (
    AdminAmbassadorRow,
    BlockParticipantRequest,
    CampaignPublic,
    ConversionAdminPublic,
    FraudFlagPublic,
    ParticipantPublic,
    PayoutPublic,
    ReverseConversionRequest,
)
from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/admin/ambassadors", tags=["ambassadors-admin"])


@router.get("", response_model=list[AdminAmbassadorRow])
def list_profiles(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AdminAmbassadorRow]:
    return [
        AdminAmbassadorRow.model_validate(r)
        for r in svc.list_admin_profiles(db, q=q, limit=limit, offset=offset)
    ]


@router.get("/campaigns", response_model=list[CampaignPublic])
def list_campaigns(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CampaignPublic]:
    return [
        CampaignPublic.model_validate(r)
        for r in svc.list_admin_campaigns(
            db, status=status, limit=limit, offset=offset
        )
    ]


@router.get("/fraud-flags", response_model=list[FraudFlagPublic])
def fraud_flags(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status: Annotated[str | None, Query()] = "open",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FraudFlagPublic]:
    return [
        FraudFlagPublic.model_validate(r)
        for r in list_fraud_flags(db, status=status, limit=limit, offset=offset)
    ]


@router.get("/reward-audit")
def reward_audit(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    host_id: Annotated[UUID | None, Query()] = None,
    campaign_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    """Platform-wide Ambassador reward action audit (all hosts)."""
    return list_admin_reward_audits(
        db,
        host_id=host_id,
        campaign_id=campaign_id,
        limit=limit,
        offset=offset,
    )


@router.get("/conversions", response_model=list[ConversionAdminPublic])
def list_conversions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConversionAdminPublic]:
    return [
        ConversionAdminPublic.model_validate(r)
        for r in svc.list_admin_conversions(
            db, status=status, limit=limit, offset=offset
        )
    ]


@router.get("/payouts", response_model=list[PayoutPublic])
def list_payouts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PayoutPublic]:
    return [
        PayoutPublic.model_validate(r)
        for r in svc.list_admin_payouts(
            db, status=status, limit=limit, offset=offset
        )
    ]


@router.post(
    "/participants/{participant_id}/block",
    response_model=ParticipantPublic,
)
def block_participant(
    participant_id: UUID,
    payload: BlockParticipantRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> ParticipantPublic:
    return ParticipantPublic.model_validate(
        svc.block_participant(
            db,
            admin=admin,
            participant_id=participant_id,
            reason=payload.reason,
        )
    )


@router.post(
    "/conversions/{conversion_id}/reverse",
    response_model=ConversionAdminPublic,
)
def reverse_conversion(
    conversion_id: UUID,
    payload: ReverseConversionRequest,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> ConversionAdminPublic:
    return ConversionAdminPublic.model_validate(
        svc.reverse_conversion(
            db,
            admin=admin,
            conversion_id=conversion_id,
            reason=payload.reason,
        )
    )
