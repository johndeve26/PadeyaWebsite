"""Host Ambassadors routes — /api/v1/host/ambassadors/..."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ambassadors import host_service as svc
from app.ambassadors import rewards as reward_svc
from app.ambassadors.schemas import (
    CampaignPublic,
    HostAnalyticsPublic,
    HostCampaignCreate,
    HostCampaignUpdate,
    HostParticipantRow,
    MessagePublic,
    PayoutPublic,
)
from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.hosts.team_access import require_host_for_permission
from app.promos.schemas import AmbassadorConversionAdmin
from app.teams.deps import ResolvedHostId

router = APIRouter(prefix="/host/ambassadors", tags=["ambassadors-host"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


class ReverseConversionBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class RewardStatusBody(BaseModel):
    status: str = Field(pattern="^(approved|rejected|paid|reversed)$")
    reason: str | None = Field(default=None, max_length=500)
    payout_reference: str | None = Field(default=None, max_length=120)
    payout_note: str | None = Field(default=None, max_length=500)


class FlagSuspiciousBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.get("/campaigns", response_model=list[CampaignPublic])
def list_campaigns(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> list[CampaignPublic]:
    return [
        CampaignPublic.model_validate(r)
        for r in svc.list_host_campaigns(db, user, host_id=host_id)
    ]


@router.post("/campaigns", response_model=CampaignPublic, status_code=201)
def create_campaign(
    payload: HostCampaignCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> CampaignPublic:
    return CampaignPublic.model_validate(
        svc.create_host_campaign(db, user=user, payload=payload, host_id=host_id)
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignPublic)
def get_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> CampaignPublic:
    return CampaignPublic.model_validate(
        svc.get_host_campaign(
            db, user=user, campaign_id=campaign_id, host_id=host_id
        )
    )


@router.patch("/campaigns/{campaign_id}", response_model=CampaignPublic)
def update_campaign(
    campaign_id: UUID,
    payload: HostCampaignUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> CampaignPublic:
    return CampaignPublic.model_validate(
        svc.update_host_campaign(
            db,
            user=user,
            campaign_id=campaign_id,
            payload=payload,
            host_id=host_id,
        )
    )


@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignPublic)
def pause_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> CampaignPublic:
    return CampaignPublic.model_validate(
        svc.pause_host_campaign(
            db, user=user, campaign_id=campaign_id, host_id=host_id
        )
    )


@router.post("/campaigns/{campaign_id}/end", response_model=CampaignPublic)
def end_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> CampaignPublic:
    return CampaignPublic.model_validate(
        svc.end_host_campaign(
            db, user=user, campaign_id=campaign_id, host_id=host_id
        )
    )


@router.get(
    "/campaigns/{campaign_id}/participants",
    response_model=list[HostParticipantRow],
)
def list_participants(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> list[HostParticipantRow]:
    return [
        HostParticipantRow.model_validate(r)
        for r in svc.list_campaign_participants(
            db, user=user, campaign_id=campaign_id, host_id=host_id
        )
    ]


@router.post("/participants/{participant_id}/remove", response_model=MessagePublic)
def remove_participant(
    participant_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> MessagePublic:
    return MessagePublic.model_validate(
        svc.remove_participant(
            db, user=user, participant_id=participant_id, host_id=host_id
        )
    )


@router.get("/analytics", response_model=HostAnalyticsPublic)
def analytics(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> HostAnalyticsPublic:
    return HostAnalyticsPublic.model_validate(
        svc.host_analytics(db, user, host_id=host_id)
    )


@router.get("/payouts", response_model=list[PayoutPublic])
def payouts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> list[PayoutPublic]:
    return [
        PayoutPublic.model_validate(r)
        for r in svc.list_host_payouts(db, user, host_id=host_id)
    ]


@router.get("/conversions", response_model=list[AmbassadorConversionAdmin])
def list_conversions(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AmbassadorConversionAdmin]:
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=host_id,
        permission=(
            "ambassadors.view_conversions",
            "ambassadors.view",
            "ambassadors.approve_rewards",
        ),
    )
    return [
        AmbassadorConversionAdmin.model_validate(r)
        for r in reward_svc.list_host_conversions(
            db,
            host_id=host.id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/conversions/export")
def export_conversions(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
    status_filter: str | None = Query(default=None, alias="status"),
) -> Response:
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=host_id,
        permission=("ambassadors.export", "finance.view_payouts"),
    )
    csv_body = reward_svc.export_host_conversions_csv(
        db, host_id=host.id, status=status_filter
    )
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="ambassador-conversions.csv"'
        },
    )


@router.get("/reward-audit")
def list_reward_audit(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
    campaign_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """Host-visible reward action audit for this workspace's campaigns."""
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=host_id,
        permission=(
            "ambassadors.view_conversions",
            "ambassadors.view",
            "ambassadors.approve_rewards",
            "ambassadors.view_payouts",
        ),
    )
    return reward_svc.list_host_campaign_reward_audits(
        db,
        host_id=host.id,
        campaign_id=campaign_id,
        limit=limit,
        offset=offset,
    )


