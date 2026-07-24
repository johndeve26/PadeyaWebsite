"""Admin sponsorship deals and invoices API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.sponsorships import deals_service as svc
from app.sponsorships import deliverables_service as deliv_svc
from app.sponsorships.deals_schemas import SponsorshipDealPublic
from app.sponsorships.deliverables_schemas import (
    AdminDeliverablePatch,
    SponsorshipDeliverablePublic,
)
from app.users.models import User

deals_router = APIRouter(prefix="/admin/sponsorship-deals", tags=["admin-sponsorship-deals"])
invoices_router = APIRouter(
    prefix="/admin/sponsorship-invoices", tags=["admin-sponsorship-invoices"]
)


@deals_router.get("", response_model=list[SponsorshipDealPublic])
def admin_list(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsorship_deals.view"))],
) -> list[SponsorshipDealPublic]:
    rows = svc.admin_list_deals(db)
    return [SponsorshipDealPublic.model_validate(r) for r in rows]


@deals_router.get("/{deal_id}", response_model=SponsorshipDealPublic)
def admin_detail(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsorship_deals.view"))],
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(svc.admin_get_deal(db, deal_id))


@deals_router.post("/{deal_id}/cancel", response_model=SponsorshipDealPublic)
def admin_cancel(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsorship_deals.manage"))],
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(
        svc.admin_cancel_deal(db, actor, deal_id)
    )


@deals_router.get(
    "/{deal_id}/deliverables",
    response_model=list[SponsorshipDeliverablePublic],
)
def admin_list_deliverables(
    deal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsorship_deals.view"))],
) -> list[SponsorshipDeliverablePublic]:
    rows = deliv_svc.admin_list_deliverables(db, deal_id)
    return [SponsorshipDeliverablePublic.model_validate(r) for r in rows]


@deals_router.patch(
    "/{deal_id}/deliverables/{deliverable_id}",
    response_model=SponsorshipDeliverablePublic,
)
def admin_patch_deliverable(
    deal_id: UUID,
    deliverable_id: UUID,
    payload: AdminDeliverablePatch,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsorship_deals.manage"))],
) -> SponsorshipDeliverablePublic:
    return SponsorshipDeliverablePublic.model_validate(
        deliv_svc.admin_patch_deliverable(
            db, actor, deal_id, deliverable_id, payload
        )
    )


@invoices_router.post("/{invoice_id}/void", response_model=SponsorshipDealPublic)
def admin_void_invoice(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsorship_deals.finance"))],
) -> SponsorshipDealPublic:
    return SponsorshipDealPublic.model_validate(
        svc.admin_void_invoice(db, actor, invoice_id)
    )
