"""Sponsor profile workspace services."""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.sponsor_profiles.constants import (
    DEFAULT_ROLE_PERMISSIONS,
    ONBOARDING_STATUSES,
    SPONSOR_STATUSES,
    SPONSOR_TYPES,
    VERIFICATION_STATUSES,
    VISIBILITY_VALUES,
)
from app.sponsor_profiles.schemas import SponsorCreateRequest, SponsorProfileUpdate
from app.sponsorships.models import Sponsor, SponsorTeamMember, SponsorshipInquiry
from app.users.models import User
from app.users.service import get_role_by_name, user_has_permission


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "sponsor"


def unique_sponsor_slug(db: Session, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    i = 2
    while db.scalar(select(Sponsor.id).where(Sponsor.slug == candidate)):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def _sync_legacy_fields(sponsor: Sponsor) -> None:
    name = (sponsor.display_name or sponsor.company_name or "").strip()
    if name:
        sponsor.company_name = name
        sponsor.display_name = name
    if sponsor.website_url and not sponsor.website:
        sponsor.website = sponsor.website_url
    elif sponsor.website and not sponsor.website_url:
        sponsor.website_url = sponsor.website
    if sponsor.owner_user_id and not sponsor.user_id:
        sponsor.user_id = sponsor.owner_user_id
    elif sponsor.user_id and not sponsor.owner_user_id:
        sponsor.owner_user_id = sponsor.user_id


def is_public_sponsor(sponsor: Sponsor) -> bool:
    return (
        sponsor.status == "active"
        and sponsor.visibility == "public"
        and sponsor.verification_status == "verified"
        and sponsor.slug
        and sponsor.onboarding_status in ("active", "legacy")
    )


def is_public_unlisted(sponsor: Sponsor) -> bool:
    return (
        sponsor.status == "active"
        and sponsor.visibility in ("public", "unlisted")
        and sponsor.verification_status == "verified"
        and sponsor.slug
    )


def _owner_permissions() -> dict[str, bool]:
    return dict(DEFAULT_ROLE_PERMISSIONS["owner"])


def get_sponsor_by_id(db: Session, sponsor_id: uuid.UUID) -> Sponsor | None:
    return db.get(Sponsor, sponsor_id)


def list_owned_sponsors(db: Session, user_id: uuid.UUID) -> list[Sponsor]:
    return list(
        db.scalars(
            select(Sponsor).where(
                Sponsor.owner_user_id == user_id,
                Sponsor.status != "archived",
            )
        )
    )


def require_sponsor_access(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID | None,
    permission: str,
) -> tuple[Sponsor, dict[str, bool]]:
    if user_has_permission(user, "admin.full_access") and sponsor_id:
        row = get_sponsor_by_id(db, sponsor_id)
        if row:
            return row, _owner_permissions()

    owned = list_owned_sponsors(db, user.id)
    if sponsor_id is None and owned:
        sponsor = owned[0]
        return sponsor, _owner_permissions()

    if sponsor_id is not None:
        sponsor = get_sponsor_by_id(db, sponsor_id)
        if sponsor is None:
            raise HTTPException(status_code=404, detail="Sponsor not found")
        if sponsor.owner_user_id == user.id:
            perms = _owner_permissions()
            if not perms.get(permission):
                raise HTTPException(status_code=403, detail="Permission denied")
            return sponsor, perms
        membership = db.scalar(
            select(SponsorTeamMember).where(
                SponsorTeamMember.sponsor_id == sponsor.id,
                SponsorTeamMember.user_id == user.id,
                SponsorTeamMember.status == "active",
                SponsorTeamMember.removed_at.is_(None),
            )
        )
        if membership:
            perms = DEFAULT_ROLE_PERMISSIONS.get(membership.role, {})
            if not perms.get(permission):
                raise HTTPException(status_code=403, detail="Permission denied")
            return sponsor, perms

    raise HTTPException(status_code=404, detail="Sponsor profile not found")


def list_user_sponsor_workspaces(db: Session, *, user: User) -> list[dict[str, Any]]:
    out: dict[uuid.UUID, dict[str, Any]] = {}
    for sponsor in list_owned_sponsors(db, user.id):
        out[sponsor.id] = {
            "sponsor_id": sponsor.id,
            "display_name": sponsor.display_name or sponsor.company_name,
            "slug": sponsor.slug,
            "role": "owner",
            "is_owner": True,
            "permissions": _owner_permissions(),
            "verification_status": sponsor.verification_status,
            "status": sponsor.status,
            "onboarding_status": sponsor.onboarding_status,
        }
    memberships = list(
        db.scalars(
            select(SponsorTeamMember).where(
                SponsorTeamMember.user_id == user.id,
                SponsorTeamMember.status == "active",
                SponsorTeamMember.removed_at.is_(None),
            )
        )
    )
    for row in memberships:
        if row.sponsor_id in out:
            continue
        sponsor = get_sponsor_by_id(db, row.sponsor_id)
        if sponsor is None or sponsor.status == "archived":
            continue
        out[sponsor.id] = {
            "sponsor_id": sponsor.id,
            "display_name": sponsor.display_name or sponsor.company_name,
            "slug": sponsor.slug,
            "role": row.role,
            "is_owner": False,
            "permissions": DEFAULT_ROLE_PERMISSIONS.get(row.role, {}),
            "verification_status": sponsor.verification_status,
            "status": sponsor.status,
            "onboarding_status": sponsor.onboarding_status,
        }
    return list(out.values())


def create_sponsor_profile(
    db: Session,
    *,
    user: User,
    payload: SponsorCreateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Sponsor:
    display = payload.display_name.strip()
    slug = unique_sponsor_slug(db, display)
    contact_email = str(payload.contact_email or user.email).lower()

    onboarding = "pending" if payload.submit_for_review else "draft"
    verification = "pending" if payload.submit_for_review else "unverified"
    account_status = "under_review" if payload.submit_for_review else "active"

    sponsor = Sponsor(
        owner_user_id=user.id,
        user_id=user.id,
        company_name=display,
        display_name=display,
        slug=slug,
        sponsor_type=payload.sponsor_type,
        contact_name=user.full_name or display,
        contact_email=contact_email,
        contact_phone=payload.contact_phone,
        website_url=payload.website_url,
        website=payload.website_url,
        logo_url=payload.logo_url,
        cover_image_url=payload.cover_image_url,
        short_bio=payload.short_bio,
        description=payload.description,
        industry=payload.industry,
        categories=payload.categories or [],
        target_locations=payload.target_locations or [],
        campaign_goals=payload.campaign_goals or [],
        budget_range=payload.budget_range,
        verification_status=verification,
        visibility="private",
        onboarding_status=onboarding,
        status=account_status,
    )
    db.add(sponsor)
    db.flush()

    sponsor_role = get_role_by_name(db, "sponsor")
    if sponsor_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sponsor role is not seeded",
        )
    if sponsor_role not in user.roles:
        user.roles.append(sponsor_role)

    write_audit_log(
        db,
        action="sponsors.create",
        actor_user_id=user.id,
        resource_type="sponsor",
        resource_id=str(sponsor.id),
        details={"slug": slug, "submit_for_review": payload.submit_for_review},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.flush()
    return sponsor


def update_sponsor_profile(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    payload: SponsorProfileUpdate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Sponsor:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.edit_own"
    )
    if sponsor.status in ("suspended", "archived"):
        raise HTTPException(status_code=403, detail="Sponsor account is not editable")

    data = payload.model_dump(exclude_unset=True)
    submit = data.pop("submit_for_review", None)
    if "display_name" in data and data["display_name"]:
        sponsor.display_name = data["display_name"].strip()
        sponsor.company_name = sponsor.display_name
    for key in (
        "sponsor_type",
        "industry",
        "categories",
        "website_url",
        "short_bio",
        "description",
        "logo_url",
        "cover_image_url",
        "target_locations",
        "campaign_goals",
        "budget_range",
        "contact_phone",
    ):
        if key in data:
            setattr(sponsor, key, data[key])
    if "contact_email" in data and data["contact_email"]:
        sponsor.contact_email = str(data["contact_email"]).lower()
    if "website_url" in data:
        sponsor.website = data.get("website_url")
    if "visibility" in data and data["visibility"] in VISIBILITY_VALUES:
        if data["visibility"] == "public" and sponsor.verification_status != "verified":
            raise HTTPException(
                status_code=400,
                detail="Public visibility requires verified sponsor status",
            )
        sponsor.visibility = data["visibility"]

    if submit:
        sponsor.onboarding_status = "pending"
        sponsor.verification_status = "pending"
        sponsor.status = "under_review"

    _sync_legacy_fields(sponsor)
    write_audit_log(
        db,
        action="sponsors.update",
        actor_user_id=user.id,
        resource_type="sponsor",
        resource_id=str(sponsor.id),
        details={"fields": list(data.keys())},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.flush()
    return sponsor


def get_public_sponsor_by_slug(db: Session, slug: str) -> Sponsor:
    sponsor = db.scalar(select(Sponsor).where(Sponsor.slug == slug))
    if sponsor is None or not is_public_unlisted(sponsor):
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return sponsor


def list_public_sponsors(
    db: Session,
    *,
    industry: str | None = None,
    category: str | None = None,
    location: str | None = None,
    verified_only: bool = False,
    sponsor_type: str | None = None,
) -> list[Sponsor]:
    q = select(Sponsor).where(
        Sponsor.status == "active",
        Sponsor.visibility == "public",
        Sponsor.verification_status == "verified",
        Sponsor.slug.isnot(None),
    )
    if industry:
        q = q.where(Sponsor.industry.ilike(f"%{industry}%"))
    if sponsor_type and sponsor_type in SPONSOR_TYPES:
        q = q.where(Sponsor.sponsor_type == sponsor_type)
    if verified_only:
        q = q.where(Sponsor.verification_status == "verified")
    rows = list(db.scalars(q))
    if category:
        cat = category.lower()
        rows = [
            r
            for r in rows
            if any(str(c).lower() == cat for c in (r.categories or []))
        ]
    if location:
        loc = location.lower()
        rows = [
            r
            for r in rows
            if any(loc in str(t).lower() for t in (r.target_locations or []))
        ]
    rows.sort(key=lambda s: (s.display_name or s.company_name or "").lower())
    return rows


def serialize_public(sponsor: Sponsor, *, include_private: bool = False) -> dict[str, Any]:
    verified = sponsor.verification_status == "verified"
    show_contact = verified and sponsor.visibility == "public"
    return {
        "id": sponsor.id,
        "display_name": sponsor.display_name or sponsor.company_name,
        "slug": sponsor.slug,
        "sponsor_type": sponsor.sponsor_type,
        "logo_url": sponsor.logo_url,
        "cover_image_url": sponsor.cover_image_url,
        "short_bio": sponsor.short_bio,
        "description": sponsor.description if verified else None,
        "website_url": sponsor.website_url if verified else None,
        "industry": sponsor.industry,
        "categories": list(sponsor.categories or []),
        "verification_status": sponsor.verification_status,
        "verified": verified,
        "show_contact_cta": show_contact,
        **(
            {
                "budget_range": sponsor.budget_range,
                "campaign_goals": sponsor.campaign_goals,
                "internal_notes": sponsor.internal_notes,
            }
            if include_private
            else {}
        ),
    }


def list_sponsor_inquiries_for_owner(
    db: Session, *, user: User, sponsor_id: uuid.UUID
) -> list[dict[str, Any]]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_inquiries"
    )
    from app.hosts.models import Host
    from app.sponsorships.models import SponsorshipSlot

    inquiries = list(
        db.scalars(
            select(SponsorshipInquiry)
            .where(SponsorshipInquiry.sponsor_id == sponsor.id)
            .order_by(SponsorshipInquiry.created_at.desc())
        )
    )
    out: list[dict[str, Any]] = []
    for row in inquiries:
        slot = db.get(SponsorshipSlot, row.slot_id)
        host_name = None
        if slot:
            host = db.get(Host, slot.host_id)
            host_name = host.display_name if host else None
        out.append(
            {
                "id": row.id,
                "slot_id": row.slot_id,
                "campaign_id": row.campaign_id,
                "slot_title": slot.title if slot else None,
                "host_display_name": host_name,
                "status": row.status,
                "message": row.message,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )
    return out


# --- Admin ---


def admin_list_sponsors(db: Session) -> list[Sponsor]:
    return list(
        db.scalars(select(Sponsor).where(Sponsor.status != "archived").order_by(Sponsor.created_at.desc()))
    )


def admin_get_sponsor(db: Session, sponsor_id: uuid.UUID) -> Sponsor:
    sponsor = get_sponsor_by_id(db, sponsor_id)
    if sponsor is None:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return sponsor


def admin_verify_sponsor(
    db: Session,
    *,
    actor: User,
    sponsor_id: uuid.UUID,
    action: str,
    notes: str | None,
    ip_address: str | None = None,
) -> Sponsor:
    sponsor = admin_get_sponsor(db, sponsor_id)
    if action == "approve":
        sponsor.verification_status = "verified"
        sponsor.status = "active"
        sponsor.onboarding_status = "active"
    elif action == "reject":
        sponsor.verification_status = "rejected"
        sponsor.onboarding_status = "draft"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    if notes:
        sponsor.internal_notes = notes
    write_audit_log(
        db,
        action=f"sponsors.admin.{action}",
        actor_user_id=actor.id,
        resource_type="sponsor",
        resource_id=str(sponsor.id),
        details={"notes": notes},
        ip_address=ip_address,
    )
    db.flush()
    return sponsor


def admin_set_sponsor_status(
    db: Session,
    *,
    actor: User,
    sponsor_id: uuid.UUID,
    status: str,
    notes: str | None,
    ip_address: str | None = None,
) -> Sponsor:
    if status not in SPONSOR_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    sponsor = admin_get_sponsor(db, sponsor_id)
    sponsor.status = status
    if notes:
        sponsor.internal_notes = notes
    write_audit_log(
        db,
        action="sponsors.admin.status",
        actor_user_id=actor.id,
        resource_type="sponsor",
        resource_id=str(sponsor.id),
        details={"status": status, "notes": notes},
        ip_address=ip_address,
    )
    db.flush()
    return sponsor


def admin_update_notes(
    db: Session,
    *,
    actor: User,
    sponsor_id: uuid.UUID,
    internal_notes: str | None,
    ip_address: str | None = None,
) -> Sponsor:
    sponsor = admin_get_sponsor(db, sponsor_id)
    sponsor.internal_notes = internal_notes
    write_audit_log(
        db,
        action="sponsors.admin.notes",
        actor_user_id=actor.id,
        resource_type="sponsor",
        resource_id=str(sponsor.id),
        details={},
        ip_address=ip_address,
    )
    db.flush()
    return sponsor
