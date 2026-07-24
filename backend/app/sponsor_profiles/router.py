"""Sponsor profile workspace API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.sponsor_profiles.schemas import (
    SponsorAdminDetail,
    SponsorAdminListItem,
    SponsorAdminNotesUpdate,
    SponsorAdminStatusRequest,
    SponsorAdminVerifyRequest,
    SponsorCreateRequest,
    SponsorDirectoryItem,
    SponsorInquiryOwnPublic,
    SponsorPrivate,
    SponsorProfileUpdate,
    SponsorPublicProfile,
    SponsorWorkspacePublic,
)
from app.sponsor_profiles.public_profile_service import (
    build_directory_item,
    build_public_sponsor_profile,
)
from app.sponsor_profiles.service import (
    admin_get_sponsor,
    admin_list_sponsors,
    admin_set_sponsor_status,
    admin_update_notes,
    admin_verify_sponsor,
    create_sponsor_profile,
    get_public_sponsor_by_slug,
    get_sponsor_by_id,
    list_public_sponsors,
    list_sponsor_inquiries_for_owner,
    list_user_sponsor_workspaces,
    require_sponsor_access,
    serialize_public,
    update_sponsor_profile,
)
from app.users.models import User

router = APIRouter(prefix="/sponsors", tags=["sponsor-profiles"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def _to_private(sponsor) -> SponsorPrivate:
    return SponsorPrivate(
        id=sponsor.id,
        owner_user_id=sponsor.owner_user_id,
        display_name=sponsor.display_name or sponsor.company_name,
        slug=sponsor.slug,
        sponsor_type=sponsor.sponsor_type,
        logo_url=sponsor.logo_url,
        cover_image_url=sponsor.cover_image_url,
        short_bio=sponsor.short_bio,
        description=sponsor.description,
        website_url=sponsor.website_url or sponsor.website,
        industry=sponsor.industry,
        categories=list(sponsor.categories or []),
        target_locations=list(sponsor.target_locations or []),
        budget_range=sponsor.budget_range,
        campaign_goals=list(sponsor.campaign_goals or []),
        contact_email=sponsor.contact_email,
        contact_phone=sponsor.contact_phone,
        verification_status=sponsor.verification_status,
        status=sponsor.status,
        visibility=sponsor.visibility,
        onboarding_status=sponsor.onboarding_status,
        sponsor_ready_score=sponsor.sponsor_ready_score,
        created_at=sponsor.created_at,
        updated_at=sponsor.updated_at,
    )


@router.get("/health")
async def sponsor_profiles_health() -> dict[str, str]:
    return {"module": "sponsor-profiles", "status": "ok"}


@router.get("/workspaces", response_model=list[SponsorWorkspacePublic])
def sponsor_workspaces(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[SponsorWorkspacePublic]:
    rows = list_user_sponsor_workspaces(db, user=user)
    return [SponsorWorkspacePublic.model_validate(r) for r in rows]


@router.post("/profiles", response_model=SponsorPrivate, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: SponsorCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorPrivate:
    ip, ua = _client_meta(request)
    sponsor = create_sponsor_profile(
        db, user=user, payload=payload, ip_address=ip, user_agent=ua
    )
    db.commit()
    db.refresh(sponsor)
    return _to_private(sponsor)


@router.get("/me", response_model=SponsorPrivate)
def get_my_sponsor(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    sponsor_id: UUID | None = None,
) -> SponsorPrivate:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    return _to_private(sponsor)


@router.patch("/me", response_model=SponsorPrivate)
def patch_my_sponsor(
    payload: SponsorProfileUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    sponsor_id: UUID | None = None,
) -> SponsorPrivate:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.edit_own"
    )
    ip, ua = _client_meta(request)
    updated = update_sponsor_profile(
        db, user=user, sponsor_id=sponsor.id, payload=payload, ip_address=ip, user_agent=ua
    )
    db.commit()
    db.refresh(updated)
    return _to_private(updated)


@router.get("/me/inquiries", response_model=list[SponsorInquiryOwnPublic])
def my_inquiries(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    sponsor_id: UUID | None = None,
) -> list[SponsorInquiryOwnPublic]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_inquiries"
    )
    rows = list_sponsor_inquiries_for_owner(db, user=user, sponsor_id=sponsor.id)
    return [SponsorInquiryOwnPublic.model_validate(r) for r in rows]


@router.get("/public/directory", response_model=list[SponsorDirectoryItem])
def public_directory(
    db: Annotated[Session, Depends(get_db)],
    industry: str | None = None,
    category: str | None = None,
    location: str | None = None,
    verified: bool = False,
    sponsor_type: str | None = Query(default=None, alias="type"),
) -> list[SponsorDirectoryItem]:
    rows = list_public_sponsors(
        db,
        industry=industry,
        category=category,
        location=location,
        verified_only=verified,
        sponsor_type=sponsor_type,
    )
    return [
        SponsorDirectoryItem.model_validate(build_directory_item(db, s))
        for s in rows
        if s.slug
    ]


@router.get("/public/{slug}", response_model=SponsorPublicProfile)
def public_profile(slug: str, db: Annotated[Session, Depends(get_db)]) -> SponsorPublicProfile:
    sponsor = get_public_sponsor_by_slug(db, slug)
    data = build_public_sponsor_profile(db, sponsor)
    return SponsorPublicProfile.model_validate(data)


# --- Admin ---

admin_router = APIRouter(prefix="/admin/sponsors", tags=["admin-sponsors"])


@admin_router.get("", response_model=list[SponsorAdminListItem])
def admin_list(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsors.view"))],
) -> list[SponsorAdminListItem]:
    rows = admin_list_sponsors(db)
    return [
        SponsorAdminListItem(
            id=s.id,
            display_name=s.display_name or s.company_name,
            slug=s.slug,
            sponsor_type=s.sponsor_type,
            owner_user_id=s.owner_user_id,
            verification_status=s.verification_status,
            status=s.status,
            visibility=s.visibility,
            onboarding_status=s.onboarding_status,
            created_at=s.created_at,
        )
        for s in rows
    ]


def _admin_detail(db: Session, sponsor_id: UUID) -> SponsorAdminDetail:
    sponsor = admin_get_sponsor(db, sponsor_id)
    owner_email = None
    if sponsor.owner_user_id:
        owner = db.get(User, sponsor.owner_user_id)
        owner_email = owner.email if owner else None
    base = _to_private(sponsor)
    return SponsorAdminDetail(
        **base.model_dump(),
        internal_notes=sponsor.internal_notes,
        owner_email=owner_email,
    )


@admin_router.get("/{sponsor_id}", response_model=SponsorAdminDetail)
def admin_detail(
    sponsor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsors.view"))],
) -> SponsorAdminDetail:
    return _admin_detail(db, sponsor_id)


@admin_router.post("/{sponsor_id}/verify", response_model=SponsorAdminDetail)
def admin_verify(
    sponsor_id: UUID,
    payload: SponsorAdminVerifyRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsors.verify"))],
) -> SponsorAdminDetail:
    ip, _ = _client_meta(request)
    sponsor = admin_verify_sponsor(
        db,
        actor=actor,
        sponsor_id=sponsor_id,
        action=payload.action,
        notes=payload.notes,
        ip_address=ip,
    )
    db.commit()
    db.refresh(sponsor)
    return _admin_detail(db, sponsor_id)


@admin_router.post("/{sponsor_id}/status", response_model=SponsorAdminDetail)
def admin_status(
    sponsor_id: UUID,
    payload: SponsorAdminStatusRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsors.restrict"))],
) -> SponsorAdminDetail:
    ip, _ = _client_meta(request)
    sponsor = admin_set_sponsor_status(
        db,
        actor=actor,
        sponsor_id=sponsor_id,
        status=payload.status,
        notes=payload.notes,
        ip_address=ip,
    )
    db.commit()
    db.refresh(sponsor)
    return _admin_detail(db, sponsor_id)


@admin_router.patch("/{sponsor_id}/notes", response_model=SponsorAdminDetail)
def admin_notes(
    sponsor_id: UUID,
    payload: SponsorAdminNotesUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsors.moderate"))],
) -> SponsorAdminDetail:
    ip, _ = _client_meta(request)
    sponsor = admin_update_notes(
        db,
        actor=actor,
        sponsor_id=sponsor_id,
        internal_notes=payload.internal_notes,
        ip_address=ip,
    )
    db.commit()
    db.refresh(sponsor)
    return _admin_detail(db, sponsor_id)
