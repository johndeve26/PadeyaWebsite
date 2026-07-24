"""Public merch marketplace routes + host/admin marketplace aliases."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.merch import marketplace as marketplace_svc
from app.merch import service as merch_service
from app.merch.schemas import MerchProductCreate, MerchProductPublic
from app.users.models import User

router = APIRouter(tags=["merch-marketplace"])


class CategoryUpsertIn(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int = 0
    status: str = "active"


# --- Public marketplace ---


@router.get("/merch")
def marketplace_list(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    q: str | None = None,
    host: str | None = None,
    event: str | None = None,
    category: str | None = None,
    merch_type: str | None = Query(default=None, alias="type"),
    fulfillment_type: str | None = None,
    availability: str | None = None,
    city: str | None = None,
    vault_only: bool = False,
    drops_only: bool = False,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    sort: str = "featured",
    limit: int = Query(default=48, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return marketplace_svc.list_marketplace_products(
        db,
        buyer_user_id=user.id if user else None,
        q=q,
        host=host,
        event=event,
        category=category,
        merch_kind=merch_type,
        fulfillment_type=fulfillment_type,
        availability=availability,
        city=city,
        vault_only=vault_only,
        drops_only=drops_only,
        price_min=price_min,
        price_max=price_max,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/merch/home")
def marketplace_home(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> dict[str, Any]:
    return marketplace_svc.get_marketplace_homepage(
        db, buyer_user_id=user.id if user else None
    )


@router.get("/merch/drops")
def marketplace_drops(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    limit: int = Query(default=48, ge=1, le=100),
) -> dict[str, Any]:
    return marketplace_svc.list_marketplace_drops(
        db, buyer_user_id=user.id if user else None, limit=limit
    )


@router.get("/merch/vault")
def marketplace_vault(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    limit: int = Query(default=48, ge=1, le=100),
) -> dict[str, Any]:
    return marketplace_svc.list_marketplace_vault(
        db, buyer_user_id=user.id if user else None, limit=limit
    )


@router.get("/merch/categories")
def marketplace_categories(
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    return marketplace_svc.list_marketplace_categories(db)


@router.get("/merch/hosts")
def marketplace_host_shops(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=24, ge=1, le=60),
) -> list[dict[str, Any]]:
    return marketplace_svc.list_marketplace_host_shops(db, limit=limit)


@router.get("/merch/hosts/{username}")
def marketplace_host_shop(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    product_type: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    return marketplace_svc.get_marketplace_host_shop(
        db,
        username=username,
        buyer_user_id=user.id if user else None,
        product_type=product_type,
        kind=kind,
    )


@router.get("/merch/item/{slug}")
def marketplace_product_by_slug(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    h: str | None = Query(default=None, description="Optional host slug disambiguator"),
) -> dict[str, Any]:
    return marketplace_svc.get_marketplace_product_by_slug(
        db, slug=slug, host_slug=h, buyer_user_id=user.id if user else None
    )


# Preferred public alias matching product brief (after static paths above).
@router.get("/merch/{slug}")
def marketplace_product_slug_alias(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    h: str | None = Query(default=None),
) -> dict[str, Any]:
    reserved = {
        "home",
        "drops",
        "vault",
        "hosts",
        "categories",
        "item",
        "health",
        "mine",
        "admin",
        "host",
        "products",
        "events",
        "me",
        "size-charts",
        "discounts",
    }
    if slug in reserved:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Merch not found")
    return marketplace_svc.get_marketplace_product_by_slug(
        db, slug=slug, host_slug=h, buyer_user_id=user.id if user else None
    )


@router.get("/events/{slug}/merch")
def event_merch_by_slug(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> dict[str, Any]:
    return marketplace_svc.get_event_merch_by_slug(
        db, event_slug=slug, buyer_user_id=user.id if user else None
    )


# --- Host standalone create + publish ---


@router.get("/host/merch", response_model=list[MerchProductPublic])
def host_list_merch(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return merch_service.list_all_host_products(db, user=user)


@router.post("/host/merch", response_model=MerchProductPublic)
def host_create_standalone_merch(
    payload: MerchProductCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.create_standalone_product(db, user=user, payload=payload)


@router.post("/host/merchandise", response_model=MerchProductPublic)
def host_create_standalone_merchandise_alias(
    payload: MerchProductCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.create_standalone_product(db, user=user, payload=payload)


@router.patch("/host/merch/{product_id}", response_model=MerchProductPublic)
def host_patch_merch(
    product_id: UUID,
    payload: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    from app.merch.schemas import MerchProductUpdate

    update = MerchProductUpdate.model_validate(payload)
    return merch_service.update_product(
        db, user=user, product_id=product_id, payload=update
    )


@router.post("/host/merch/{product_id}/publish", response_model=MerchProductPublic)
def host_publish_merch(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    from app.merch.schemas import MerchProductUpdate

    return merch_service.update_product(
        db,
        user=user,
        product_id=product_id,
        payload=MerchProductUpdate(status="active"),
    )


@router.post("/host/merch/{product_id}/archive", response_model=MerchProductPublic)
def host_archive_merch(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return merch_service.archive_product(db, user=user, product_id=product_id)


# --- Admin categories ---


@router.get("/admin/merch/categories")
def admin_list_merch_categories(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("merch.view_admin"))],
) -> list[dict[str, Any]]:
    return marketplace_svc.admin_list_categories(db)


@router.post("/admin/merch/categories")
def admin_upsert_merch_category(
    payload: CategoryUpsertIn,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("merch.moderate"))],
) -> dict[str, Any]:
    return marketplace_svc.admin_upsert_category(
        db,
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        status=payload.status,
    )


@router.patch("/admin/merch/categories/{category_id}")
def admin_patch_merch_category(
    category_id: UUID,
    payload: CategoryUpsertIn,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("merch.moderate"))],
) -> dict[str, Any]:
    return marketplace_svc.admin_upsert_category(
        db,
        category_id=category_id,
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        status=payload.status,
    )