@router.get("/conversions/{conversion_id}/audit")
def conversion_audit(
    conversion_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> list[dict]:
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=host_id,
        permission=(
            "ambassadors.view_conversions",
            "ambassadors.view",
            "ambassadors.approve_rewards",
        ),
    )
    return reward_svc.list_host_conversion_audit(
        db, host_id=host.id, conversion_id=conversion_id
    )


@router.post("/conversions/{conversion_id}/flag")
def flag_conversion(
    conversion_id: UUID,
    payload: FlagSuspiciousBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> dict:
    """Flag a suspicious host-owned conversion for review."""
    from app.ambassadors.fraud import flag_suspicious_conversion
    from app.promos.models import Ambassador, AmbassadorSale

    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=host_id,
        permission=(
            "ambassadors.approve_rewards",
            "ambassadors.view_conversions",
            "ambassadors.reverse_rewards",
        ),
    )
    sale = db.get(AmbassadorSale, conversion_id)
    if sale is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Conversion not found")
    amb = db.get(Ambassador, sale.ambassador_id)
    if amb is None or amb.host_id != host.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Conversion not found")
    return flag_suspicious_conversion(
        db,
        actor_user_id=user.id,
        campaign_id=amb.campaign_id,
        conversion_id=sale.id,
        reason=payload.reason,
        host_id=host.id,
    )


@router.post(
    "/conversions/{conversion_id}/reward-status",
    response_model=AmbassadorConversionAdmin,
)
def set_reward_status(
    conversion_id: UUID,
    payload: RewardStatusBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> AmbassadorConversionAdmin:
    """Normal host-owned Ambassador reward workflow.

    Host owner or team member with Ambassadors/finance permissions — does
    **not** require ``admin.full_access``. Platform admin oversight remains on
    ``POST /promos/admin/conversions/{sale_id}/reward-status``.
    """
    ip, ua = _client_meta(request)
    return AmbassadorConversionAdmin.model_validate(
        reward_svc.set_host_conversion_reward_status(
            db,
            actor=user,
            conversion_id=conversion_id,
            host_id=host_id,
            status=payload.status,
            reason=payload.reason,
            payout_reference=payload.payout_reference,
            payout_note=payload.payout_note,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post(
    "/conversions/{conversion_id}/reverse",
    response_model=AmbassadorConversionAdmin,
)
def reverse_conversion(
    conversion_id: UUID,
    payload: ReverseConversionBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: ResolvedHostId,
) -> AmbassadorConversionAdmin:
    """Legacy reverse path — prefer reward-status with status=reversed."""
    ip, ua = _client_meta(request)
    return AmbassadorConversionAdmin.model_validate(
        reward_svc.set_host_conversion_reward_status(
            db,
            actor=user,
            conversion_id=conversion_id,
            host_id=host_id,
            status="reversed",
            reason=payload.reason,
            ip_address=ip,
            user_agent=ua,
        )
    )
