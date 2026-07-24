"""Ambassador conversion reward status — host owner / team / platform admin.

Two surfaces (admin is not exclusive for host-owned campaigns):

- Host: ``set_host_conversion_reward_status`` — normal approve/pay workflow
  for host-owned campaigns (owner or team perms; no ``admin.full_access``).
- Admin: ``set_conversion_reward_status`` — platform oversight, fraud,
  support escalation, platform-wide campaigns, emergency correction.

Platform campaigns: admin override path only.
Ambassadors cannot change reward status on their own conversions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ambassadors.reward_audit import (
    list_host_reward_audits,
    list_reward_audits_for_conversion,
    resolve_actor_type,
    write_reward_audit,
)
from app.events.models import Event
from app.hosts.team_access import require_host_for_permission
from app.payments.models import Order
from app.promos.models import Ambassador, AmbassadorCampaign, AmbassadorSale
from app.teams.permissions import (
    has_event_permission,
    has_host_permission,
    is_host_owner,
)
from app.users.models import User
from app.users.service import user_has_permission, user_has_role

HOST_REWARD_STATUSES = frozenset({"approved", "rejected", "paid", "reversed"})
ADMIN_REWARD_STATUSES = frozenset({"attributed", "approved", "paid", "rejected"})
SALE_ACTIVE = frozenset({"attributed", "approved", "paid"})
PAID_ORDER_STATUSES = frozenset({"paid"})
UNVERIFIED_ORDER_STATUSES = frozenset(
    {"pending", "failed", "cancelled", "expired", "refunded", "partially_refunded"}
)

# Any listed permission is sufficient for the action.
ACTION_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "approve": ("ambassadors.approve_rewards",),
    "reject": ("ambassadors.approve_rewards", "ambassadors.reject_rewards"),
    "mark_paid": ("ambassadors.mark_rewards_paid", "finance.manage_payouts"),
    "reopen": ("ambassadors.approve_rewards",),
    "reverse": ("ambassadors.reverse_rewards",),
    "view": ("ambassadors.view_conversions",),
    "export": ("ambassadors.export", "finance.view_payouts"),
}


def is_platform_admin(user: User) -> bool:
    return user_has_role(user, "super_admin") or user_has_permission(
        user, "admin.full_access"
    )


def _campaign_for_sale(
    db: Session, sale: AmbassadorSale
) -> tuple[Ambassador, AmbassadorCampaign | None]:
    amb = db.get(Ambassador, sale.ambassador_id)
    if amb is None:
        raise HTTPException(status_code=404, detail="Conversion not found")
    campaign = None
    if amb.campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, amb.campaign_id)
    return amb, campaign


def is_platform_owned_campaign(campaign: AmbassadorCampaign | None) -> bool:
    if campaign is None:
        return False
    if (campaign.source or "").lower() == "platform":
        return True
    if (campaign.campaign_type or "").lower() == "platform":
        return True
    return False


def host_id_for_sale(
    amb: Ambassador, campaign: AmbassadorCampaign | None
) -> UUID:
    if campaign is not None and campaign.host_id is not None:
        return campaign.host_id
    return amb.host_id


def permissions_for_status(status: str) -> tuple[str, ...]:
    if status == "approved":
        return ACTION_PERMISSIONS["approve"]
    if status == "rejected":
        return ACTION_PERMISSIONS["reject"]
    if status == "paid":
        return ACTION_PERMISSIONS["mark_paid"]
    if status == "reversed":
        return ACTION_PERMISSIONS["reverse"]
    if status == "attributed":
        return ACTION_PERMISSIONS["reopen"]
    raise HTTPException(status_code=400, detail="Invalid reward status")


def _has_any_team_permission(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
    event_id: UUID | None,
    permissions: tuple[str, ...],
) -> bool:
    for key in permissions:
        if event_id is not None and has_event_permission(
            db, user_id, host_id, event_id, key
        ):
            return True
        if has_host_permission(db, user_id, host_id, key):
            return True
    return False


def assert_can_manage_sale_reward(
    db: Session,
    *,
    user: User,
    sale: AmbassadorSale,
    permission: str | tuple[str, ...],
    require_host_id: UUID | None = None,
) -> tuple[Ambassador, AmbassadorCampaign | None]:
    """Raise 403/404 when actor cannot manage this sale's reward."""
    permissions = (permission,) if isinstance(permission, str) else tuple(permission)
    amb, campaign = _campaign_for_sale(db, sale)
    sale_host_id = host_id_for_sale(amb, campaign)

    if require_host_id is not None and sale_host_id != require_host_id:
        raise HTTPException(status_code=404, detail="Conversion not found")

    if is_platform_admin(user) and require_host_id is None:
        return amb, campaign

    if is_platform_owned_campaign(campaign):
        raise HTTPException(
            status_code=403,
            detail="Only platform admins can manage rewards for platform campaigns",
        )

    if amb.user_id is not None and amb.user_id == user.id:
        raise HTTPException(
            status_code=403,
            detail="Ambassadors cannot manage their own reward status",
        )

    if is_host_owner(db, user.id, sale_host_id):
        return amb, campaign

    if not _has_any_team_permission(
        db,
        user_id=user.id,
        host_id=sale_host_id,
        event_id=sale.event_id,
        permissions=permissions,
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Missing permission: {permissions[0]}",
        )
    return amb, campaign


