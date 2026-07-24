"""Sponsor workspace analytics — aggregate, public-safe metrics only."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.hosts.models import Host, HostProfile
from app.legacy.models import HostLegacyScore
from app.sponsor_profiles.campaign_service import _get_campaign_for_sponsor
from app.sponsor_profiles.recommendations import constants as RecC
from app.sponsor_profiles.recommendations.models import CampaignRecommendationFeedback
from app.sponsor_profiles.service import require_sponsor_access
from app.sponsorships.models import (
    CampaignSavedItem,
    Sponsor,
    SponsorCampaign,
    SponsorSavedItem,
    SponsorshipDeal,
    SponsorshipInquiry,
    SponsorshipInvoice,
    SponsorshipPlacement,
    SponsorshipSlot,
)
from app.sponsorships.deals_service import deal_spend_totals
from app.sponsorships.deliverables_service import deliverables_summary_for_sponsor
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _inquiry_counts(rows: list[SponsorshipInquiry]) -> dict[str, int]:
    c = Counter(r.status for r in rows)
    total = len(rows)
    pending = c.get("new", 0) + c.get("reviewing", 0)
    return {
        "total": total,
        "new": c.get("new", 0),
        "reviewing": c.get("reviewing", 0),
        "accepted": c.get("accepted", 0),
        "declined": c.get("declined", 0),
        "closed": c.get("closed", 0),
        "pending": pending,
    }


def _response_rate(counts: dict[str, int]) -> float | None:
    decided = counts["accepted"] + counts["declined"]
    if decided == 0:
        return None
    return round(counts["accepted"] / decided, 4)


def _avg_response_hours(rows: list[SponsorshipInquiry]) -> float | None:
    deltas: list[float] = []
    for row in rows:
        if row.status in {"new"}:
            continue
        created = row.created_at
        updated = row.updated_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        hours = (updated - created).total_seconds() / 3600.0
        if hours >= 0:
            deltas.append(hours)
    if not deltas:
        return None
    return round(sum(deltas) / len(deltas), 2)


def _top_labels(values: list[str], *, limit: int = 5) -> list[dict[str, Any]]:
    cleaned = [v.strip() for v in values if v and v.strip()]
    if not cleaned:
        return []
    counts = Counter(cleaned)
    return [
        {"label": label, "count": count}
        for label, count in counts.most_common(limit)
    ]


def _placement_spend(
    db: Session, *, sponsor_id: uuid.UUID, inquiry_ids: set[uuid.UUID] | None = None
) -> tuple[int, Decimal | None]:
    q = select(SponsorshipPlacement).where(
        SponsorshipPlacement.sponsor_id == sponsor_id,
        SponsorshipPlacement.status.in_(("planned", "active", "completed")),
    )
    if inquiry_ids is not None:
        if not inquiry_ids:
            return 0, None
        q = q.where(SponsorshipPlacement.inquiry_id.in_(inquiry_ids))
    placements = list(db.scalars(q))
    if not placements:
        return 0, None
    total = Decimal("0")
    for p in placements:
        slot = db.get(SponsorshipSlot, p.slot_id)
        if slot is not None:
            total += slot.price
    return len(placements), total.quantize(Decimal("0.01")) if total else None


def _estimated_reach(db: Session, host_ids: set[uuid.UUID]) -> int | None:
    if not host_ids:
        return None
    rows = list(
        db.scalars(
            select(HostLegacyScore).where(HostLegacyScore.host_id.in_(host_ids))
        )
    )
    if not rows:
        return None
    reach = 0
    for row in rows:
        if row.verified_checkins:
            reach += min(int(row.verified_checkins), 5000)
        elif row.followers:
            reach += min(int(row.followers), 5000)
    return reach if reach > 0 else None


def _recommendation_engagement(
    db: Session, *, campaign_ids: list[uuid.UUID] | None = None
) -> dict[str, int]:
    q = select(CampaignRecommendationFeedback.action, func.count()).group_by(
        CampaignRecommendationFeedback.action
    )
    if campaign_ids is not None:
        if not campaign_ids:
            return {"clicked": 0, "saved": 0, "dismissed": 0}
        q = q.where(CampaignRecommendationFeedback.campaign_id.in_(campaign_ids))
    rows = db.execute(q).all()
    counts = {str(a): int(c) for a, c in rows}
    return {
        "clicked": counts.get(RecC.FEEDBACK_CLICKED, 0),
        "saved": counts.get(RecC.FEEDBACK_SAVED, 0),
        "dismissed": counts.get(RecC.FEEDBACK_DISMISSED, 0)
        + counts.get(RecC.FEEDBACK_NOT_INTERESTED, 0),
    }


def _host_ids_from_inquiries(
    db: Session, inquiries: list[SponsorshipInquiry]
) -> set[uuid.UUID]:
    slot_ids = {i.slot_id for i in inquiries}
    if not slot_ids:
        return set()
    slots = list(db.scalars(select(SponsorshipSlot).where(SponsorshipSlot.id.in_(slot_ids))))
    return {s.host_id for s in slots}


def _categories_from_context(
    db: Session,
    *,
    sponsor: Sponsor,
    campaigns: list[SponsorCampaign],
    inquiries: list[SponsorshipInquiry],
) -> list[str]:
    labels: list[str] = []
    if sponsor.categories:
        labels.extend(str(c) for c in sponsor.categories if c)
    if sponsor.industry:
        labels.append(sponsor.industry)
    for camp in campaigns:
        if camp.target_categories:
            labels.extend(str(c) for c in camp.target_categories if c)
    for inq in inquiries:
        slot = db.get(SponsorshipSlot, inq.slot_id)
        if slot:
            labels.append(slot.slot_type.replace("_", " "))
    return labels


def _locations_from_context(
    db: Session,
    *,
    campaigns: list[SponsorCampaign],
    inquiries: list[SponsorshipInquiry],
) -> list[str]:
    labels: list[str] = []
    for camp in campaigns:
        if camp.target_locations:
            labels.extend(str(x) for x in camp.target_locations if x)
    host_ids = _host_ids_from_inquiries(db, inquiries)
    if host_ids:
        profiles = db.scalars(
            select(HostProfile).where(HostProfile.host_id.in_(host_ids))
        ).all()
        for p in profiles:
            if p.city:
                labels.append(p.city)
    return labels


def _deal_metrics(
    db: Session,
    *,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    q = select(SponsorshipDeal).where(SponsorshipDeal.sponsor_id == sponsor_id)
    if campaign_id is not None:
        q = q.where(SponsorshipDeal.campaign_id == campaign_id)
    deals = list(db.scalars(q))
    totals = deal_spend_totals(db, sponsor_id, campaign_id=campaign_id)
    pending_invoices = int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipInvoice)
            .join(SponsorshipDeal, SponsorshipInvoice.deal_id == SponsorshipDeal.id)
            .where(
                SponsorshipDeal.sponsor_id == sponsor_id,
                SponsorshipInvoice.status.in_(("issued", "payment_pending", "overdue")),
                *(
                    [SponsorshipDeal.campaign_id == campaign_id]
                    if campaign_id is not None
                    else []
                ),
            )
        )
        or 0
    )
    active = sum(1 for d in deals if d.status == "active")
    completed = sum(1 for d in deals if d.status == "completed")
    proposed = sum(1 for d in deals if d.status == "proposed")
    deliv = deliverables_summary_for_sponsor(db, sponsor_id, campaign_id=campaign_id)
    return {
        "committed_spend_ngn": totals["committed"],
        "paid_spend_ngn": totals["paid"],
        "pending_invoices": pending_invoices,
        "active_deals": active,
        "completed_deals": completed,
        "proposals_awaiting": proposed,
        "deliverables_pending": deliv["pending"] + deliv["in_progress"] + deliv["submitted"],
        "deliverables_completed": deliv["completed"],
        "deliverables_overdue": deliv["overdue"],
        "deliverables_completion_rate": deliv["completion_rate"],
    }


def _pending_actions_overview(
    *,
    inquiry_counts: dict[str, int],
    campaigns: list[SponsorCampaign],
    deal_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if inquiry_counts["pending"] > 0:
        actions.append(
            {
                "kind": "inquiry_pending",
                "count": inquiry_counts["pending"],
                "label": "Inquiries awaiting host response",
            }
        )
    drafts = sum(1 for c in campaigns if c.status == "draft")
    if drafts:
        actions.append(
            {
                "kind": "campaign_draft",
                "count": drafts,
                "label": "Draft campaigns to review",
            }
        )
    under_review = sum(1 for c in campaigns if c.status == "under_review")
    if under_review:
        actions.append(
            {
                "kind": "campaign_moderation",
                "count": under_review,
                "label": "Campaigns pending Pàdéyá review",
            }
        )
    if deal_metrics and deal_metrics.get("proposals_awaiting", 0) > 0:
        actions.append(
            {
                "kind": "deal_proposal",
                "count": deal_metrics["proposals_awaiting"],
                "label": "Sponsorship proposals to review",
            }
        )
    if deal_metrics and deal_metrics.get("pending_invoices", 0) > 0:
        actions.append(
            {
                "kind": "deal_invoice",
                "count": deal_metrics["pending_invoices"],
                "label": "Invoices awaiting payment",
            }
        )
    return actions


def overview_report(
    db: Session, *, user: User, sponsor_id: uuid.UUID
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    inquiries = list(
        db.scalars(
            select(SponsorshipInquiry).where(
                SponsorshipInquiry.sponsor_id == sponsor.id
            )
        )
    )
    campaigns = list(
        db.scalars(
            select(SponsorCampaign).where(SponsorCampaign.sponsor_id == sponsor.id)
        )
    )
    saved_count = int(
        db.scalar(
            select(func.count())
            .select_from(SponsorSavedItem)
            .where(SponsorSavedItem.sponsor_id == sponsor.id)
        )
        or 0
    )
    inq_counts = _inquiry_counts(inquiries)
    camp_status = Counter(c.status for c in campaigns)
    placement_count, placement_spend = _placement_spend(db, sponsor_id=sponsor.id)
    deal_stats = _deal_metrics(db, sponsor_id=sponsor.id)
    committed = deal_stats["committed_spend_ngn"] or placement_spend
    host_ids = _host_ids_from_inquiries(db, inquiries)

    return {
        "sponsor_id": sponsor.id,
        "generated_at": _now(),
        "saved_opportunities_count": saved_count,
        "inquiries": inq_counts,
        "response_rate": _response_rate(inq_counts),
        "avg_response_hours": _avg_response_hours(inquiries),
        "campaigns_by_status": dict(camp_status),
        "top_categories": _top_labels(
            _categories_from_context(
                db, sponsor=sponsor, campaigns=campaigns, inquiries=inquiries
            )
        ),
        "top_locations": _top_labels(
            _locations_from_context(db, campaigns=campaigns, inquiries=inquiries)
        ),
        "recommendation_engagement": _recommendation_engagement(
            db, campaign_ids=[c.id for c in campaigns]
        ),
        "linked_placements": {
            "count": placement_count,
            "spend_committed_ngn": committed,
        },
        "deals": deal_stats,
        "estimated_reach": _estimated_reach(db, host_ids),
        "pending_actions": _pending_actions_overview(
            inquiry_counts=inq_counts,
            campaigns=campaigns,
            deal_metrics=deal_stats,
        ),
    }


def campaign_report(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    campaign = _get_campaign_for_sponsor(
        db, sponsor_id=sponsor.id, campaign_id=campaign_id
    )
    inquiries = list(
        db.scalars(
            select(SponsorshipInquiry).where(
                SponsorshipInquiry.sponsor_id == sponsor.id,
                SponsorshipInquiry.campaign_id == campaign.id,
            )
        )
    )
    saved_links = int(
        db.scalar(
            select(func.count())
            .select_from(CampaignSavedItem)
            .where(CampaignSavedItem.campaign_id == campaign.id)
        )
        or 0
    )
    inq_counts = _inquiry_counts(inquiries)
    inq_ids = {i.id for i in inquiries}
    placement_count, placement_spend = _placement_spend(
        db, sponsor_id=sponsor.id, inquiry_ids=inq_ids
    )
    deal_stats = _deal_metrics(
        db, sponsor_id=sponsor.id, campaign_id=campaign.id
    )
    committed = deal_stats["committed_spend_ngn"] or placement_spend
    host_ids = _host_ids_from_inquiries(db, inquiries)

    pending: list[dict[str, Any]] = []
    if inq_counts["pending"] > 0:
        pending.append(
            {
                "kind": "inquiry_pending",
                "count": inq_counts["pending"],
                "label": "Inquiries awaiting host response",
            }
        )
    if campaign.status == "draft":
        pending.append(
            {
                "kind": "campaign_activate",
                "count": 1,
                "label": "Activate campaign when ready",
            }
        )
    if campaign.status == "under_review":
        pending.append(
            {
                "kind": "campaign_moderation",
                "count": 1,
                "label": "Awaiting Pàdéyá moderation",
            }
        )
    if deal_stats.get("proposals_awaiting", 0) > 0:
        pending.append(
            {
                "kind": "deal_proposal",
                "count": deal_stats["proposals_awaiting"],
                "label": "Sponsorship proposals to review",
            }
        )
    if deal_stats.get("pending_invoices", 0) > 0:
        pending.append(
            {
                "kind": "deal_invoice",
                "count": deal_stats["pending_invoices"],
                "label": "Invoices awaiting payment",
            }
        )

    return {
        "campaign": {
            "campaign_id": campaign.id,
            "name": campaign.name,
            "objective": campaign.objective,
            "status": campaign.status,
            "start_date": campaign.start_date,
            "end_date": campaign.end_date,
            "budget_min": campaign.budget_min,
            "budget_max": campaign.budget_max,
            "currency": campaign.currency,
            "description": campaign.description,
        },
        "generated_at": _now(),
        "saved_opportunities_count": saved_links,
        "inquiries": inq_counts,
        "response_rate": _response_rate(inq_counts),
        "avg_response_hours": _avg_response_hours(inquiries),
        "recommendation_engagement": _recommendation_engagement(
            db, campaign_ids=[campaign.id]
        ),
        "linked_placements": {
            "count": placement_count,
            "spend_committed_ngn": committed,
        },
        "deals": deal_stats,
        "estimated_reach": _estimated_reach(db, host_ids),
        "pending_actions": pending,
        "top_categories": _top_labels(
            list(campaign.target_categories or [])
            + [campaign.objective.replace("_", " ")]
        ),
        "top_locations": _top_labels(list(campaign.target_locations or [])),
    }


def admin_sponsor_report_summary(db: Session, *, sponsor_id: uuid.UUID) -> dict[str, Any]:
    sponsor = db.get(Sponsor, sponsor_id)
    if sponsor is None:
        return {}
    inquiries = list(
        db.scalars(
            select(SponsorshipInquiry).where(
                SponsorshipInquiry.sponsor_id == sponsor.id
            )
        )
    )
    inq_counts = _inquiry_counts(inquiries)
    campaigns = list(
        db.scalars(
            select(SponsorCampaign).where(SponsorCampaign.sponsor_id == sponsor.id)
        )
    )
    return {
        "sponsor_id": sponsor.id,
        "company_name": sponsor.display_name or sponsor.company_name,
        "inquiries_total": inq_counts["total"],
        "campaigns_total": len(campaigns),
        "campaigns_active": sum(1 for c in campaigns if c.status == "active"),
    }
