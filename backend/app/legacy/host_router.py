"""Host Legacy Content Studio API — /api/v1/host/legacy*."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.legacy.schemas import (
    LegacyContentBlockCreate,
    LegacyContentBlockPublic,
    LegacyContentBlockReorder,
    LegacyContentBlockUpdate,
    LegacyFeaturedItemPublic,
    LegacyFeaturedItemUpsert,
    LegacyPagePublic,
    LegacyProfileUpdate,
)
from app.legacy.studio import (
    clear_featured_placement,
    create_block,
    delete_block,
    get_host_legacy_studio,
    list_blocks,
    list_featured,
    reorder_blocks,
    toggle_block,
    update_block,
    update_legacy_studio,
    upsert_featured,
)
from app.hosts.service import require_user_host

router = APIRouter(prefix="/host/legacy", tags=["legacy-studio"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("", response_model=LegacyPagePublic)
def get_host_legacy(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyPagePublic:
    return LegacyPagePublic.model_validate(get_host_legacy_studio(db, user))


@router.patch("", response_model=LegacyPagePublic)
def patch_host_legacy(
    payload: LegacyProfileUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyPagePublic:
    ip, ua = _client_meta(request)
    data = payload.model_dump(exclude_unset=True)
    page = update_legacy_studio(
        db, user=user, payload=data, ip_address=ip, user_agent=ua
    )
    return LegacyPagePublic.model_validate(page)


@router.get("/content-blocks", response_model=list[LegacyContentBlockPublic])
def get_content_blocks(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[LegacyContentBlockPublic]:
    host = require_user_host(db, user)
    return [LegacyContentBlockPublic.model_validate(b) for b in list_blocks(db, host.id)]


@router.post("/content-blocks", response_model=LegacyContentBlockPublic)
def post_content_block(
    payload: LegacyContentBlockCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyContentBlockPublic:
    ip, ua = _client_meta(request)
    block = create_block(
        db,
        user=user,
        payload=payload.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return LegacyContentBlockPublic.model_validate(block)


@router.patch("/content-blocks/{block_id}", response_model=LegacyContentBlockPublic)
def patch_content_block(
    block_id: UUID,
    payload: LegacyContentBlockUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyContentBlockPublic:
    ip, ua = _client_meta(request)
    block = update_block(
        db,
        user=user,
        block_id=block_id,
        payload=payload.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return LegacyContentBlockPublic.model_validate(block)


@router.post("/content-blocks/reorder", response_model=list[LegacyContentBlockPublic])
def post_reorder_blocks(
    payload: LegacyContentBlockReorder,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[LegacyContentBlockPublic]:
    ip, ua = _client_meta(request)
    blocks = reorder_blocks(
        db,
        user=user,
        ordered_ids=payload.ordered_ids,
        ip_address=ip,
        user_agent=ua,
    )
    return [LegacyContentBlockPublic.model_validate(b) for b in blocks]


@router.post("/content-blocks/{block_id}/toggle", response_model=LegacyContentBlockPublic)
def post_toggle_block(
    block_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyContentBlockPublic:
    ip, ua = _client_meta(request)
    block = toggle_block(
        db, user=user, block_id=block_id, ip_address=ip, user_agent=ua
    )
    return LegacyContentBlockPublic.model_validate(block)


@router.delete("/content-blocks/{block_id}", status_code=204)
def remove_content_block(
    block_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    ip, ua = _client_meta(request)
    delete_block(db, user=user, block_id=block_id, ip_address=ip, user_agent=ua)


@router.get("/featured-items", response_model=list[LegacyFeaturedItemPublic])
def get_featured_items(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[LegacyFeaturedItemPublic]:
    host = require_user_host(db, user)
    return [LegacyFeaturedItemPublic.model_validate(f) for f in list_featured(db, host.id)]


@router.post("/featured-items", response_model=LegacyFeaturedItemPublic)
def post_featured_item(
    payload: LegacyFeaturedItemUpsert,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyFeaturedItemPublic:
    ip, ua = _client_meta(request)
    item = upsert_featured(
        db,
        user=user,
        payload=payload.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return LegacyFeaturedItemPublic.model_validate(item)


@router.delete("/featured-items/{placement}", status_code=204)
def remove_featured_placement(
    placement: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    ip, ua = _client_meta(request)
    clear_featured_placement(
        db, user=user, placement=placement, ip_address=ip, user_agent=ua
    )