def _require_reason(status: str, reason: str | None) -> str:
    clean = (reason or "").strip()
    if status in {"rejected", "reversed"} and len(clean) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Reason is required when status is {status}",
        )
    return clean[:500]


def _assert_order_verified_for_approve(db: Session, sale: AmbassadorSale) -> Order:
    order = db.get(Order, sale.order_id)
    if order is None:
        raise HTTPException(
            status_code=400,
            detail="Conversion has no linked order",
        )
    status = (order.status or "").lower()
    if status in UNVERIFIED_ORDER_STATUSES or status not in PAID_ORDER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve a conversion without a verified paid payment",
        )
    return order


def _assert_not_self_referral(db: Session, amb: Ambassador, order: Order) -> None:
    from app.ambassadors.fraud import is_self_referral

    if is_self_referral(
        ambassador_user_id=amb.user_id,
        buyer_user_id=order.buyer_user_id,
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot approve a self-referral conversion",
        )


def serialize_conversion(
    db: Session,
    sale: AmbassadorSale,
    *,
    include_order_refs: bool = False,
) -> dict:
    """Host-safe conversion DTO by default.

    Hosts/team see ambassador + campaign + amounts + status — never buyer PII,
    payment refs, QRs, venue, shipping, or Fan Connect. Platform admin paths
    may pass ``include_order_refs=True`` for oversight.
    """
    amb = db.get(Ambassador, sale.ambassador_id)
    event = db.get(Event, sale.event_id)
    campaign = None
    if amb is not None and amb.campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, amb.campaign_id)
    payout_status = sale.status
    if sale.status == "paid":
        payout_status = "paid"
    elif sale.status == "approved":
        payout_status = "payable"
    elif sale.status in {"rejected", "reversed"}:
        payout_status = sale.status
    else:
        payout_status = "pending"

    data = {
        "id": sale.id,
        "ambassador_id": sale.ambassador_id,
        "event_id": sale.event_id,
        "tickets_sold": sale.tickets_sold,
        "merch_units_sold": getattr(sale, "merch_units_sold", 0) or 0,
        "revenue_amount": sale.revenue_amount,
        "eligible_sale_amount": sale.revenue_amount,
        "commission_owed": sale.commission_owed,
        "commission_amount": sale.commission_owed,
        "commission_type": getattr(sale, "commission_type", None),
        "hold_until": getattr(sale, "hold_until", None),
        "status": sale.status,
        "payout_status": payout_status,
        "created_at": sale.created_at,
        "reversed_at": getattr(sale, "reversed_at", None),
        "reversed_by_user_id": getattr(sale, "reversed_by_user_id", None),
        "reversal_reason": getattr(sale, "reversal_reason", None),
        "rejection_reason": getattr(sale, "rejection_reason", None),
        "payout_reference": getattr(sale, "payout_reference", None),
        "payout_note": getattr(sale, "payout_note", None),
        "reward_status_updated_at": getattr(sale, "reward_status_updated_at", None),
        "event_title": event.title if event else None,
        "ambassador_display_name": amb.display_name if amb else None,
        "ambassador_referral_code": amb.referral_code if amb else None,
        "ambassador_user_id": amb.user_id if amb else None,
        "host_id": amb.host_id if amb else None,
        "campaign_id": amb.campaign_id if amb else None,
        "campaign_name": campaign.name if campaign else None,
    }
    if include_order_refs:
        data["order_id"] = sale.order_id
    return data


def _apply_payout_meta(
    sale: AmbassadorSale,
    *,
    payout_reference: str | None,
    payout_note: str | None,
) -> None:
    if payout_reference is not None:
        sale.payout_reference = payout_reference.strip()[:120] or None
    if payout_note is not None:
        sale.payout_note = payout_note.strip()[:500] or None


