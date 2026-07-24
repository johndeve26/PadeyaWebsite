"""Host sponsorship deals API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.sponsorships import deals_service as svc
from app.sponsorships import deliverables_service as deliv_svc
from app.sponsorships.deliverables_schemas import (
    HostDeliverablePatch,
    HostDeliverableSubmit,
    SponsorshipDeliverablePublic,
)
from app.sponsorships.deals_schemas import (
    HostSponsorshipRevenueReport,
    SponsorshipDealCreate,
    SponsorshipDealPublic,
    SponsorshipDealUpdate,
)

router = APIRouter(prefix="/host/sponsorship-deals", tags=["host-sponsorship-deals"])


@router.get("", response_model=list[SponsorshipDealPublic])
def list_deals(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[SponsorshipDealPublic]:
    rows = svc.host_list_deals(db, user)
    return [SponsorshipDealPublic.model_validate(r) for r in rows]


@router.get("/reports/summary", response_model=HostSponsorshipRevenueReport)
def revenue_summary(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostSponsorshipRevenueReport:
    return HostSponsorshipRevenueReport.model_validate(svc.host_revenue_report(db, user))


@router.post("", response_model=SponsorshipDealPublic, status_code=status.HTTP_201_CREATED)
def create_deal(
    payload: SponsorshipDealCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    row = svc.host_create_deal(db, user, payload)
    return SponsorshipDealPublic.model_validate(row)


@router.get("/{deal_id}", response_model=SponsorshipDealPublic)
def get_deal(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(svc.host_get_deal(db, user, deal_id))


@router.patch("/{deal_id}", response_model=SponsorshipDealPublic)
def patch_deal(
    deal_id: UUID,
    payload: SponsorshipDealUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(
        svc.host_update_deal(db, user, deal_id, payload)
    )


@router.post("/{deal_id}/send", response_model=SponsorshipDealPublic)
def send_deal(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(svc.host_send_deal(db, user, deal_id))


@router.post("/{deal_id}/cancel", response_model=SponsorshipDealPublic)
def cancel_deal(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(svc.host_cancel_deal(db, user, deal_id))


@router.get("/{deal_id}/deliverables", response_model=list[SponsorshipDeliverablePublic])
def list_deliverables(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[SponsorshipDeliverablePublic]:
    rows = deliv_svc.host_list_deliverables(db, user, deal_id)
    return [SponsorshipDeliverablePublic.model_validate(r) for r in rows]


@router.patch(
    "/{deal_id}/deliverables/{deliverable_id}",
    response_model=SponsorshipDeliverablePublic,
)
def patch_deliverable(
    deal_id: UUID,
    deliverable_id: UUID,
    payload: HostDeliverablePatch,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDeliverablePublic:
    return SponsorshipDeliverablePublic.model_validate(
        deliv_svc.host_patch_deliverable(db, user, deal_id, deliverable_id, payload)
    )


@router.post(
    "/{deal_id}/deliverables/{deliverable_id}/submit",
    response_model=SponsorshipDeliverablePublic,
)
def submit_deliverable(
    deal_id: UUID,
    deliverable_id: UUID,
    payload: HostDeliverableSubmit,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDeliverablePublic:
    return SponsorshipDeliverablePublic.model_validate(
        deliv_svc.host_submit_deliverable(
            db, user, deal_id, deliverable_id, payload
        )
    )
