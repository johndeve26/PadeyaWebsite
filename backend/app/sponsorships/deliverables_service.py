"""Sponsorship deliverable fulfillment services."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.hosts.team_access import require_host_for_permission
from app.sponsor_profiles.campaign_service import require_sponsor_can_manage_campaigns
from app.sponsor_profiles.service import require_sponsor_access
from app.sponsorships.deliverables_constants import (
    DELIVERABLE_STATUSES,
    DELIVERABLE_TYPES,
    HOST_EDIT_STATUSES,
    SPONSOR_REVIEW_STATUSES,
    TERMINAL_STATUSES,
)
from app.sponsorships.deliverables_schemas import (
    AdminDeliverablePatch,
    HostDeliverablePatch,
    HostDeliverableSubmit,
    SponsorDeliverableReject,
)
from app.sponsorships.models import (
    Sponsor,
    SponsorshipDeal,
    SponsorshipDeliverable,
    SponsorshipPlacement,
)
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _infer_type(text: str) -> str:
    lower = text.lower()
    rules: list[tuple[str, str]] = [
        (r"logo|brand", "logo_placement"),
        (r"stage|mention|shout", "stage_mention"),
        (r"booth|stand", "booth_space"),
        (r"social|instagram|twitter|tiktok", "social_post"),
        (r"email|newsletter", "email_feature"),
        (r"push|notification", "push_feature"),
        (r"merch|merchandise", "merch_collab"),
        (r"banner|ad", "banner_ad"),
        (r"sampl|product", "product_sampling"),
    ]
    for pattern, dtype in rules:
        if re.search(pattern, lower):
            return dtype
    return "custom"


def _parse_deal_deliverable_item(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        title = item.strip()
        return {
            "title": title[:200] or "Deliverable",
            "description": None,
            "deliverable_type": _infer_type(title),
            "due_at": None,
        }
    if isinstance(item, dict):
        title = str(item.get("title") or item.get("name") or "Deliverable").strip()[:200]
        dtype = str(item.get("deliverable_type") or item.get("type") or _infer_type(title))
        if dtype not in DELIVERABLE_TYPES:
            dtype = "custom"
        due = item.get("due_at")
        return {
            "title": title or "Deliverable",
            "description": item.get("description"),
            "deliverable_type": dtype,
            "due_at": due,
        }
    return {
        "title": "Deliverable",
        "description": None,
        "deliverable_type": "custom",
        "due_at": None,
    }


def ensure_deliverables_for_active_deal(
    db: Session,
    *,
    deal: SponsorshipDeal,
    placement_id: uuid.UUID | None,
) -> list[SponsorshipDeliverable]:
    """Idempotent: create rows from deal.deliverables when deal is active."""
    if deal.status not in {"active", "completed", "paid"}:
        return []
    existing = int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipDeliverable)
            .where(SponsorshipDeliverable.deal_id == deal.id)
        )
        or 0
    )
    if existing > 0:
        return list(
            db.scalars(
                select(SponsorshipDeliverable)
                .where(SponsorshipDeliverable.deal_id == deal.id)
                .order_by(SponsorshipDeliverable.created_at)
            )
        )

    raw = deal.deliverables or []
    if not raw:
        raw = [deal.title or "Sponsorship package delivery"]

    created: list[SponsorshipDeliverable] = []
    for item in raw:
        parsed = _parse_deal_deliverable_item(item)
        row = SponsorshipDeliverable(
            deal_id=deal.id,
            placement_id=placement_id or deal.placement_id,
            title=parsed["title"],
            description=parsed.get("description"),
            deliverable_type=parsed["deliverable_type"],
            due_at=parsed.get("due_at") or deal.ends_at,
            status="pending",
        )
        db.add(row)
        created.append(row)
    db.flush()
    return created


def deliverable_counts_for_deals(
    db: Session, *, deal_ids: list[uuid.UUID], now: datetime | None = None
) -> dict[str, int]:
    if not deal_ids:
        return {
            "pending": 0,
            "in_progress": 0,
            "submitted": 0,
            "completed": 0,
            "overdue": 0,
        }
    now = now or _now()
    rows = list(
        db.scalars(
            select(SponsorshipDeliverable).where(
                SponsorshipDeliverable.deal_id.in_(deal_ids)
            )
        )
    )
    pending = sum(1 for r in rows if r.status == "pending")
    in_progress = sum(1 for r in rows if r.status == "in_progress")
    submitted = sum(1 for r in rows if r.status == "submitted")
    completed = sum(
        1 for r in rows if r.status in {"completed", "approved"}
    )
    overdue = 0
    for r in rows:
        if r.status in TERMINAL_STATUSES or r.status == "approved":
            continue
        if r.due_at is not None:
            due = r.due_at
            if due.tzinfo is None:
                due = due.replace(tzinfo=UTC)
            if due < now:
                overdue += 1
    return {
        "pending": pending,
        "in_progress": in_progress,
        "submitted": submitted,
        "completed": completed,
        "overdue": overdue,
    }


def completion_rate(counts: dict[str, int]) -> float | None:
    total = (
        counts["pending"]
        + counts["in_progress"]
        + counts["submitted"]
        + counts["completed"]
    )
    if total == 0:
        return None
    return round(counts["completed"] / total, 4)


def _serialize(
    row: SponsorshipDeliverable,
    *,
    host_can_edit: bool = False,
    sponsor_can_review: bool = False,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "deal_id": row.deal_id,
        "placement_id": row.placement_id,
        "title": row.title,
        "description": row.description,
        "deliverable_type": row.deliverable_type,
        "due_at": row.due_at,
        "status": row.status,
        "proof_url": row.proof_url if row.status in {"submitted", "approved", "completed", "rejected"} else None,
        "proof_notes": row.proof_notes,
        "submitted_at": row.submitted_at,
        "approved_at": row.approved_at,
        "rejection_reason": row.rejection_reason,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "can_host_edit": host_can_edit and row.status in HOST_EDIT_STATUSES,
        "can_host_submit": host_can_edit
        and row.status in {"in_progress", "rejected", "pending"},
        "can_sponsor_review": sponsor_can_review and row.status in SPONSOR_REVIEW_STATUSES,
    }


def _get_deal_host(db: Session, user: User, deal_id: uuid.UUID) -> SponsorshipDeal:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.view"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.host_id != host.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


def _maybe_complete_placement(db: Session, deal: SponsorshipDeal) -> None:
    rows = list(
        db.scalars(
            select(SponsorshipDeliverable).where(
                SponsorshipDeliverable.deal_id == deal.id
            )
        )
    )
    if not rows:
        return
    open_left = [r for r in rows if r.status not in TERMINAL_STATUSES]
    if open_left:
        return
    all_done = all(r.status in {"completed", "cancelled"} for r in rows)
    if not all_done:
        return
    now = _now()
    if deal.ends_at is not None:
        end = deal.ends_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        if end > now:
            return
    if deal.placement_id:
        placement = db.get(SponsorshipPlacement, deal.placement_id)
        if placement and placement.status == "active":
            placement.status = "completed"
    if deal.status == "active":
        deal.status = "completed"
        _notify_all_completed(db, deal=deal)


def _notify_submitted(db: Session, *, deal: SponsorshipDeal, row: SponsorshipDeliverable) -> None:
    from app.notifications.service import notify_user

    sponsor = db.get(Sponsor, deal.sponsor_id)
    if sponsor and sponsor.owner_user_id:
        notify_user(
            db,
            user_id=sponsor.owner_user_id,
            kind="sponsor.deliverable_submitted",
            title="Deliverable submitted for review",
            body=f"“{row.title}” on deal “{deal.title}” is ready for your review.",
            link_path=f"/sponsor/deals/{deal.id}",
            dedupe_key=f"spn_deliv_submitted:{row.id}",
        )


def _notify_approved(db: Session, *, deal: SponsorshipDeal, row: SponsorshipDeliverable) -> None:
    from app.notifications.service import notify_user
    from app.hosts.models import Host

    host = db.get(Host, deal.host_id)
    if host and host.user_id:
        notify_user(
            db,
            user_id=host.user_id,
            kind="sponsor.deliverable_approved",
            title="Deliverable approved",
            body=f"Sponsor approved “{row.title}” on Pàdéyá.",
            link_path=f"/host/sponsorships/deals/{deal.id}",
            dedupe_key=f"spn_deliv_approved:{row.id}",
        )


def _notify_rejected(
    db: Session, *, deal: SponsorshipDeal, row: SponsorshipDeliverable
) -> None:
    from app.notifications.service import notify_user
    from app.hosts.models import Host

    host = db.get(Host, deal.host_id)
    if host and host.user_id:
        notify_user(
            db,
            user_id=host.user_id,
            kind="sponsor.deliverable_rejected",
            title="Revision requested",
            body=f"Sponsor requested changes on “{row.title}”.",
            link_path=f"/host/sponsorships/deals/{deal.id}",
            dedupe_key=f"spn_deliverable_rejected:{row.id}",
        )


def _notify_all_completed(db: Session, *, deal: SponsorshipDeal) -> None:
    from app.notifications.service import notify_user
    from app.hosts.models import Host

    sponsor = db.get(Sponsor, deal.sponsor_id)
    host = db.get(Host, deal.host_id)
    for uid, path, prefix in (
        (sponsor.owner_user_id if sponsor else None, f"/sponsor/deals/{deal.id}", "sp"),
        (host.user_id if host else None, f"/host/sponsorships/deals/{deal.id}", "ho"),
    ):
        if uid:
            notify_user(
                db,
                user_id=uid,
                kind="sponsor.deliverables_completed",
                title="All deliverables complete",
                body=f"Deal “{deal.title}” fulfillment is complete on Pàdéyá.",
                link_path=path,
                dedupe_key=f"{prefix}_deliv_all_done:{deal.id}",
            )


def host_list_deliverables(
    db: Session, user: User, deal_id: uuid.UUID
) -> list[dict[str, Any]]:
    deal = _get_deal_host(db, user, deal_id)
    if deal.status not in {"active", "completed", "paid"}:
        return []
    ensure_deliverables_for_active_deal(db, deal=deal, placement_id=deal.placement_id)
    db.commit()
    rows = list(
        db.scalars(
            select(SponsorshipDeliverable)
            .where(SponsorshipDeliverable.deal_id == deal.id)
            .order_by(SponsorshipDeliverable.due_at.nulls_last(), SponsorshipDeliverable.created_at)
        )
    )
    host_can = False
    try:
        require_host_for_permission(
            db, user=user, host_id=None, permission="sponsors.manage_slots"
        )
        host_can = True
    except HTTPException:
        host_can = False
    return [_serialize(r, host_can_edit=host_can) for r in rows]


def host_patch_deliverable(
    db: Session,
    user: User,
    deal_id: uuid.UUID,
    deliverable_id: uuid.UUID,
    payload: HostDeliverablePatch,
) -> dict[str, Any]:
    require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )
    deal = _get_deal_host(db, user, deal_id)
    row = db.get(SponsorshipDeliverable, deliverable_id)
    if row is None or row.deal_id != deal.id:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    if row.status not in HOST_EDIT_STATUSES | {"pending"}:
        raise HTTPException(status_code=400, detail="Deliverable cannot be edited")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        new_status = data["status"]
        if new_status not in {"pending", "in_progress"}:
            raise HTTPException(status_code=400, detail="Invalid status transition")
        row.status = new_status
    if "proof_notes" in data:
        row.proof_notes = data["proof_notes"]
    if "description" in data:
        row.description = data["description"]
    db.commit()
    db.refresh(row)
    return _serialize(row, host_can_edit=True)


def host_submit_deliverable(
    db: Session,
    user: User,
    deal_id: uuid.UUID,
    deliverable_id: uuid.UUID,
    payload: HostDeliverableSubmit,
) -> dict[str, Any]:
    require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )
    deal = _get_deal_host(db, user, deal_id)
    row = db.get(SponsorshipDeliverable, deliverable_id)
    if row is None or row.deal_id != deal.id:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    if row.status not in {"pending", "in_progress", "rejected"}:
        raise HTTPException(status_code=400, detail="Cannot submit this deliverable")
    row.proof_url = payload.proof_url.strip()
    if payload.proof_notes:
        row.proof_notes = payload.proof_notes
    row.status = "submitted"
    row.submitted_by_user_id = user.id
    row.submitted_at = _now()
    row.rejection_reason = None
    write_audit_log(
        db,
        action="sponsorship_deliverables.submit",
        actor_user_id=user.id,
        resource_type="sponsorship_deliverable",
        resource_id=str(row.id),
        details={"deal_id": str(deal.id)},
    )
    _notify_submitted(db, deal=deal, row=row)
    db.commit()
    db.refresh(row)
    return _serialize(row, host_can_edit=True)


def sponsor_list_deliverables(
    db: Session, user: User, sponsor_id: uuid.UUID, deal_id: uuid.UUID
) -> list[dict[str, Any]]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    can_review = False
    try:
        require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
        can_review = True
    except HTTPException:
        can_review = False
    rows = list(
        db.scalars(
            select(SponsorshipDeliverable)
            .where(SponsorshipDeliverable.deal_id == deal.id)
            .order_by(SponsorshipDeliverable.due_at.nulls_last(), SponsorshipDeliverable.created_at)
        )
    )
    return [_serialize(r, sponsor_can_review=can_review) for r in rows]


def sponsor_approve_deliverable(
    db: Session, user: User, sponsor_id: uuid.UUID, deal_id: uuid.UUID, deliverable_id: uuid.UUID
) -> dict[str, Any]:
    require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    row = db.get(SponsorshipDeliverable, deliverable_id)
    if row is None or row.deal_id != deal.id:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    if row.status not in SPONSOR_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="Deliverable is not awaiting review")
    row.status = "completed"
    row.approved_by_user_id = user.id
    row.approved_at = _now()
    write_audit_log(
        db,
        action="sponsorship_deliverables.approve",
        actor_user_id=user.id,
        resource_type="sponsorship_deliverable",
        resource_id=str(row.id),
        details={},
    )
    _notify_approved(db, deal=deal, row=row)
    _maybe_complete_placement(db, deal)
    db.commit()
    db.refresh(row)
    return _serialize(row, sponsor_can_review=False)


def sponsor_reject_deliverable(
    db: Session,
    user: User,
    sponsor_id: uuid.UUID,
    deal_id: uuid.UUID,
    deliverable_id: uuid.UUID,
    payload: SponsorDeliverableReject,
) -> dict[str, Any]:
    require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    row = db.get(SponsorshipDeliverable, deliverable_id)
    if row is None or row.deal_id != deal.id:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    if row.status not in SPONSOR_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="Deliverable is not awaiting review")
    row.status = "rejected"
    row.rejection_reason = payload.rejection_reason.strip()
    row.approved_by_user_id = None
    row.approved_at = None
    write_audit_log(
        db,
        action="sponsorship_deliverables.reject",
        actor_user_id=user.id,
        resource_type="sponsorship_deliverable",
        resource_id=str(row.id),
        details={},
    )
    _notify_rejected(db, deal=deal, row=row)
    db.commit()
    db.refresh(row)
    return _serialize(row, sponsor_can_review=False)


def admin_list_deliverables(db: Session, deal_id: uuid.UUID) -> list[dict[str, Any]]:
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    rows = list(
        db.scalars(
            select(SponsorshipDeliverable)
            .where(SponsorshipDeliverable.deal_id == deal.id)
            .order_by(SponsorshipDeliverable.created_at)
        )
    )
    return [_serialize(r) for r in rows]


def admin_patch_deliverable(
    db: Session,
    actor: User,
    deal_id: uuid.UUID,
    deliverable_id: uuid.UUID,
    payload: AdminDeliverablePatch,
) -> dict[str, Any]:
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    row = db.get(SponsorshipDeliverable, deliverable_id)
    if row is None or row.deal_id != deal.id:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        st = data["status"]
        if st not in DELIVERABLE_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        row.status = st
    if "due_at" in data:
        row.due_at = data["due_at"]
    if "rejection_reason" in data:
        row.rejection_reason = data["rejection_reason"]
    write_audit_log(
        db,
        action="sponsorship_deliverables.admin_override",
        actor_user_id=actor.id,
        resource_type="sponsorship_deliverable",
        resource_id=str(row.id),
        details={"status": row.status},
    )
    _maybe_complete_placement(db, deal)
    db.commit()
    db.refresh(row)
    return _serialize(row)


def deliverables_summary_for_sponsor(
    db: Session, sponsor_id: uuid.UUID, *, campaign_id: uuid.UUID | None = None
) -> dict[str, Any]:
    q = select(SponsorshipDeal.id).where(
        SponsorshipDeal.sponsor_id == sponsor_id,
        SponsorshipDeal.status.in_(("active", "completed", "paid")),
    )
    if campaign_id is not None:
        q = q.where(SponsorshipDeal.campaign_id == campaign_id)
    deal_ids = [row[0] for row in db.execute(q).all()]
    counts = deliverable_counts_for_deals(db, deal_ids=deal_ids)
    return {
        **counts,
        "completion_rate": completion_rate(counts),
    }


def deliverables_summary_for_host(db: Session, host_id: uuid.UUID) -> dict[str, Any]:
    deal_ids = [
        row[0]
        for row in db.execute(
            select(SponsorshipDeal.id).where(
                SponsorshipDeal.host_id == host_id,
                SponsorshipDeal.status.in_(("active", "completed", "paid")),
            )
        ).all()
    ]
    counts = deliverable_counts_for_deals(db, deal_ids=deal_ids)
    active_deals = int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipDeal)
            .where(
                SponsorshipDeal.host_id == host_id,
                SponsorshipDeal.status == "active",
            )
        )
        or 0
    )
    return {
        "active_deals": active_deals,
        **counts,
        "pending_deliverables": counts["pending"] + counts["in_progress"] + counts["submitted"],
        "completion_rate": completion_rate(counts),
    }