def _campaign_has_open_fraud_flag(
    db: Session, *, campaign_id: UUID | None
) -> bool:
    if campaign_id is None:
        return False
    from app.promos.ambassador_domain import AmbassadorFraudFlag

    row = db.scalar(
        select(AmbassadorFraudFlag.id).where(
            AmbassadorFraudFlag.campaign_id == campaign_id,
            AmbassadorFraudFlag.status == "open",
        )
    )
    return row is not None


def _finalize_reward_change(
    db: Session,
    *,
    actor: User,
    amb: Ambassador,
    campaign: AmbassadorCampaign | None,
    sale: AmbassadorSale,
    previous: str,
    status: str,
    reason: str | None,
    payout_reference: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist structured audit + fan-out notifications (after sale mutation)."""
    host_profile_id = host_id_for_sale(amb, campaign)
    actor_type = resolve_actor_type(
        db, actor=actor, host_profile_id=host_profile_id
    )
    campaign_id = campaign.id if campaign is not None else amb.campaign_id
    write_reward_audit(
        db,
        actor=actor,
        actor_type=actor_type,
        host_profile_id=host_profile_id,
        campaign_id=campaign_id,
        conversion_id=sale.id,
        old_status=previous,
        new_status=status,
        reason=reason,
        payout_reference=payout_reference
        or getattr(sale, "payout_reference", None),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(sale)

    fraud_flagged = status == "reversed" and _campaign_has_open_fraud_flag(
        db, campaign_id=campaign_id
    )
    from app.ambassadors.notifications import dispatch_reward_status_notifications

    dispatch_reward_status_notifications(
        db,
        actor_user_id=actor.id,
        actor_type=actor_type,
        amb=amb,
        campaign=campaign,
        sale=sale,
        previous=previous,
        status=status,
        fraud_flagged=fraud_flagged,
    )
    try:
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


def set_host_conversion_reward_status(
    db: Session,
    *,
    actor: User,
    conversion_id: UUID,
    host_id: UUID | None,
    status: str,
    reason: str | None = None,
    payout_reference: str | None = None,
    payout_note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Host workspace reward-status path for host-owned conversions."""
    if status not in HOST_REWARD_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid reward status")

    permissions = permissions_for_status(status)
    host, _ = require_host_for_permission(
        db, user=actor, host_id=host_id, permission=permissions
    )

    sale = db.get(AmbassadorSale, conversion_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Conversion not found")

    amb, campaign = assert_can_manage_sale_reward(
        db,
        user=actor,
        sale=sale,
        permission=permissions,
        require_host_id=host.id,
    )
    if is_platform_owned_campaign(campaign):
        raise HTTPException(
            status_code=403,
            detail="Platform campaigns are managed by Pàdéyá admin",
        )

    clean_reason = _require_reason(status, reason)
    previous = sale.status

    # Idempotent no-op (still allow payout meta refresh on paid).
    if previous == status:
        if status == "paid":
            _apply_payout_meta(
                sale,
                payout_reference=payout_reference,
                payout_note=payout_note,
            )
            db.commit()
            db.refresh(sale)
        return serialize_conversion(db, sale)

    if previous == "reversed":
        raise HTTPException(
            status_code=400,
            detail="Reversed conversions cannot change reward status",
        )
    if previous == "rejected" and status == "paid":
        raise HTTPException(
            status_code=400,
            detail="Cannot mark a rejected conversion as paid",
        )

    if status == "paid":
        if previous not in {"approved", "paid"}:
            raise HTTPException(
                status_code=400, detail="Approve the conversion before marking paid"
            )
        if previous == "reversed":
            raise HTTPException(
                status_code=400,
                detail="Cannot mark a refunded or reversed conversion as paid",
            )
        order = db.get(Order, sale.order_id)
        if order is not None and (order.status or "").lower() in {
            "refunded",
            "partially_refunded",
            "cancelled",
        }:
            raise HTTPException(
                status_code=400,
                detail="Cannot mark a refunded or reversed conversion as paid",
            )

    if status == "approved":
        if previous not in {"attributed", "approved"}:
            raise HTTPException(
                status_code=400,
                detail="Only attributed conversions can be approved",
            )
        order = _assert_order_verified_for_approve(db, sale)
        _assert_not_self_referral(db, amb, order)
        from app.promos.commission import sale_is_past_hold

        if previous == "attributed" and not sale_is_past_hold(sale):
            raise HTTPException(
                status_code=400,
                detail="Commission is still in the hold period",
            )

    if status == "rejected":
        if previous not in {"attributed", "approved", "rejected"}:
            raise HTTPException(
                status_code=400,
                detail="Only attributed or approved conversions can be rejected",
            )

    if status == "reversed":
        if previous == "paid":
            raise HTTPException(
                status_code=400,
                detail="Paid conversions cannot be reversed — reverse via finance first",
            )
        if previous not in {"attributed", "approved", "rejected", "reversed"}:
            raise HTTPException(
                status_code=400,
                detail="Conversion cannot be reversed from this status",
            )

    now = datetime.now(UTC)
    sale.status = status
    sale.reward_status_updated_at = now
    sale.reward_status_updated_by_user_id = actor.id

    if status == "rejected":
        sale.rejection_reason = clean_reason
    if status == "reversed":
        sale.reversed_at = now
        sale.reversed_by_user_id = actor.id
        sale.reversal_reason = clean_reason
    if status == "paid":
        _apply_payout_meta(
            sale,
            payout_reference=payout_reference,
            payout_note=payout_note,
        )

    _finalize_reward_change(
        db,
        actor=actor,
        amb=amb,
        campaign=campaign,
        sale=sale,
        previous=previous,
        status=status,
        reason=clean_reason or None,
        payout_reference=getattr(sale, "payout_reference", None),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return serialize_conversion(db, sale)


def set_conversion_reward_status(
    db: Session,
    *,
    actor: User,
    sale_id: UUID,
    status: str,
    reason: str | None = None,
    payout_reference: str | None = None,
    payout_note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Admin / shared path (supports attributed reopen)."""
    if status not in ADMIN_REWARD_STATUSES and status != "reversed":
        raise HTTPException(status_code=400, detail="Invalid reward status")
    if status in HOST_REWARD_STATUSES:
        # Admin override without host workspace constraint.
        sale = db.get(AmbassadorSale, sale_id)
        if sale is None:
            raise HTTPException(status_code=404, detail="Conversion not found")
        permissions = permissions_for_status(status)
        amb, campaign = assert_can_manage_sale_reward(
            db, user=actor, sale=sale, permission=permissions
        )
        clean_reason = (
            _require_reason(status, reason)
            if status in {"rejected", "reversed"}
            else (reason or "").strip()[:500]
        )
        previous = sale.status
        if previous == status:
            if status == "paid":
                _apply_payout_meta(
                    sale,
                    payout_reference=payout_reference,
                    payout_note=payout_note,
                )
                db.commit()
                db.refresh(sale)
            return serialize_conversion(db, sale)

        if previous == "reversed" and status != "reversed":
            raise HTTPException(
                status_code=400,
                detail="Reversed conversions cannot change reward status",
            )
        if status == "paid" and previous not in {"approved", "paid"}:
            raise HTTPException(
                status_code=400, detail="Approve the conversion before marking paid"
            )
        if status == "paid" and previous == "reversed":
            raise HTTPException(
                status_code=400,
                detail="Cannot mark a refunded or reversed conversion as paid",
            )
        if status == "approved" and previous not in {"attributed", "approved"}:
            raise HTTPException(
                status_code=400,
                detail="Only attributed conversions can be approved",
            )
        if status == "approved" and previous == "attributed":
            order = _assert_order_verified_for_approve(db, sale)
            _assert_not_self_referral(db, amb, order)
            from app.promos.commission import sale_is_past_hold

            if not sale_is_past_hold(sale):
                raise HTTPException(
                    status_code=400,
                    detail="Commission is still in the hold period",
                )
        if status == "rejected" and previous not in {
            "attributed",
            "approved",
            "rejected",
        }:
            raise HTTPException(
                status_code=400,
                detail="Only attributed or approved conversions can be rejected",
            )
        if status == "reversed":
            if previous == "paid":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Paid conversions cannot be reversed — reverse via finance first"
                    ),
                )
            if len(clean_reason) < 3:
                raise HTTPException(
                    status_code=400, detail="Reversal reason is required"
                )

        now = datetime.now(UTC)
        sale.status = status
        sale.reward_status_updated_at = now
        sale.reward_status_updated_by_user_id = actor.id
        if status == "rejected":
            sale.rejection_reason = clean_reason
        if status == "reversed":
            sale.reversed_at = now
            sale.reversed_by_user_id = actor.id
            sale.reversal_reason = clean_reason
        if status == "paid":
            _apply_payout_meta(
                sale,
                payout_reference=payout_reference,
                payout_note=payout_note,
            )
        _finalize_reward_change(
            db,
            actor=actor,
            amb=amb,
            campaign=campaign,
            sale=sale,
            previous=previous,
            status=status,
            reason=clean_reason or None,
            payout_reference=getattr(sale, "payout_reference", None),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return serialize_conversion(db, sale)

    # attributed reopen (admin)
    sale = db.get(AmbassadorSale, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Conversion not found")
    amb, campaign = assert_can_manage_sale_reward(
        db,
        user=actor,
        sale=sale,
        permission=ACTION_PERMISSIONS["reopen"],
    )
    previous = sale.status
    if previous == status:
        return serialize_conversion(db, sale)
    if previous == "reversed":
        raise HTTPException(
            status_code=400,
            detail="Reversed conversions cannot change reward status",
        )
    if previous not in {"attributed", "approved", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Cannot reopen this conversion to attributed",
        )
    now = datetime.now(UTC)
    sale.status = "attributed"
    sale.reward_status_updated_at = now
    sale.reward_status_updated_by_user_id = actor.id
    _finalize_reward_change(
        db,
        actor=actor,
        amb=amb,
        campaign=campaign,
        sale=sale,
        previous=previous,
        status="attributed",
        reason=None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return serialize_conversion(db, sale)


def reverse_conversion(
    db: Session,
    *,
    actor: User,
    sale_id: UUID,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    return set_conversion_reward_status(
        db,
        actor=actor,
        sale_id=sale_id,
        status="reversed",
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def list_host_conversions(
    db: Session,
    *,
    host_id: UUID,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = (
        select(AmbassadorSale)
        .join(Ambassador, Ambassador.id == AmbassadorSale.ambassador_id)
        .where(Ambassador.host_id == host_id)
        .order_by(AmbassadorSale.created_at.desc())
    )
    if status:
        stmt = stmt.where(AmbassadorSale.status == status)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    return [serialize_conversion(db, s) for s in rows]


def list_host_conversion_audit(
    db: Session,
    *,
    host_id: UUID,
    conversion_id: UUID,
) -> list[dict]:
    """Audit trail for one host-owned conversion (core audit_logs)."""
    sale = db.get(AmbassadorSale, conversion_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Conversion not found")
    amb = db.get(Ambassador, sale.ambassador_id)
    if amb is None or amb.host_id != host_id:
        raise HTTPException(status_code=404, detail="Conversion not found")
    return list_reward_audits_for_conversion(db, conversion_id=conversion_id)


def list_host_campaign_reward_audits(
    db: Session,
    *,
    host_id: UUID,
    campaign_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    return list_host_reward_audits(
        db,
        host_id=host_id,
        campaign_id=campaign_id,
        limit=limit,
        offset=offset,
    )


def export_host_conversions_csv(
    db: Session,
    *,
    host_id: UUID,
    status: str | None = None,
) -> str:
    import csv
    import io

    rows = list_host_conversions(
        db, host_id=host_id, status=status, limit=5000, offset=0
    )
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "id",
            "status",
            "payout_status",
            "commission_owed",
            "eligible_sale_amount",
            "tickets_sold",
            "merch_units_sold",
            "event_title",
            "campaign_name",
            "ambassador_display_name",
            "ambassador_referral_code",
            "created_at",
            "hold_until",
            "reversed_at",
            "reversal_reason",
            "rejection_reason",
            "payout_reference",
            "payout_note",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": str(row["id"]),
                "status": row["status"],
                "payout_status": row.get("payout_status") or row["status"],
                "commission_owed": str(row["commission_owed"]),
                "eligible_sale_amount": str(
                    row.get("eligible_sale_amount") or row["revenue_amount"]
                ),
                "tickets_sold": row["tickets_sold"],
                "merch_units_sold": row["merch_units_sold"],
                "event_title": row.get("event_title") or "",
                "campaign_name": row.get("campaign_name") or "",
                "ambassador_display_name": row.get("ambassador_display_name") or "",
                "ambassador_referral_code": row.get("ambassador_referral_code") or "",
                "created_at": row["created_at"].isoformat()
                if row.get("created_at")
                else "",
                "hold_until": row["hold_until"].isoformat()
                if row.get("hold_until")
                else "",
                "reversed_at": row["reversed_at"].isoformat()
                if row.get("reversed_at")
                else "",
                "reversal_reason": row.get("reversal_reason") or "",
                "rejection_reason": row.get("rejection_reason") or "",
                "payout_reference": row.get("payout_reference") or "",
                "payout_note": row.get("payout_note") or "",
            }
        )
    return buf.getvalue()
