"""Ambassadors email + in-app/push notifications (phase 15).

Privacy: event/campaign names and status words only — never buyer PII,
payment refs, order IDs, commission amounts with gateway refs, or raw IP.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.email.service import enqueue_template
from app.events.models import Event
from app.hosts.models import Host
from app.promos.ambassador_domain import (
    AmbassadorConversion,
    AmbassadorFraudFlag,
    AmbassadorParticipant,
)
from app.promos.models import Ambassador, AmbassadorCampaign, AmbassadorSale
from app.users.models import User
from app.users.service import get_user_by_id

logger = logging.getLogger(__name__)

# Host milestone thresholds (confirmed non-reversed sales on a campaign).
HOST_MILESTONES = (1, 10, 25, 50)


def _safe_notify_user(
    db: Session,
    *,
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    link_path: str,
    dedupe_key: str,
    push_context: dict | None = None,
) -> None:
    try:
        from app.notifications.service import notify_user

        notify_user(
            db,
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            link_path=link_path,
            dedupe_key=dedupe_key,
            send_push=True,
            push_context=push_context,
        )
    except Exception:  # noqa: BLE001 — never block ambassador flows
        logger.exception("ambassador notify failed kind=%s user=%s", kind, user_id)


def _event_title(db: Session, event_id: UUID | None) -> str:
    if event_id is None:
        return "your event"
    event = db.get(Event, event_id)
    return event.title if event else "your event"


def _campaign_label(db: Session, campaign: AmbassadorCampaign | None) -> str:
    if campaign is None:
        return "Ambassadors"
    if campaign.name:
        return campaign.name.strip()
    return _event_title(db, campaign.event_id)


def notify_ambassador_joined(
    db: Session,
    *,
    user: User,
    event_id: UUID | None,
    campaign: AmbassadorCampaign | None = None,
    enrollment_id: UUID,
) -> None:
    """User joined (or rejoined) an Ambassadors campaign."""
    if user.email is None:
        return
    title = _event_title(db, event_id or (campaign.event_id if campaign else None))
    campaign_name = _campaign_label(db, campaign)
    enqueue_template(
        db,
        template="ambassador_joined",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"ambassador_joined:{enrollment_id}",
        context={
            "event_title": title,
            "campaign_name": campaign_name,
            "cta_path": "/dashboard/ambassador",
        },
    )
    _safe_notify_user(
        db,
        user_id=user.id,
        kind="ambassador.joined",
        title="You’re promoting on Pàdéyá",
        body=f"You’re now an Ambassador for {title}. Share your link to earn.",
        link_path="/dashboard/ambassador/links",
        dedupe_key=f"ambassador_joined:{enrollment_id}",
        push_context={"event_title": title, "campaign_name": campaign_name},
    )


def notify_ambassador_first_sale(
    db: Session,
    *,
    user_id: UUID,
    event_id: UUID | None,
    enrollment_id: UUID,
) -> None:
    user = get_user_by_id(db, user_id)
    if user is None or not user.email:
        return
    title = _event_title(db, event_id)
    enqueue_template(
        db,
        template="ambassador_first_sale",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"ambassador_first_sale:{enrollment_id}",
        context={
            "event_title": title,
            "cta_path": "/dashboard/ambassador/earnings",
        },
    )
    _safe_notify_user(
        db,
        user_id=user.id,
        kind="ambassador.first_sale",
        title="First Ambassador sale",
        body=f"Your first verified sale for {title} is in.",
        link_path="/dashboard/ambassador/earnings",
        dedupe_key=f"ambassador_first_sale:{enrollment_id}",
        push_context={"event_title": title},
    )


def notify_ambassador_commission_payable(
    db: Session,
    *,
    user_id: UUID,
    event_id: UUID | None,
    sale_id: UUID,
) -> None:
    """Reward approved — ambassador can review earnings (no buyer PII)."""
    user = get_user_by_id(db, user_id)
    if user is None or not user.email:
        return
    title = _event_title(db, event_id)
    enqueue_template(
        db,
        template="ambassador_commission_payable",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"ambassador_commission_payable:{sale_id}",
        context={
            "event_title": title,
            "cta_path": "/dashboard/ambassador/earnings",
        },
    )
    _safe_notify_user(
        db,
        user_id=user.id,
        kind="ambassador.reward_approved",
        title="Reward approved",
        body=f"Your Ambassador reward for {title} was approved.",
        link_path="/dashboard/ambassador/earnings",
        dedupe_key=f"ambassador_reward_approved:{sale_id}",
        push_context={"event_title": title},
    )


def notify_ambassador_reward_rejected(
    db: Session,
    *,
    user_id: UUID,
    event_id: UUID | None,
    sale_id: UUID,
) -> None:
    user = get_user_by_id(db, user_id)
    if user is None or not user.email:
        return
    title = _event_title(db, event_id)
    enqueue_template(
        db,
        template="ambassador_reward_rejected",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"ambassador_reward_rejected:{sale_id}",
        context={
            "event_title": title,
            "cta_path": "/dashboard/ambassador/earnings",
        },
    )
    _safe_notify_user(
        db,
        user_id=user.id,
        kind="ambassador.reward_rejected",
        title="Reward not approved",
        body=f"An Ambassador reward for {title} was not approved.",
        link_path="/dashboard/ambassador/earnings",
        dedupe_key=f"ambassador_reward_rejected:{sale_id}",
        push_context={"event_title": title},
    )


def notify_ambassador_payout_ready(
    db: Session,
    *,
    user_id: UUID,
    event_id: UUID | None,
    sale_id: UUID,
) -> None:
    """Reward marked paid — privacy-safe; no bank or buyer details."""
    user = get_user_by_id(db, user_id)
    if user is None or not user.email:
        return
    title = _event_title(db, event_id)
    enqueue_template(
        db,
        template="ambassador_payout_ready",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"ambassador_payout_ready:{sale_id}",
        context={
            "event_title": title,
            "cta_path": "/dashboard/ambassador/payouts",
        },
    )
    _safe_notify_user(
        db,
        user_id=user.id,
        kind="ambassador.reward_marked_paid",
        title="Reward marked paid",
        body=f"An Ambassador reward for {title} was marked paid.",
        link_path="/dashboard/ambassador/payouts",
        dedupe_key=f"ambassador_reward_marked_paid:{sale_id}",
        push_context={"event_title": title},
    )


def notify_ambassador_reward_reversed(
    db: Session,
    *,
    user_id: UUID,
    event_id: UUID | None,
    sale_id: UUID,
) -> None:
    user = get_user_by_id(db, user_id)
    if user is None or not user.email:
        return
    title = _event_title(db, event_id)
    enqueue_template(
        db,
        template="ambassador_reward_reversed",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"ambassador_reward_reversed:{sale_id}",
        context={
            "event_title": title,
            "cta_path": "/dashboard/ambassador/earnings",
        },
    )
    _safe_notify_user(
        db,
        user_id=user.id,
        kind="ambassador.reward_reversed",
        title="Reward reversed",
        body=f"An Ambassador reward for {title} was reversed.",
        link_path="/dashboard/ambassador/earnings",
        dedupe_key=f"ambassador_reward_reversed:{sale_id}",
        push_context={"event_title": title},
    )


def notify_host_owner_team_reward_action(
    db: Session,
    *,
    host: Host,
    event_id: UUID | None,
    campaign_id: UUID | None,
    sale_id: UUID,
    action: str,
) -> None:
    """Host owner alert when a team member approves or marks a reward paid."""
    if action not in {"approved", "paid"}:
        return
    owner = get_user_by_id(db, host.user_id)
    if owner is None or not owner.email:
        return
    title = _event_title(db, event_id)
    verb = "approved a reward" if action == "approved" else "marked a reward paid"
    link = (
        f"/host/ambassadors/campaigns/{campaign_id}"
        if campaign_id
        else "/host/ambassadors/conversions"
    )
    enqueue_template(
        db,
        template="host_ambassador_team_reward_action",
        to=owner.email,
        recipient_user_id=owner.id,
        dedupe_key=f"host_team_reward:{action}:{sale_id}",
        context={
            "event_title": title,
            "action_verb": verb,
            "cta_path": link,
        },
    )
    _safe_notify_user(
        db,
        user_id=owner.id,
        kind="host.ambassador_team_reward",
        title="Team Ambassadors update",
        body=f"A team member {verb} for {title}.",
        link_path=link,
        dedupe_key=f"host_team_reward:{action}:{sale_id}",
        push_context={"event_title": title, "action": action, "action_verb": verb},
    )


def notify_host_owner_suspicious_reversal(
    db: Session,
    *,
    host: Host,
    event_id: UUID | None,
    campaign_id: UUID | None,
    sale_id: UUID,
) -> None:
    owner = get_user_by_id(db, host.user_id)
    if owner is None or not owner.email:
        return
    title = _event_title(db, event_id)
    link = (
        f"/host/ambassadors/campaigns/{campaign_id}"
        if campaign_id
        else "/host/ambassadors/conversions"
    )
    enqueue_template(
        db,
        template="host_ambassador_suspicious_reversal",
        to=owner.email,
        recipient_user_id=owner.id,
        dedupe_key=f"host_suspicious_reversal:{sale_id}",
        context={
            "event_title": title,
            "cta_path": link,
        },
    )
    _safe_notify_user(
        db,
        user_id=owner.id,
        kind="host.ambassador_suspicious_reversal",
        title="Ambassadors reversal flagged",
        body=(
            f"A reward reversal for {title} was flagged for review "
            "(suspicious Ambassadors activity)."
        ),
        link_path=link,
        dedupe_key=f"host_suspicious_reversal:{sale_id}",
        push_context={"event_title": title},
    )


def notify_admins_high_value_reward_paid(
    db: Session,
    *,
    sale_id: UUID,
    event_id: UUID | None,
) -> None:
    title = _event_title(db, event_id)
    try:
        from app.notifications.triggers import notify_admins_report

        notify_admins_report(
            db,
            report_kind="ambassador_high_value_paid",
            report_id=sale_id,
            title="High-value Ambassador reward paid",
            body=(
                f"A high-value Ambassador reward for {title} was marked paid."
            ),
            link_path="/admin/ambassadors/payouts",
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "admin high-value reward notify failed sale=%s", sale_id
        )


def notify_admins_suspicious_reward_reversal(
    db: Session,
    *,
    sale_id: UUID,
    event_id: UUID | None,
) -> None:
    title = _event_title(db, event_id)
    try:
        from app.notifications.triggers import notify_admins_report

        notify_admins_report(
            db,
            report_kind="ambassador_suspicious_reversal",
            report_id=sale_id,
            title="Suspicious Ambassador reward reversal",
            body=(
                f"A reward reversal for {title} coincided with an open "
                "Ambassadors fraud flag."
            ),
            link_path="/admin/ambassadors/fraud",
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "admin suspicious reversal notify failed sale=%s", sale_id
        )


def dispatch_reward_status_notifications(
    db: Session,
    *,
    actor_user_id: UUID,
    actor_type: str,
    amb: Ambassador,
    campaign: AmbassadorCampaign | None,
    sale: AmbassadorSale,
    previous: str,
    status: str,
    fraud_flagged: bool = False,
) -> None:
    """Fan out privacy-safe notifications after a reward status change."""
    if previous == status:
        return

    event_id = sale.event_id or (campaign.event_id if campaign else None)
    campaign_id = (
        campaign.id
        if campaign is not None
        else getattr(amb, "campaign_id", None)
    )

    if amb.user_id is not None:
        if status == "approved":
            notify_ambassador_commission_payable(
                db,
                user_id=amb.user_id,
                event_id=event_id,
                sale_id=sale.id,
            )
        elif status == "rejected":
            notify_ambassador_reward_rejected(
                db,
                user_id=amb.user_id,
                event_id=event_id,
                sale_id=sale.id,
            )
        elif status == "paid":
            notify_ambassador_payout_ready(
                db,
                user_id=amb.user_id,
                event_id=event_id,
                sale_id=sale.id,
            )
        elif status == "reversed":
            notify_ambassador_reward_reversed(
                db,
                user_id=amb.user_id,
                event_id=event_id,
                sale_id=sale.id,
            )

    host_id = None
    if campaign is not None and campaign.host_id is not None:
        host_id = campaign.host_id
    elif amb.host_id is not None:
        host_id = amb.host_id
    host = db.get(Host, host_id) if host_id else None

    if (
        host is not None
        and actor_type == "team_member"
        and status in {"approved", "paid"}
        and actor_user_id != host.user_id
    ):
        notify_host_owner_team_reward_action(
            db,
            host=host,
            event_id=event_id,
            campaign_id=campaign_id,
            sale_id=sale.id,
            action=status,
        )

    if status == "reversed" and fraud_flagged:
        if host is not None:
            notify_host_owner_suspicious_reversal(
                db,
                host=host,
                event_id=event_id,
                campaign_id=campaign_id,
                sale_id=sale.id,
            )
        notify_admins_suspicious_reward_reversal(
            db, sale_id=sale.id, event_id=event_id
        )

    if status == "paid":
        from decimal import Decimal

        from app.runtime_settings import get_runtime_setting

        threshold = Decimal(
            str(get_runtime_setting("ambassador_high_value_reward_ngn", db=db) or 0)
        )
        commission = Decimal(str(sale.commission_owed or 0))
        if threshold > 0 and commission >= threshold:
            notify_admins_high_value_reward_paid(
                db, sale_id=sale.id, event_id=event_id
            )


def _notify_participants_campaign_status(
    db: Session,
    *,
    campaign: AmbassadorCampaign,
    template: str,
    kind: str,
    title: str,
    body_fn,
    link_path: str = "/dashboard/ambassador",
) -> None:
    event_title = _event_title(db, campaign.event_id)
    campaign_name = _campaign_label(db, campaign)
    # Domain participants
    participants = list(
        db.scalars(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.campaign_id == campaign.id,
                AmbassadorParticipant.status == "active",
            )
        )
    )
    notified: set[UUID] = set()
    for row in participants:
        if row.user_id in notified:
            continue
        notified.add(row.user_id)
        user = get_user_by_id(db, row.user_id)
        if user is None or not user.email:
            continue
        enqueue_template(
            db,
            template=template,
            to=user.email,
            recipient_user_id=user.id,
            dedupe_key=f"{template}:{campaign.id}:{user.id}",
            context={
                "event_title": event_title,
                "campaign_name": campaign_name,
                "cta_path": link_path,
            },
        )
        _safe_notify_user(
            db,
            user_id=user.id,
            kind=kind,
            title=title,
            body=body_fn(event_title),
            link_path=link_path,
            dedupe_key=f"{template}:{campaign.id}:{user.id}",
            push_context={
                "event_title": event_title,
                "campaign_name": campaign_name,
            },
        )
    # Legacy v1 ambassadors on this campaign
    legacy = list(
        db.scalars(
            select(Ambassador).where(
                Ambassador.campaign_id == campaign.id,
                Ambassador.status == "active",
                Ambassador.user_id.is_not(None),
            )
        )
    )
    for amb in legacy:
        if amb.user_id is None or amb.user_id in notified:
            continue
        notified.add(amb.user_id)
        user = get_user_by_id(db, amb.user_id)
        if user is None or not user.email:
            continue
        enqueue_template(
            db,
            template=template,
            to=user.email,
            recipient_user_id=user.id,
            dedupe_key=f"{template}:{campaign.id}:{user.id}",
            context={
                "event_title": event_title,
                "campaign_name": campaign_name,
                "cta_path": link_path,
            },
        )
        _safe_notify_user(
            db,
            user_id=user.id,
            kind=kind,
            title=title,
            body=body_fn(event_title),
            link_path=link_path,
            dedupe_key=f"{template}:{campaign.id}:{user.id}",
            push_context={
                "event_title": event_title,
                "campaign_name": campaign_name,
            },
        )


def notify_campaign_paused(db: Session, *, campaign: AmbassadorCampaign) -> None:
    _notify_participants_campaign_status(
        db,
        campaign=campaign,
        template="ambassador_campaign_paused",
        kind="ambassador.campaign_paused",
        title="Campaign paused",
        body_fn=lambda t: f"The Ambassadors campaign for {t} is paused.",
    )


def notify_campaign_ended(db: Session, *, campaign: AmbassadorCampaign) -> None:
    _notify_participants_campaign_status(
        db,
        campaign=campaign,
        template="ambassador_campaign_ended",
        kind="ambassador.campaign_ended",
        title="Campaign ended",
        body_fn=lambda t: f"The Ambassadors campaign for {t} has ended.",
    )


def maybe_notify_host_milestone(
    db: Session,
    *,
    campaign: AmbassadorCampaign | None,
    confirmed_sales_count: int,
) -> None:
    """Notify campaign host when sales hit milestone thresholds."""
    if campaign is None or campaign.host_id is None:
        return
    if confirmed_sales_count not in HOST_MILESTONES:
        return
    host = db.get(Host, campaign.host_id)
    if host is None:
        return
    owner = get_user_by_id(db, host.user_id)
    if owner is None or not owner.email:
        return
    event_title = _event_title(db, campaign.event_id)
    enqueue_template(
        db,
        template="host_ambassador_milestone",
        to=owner.email,
        recipient_user_id=owner.id,
        dedupe_key=f"host_ambassador_milestone:{campaign.id}:{confirmed_sales_count}",
        context={
            "event_title": event_title,
            "sale_count": confirmed_sales_count,
            "cta_path": f"/host/ambassadors/campaigns/{campaign.id}",
        },
    )
    _safe_notify_user(
        db,
        user_id=owner.id,
        kind="host.ambassador_milestone",
        title="Ambassadors milestone",
        body=(
            f"Ambassadors hit {confirmed_sales_count} verified "
            f"sale{'s' if confirmed_sales_count != 1 else ''} for {event_title}."
        ),
        link_path=f"/host/ambassadors/campaigns/{campaign.id}",
        dedupe_key=f"host_ambassador_milestone:{campaign.id}:{confirmed_sales_count}",
        push_context={
            "event_title": event_title,
            "sale_count": confirmed_sales_count,
        },
    )


def notify_admins_suspicious_activity(
    db: Session,
    *,
    flag: AmbassadorFraudFlag,
) -> None:
    """Admin alert when a new click-spike (or similar) fraud flag opens."""
    try:
        from app.notifications.triggers import notify_admins_report

        notify_admins_report(
            db,
            report_kind="ambassador_fraud",
            report_id=flag.id,
            title="Ambassadors fraud flag",
            body="Suspicious Ambassadors click activity was flagged for review.",
            link_path="/admin/ambassadors/fraud",
        )
        from app.email.admin_triggers import admin_notify_ambassador_fraud_signal

        admin_notify_ambassador_fraud_signal(
            db,
            campaign_id=flag.campaign_id or flag.id,
            event_title=_event_title(db, None),
            host_name="Host",
            campaign_name="Ambassadors campaign",
            signal_summary=flag.flag_type.replace("_", " "),
        )
    except Exception:  # noqa: BLE001
        logger.exception("admin ambassador fraud notify failed flag=%s", flag.id)


def on_v1_sale_created(
    db: Session,
    *,
    ambassador: Ambassador,
    sale: AmbassadorSale,
) -> None:
    """After a new v1 ambassador_sale is created (verified payment)."""
    if ambassador.user_id is None:
        return
    # First sale for this enrollment?
    prior = int(
        db.scalar(
            select(func.count())
            .select_from(AmbassadorSale)
            .where(
                AmbassadorSale.ambassador_id == ambassador.id,
                AmbassadorSale.status != "reversed",
                AmbassadorSale.id != sale.id,
            )
        )
        or 0
    )
    if prior == 0:
        notify_ambassador_first_sale(
            db,
            user_id=ambassador.user_id,
            event_id=sale.event_id or ambassador.event_id,
            enrollment_id=ambassador.id,
        )
    campaign = (
        db.get(AmbassadorCampaign, ambassador.campaign_id)
        if ambassador.campaign_id
        else None
    )
    if campaign is not None:
        amb_ids = list(
            db.scalars(
                select(Ambassador.id).where(
                    Ambassador.campaign_id == campaign.id
                )
            )
        )
        confirmed = int(
            db.scalar(
                select(func.count())
                .select_from(AmbassadorSale)
                .where(
                    AmbassadorSale.ambassador_id.in_(amb_ids or [ambassador.id]),
                    AmbassadorSale.status != "reversed",
                )
            )
            or 0
        )
        maybe_notify_host_milestone(
            db, campaign=campaign, confirmed_sales_count=confirmed
        )


def on_domain_conversions_created(
    db: Session,
    *,
    participant: AmbassadorParticipant,
    campaign: AmbassadorCampaign,
    created: list[AmbassadorConversion],
) -> None:
    if not created:
        return
    prior = int(
        db.scalar(
            select(func.count())
            .select_from(AmbassadorConversion)
            .where(
                AmbassadorConversion.participant_id == participant.id,
                AmbassadorConversion.status != "reversed",
                AmbassadorConversion.id.notin_([c.id for c in created]),
            )
        )
        or 0
    )
    if prior == 0:
        notify_ambassador_first_sale(
            db,
            user_id=participant.user_id,
            event_id=campaign.event_id,
            enrollment_id=participant.id,
        )
    confirmed = int(
        db.scalar(
            select(func.count())
            .select_from(AmbassadorConversion)
            .where(
                AmbassadorConversion.campaign_id == campaign.id,
                AmbassadorConversion.status != "reversed",
            )
        )
        or 0
    )
    maybe_notify_host_milestone(
        db, campaign=campaign, confirmed_sales_count=confirmed
    )
