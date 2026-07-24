"""Thin path aliases for merch — delegates to existing merch services.

Keeps `/api/v1/merch/*` working. Preferred REST-shaped paths for host/public/buyer/admin.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.merch import admin_service
from app.merch import fulfillment as fulfillment_service
from app.merch import service as merch_service
from app.merch.schemas import (
    MerchAdminProductPublic,
    MerchCatalogProduct,
    MerchFulfillmentPublic,
    MerchProductCreate,
    MerchProductPublic,
    MerchProductUpdate,
)
from app.users.models import User

router = APIRouter(tags=["merchandise-aliases"])


# --- Host catalog ---


@router.get(
    "/host/events/{event_id}/merchandise",
    response_model=list[MerchProductPublic],
)
def host_list_merchandise(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return merch_service.list_host_products(db, user=user, event_id=event_id)


@router.post(
    "/host/events/{event_id}/merchandise",
    response_model=MerchProductPublic,
)
def host_create_merchandise(
    event_id: UUID,
    payload: MerchProductCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.create_product(
        db, user=user, event_id=event_id, payload=payload
    )


@router.get(
    "/host/events/{event_id}/merchandise/orders",
    response_model=list[MerchFulfillmentPublic],
)
def host_merchandise_orders(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict]:
    return fulfillment_service.list_host_fulfillments(
        db, user=user, event_id=event_id, status_filter=status, q=q
    )


@router.get(
    "/host/events/{event_id}/merchandise/{product_id}",
    response_model=MerchProductPublic,
)
def host_get_merchandise(
    event_id: UUID,
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    product = merch_service.get_host_product(db, user=user, product_id=product_id)
    if str(product.get("event_id")) != str(event_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch(
    "/host/events/{event_id}/merchandise/{product_id}",
    response_model=MerchProductPublic,
)
def host_update_merchandise(
    event_id: UUID,
    product_id: UUID,
    payload: MerchProductUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    product = merch_service.get_host_product(db, user=user, product_id=product_id)
    if str(product.get("event_id")) != str(event_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return merch_service.update_product(
        db, user=user, product_id=product_id, payload=payload
    )


@router.patch(
    "/host/events/{event_id}/merchandise/{product_id}/pause",
    response_model=MerchProductPublic,
)
def host_pause_merchandise(
    event_id: UUID,
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    product = merch_service.get_host_product(db, user=user, product_id=product_id)
    if str(product.get("event_id")) != str(event_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return merch_service.update_product(
        db,
        user=user,
        product_id=product_id,
        payload=MerchProductUpdate(status="paused"),
    )


@router.patch(
    "/host/events/{event_id}/merchandise/{product_id}/archive",
    response_model=MerchProductPublic,
)
def host_archive_merchandise(
    event_id: UUID,
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    product = merch_service.get_host_product(db, user=user, product_id=product_id)
    if str(product.get("event_id")) != str(event_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return merch_service.archive_product(db, user=user, product_id=product_id)


@router.patch(
    "/host/merchandise/order-items/{item_id}/ready",
    response_model=MerchFulfillmentPublic,
)
def host_order_item_ready(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    fulfillment_id = fulfillment_service.resolve_host_fulfillment_id(
        db, user=user, item_id=item_id
    )
    return fulfillment_service.update_fulfillment_status(
        db, user=user, fulfillment_id=fulfillment_id, status="collect_at_stand"
    )


@router.patch(
    "/host/merchandise/order-items/{item_id}/picked-up",
    response_model=MerchFulfillmentPublic,
)
def host_order_item_picked_up(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    fulfillment_id = fulfillment_service.resolve_host_fulfillment_id(
        db, user=user, item_id=item_id
    )
    return fulfillment_service.mark_fulfilled(
        db, user=user, fulfillment_id=fulfillment_id
    )


# --- Public catalog by event slug ---


@router.get(
    "/events/{event_slug}/merchandise",
    response_model=list[MerchCatalogProduct],
)
def public_event_merchandise(
    event_slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> list[dict]:
    return merch_service.get_public_catalog_by_slug(
        db, event_slug=event_slug, buyer_user_id=user.id if user else None
    )


@router.get(
    "/events/{event_slug}/merchandise/{product_slug}",
    response_model=MerchCatalogProduct,
)
def public_event_merchandise_product(
    event_slug: str,
    product_slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> dict:
    return merch_service.get_public_catalog_product_by_slug(
        db,
        event_slug=event_slug,
        product_slug=product_slug,
        buyer_user_id=user.id if user else None,
    )


# --- Buyer dashboard ---


@router.get("/dashboard/merchandise", response_model=list[MerchFulfillmentPublic])
def buyer_merchandise(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return fulfillment_service.list_buyer_fulfillments(db, user=user)


@router.get("/dashboard/merchandise/post-event-drops")
def buyer_eligible_post_event_drops_alias(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    """Static path must stay above /dashboard/merchandise/{item_id}."""
    from app.merch import post_event_drops as drops_svc

    return drops_svc.list_buyer_eligible_drops(db, buyer_user_id=user.id)


@router.get(
    "/dashboard/merchandise/{item_id}",
    response_model=MerchFulfillmentPublic,
)
def buyer_merchandise_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return fulfillment_service.get_buyer_fulfillment(db, user=user, item_id=item_id)


# --- Admin ---


@router.get("/admin/merchandise", response_model=list[MerchAdminProductPublic])
def admin_merchandise(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "merch.view_admin", "merch.moderate", "admin.full_access"
            )
        ),
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


@router.patch(
    "/admin/merchandise/{product_id}/hide",
    response_model=MerchAdminProductPublic,
)
def admin_merchandise_hide(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
) -> dict:
    return admin_service.moderate_product(
        db, user=user, product_id=product_id, action="hide", note="Hidden via admin"
    )


@router.patch(
    "/admin/merchandise/{product_id}/restore",
    response_model=MerchAdminProductPublic,
)
def admin_merchandise_restore(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("merch.moderate", "admin.full_access"))
    ],
) -> dict:
    return admin_service.moderate_product(
        db,
        user=user,
        product_id=product_id,
        action="restore",
        note="Restored via admin",
    )
