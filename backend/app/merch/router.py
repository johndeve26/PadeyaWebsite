"""Event-linked merchandise API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.merch import admin_service
from app.merch import fulfillment as fulfillment_service
from app.merch import service as merch_service
from app.merch.schemas import (
    MerchAdminOrderPublic,
    MerchAdminProductPublic,
    MerchCatalogProduct,
    MerchDeactivateUnsafeRequest,
    MerchFulfillmentNoteCreate,
    MerchFulfillmentPublic,
    MerchFulfillStatusUpdate,
    MerchHostEventStats,
    MerchModerateRequest,
    MerchProductCreate,
    MerchProductPublic,
    MerchProductUpdate,
    MerchReportCreate,
    MerchReportPublic,
    MerchReportResolve,
    MerchReportUpdate,
    MerchVariantCreate,
    MerchVariantPublic,
    MerchVariantUpdate,
)
from app.users.models import User

router = APIRouter(prefix="/merch", tags=["merch"])


@router.get("/health")
async def merch_module_health() -> dict[str, str]:
    return {"module": "merch", "status": "ok"}


@router.get("/events/{event_id}/catalog", response_model=list[MerchCatalogProduct])
def public_catalog(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> list[dict]:
    return merch_service.get_public_catalog(
        db, event_id=event_id, buyer_user_id=user.id if user else None
    )


@router.get("/host/products", response_model=list[MerchProductPublic])
def list_all_host_products(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return merch_service.list_all_host_products(db, user=user)


@router.get("/products/{product_id}", response_model=MerchProductPublic)
def get_product(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.get_host_product(db, user=user, product_id=product_id)


@router.get("/events/{event_id}/products", response_model=list[MerchProductPublic])
def list_products(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return merch_service.list_host_products(db, user=user, event_id=event_id)


@router.post("/events/{event_id}/products", response_model=MerchProductPublic)
def create_product(
    event_id: UUID,
    payload: MerchProductCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.create_product(db, user=user, event_id=event_id, payload=payload)


@router.patch("/products/{product_id}", response_model=MerchProductPublic)
def update_product(
    product_id: UUID,
    payload: MerchProductUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.update_product(db, user=user, product_id=product_id, payload=payload)


@router.post("/products/{product_id}/archive", response_model=MerchProductPublic)
def archive_product(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.archive_product(db, user=user, product_id=product_id)


@router.post("/products/{product_id}/duplicate", response_model=MerchProductPublic)
def duplicate_product(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.duplicate_product(db, user=user, product_id=product_id)


@router.get(
    "/host/events/{event_id}/stats",
    response_model=MerchHostEventStats,
)
def host_event_merch_stats(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.get_host_event_merch_stats(db, user=user, event_id=event_id)


@router.post("/products/{product_id}/variants", response_model=MerchVariantPublic)
def create_variant(
    product_id: UUID,
    payload: MerchVariantCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.create_variant(db, user=user, product_id=product_id, payload=payload)


@router.patch("/variants/{variant_id}", response_model=MerchVariantPublic)
def update_variant(
    variant_id: UUID,
    payload: MerchVariantUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.update_variant(db, user=user, variant_id=variant_id, payload=payload)


@router.post("/variants/{variant_id}/archive", response_model=MerchVariantPublic)
def archive_variant(
    variant_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.archive_variant(db, user=user, variant_id=variant_id)


@router.get(
    "/host/events/{event_id}/fulfillments",
    response_model=list[MerchFulfillmentPublic],
)
def host_fulfillments(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict]:
    return fulfillment_service.list_host_fulfillments(
        db, user=user, event_id=event_id, status_filter=status, q=q
    )


@router.post("/fulfillments/{fulfillment_id}/fulfill", response_model=MerchFulfillmentPublic)
def fulfill(
    fulfillment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return fulfillment_service.mark_fulfilled(db, user=user, fulfillment_id=fulfillment_id)


@router.post(
    "/fulfillments/{fulfillment_id}/notes",
    response_model=MerchFulfillmentPublic,
)
def add_fulfillment_note(
    fulfillment_id: UUID,
    payload: MerchFulfillmentNoteCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return fulfillment_service.add_fulfillment_note(
        db, user=user, fulfillment_id=fulfillment_id, note=payload.note
    )


@router.patch("/fulfillments/{fulfillment_id}", response_model=MerchFulfillmentPublic)
def patch_fulfillment(
    fulfillment_id: UUID,
    payload: MerchFulfillStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return fulfillment_service.update_fulfillment_status(
        db, user=user, fulfillment_id=fulfillment_id, status=payload.status
    )


@router.get("/mine", response_model=list[MerchFulfillmentPublic])
def my_merch(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return fulfillment_service.list_buyer_fulfillments(db, user=user)


@router.post("/products/{product_id}/report", response_model=MerchReportPublic)
def report_product(
    product_id: UUID,
    payload: MerchReportCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return admin_service.create_product_report(
        db,
        user=user,
        product_id=product_id,
        reason=payload.reason,
        details=payload.details,
    )


@router.get("/admin/products", response_model=list[MerchAdminProductPublic])
def admin_list_products(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "merch.moderate", "admin.full_access"))
    ],
    moderation_status: str | None = None,
    status: str | None = None,
    event_id: UUID | None = None,
    host_id: UUID | None = None,
    q: str | None = None,
    is_sponsor_branded: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    return admin_service.list_admin_products(
        db,
        user=user,
        moderation_status=moderation_status,
        status=status,
        event_id=event_id,
        host_id=host_id,
        q=q,
        is_sponsor_branded=is_sponsor_branded,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin/products/{product_id}",
    response_model=MerchAdminProductPublic,
)
def admin_get_product(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "merch.moderate", "admin.full_access"))
    ],
) -> dict:
    return admin_service.get_admin_product(db, user=user, product_id=product_id)


@router.post("/admin/products/{product_id}/moderate", response_model=MerchAdminProductPublic)
def admin_moderate_product(
    product_id: UUID,
    payload: MerchModerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
) -> dict:
    return admin_service.moderate_product(
        db,
        user=user,
        product_id=product_id,
        action=payload.action,
        note=payload.note,
    )


@router.post(
    "/admin/products/{product_id}/deactivate-unsafe",
    response_model=MerchAdminProductPublic,
)
def admin_deactivate_unsafe(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
    payload: MerchDeactivateUnsafeRequest | None = None,
) -> dict:
    return admin_service.deactivate_unsafe_product(
        db,
        user=user,
        product_id=product_id,
        note=payload.note if payload else None,
    )


@router.get("/admin/orders", response_model=list[MerchAdminOrderPublic])
def admin_list_orders(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "merch.moderate", "admin.full_access"))
    ],
    status: str | None = None,
    issues: bool = Query(default=False),
    event_id: UUID | None = None,
    host_id: UUID | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    return admin_service.list_admin_orders(
        db,
        user=user,
        status=status,
        issues_only=issues,
        event_id=event_id,
        host_id=host_id,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/reports", response_model=list[MerchReportPublic])
def admin_list_reports(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.view_admin", "merch.moderate", "admin.full_access"))
    ],
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    return admin_service.list_admin_reports(
        db, user=user, status=status, limit=limit, offset=offset
    )


@router.patch("/admin/reports/{report_id}", response_model=MerchReportPublic)
def admin_update_report(
    report_id: UUID,
    payload: MerchReportUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
) -> dict:
    return admin_service.update_report(
        db,
        user=user,
        report_id=report_id,
        status=payload.status,
        admin_notes=payload.admin_notes,
    )


@router.post("/admin/reports/{report_id}/resolve", response_model=MerchReportPublic)
def admin_resolve_report(
    report_id: UUID,
    payload: MerchReportResolve,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
) -> dict:
    return admin_service.resolve_report(
        db,
        user=user,
        report_id=report_id,
        resolution=payload.resolution,
        note=payload.note,
        admin_notes=payload.admin_notes,
        moderate_action=payload.moderate_action,
    )
