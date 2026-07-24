"""Campaign recommendation API services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.sponsor_profiles.campaign_service import (
    _get_campaign_for_sponsor,
    require_sponsor_can_manage_campaigns,
)
from app.sponsor_profiles.recommendations import constants as C
from app.sponsor_profiles.recommendations.models import (
    CampaignRecommendationDismissal,
    CampaignRecommendationFeedback,
)
from app.sponsor_profiles.recommendations.scoring import list_campaign_recommendations
from app.sponsor_profiles.service import require_sponsor_access
from app.sponsorships.models import Sponsor
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def get_recommendations(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID,
    limit: int = C.RECOMMENDATIONS_CAP,
    debug: bool = False,
) -> dict:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    if campaign.status == "archived":
        return {"items": [], "total": 0}
    return list_campaign_recommendations(
        db,
        campaign=campaign,
        sponsor=sponsor,
        limit=limit,
        debug=debug,
    )


def record_recommendation_feedback(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID,
    item_type: str,
    item_id: uuid.UUID,
    action: str,
) -> None:
    if item_type not in C.ITEM_TYPES:
        raise HTTPException(status_code=400, detail="Invalid item_type")
    if action not in C.FEEDBACK_ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid feedback action")

    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    if action not in {C.FEEDBACK_CLICKED}:
        require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)

    db.add(
        CampaignRecommendationFeedback(
            campaign_id=campaign.id,
            sponsor_id=sponsor.id,
            actor_user_id=user.id,
            item_type=item_type,
            item_id=item_id,
            action=action,
        )
    )

    if action in C.DISMISS_ACTIONS:
        expires = _now() + timedelta(days=C.DISMISS_COOLDOWN_DAYS)
        row = db.scalar(
            select(CampaignRecommendationDismissal).where(
                CampaignRecommendationDismissal.campaign_id == campaign.id,
                CampaignRecommendationDismissal.item_type == item_type,
                CampaignRecommendationDismissal.item_id == item_id,
            )
        )
        if row is None:
            db.add(
                CampaignRecommendationDismissal(
                    campaign_id=campaign.id,
                    item_type=item_type,
                    item_id=item_id,
                    expires_at=expires,
                )
            )
        else:
            row.dismissed_at = _now()
            row.expires_at = expires

    write_audit_log(
        db,
        action=f"sponsor_campaigns.recommendation.{action}",
        actor_user_id=user.id,
        resource_type="sponsor_campaign",
        resource_id=str(campaign.id),
        details={
            "item_type": item_type,
            "item_id": str(item_id),
        },
    )
    db.commit()


def admin_debug_recommendations(
    db: Session, *, campaign_id: uuid.UUID
) -> dict:
    from app.sponsorships.models import SponsorCampaign

    campaign = db.get(SponsorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    sponsor = db.get(Sponsor, campaign.sponsor_id)
    if sponsor is None:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    data = list_campaign_recommendations(
        db,
        campaign=campaign,
        sponsor=sponsor,
        limit=50,
        debug=True,
    )
    return {
        "campaign_id": campaign.id,
        "sponsor_id": sponsor.id,
        **data,
    }
