"""Sponsorship marketplace API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_current_user_optional, require_permission
from app.core.database import get_db
from app.sponsorships.schemas import (
    HostSponsorshipSettingsPublic,
    HostSponsorshipSettingsUpdate,
    SponsorHostPublic,
    SponsorshipAnalyticsPublic,
    SponsorshipInquiryCreate,
    SponsorshipInquiryPublic,
    SponsorshipInquiryUpdate,
    SponsorshipModerateRequest,
    SponsorshipPlacementCreate,
    SponsorshipPlacementPublic,
    SponsorshipSlotCreate,
    SponsorshipSlotPublic,
    SponsorshipSlotUpdate,
)
from app.sponsorships.service import (
    create_placement,
    create_slot,
    get_host_settings,
    get_public_slot,
    list_admin_slots,
    list_host_inquiries,
    list_host_placements,
    list_host_slots,
    list_public_slots,
    list_sponsor_hosts,
    moderate_slot,
    record_placement_click,
    record_placement_impression,
    submit_inquiry,
    update_host_settings,
    update_inquiry,
    update_slot,
)
from app.users.models import User

router = APIRouter(prefix="/sponsorships", tags=["sponsorships"])


@router.get("/health")
async def sponsorships_health() -> dict[str, str]:
    return {"module": "sponsorships", "status": "ok"}


# --- Public ---


@router.get("/public/slots", response_model=list[SponsorshipSlotPublic])
def public_slots(db: Annotated[Session, Depends(get_db)]) -> list[SponsorshipSlotPublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            SponsorshipSlotPublic.model_validate(r).model_dump(mode="json")
            for r in list_public_slots(db)
        ]

    cached = get_or_set(
        cache_key("sponsorships", "slots"), CacheTTL.profile, _produce
    )
    return [SponsorshipSlotPublic.model_validate(row) for row in cached]


@router.get("/public/slots/{slot_id}", response_model=SponsorshipSlotPublic)
def public_slot(
    slot_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> SponsorshipSlotPublic:
    from app.core.cache import CacheTTL, cache_get, cache_key, cache_set

    key = cache_key("sponsorships", "slot", str(slot_id))
    hit = cache_get(key)
    if hit is not None:
        return SponsorshipSlotPublic.model_validate(hit)
    payload = SponsorshipSlotPublic.model_validate(get_public_slot(db, slot_id))
    cache_set(key, payload.model_dump(mode="json"), CacheTTL.profile)
    return payload


@router.get("/public/hosts", response_model=list[SponsorHostPublic])
def public_hosts(db: Annotated[Session, Depends(get_db)]) -> list[SponsorHostPublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            SponsorHostPublic.model_validate(r).model_dump(mode="json")
            for r in list_sponsor_hosts(db)
        ]

    cached = get_or_set(
        cache_key("sponsorships", "hosts"), CacheTTL.profile, _produce
    )
    return [SponsorHostPublic.model_validate(row) for row in cached]


@router.post(
    "/public/slots/{slot_id}/inquire",
    response_model=SponsorshipInquiryPublic,
    status_code=201,
)
def public_inquire(
    slot_id: UUID,
    payload: SponsorshipInquiryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> SponsorshipInquiryPublic:
    return SponsorshipInquiryPublic.model_validate(
        submit_inquiry(db, slot_id=slot_id, payload=payload, user=user)
    )


@router.post(
    "/public/placements/{placement_id}/impression",
    response_model=SponsorshipAnalyticsPublic,
)
def public_impression(
    placement_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> SponsorshipAnalyticsPublic:
    return SponsorshipAnalyticsPublic.model_validate(
        record_placement_impression(db, placement_id)
    )


@router.post(
    "/public/placements/{placement_id}/click",
    response_model=SponsorshipAnalyticsPublic,
)
def public_click(
    placement_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> SponsorshipAnalyticsPublic:
    return SponsorshipAnalyticsPublic.model_validate(
        record_placement_click(db, placement_id)
    )


# --- Host ---


@router.get("/host/settings", response_model=HostSponsorshipSettingsPublic)
def host_settings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> HostSponsorshipSettingsPublic:
    return HostSponsorshipSettingsPublic.model_validate(get_host_settings(db, user))


@router.patch("/host/settings", response_model=HostSponsorshipSettingsPublic)
def host_settings_update(
    payload: HostSponsorshipSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> HostSponsorshipSettingsPublic:
    return HostSponsorshipSettingsPublic.model_validate(
        update_host_settings(db, user=user, payload=payload)
    )


@router.get("/host/slots", response_model=list[SponsorshipSlotPublic])
def host_slots(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[SponsorshipSlotPublic]:
    return [SponsorshipSlotPublic.model_validate(r) for r in list_host_slots(db, user)]


@router.post("/host/slots", response_model=SponsorshipSlotPublic, status_code=201)
def host_create_slot(
    payload: SponsorshipSlotCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SponsorshipSlotPublic:
    return SponsorshipSlotPublic.model_validate(
        create_slot(db, user=user, payload=payload)
    )


@router.patch("/host/slots/{slot_id}", response_model=SponsorshipSlotPublic)
def host_update_slot(
    slot_id: UUID,
    payload: SponsorshipSlotUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SponsorshipSlotPublic:
    return SponsorshipSlotPublic.model_validate(
        update_slot(db, user=user, slot_id=slot_id, payload=payload)
    )


@router.get("/host/inquiries", response_model=list[SponsorshipInquiryPublic])
def host_inquiries(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[SponsorshipInquiryPublic]:
    return [
        SponsorshipInquiryPublic.model_validate(r)
        for r in list_host_inquiries(db, user)
    ]


@router.patch("/host/inquiries/{inquiry_id}", response_model=SponsorshipInquiryPublic)
def host_update_inquiry(
    inquiry_id: UUID,
    payload: SponsorshipInquiryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SponsorshipInquiryPublic:
    return SponsorshipInquiryPublic.model_validate(
        update_inquiry(db, user=user, inquiry_id=inquiry_id, payload=payload)
    )


@router.get("/host/placements", response_model=list[SponsorshipPlacementPublic])
def host_placements(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[SponsorshipPlacementPublic]:
    return [
        SponsorshipPlacementPublic.model_validate(r)
        for r in list_host_placements(db, user)
    ]


@router.post(
    "/host/placements", response_model=SponsorshipPlacementPublic, status_code=201
)
def host_create_placement(
    payload: SponsorshipPlacementCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SponsorshipPlacementPublic:
    return SponsorshipPlacementPublic.model_validate(
        create_placement(db, user=user, payload=payload)
    )


# --- Admin ---


@router.get("/admin/slots", response_model=list[SponsorshipSlotPublic])
def admin_slots(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("sponsorships.moderate", "admin.full_access")),
    ],
) -> list[SponsorshipSlotPublic]:
    return [SponsorshipSlotPublic.model_validate(r) for r in list_admin_slots(db, user)]


@router.post("/admin/slots/{slot_id}/moderate", response_model=SponsorshipSlotPublic)
def admin_moderate(
    slot_id: UUID,
    payload: SponsorshipModerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("sponsorships.moderate", "admin.full_access")),
    ],
) -> SponsorshipSlotPublic:
    return SponsorshipSlotPublic.model_validate(
        moderate_slot(db, user=user, slot_id=slot_id, payload=payload)
    )
