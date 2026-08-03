"""Admin Ambassadors API — platform-wide management."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.promos import admin_service
from app.promos.schemas import (
    AmbassadorCampaignCreate,
    AmbassadorCampaignPublic,
    AmbassadorConversionAdmin,
    AmbassadorPlatformSettingsPublic,
    AmbassadorReportsSummary,
    AdminAmbassadorRow,
)
from app.users.models import User

router = APIRouter(prefix="/promos/admin", tags=["promos-admin"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


class PlatformSettingsUpdate(BaseModel):
    enabled: bool


class PauseReasonBody(BaseModel):
    reason: str | None = None


class ReverseConversionBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class RewardStatusBody(BaseModel):
    status: str = Field(pattern="^(attributed|approved|paid|rejected|reversed)$")
    reason: str | None = Field(default=None, max_length=500)
    payout_reference: str | None = Field(default=None, max_length=120)
    payout_note: str | None = Field(default=None, max_length=500)


class BlockResult(BaseModel):
    ambassador_id: UUID
    user_id: UUID
    ambassadors_blocked: bool


@router.get("/settings", response_model=AmbassadorPlatformSettingsPublic)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.get_platform_settings(db)


@router.patch("/settings", response_model=AmbassadorPlatformSettingsPublic)
def patch_settings(
    payload: PlatformSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.set_platform_enabled(
        db, admin=admin, enabled=payload.enabled
    )


@router.get("/campaigns", response_model=list[AmbassadorCampaignPublic])
def admin_list_campaigns(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status_filter: str | None = Query(default=None, alias="status"),
    source: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return admin_service.list_all_campaigns(
        db, status=status_filter, source=source, limit=limit, offset=offset
    )


@router.post(
    "/campaigns",
    response_model=AmbassadorCampaignPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_campaign(
    payload: AmbassadorCampaignCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.create_platform_campaign(db, admin=admin, payload=payload)


@router.post("/campaigns/{campaign_id}/pause", response_model=AmbassadorCampaignPublic)
def admin_pause(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
    payload: PauseReasonBody | None = None,
) -> dict:
    return admin_service.admin_pause_campaign(
        db,
        admin=admin,
        campaign_id=campaign_id,
        reason=payload.reason if payload else None,
    )


@router.post("/campaigns/{campaign_id}/resume", response_model=AmbassadorCampaignPublic)
def admin_resume(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.admin_resume_campaign(
        db, admin=admin, campaign_id=campaign_id
    )


@router.get("/ambassadors", response_model=list[AdminAmbassadorRow])
def admin_list_ambassadors(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    blocked_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return admin_service.list_admin_ambassadors(
        db,
        q=q,
        status=status_filter,
        blocked_only=blocked_only,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/ambassadors/{ambassador_id}/block",
    response_model=BlockResult,
)
def admin_block(
    ambassador_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.admin_block_ambassador_user(
        db, admin=admin, ambassador_id=ambassador_id, blocked=True
    )


@router.post(
    "/ambassadors/{ambassador_id}/unblock",
    response_model=BlockResult,
)
def admin_unblock(
    ambassador_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.admin_block_ambassador_user(
        db, admin=admin, ambassador_id=ambassador_id, blocked=False
    )


@router.get("/conversions", response_model=list[AmbassadorConversionAdmin])
def admin_list_conversions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return admin_service.list_conversions(
        db, status=status_filter, limit=limit, offset=offset
    )


@router.post(
    "/conversions/{sale_id}/reverse",
    response_model=AmbassadorConversionAdmin,
)
def admin_reverse_conversion(
    sale_id: UUID,
    payload: ReverseConversionBody,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.reverse_conversion(
        db, admin=admin, sale_id=sale_id, reason=payload.reason
    )


@router.post(
    "/conversions/{sale_id}/reward-status",
    response_model=AmbassadorConversionAdmin,
)
def admin_set_reward_status(
    sale_id: UUID,
    payload: RewardStatusBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    """Platform oversight reward-status (not exclusive for host-owned campaigns).

    Use for fraud intervention, support escalation, platform-wide campaigns,
    and emergency correction. Normal host-owned approval/payment workflow
    belongs on ``POST /host/ambassadors/conversions/{id}/reward-status`` and
    does not require ``admin.full_access``.
    """
    ip, ua = _client_meta(request)
    return admin_service.set_conversion_reward_status(
        db,
        admin=admin,
        sale_id=sale_id,
        status=payload.status,
        reason=payload.reason,
        payout_reference=payload.payout_reference,
        payout_note=payload.payout_note,
        ip_address=ip,
        user_agent=ua,
    )


@router.get("/reports/summary", response_model=AmbassadorReportsSummary)
def admin_reports_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> dict:
    return admin_service.reports_summary(db)


# --- Platform-wide referral programs ---


class PlatformProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    public_description: str | None = None
    enrollment_mode: str = "manual_enrollment"
    status: str = "active"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    attribution_window_days: int = Field(default=30, ge=1, le=365)
    default_landing_path: str = "/events"
    hold_period_days: int = Field(default=7, ge=0, le=365)
    budget_total: Decimal | None = None
    per_ambassador_cap: Decimal | None = None
    ticket_rule: dict | None = None
    merchandise_rule: dict | None = None
    excluded_host_ids: list[UUID] | None = None
    excluded_event_ids: list[UUID] | None = None


class PlatformProgramPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    public_description: str | None = None
    enrollment_mode: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    attribution_window_days: int | None = Field(default=None, ge=1, le=365)
    default_landing_path: str | None = None
    hold_period_days: int | None = Field(default=None, ge=0, le=365)
    budget_total: Decimal | None = None
    per_ambassador_cap: Decimal | None = None
    ticket_rule: dict | None = None
    merchandise_rule: dict | None = None


class EnrollmentCreate(BaseModel):
    user_id: UUID | None = None
    email: str | None = None
    display_name: str | None = None
    referral_code: str | None = None
    status: str = "active"


class EnrollmentPatch(BaseModel):
    status: str | None = None


@router.get("/referral-programs")
def admin_list_referral_programs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.referrals.view", "admin.referrals.programs.manage", "admin.full_access"))],
    scope: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    from app.promos import programs_service

    return programs_service.list_programs(
        db, scope=scope, status=status_filter, limit=limit, offset=offset
    )


@router.post("/referral-programs", status_code=status.HTTP_201_CREATED)
def admin_create_referral_program(
    payload: PlatformProgramCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.referrals.programs.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    return programs_service.create_platform_program(
        db, admin=admin, payload=payload.model_dump()
    )


@router.get("/referral-programs/{program_id}")
def admin_get_referral_program(
    program_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.referrals.view", "admin.referrals.programs.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    program = programs_service.get_program(db, program_id)
    return programs_service.serialize_program(db, program)


@router.patch("/referral-programs/{program_id}")
def admin_patch_referral_program(
    program_id: UUID,
    payload: PlatformProgramPatch,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.referrals.programs.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    return programs_service.patch_program(
        db,
        admin=admin,
        program_id=program_id,
        payload=payload.model_dump(exclude_unset=True),
    )


@router.post("/referral-programs/{program_id}/activate")
def admin_activate_program(
    program_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.referrals.programs.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    return programs_service.transition_program(
        db, admin=admin, program_id=program_id, new_status="active"
    )


@router.post("/referral-programs/{program_id}/pause")
def admin_pause_program(
    program_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.referrals.programs.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    return programs_service.transition_program(
        db, admin=admin, program_id=program_id, new_status="paused"
    )


@router.post("/referral-programs/{program_id}/close")
def admin_close_program(
    program_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.referrals.programs.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    return programs_service.transition_program(
        db, admin=admin, program_id=program_id, new_status="ended"
    )


@router.get("/referral-programs/{program_id}/enrollments")
def admin_list_enrollments(
    program_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.referrals.view", "admin.referrals.enrollments.manage", "admin.full_access"))],
) -> list[dict]:
    from app.promos import programs_service

    return programs_service.list_enrollments(db, program_id)


@router.post(
    "/referral-programs/{program_id}/enrollments",
    status_code=status.HTTP_201_CREATED,
)
def admin_enroll(
    program_id: UUID,
    payload: EnrollmentCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.referrals.enrollments.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    return programs_service.enroll_user(
        db,
        admin=admin,
        program_id=program_id,
        user_id=payload.user_id,
        email=payload.email,
        display_name=payload.display_name,
        referral_code=payload.referral_code,
        status=payload.status,
    )


@router.patch("/referral-enrollments/{enrollment_id}")
def admin_patch_enrollment(
    enrollment_id: UUID,
    payload: EnrollmentPatch,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("admin.referrals.enrollments.manage", "admin.full_access"))],
) -> dict:
    from app.promos import programs_service

    return programs_service.patch_enrollment(
        db,
        admin=admin,
        enrollment_id=enrollment_id,
        payload=payload.model_dump(exclude_unset=True),
    )
