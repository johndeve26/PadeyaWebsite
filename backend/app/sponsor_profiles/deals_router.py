"""Sponsor workspace deals API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.sponsorships import deals_service as svc
from app.sponsorships import deliverables_service as deliv_svc
from app.sponsorships.deals_schemas import (
    SponsorshipDealPayResponse,
    SponsorshipDealPublic,
)
from app.sponsorships.deliverables_schemas import (
    SponsorDeliverableReject,
    SponsorshipDeliverablePublic,
)

router = APIRouter(prefix="/sponsors/workspaces", tags=["sponsor-deals"])


@router.get("/{sponsor_id}/deals", response_model=list[SponsorshipDealPublic])
def list_deals(
    sponsor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[SponsorshipDealPublic]:
    rows = svc.sponsor_list_deals(db, user, sponsor_id)
    return [SponsorshipDealPublic.model_validate(r) for r in rows]


@router.get("/{sponsor_id}/deals/{deal_id}", response_model=SponsorshipDealPublic)
def get_deal(
    sponsor_id: UUID,
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(
        svc.sponsor_get_deal(db, user, sponsor_id, deal_id)
    )


@router.post("/{sponsor_id}/deals/{deal_id}/accept", response_model=SponsorshipDealPublic)
def accept_deal(
    sponsor_id: UUID,
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(
        svc.sponsor_accept_deal(db, user, sponsor_id, deal_id)
    )


@router.post("/{sponsor_id}/deals/{deal_id}/reject", response_model=SponsorshipDealPublic)
def reject_deal(
    sponsor_id: UUID,
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(
        svc.sponsor_reject_deal(db, user, sponsor_id, deal_id)
    )


@router.post("/{sponsor_id}/deals/{deal_id}/pay", response_model=SponsorshipDealPayResponse)
def pay_deal(
    sponsor_id: UUID,
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDealPayResponse:
    return SponsorshipDealPayResponse.model_validate(
        svc.sponsor_pay_deal(db, user, sponsor_id, deal_id)
    )


@router.get(
    "/{sponsor_id}/deals/{deal_id}/deliverables",
    response_model=list[SponsorshipDeliverablePublic],
)
def list_deliverables(
    sponsor_id: UUID,
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[SponsorshipDeliverablePublic]:
    rows = deliv_svc.sponsor_list_deliverables(db, user, sponsor_id, deal_id)
    return [SponsorshipDeliverablePublic.model_validate(r) for r in rows]


@router.post(
    "/{sponsor_id}/deals/{deal_id}/deliverables/{deliverable_id}/approve",
    response_model=SponsorshipDeliverablePublic,
)
def approve_deliverable(
    sponsor_id: UUID,
    deal_id: UUID,
    deliverable_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDeliverablePublic:
    return SponsorshipDeliverablePublic.model_validate(
        deliv_svc.sponsor_approve_deliverable(
            db, user, sponsor_id, deal_id, deliverable_id
        )
    )


@router.post(
    "/{sponsor_id}/deals/{deal_id}/deliverables/{deliverable_id}/reject",
    response_model=SponsorshipDeliverablePublic,
)
def reject_deliverable(
    sponsor_id: UUID,
    deal_id: UUID,
    deliverable_id: UUID,
    payload: SponsorDeliverableReject,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorshipDeliverablePublic:
    return SponsorshipDeliverablePublic.model_validate(
        deliv_svc.sponsor_reject_deliverable(
            db, user, sponsor_id, deal_id, deliverable_id, payload
        )
    )
