"""Sponsor saved items API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.sponsor_profiles import saved_service as svc
from app.sponsor_profiles.saved_schemas import (
    SponsorSavedItemCreate,
    SponsorSavedItemNoteUpdate,
    SponsorSavedItemPublic,
    SponsorSavedListPublic,
)

router = APIRouter(prefix="/sponsors/workspaces", tags=["sponsor-saved"])


@router.get("/{sponsor_id}/saved", response_model=SponsorSavedListPublic)
def list_saved(
    sponsor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    item_type: str | None = None,
    sort: str = Query(default="newest", pattern="^(newest|event_date|host_name)$"),
) -> SponsorSavedListPublic:
    data = svc.list_saved_items(
        db, user=user, sponsor_id=sponsor_id, item_type=item_type, sort=sort
    )
    return SponsorSavedListPublic(
        items=[SponsorSavedItemPublic.model_validate(i) for i in data["items"]],
        total=data["total"],
        saved_count=data["saved_count"],
    )


@router.post(
    "/{sponsor_id}/saved",
    response_model=SponsorSavedItemPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_saved(
    sponsor_id: UUID,
    payload: SponsorSavedItemCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorSavedItemPublic:
    row = svc.create_saved_item(
        db, user=user, sponsor_id=sponsor_id, payload=payload
    )
    return SponsorSavedItemPublic.model_validate(row)


@router.patch(
    "/{sponsor_id}/saved/{saved_id}",
    response_model=SponsorSavedItemPublic,
)
def patch_saved(
    sponsor_id: UUID,
    saved_id: UUID,
    payload: SponsorSavedItemNoteUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorSavedItemPublic:
    row = svc.update_saved_note(
        db,
        user=user,
        sponsor_id=sponsor_id,
        saved_id=saved_id,
        payload=payload,
    )
    return SponsorSavedItemPublic.model_validate(row)


@router.delete(
    "/{sponsor_id}/saved/{saved_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_saved(
    sponsor_id: UUID,
    saved_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    svc.delete_saved_item(db, user=user, sponsor_id=sponsor_id, saved_id=saved_id)
