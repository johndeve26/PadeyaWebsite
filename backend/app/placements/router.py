"""Admin routes for Featured Placement Slots (Pàdéyá Picks)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.placements import service as placements_service
from app.placements.constants import CONTEXT_EVENTS
from app.placements.schemas import (
    FeaturedPlacementAssign,
    FeaturedPlacementContextPublic,
    FeaturedPlacementSetStatusUpdate,
    FeaturedPlacementSetUpsert,
    FeaturedPlacementSlotPublic,
    ListingPadeyaPickClearRequest,
    ListingPadeyaPickRequest,
    ListingPadeyaPickSwapRequest,
)
from app.users.models import User

router = APIRouter(tags=["placements"])

_ADMIN = Depends(require_permission("admin.full_access", "events.approve"))


@router.get(
    "/admin/featured-placements/contexts",
    response_model=list[FeaturedPlacementContextPublic],
)
def admin_list_contexts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    include_archived: Annotated[bool, Query()] = False,
) -> list[FeaturedPlacementContextPublic]:
    return [
        FeaturedPlacementContextPublic.model_validate(row)
        for row in placements_service.list_configured_contexts(
            db, include_archived=include_archived
        )
    ]


@router.get(
    "/admin/featured-placements/sets/{set_id}",
    response_model=FeaturedPlacementContextPublic,
)
def admin_get_set(
    set_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
) -> FeaturedPlacementContextPublic:
    return FeaturedPlacementContextPublic.model_validate(
        placements_service.get_set_by_id(db, set_id)
    )


@router.put(
    "/admin/featured-placements/sets",
    response_model=FeaturedPlacementContextPublic,
)
def admin_upsert_set(
    payload: FeaturedPlacementSetUpsert,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> FeaturedPlacementContextPublic:
    return FeaturedPlacementContextPublic.model_validate(
        placements_service.upsert_placement_set(
            db,
            user=user,
            context_type=payload.context_type,
            location_id=payload.location_id,
            category_id=payload.category_id,
            slot_1_event_id=payload.slot_1.event_id,
            slot_2_event_id=payload.slot_2.event_id,
            title_override=payload.title_override,
            subtitle_override=payload.subtitle_override,
            badge_text=payload.badge_text,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            status=payload.status,
        )
    )


@router.post(
    "/admin/featured-placements/sets/{set_id}/status",
    response_model=FeaturedPlacementContextPublic,
)
def admin_set_status(
    set_id: UUID,
    payload: FeaturedPlacementSetStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> FeaturedPlacementContextPublic:
    return FeaturedPlacementContextPublic.model_validate(
        placements_service.update_set_status(
            db, user=user, set_id=set_id, status=payload.status
        )
    )


@router.get(
    "/admin/featured-placements",
    response_model=list[FeaturedPlacementSlotPublic],
)
def admin_list_slots(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    context_type: Annotated[str, Query()] = CONTEXT_EVENTS,
    location_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
) -> list[FeaturedPlacementSlotPublic]:
    slots = placements_service.list_slots_for_context(
        db,
        context_type=context_type,
        location_id=location_id,
        category_id=category_id,
    )
    return [
        FeaturedPlacementSlotPublic.model_validate(
            placements_service.slot_to_public(db, s)
        )
        for s in slots
    ]


@router.put(
    "/admin/featured-placements/{slot_index}",
    response_model=FeaturedPlacementSlotPublic,
)
def admin_assign_slot(
    slot_index: int,
    payload: FeaturedPlacementAssign,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> FeaturedPlacementSlotPublic:
    slot = placements_service.assign_slot(
        db,
        user=user,
        slot_index=slot_index,
        context_type=payload.context_type,
        location_id=payload.location_id,
        category_id=payload.category_id,
        event_id=payload.event_id,
        title_override=payload.title_override,
        subtitle_override=payload.subtitle_override,
        badge_text=payload.badge_text,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=payload.status,
    )
    return FeaturedPlacementSlotPublic.model_validate(
        placements_service.slot_to_public(db, slot)
    )


@router.post(
    "/admin/featured-placements/listing-picks",
    response_model=FeaturedPlacementSlotPublic,
)
def admin_set_listing_padeya_pick(
    payload: ListingPadeyaPickRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> FeaturedPlacementSlotPublic:
    """Assign a published listing into homepage/events_page Pàdéyá Picks."""
    slot = placements_service.set_event_as_padeya_pick(
        db,
        user=user,
        event_id=payload.event_id,
        context_type=payload.context_type,
        slot_number=payload.slot_number,
    )
    return FeaturedPlacementSlotPublic.model_validate(
        placements_service.slot_to_public(db, slot)
    )


@router.post(
    "/admin/featured-placements/listing-picks/clear",
    response_model=list[FeaturedPlacementSlotPublic],
)
def admin_clear_listing_padeya_pick(
    payload: ListingPadeyaPickClearRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> list[FeaturedPlacementSlotPublic]:
    """Remove a listing from homepage/events_page Pàdéyá Picks."""
    cleared = placements_service.clear_event_padeya_pick(
        db,
        user=user,
        event_id=payload.event_id,
        context_type=payload.context_type,
    )
    return [
        FeaturedPlacementSlotPublic.model_validate(
            placements_service.slot_to_public(db, slot)
        )
        for slot in cleared
    ]


@router.post(
    "/admin/featured-placements/listing-picks/swap",
    response_model=list[FeaturedPlacementSlotPublic],
)
def admin_swap_listing_padeya_picks(
    payload: ListingPadeyaPickSwapRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> list[FeaturedPlacementSlotPublic]:
    """Swap Primary and Secondary listing picks for a global context."""
    slots = placements_service.swap_padeya_pick_slots(
        db, user=user, context_type=payload.context_type
    )
    return [
        FeaturedPlacementSlotPublic.model_validate(
            placements_service.slot_to_public(db, slot)
        )
        for slot in slots
    ]
