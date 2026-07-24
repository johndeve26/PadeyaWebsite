"""Sponsor campaign workspace services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.hosts.models import Host
from app.sponsor_profiles.campaign_schemas import (
    CampaignSavedItemLinkCreate,
    SponsorCampaignCreate,
    SponsorCampaignUpdate,
)
from app.sponsor_profiles.constants import VISIBILITY_REQUIRES_MODERATION
from app.sponsor_profiles.saved_service import _enrich_item
from app.sponsor_profiles.service import require_sponsor_access, slugify
from app.sponsorships.models import (
    CampaignSavedItem,
    Sponsor,
    SponsorCampaign,
    SponsorSavedItem,
    SponsorTeamMember,
    SponsorshipInquiry,
    SponsorshipSlot,
)
from app.users.models import User


def _member_role(db: Session, sponsor: Sponsor, user_id: uuid.UUID) -> str | None:
    if sponsor.owner_user_id == user_id:
        return "owner"
    row = db.scalar(
        select(SponsorTeamMember).where(
            SponsorTeamMember.sponsor_id == sponsor.id,
            SponsorTeamMember.user_id == user_id,
            SponsorTeamMember.status == "active",
            SponsorTeamMember.removed_at.is_(None),
        )
    )
    return row.role if row else None


def require_sponsor_can_manage_campaigns(
    db: Session, *, user: User, sponsor_id: uuid.UUID
) -> Sponsor:
    sponsor, perms = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    role = _member_role(db, sponsor, user.id)
    can = perms.get("sponsors.manage_campaigns") and role in {
        "owner",
        "admin",
        "campaign_manager",
    }
    if not can:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot manage campaigns for this sponsor workspace",
        )
    return sponsor


def _can_edit_campaign(db: Session, *, user: User, sponsor: Sponsor) -> bool:
    try:
        require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor.id)
        return True
    except HTTPException:
        return False


def unique_campaign_ref(db: Session, sponsor_id: uuid.UUID, base: str) -> str:
    slug = slugify(base)[:160] or "campaign"
    candidate = slug
    i = 2
    while db.scalar(
        select(SponsorCampaign.id).where(
            SponsorCampaign.sponsor_id == sponsor_id,
            SponsorCampaign.public_ref == candidate,
        )
    ):
        candidate = f"{slug}-{i}"[:180]
        i += 1
    return candidate


def _inquiries_count(db: Session, campaign_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipInquiry)
            .where(SponsorshipInquiry.campaign_id == campaign_id)
        )
        or 0
    )


def _saved_count(db: Session, campaign_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CampaignSavedItem)
            .where(CampaignSavedItem.campaign_id == campaign_id)
        )
        or 0
    )


def _serialize_list_item(db: Session, row: SponsorCampaign) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "public_ref": row.public_ref,
        "objective": row.objective,
        "status": row.status,
        "visibility": row.visibility,
        "moderation_status": row.moderation_status,
        "budget_min": row.budget_min,
        "budget_max": row.budget_max,
        "currency": row.currency,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "saved_items_count": _saved_count(db, row.id),
        "inquiries_count": _inquiries_count(db, row.id),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _serialize_saved_link(db: Session, link: CampaignSavedItem) -> dict[str, Any]:
    saved = db.get(SponsorSavedItem, link.sponsor_saved_item_id)
    enriched = _enrich_item(db, saved) if saved else {}
    return {
        "id": link.id,
        "sponsor_saved_item_id": link.sponsor_saved_item_id,
        "item_type": saved.item_type if saved else "",
        "item_id": saved.item_id if saved else link.sponsor_saved_item_id,
        "title": enriched.get("title"),
        "subtitle": enriched.get("subtitle"),
        "href": enriched.get("href"),
        "available": enriched.get("available", False),
        "note": link.note,
        "created_at": link.created_at,
    }


def _serialize_inquiry(db: Session, inquiry: SponsorshipInquiry) -> dict[str, Any]:
    slot = db.get(SponsorshipSlot, inquiry.slot_id)
    host_name = None
    if slot:
        host = db.get(Host, slot.host_id)
        host_name = host.display_name if host else None
    return {
        "id": inquiry.id,
        "slot_id": inquiry.slot_id,
        "slot_title": slot.title if slot else None,
        "host_display_name": host_name,
        "status": inquiry.status,
        "created_at": inquiry.created_at,
    }


def _get_campaign_for_sponsor(
    db: Session, *, sponsor_id: uuid.UUID, campaign_id: uuid.UUID
) -> SponsorCampaign:
    row = db.scalar(
        select(SponsorCampaign).where(
            SponsorCampaign.id == campaign_id,
            SponsorCampaign.sponsor_id == sponsor_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return row


def _ensure_editable(campaign: SponsorCampaign) -> None:
    if campaign.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Archived campaigns are read-only",
        )


def list_campaigns(
    db: Session, *, user: User, sponsor_id: uuid.UUID
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    rows = list(
        db.scalars(
            select(SponsorCampaign)
            .where(SponsorCampaign.sponsor_id == sponsor.id)
            .order_by(SponsorCampaign.updated_at.desc())
        )
    )
    items = [_serialize_list_item(db, r) for r in rows]
    return {"items": items, "total": len(items)}


def create_campaign(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    payload: SponsorCampaignCreate,
) -> dict[str, Any]:
    sponsor = require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    ref = unique_campaign_ref(db, sponsor.id, payload.name)
    campaign = SponsorCampaign(
        sponsor_id=sponsor.id,
        created_by_user_id=user.id,
        name=payload.name.strip(),
        public_ref=ref,
        objective=payload.objective,
        description=payload.description,
        target_categories=payload.target_categories,
        target_locations=payload.target_locations,
        target_audience=payload.target_audience,
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        currency=(payload.currency or "NGN").upper(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="draft",
        visibility=payload.visibility,
        moderation_status=(
            "pending"
            if payload.visibility in VISIBILITY_REQUIRES_MODERATION
            else "not_required"
        ),
    )
    db.add(campaign)
    db.flush()
    if payload.sponsor_saved_item_id is not None:
        saved = db.scalar(
            select(SponsorSavedItem).where(
                SponsorSavedItem.id == payload.sponsor_saved_item_id,
                SponsorSavedItem.sponsor_id == sponsor.id,
            )
        )
        if saved is None:
            raise HTTPException(status_code=404, detail="Saved item not found")
        existing = db.scalar(
            select(CampaignSavedItem).where(
                CampaignSavedItem.campaign_id == campaign.id,
                CampaignSavedItem.sponsor_saved_item_id == saved.id,
            )
        )
        if not existing:
            db.add(
                CampaignSavedItem(
                    campaign_id=campaign.id,
                    sponsor_saved_item_id=saved.id,
                    added_by_user_id=user.id,
                )
            )
    write_audit_log(
        db,
        action="sponsor_campaigns.create",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={"name": campaign.name, "sponsor_id": str(sponsor.id)},
    )
    db.commit()
    db.refresh(campaign)
    return get_campaign(db, user=user, sponsor_id=sponsor.id, campaign_id=campaign.id)


def get_campaign(
    db: Session, *, user: User, sponsor_id: uuid.UUID, campaign_id: uuid.UUID
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    links = list(
        db.scalars(
            select(CampaignSavedItem)
            .where(CampaignSavedItem.campaign_id == campaign.id)
            .order_by(CampaignSavedItem.created_at.desc())
        )
    )
    inquiries = list(
        db.scalars(
            select(SponsorshipInquiry)
            .where(SponsorshipInquiry.campaign_id == campaign.id)
            .order_by(SponsorshipInquiry.created_at.desc())
        )
    )
    base = _serialize_list_item(db, campaign)
    base.update(
        {
            "description": campaign.description,
            "target_categories": campaign.target_categories,
            "target_locations": campaign.target_locations,
            "target_audience": campaign.target_audience,
            "rejection_reason": campaign.rejection_reason,
            "saved_items": [_serialize_saved_link(db, link) for link in links],
            "inquiries": [_serialize_inquiry(db, i) for i in inquiries],
            "can_edit": _can_edit_campaign(db, user=user, sponsor=sponsor),
        }
    )
    return base


def update_campaign(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID,
    payload: SponsorCampaignUpdate,
) -> dict[str, Any]:
    sponsor = require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    _ensure_editable(campaign)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        campaign.name = data["name"].strip()
    for field in (
        "objective",
        "description",
        "target_categories",
        "target_locations",
        "target_audience",
        "budget_min",
        "budget_max",
        "currency",
        "start_date",
        "end_date",
    ):
        if field in data:
            setattr(campaign, field, data[field])
    if "currency" in data and data["currency"]:
        campaign.currency = str(data["currency"]).upper()
    if "visibility" in data and data["visibility"]:
        campaign.visibility = data["visibility"]
        if data["visibility"] in VISIBILITY_REQUIRES_MODERATION:
            if campaign.moderation_status != "approved":
                campaign.moderation_status = "pending"
                if campaign.status == "active":
                    campaign.status = "under_review"
    if "status" in data and data["status"]:
        if data["status"] not in {"draft", "paused", "completed"}:
            raise HTTPException(status_code=400, detail="Use lifecycle actions for status")
        campaign.status = data["status"]
    write_audit_log(
        db,
        action="sponsor_campaigns.update",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={"fields": list(data.keys())},
    )
    db.commit()
    return get_campaign(db, user=user, sponsor_id=sponsor.id, campaign_id=campaign.id)


def _apply_activation_rules(campaign: SponsorCampaign) -> None:
    if campaign.visibility in VISIBILITY_REQUIRES_MODERATION:
        if campaign.moderation_status != "approved":
            campaign.status = "under_review"
            campaign.moderation_status = "pending"
            return
    campaign.status = "active"


def activate_campaign(
    db: Session, *, user: User, sponsor_id: uuid.UUID, campaign_id: uuid.UUID
) -> dict[str, Any]:
    sponsor = require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    _ensure_editable(campaign)
    if campaign.status == "rejected":
        raise HTTPException(status_code=400, detail="Rejected campaigns cannot activate")
    _apply_activation_rules(campaign)
    write_audit_log(
        db,
        action="sponsor_campaigns.activate",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={"status": campaign.status},
    )
    db.commit()
    return get_campaign(db, user=user, sponsor_id=sponsor.id, campaign_id=campaign.id)


def pause_campaign(
    db: Session, *, user: User, sponsor_id: uuid.UUID, campaign_id: uuid.UUID
) -> dict[str, Any]:
    sponsor = require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    _ensure_editable(campaign)
    if campaign.status not in {"active", "under_review"}:
        raise HTTPException(status_code=400, detail="Only active campaigns can pause")
    campaign.status = "paused"
    write_audit_log(
        db,
        action="sponsor_campaigns.pause",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={},
    )
    db.commit()
    return get_campaign(db, user=user, sponsor_id=sponsor.id, campaign_id=campaign.id)


def archive_campaign(
    db: Session, *, user: User, sponsor_id: uuid.UUID, campaign_id: uuid.UUID
) -> dict[str, Any]:
    sponsor = require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    campaign.status = "archived"
    write_audit_log(
        db,
        action="sponsor_campaigns.archive",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={},
    )
    db.commit()
    return get_campaign(db, user=user, sponsor_id=sponsor.id, campaign_id=campaign.id)


def attach_saved_item(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID,
    payload: CampaignSavedItemLinkCreate,
) -> dict[str, Any]:
    sponsor = require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    _ensure_editable(campaign)
    saved = db.scalar(
        select(SponsorSavedItem).where(
            SponsorSavedItem.id == payload.sponsor_saved_item_id,
            SponsorSavedItem.sponsor_id == sponsor.id,
        )
    )
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved item not found")
    existing = db.scalar(
        select(CampaignSavedItem).where(
            CampaignSavedItem.campaign_id == campaign.id,
            CampaignSavedItem.sponsor_saved_item_id == saved.id,
        )
    )
    if existing:
        if payload.note is not None:
            existing.note = payload.note
        db.flush()
        return _serialize_saved_link(db, existing)
    link = CampaignSavedItem(
        campaign_id=campaign.id,
        sponsor_saved_item_id=saved.id,
        added_by_user_id=user.id,
        note=payload.note,
    )
    db.add(link)
    db.flush()
    write_audit_log(
        db,
        action="sponsor_campaigns.saved_item_add",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={"saved_item_id": str(saved.id)},
    )
    db.commit()
    db.refresh(link)
    return _serialize_saved_link(db, link)


def detach_saved_item(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID,
    saved_item_id: uuid.UUID,
) -> None:
    sponsor = require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    _ensure_editable(campaign)
    link = db.scalar(
        select(CampaignSavedItem).where(
            CampaignSavedItem.campaign_id == campaign.id,
            CampaignSavedItem.sponsor_saved_item_id == saved_item_id,
        )
    )
    if link is None:
        link = db.get(CampaignSavedItem, saved_item_id)
        if link is None or link.campaign_id != campaign.id:
            raise HTTPException(status_code=404, detail="Campaign saved link not found")
    db.delete(link)
    write_audit_log(
        db,
        action="sponsor_campaigns.saved_item_remove",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={"link_id": str(link.id)},
    )
    db.commit()


def validate_inquiry_campaign(
    db: Session,
    *,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID | None,
) -> None:
    if campaign_id is None:
        return
    campaign = db.scalar(
        select(SponsorCampaign).where(
            SponsorCampaign.id == campaign_id,
            SponsorCampaign.sponsor_id == sponsor_id,
        )
    )
    if campaign is None:
        raise HTTPException(status_code=400, detail="Invalid campaign for this sponsor")
    if campaign.status == "archived":
        raise HTTPException(status_code=400, detail="Cannot attach inquiry to archived campaign")


# --- Admin ---


def admin_list_campaigns(db: Session) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(SponsorCampaign)
            .order_by(SponsorCampaign.created_at.desc())
            .limit(200)
        )
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        sponsor = db.get(Sponsor, row.sponsor_id)
        out.append(
            {
                "id": row.id,
                "sponsor_id": row.sponsor_id,
                "sponsor_name": (
                    sponsor.display_name or sponsor.company_name if sponsor else "—"
                ),
                "name": row.name,
                "objective": row.objective,
                "status": row.status,
                "visibility": row.visibility,
                "moderation_status": row.moderation_status,
                "created_at": row.created_at,
            }
        )
    return out


def admin_get_campaign(db: Session, campaign_id: uuid.UUID) -> dict[str, Any]:
    campaign = db.get(SponsorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    sponsor = db.get(Sponsor, campaign.sponsor_id)
    return {
        "id": campaign.id,
        "sponsor_id": campaign.sponsor_id,
        "sponsor_name": (
            sponsor.display_name or sponsor.company_name if sponsor else "—"
        ),
        "name": campaign.name,
        "objective": campaign.objective,
        "status": campaign.status,
        "visibility": campaign.visibility,
        "moderation_status": campaign.moderation_status,
        "description": campaign.description,
        "rejection_reason": campaign.rejection_reason,
        "budget_min": campaign.budget_min,
        "budget_max": campaign.budget_max,
        "currency": campaign.currency,
        "created_at": campaign.created_at,
    }


def admin_approve_campaign(
    db: Session, *, actor: User, campaign_id: uuid.UUID
) -> dict[str, Any]:
    campaign = db.get(SponsorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.moderation_status not in {"pending", "rejected"}:
        raise HTTPException(status_code=400, detail="Campaign is not pending moderation")
    campaign.moderation_status = "approved"
    campaign.rejection_reason = None
    if campaign.status in {"under_review", "draft"}:
        campaign.status = "active"
    write_audit_log(
        db,
        action="sponsor_campaigns.admin.approve",
        actor_user_id=actor.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={},
    )
    db.commit()
    return admin_get_campaign(db, campaign.id)


def admin_reject_campaign(
    db: Session,
    *,
    actor: User,
    campaign_id: uuid.UUID,
    rejection_reason: str,
) -> dict[str, Any]:
    campaign = db.get(SponsorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.moderation_status = "rejected"
    campaign.status = "rejected"
    campaign.rejection_reason = rejection_reason.strip()
    write_audit_log(
        db,
        action="sponsor_campaigns.admin.reject",
        actor_user_id=actor.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={"reason": campaign.rejection_reason},
    )
    db.commit()
    return admin_get_campaign(db, campaign.id)
