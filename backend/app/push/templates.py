"""Push notification templates — short, generic copy only.

Never include chat bodies, attachment URLs, venues, payments, or addresses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


BRAND = "Pàdéyá"
DEFAULT_ICON = "/brand/padeya-mark.png"
DEFAULT_BADGE = "/brand/padeya-mark.png"


@dataclass(frozen=True)
class PushTemplate:
    name: str
    title: str | Callable[[dict[str, Any]], str]
    body: str | Callable[[dict[str, Any]], str]
    action_url: str | Callable[[dict[str, Any]], str]
    icon_url: str = DEFAULT_ICON
    badge_url: str = DEFAULT_BADGE


def _ctx_str(ctx: dict[str, Any], key: str, default: str = "") -> str:
    val = ctx.get(key)
    return str(val).strip() if val is not None else default


def _event(ctx: dict[str, Any], default: str = "your event") -> str:
    return _ctx_str(ctx, "event_title", default) or default


def _name(ctx: dict[str, Any], default: str = "Someone") -> str:
    for key in ("sender_name", "name", "requester_name", "acceptor_name"):
        val = _ctx_str(ctx, key)
        if val:
            return val
    return default


def _message_body(
    ctx: dict[str, Any],
    *,
    fan_connect: bool = False,
    has_attachments: bool = False,
) -> str:
    from app.push.privacy import message_push_copy

    _title, body = message_push_copy(
        sender_name=_ctx_str(ctx, "sender_name") or _ctx_str(ctx, "name") or None,
        allow_preview=bool(ctx.get("allow_message_preview")),
        has_attachments=has_attachments,
        fan_connect=fan_connect,
    )
    return body


def _t(
    name: str,
    title: str | Callable[[dict[str, Any]], str],
    body: str | Callable[[dict[str, Any]], str],
    action: str | Callable[[dict[str, Any]], str],
) -> PushTemplate:
    return PushTemplate(name, title, body, action)


TEMPLATES: dict[str, PushTemplate] = {
    # --- Tickets ---
    "ticket_confirmed": _t(
        "ticket_confirmed",
        "Ticket confirmed",
        lambda c: f"Your tickets for {_event(c)} are ready on {BRAND}.",
        "/dashboard/tickets",
    ),
    "ticket_qr_ready": _t(
        "ticket_qr_ready",
        "QR ready",
        lambda c: f"Your ticket QR for {_event(c)} is ready.",
        "/dashboard/tickets",
    ),
    "ticket_event_reminder": _t(
        "ticket_event_reminder",
        "Event reminder",
        lambda c: f"{_event(c)} is coming up. Open {BRAND} for your ticket.",
        "/dashboard/tickets",
    ),
    "ticket_event_cancelled": _t(
        "ticket_event_cancelled",
        "Event cancelled",
        lambda c: f"{_event(c)} was cancelled. Details are in {BRAND}.",
        "/dashboard/tickets",
    ),
    "ticket_refund_update": _t(
        "ticket_refund_update",
        "Refund update",
        f"There’s a ticket refund update on {BRAND}.",
        "/dashboard/refunds",
    ),
    # --- Merch ---
    "merch_order_confirmed": _t(
        "merch_order_confirmed",
        "Merch confirmed",
        lambda c: f"Your merch for {_event(c)} is confirmed on {BRAND}.",
        "/dashboard/merchandise",
    ),
    "merch_pickup_ready": _t(
        "merch_pickup_ready",
        "Pickup ready",
        lambda c: f"{_ctx_str(c, 'product_name', 'Your merch')} is ready at the stand.",
        "/dashboard/merchandise",
    ),
    "merch_shipping_update": _t(
        "merch_shipping_update",
        "Shipping update",
        f"Your merch shipping status changed on {BRAND}.",
        "/dashboard/merchandise",
    ),
    "merch_picked_up": _t(
        "merch_picked_up",
        "Merch picked up",
        f"Pickup confirmed. Thanks for shopping on {BRAND}.",
        "/dashboard/merchandise",
    ),
    "merch_refund_update": _t(
        "merch_refund_update",
        "Merch refund",
        f"There’s a merch refund update on {BRAND}.",
        "/dashboard/merchandise",
    ),
    "post_event_drop_available": _t(
        "post_event_drop_available",
        "New drop",
        lambda c: f"A post-event drop for {_event(c)} is available.",
        "/dashboard/merchandise",
    ),
    "merch_cart_reminder": _t(
        "merch_cart_reminder",
        "Cart waiting",
        f"Your merch cart is still waiting on {BRAND}.",
        "/dashboard/cart",
    ),
    # --- Messaging (generic by default; optional name preview via privacy helpers) ---
    "new_message": _t(
        "new_message",
        "New message",
        lambda c: _message_body(c, fan_connect=False),
        lambda c: _ctx_str(c, "action_url", "/dashboard/messages"),
    ),
    "message_request": _t(
        "message_request",
        "Message request",
        f"You have a new message request on {BRAND}.",
        "/dashboard/messages",
    ),
    "attachment_received": _t(
        "attachment_received",
        "New message",
        lambda c: _message_body(c, fan_connect=False, has_attachments=True),
        lambda c: _ctx_str(c, "action_url", "/dashboard/messages"),
    ),
    # --- Fan Connect ---
    "fan_connect_request": _t(
        "fan_connect_request",
        "Fan Connect request",
        lambda c: (
            f"{_name(c)} wants to connect on {BRAND}."
            if c.get("allow_message_preview")
            else f"You have a new Fan Connect request on {BRAND}."
        ),
        "/connect/requests",
    ),
    "fan_connect_accepted": _t(
        "fan_connect_accepted",
        "Connected",
        lambda c: (
            f"{_name(c)} accepted your Fan Connect request."
            if c.get("allow_message_preview")
            else f"Your Fan Connect request was accepted on {BRAND}."
        ),
        lambda c: _ctx_str(c, "action_url", "/connect/connections"),
    ),
    "fan_connect_message": _t(
        "fan_connect_message",
        "New message",
        lambda c: _message_body(c, fan_connect=True),
        lambda c: _ctx_str(c, "action_url", "/dashboard/messages"),
    ),
    # --- Host ---
    "host_ticket_sale": _t(
        "host_ticket_sale",
        "Ticket sale",
        lambda c: f"New ticket sale for {_event(c)}.",
        "/host/analytics",
    ),
    "host_merch_sale": _t(
        "host_merch_sale",
        "Merch sale",
        lambda c: f"New merch sale for {_event(c)}.",
        "/host/merchandise",
    ),
    "host_new_review": _t(
        "host_new_review",
        "New review",
        lambda c: f"You received a new review for {_event(c)}.",
        "/host/reviews",
    ),
    "host_new_follower": _t(
        "host_new_follower",
        "New follower",
        f"Someone followed your Legacy Page on {BRAND}.",
        "/host/followers",
    ),
    "host_sponsor_inquiry": _t(
        "host_sponsor_inquiry",
        "Sponsor inquiry",
        f"A new sponsor inquiry landed on {BRAND}.",
        "/host",
    ),
    # --- Sponsor ---
    "sponsor_inquiry_confirmation": _t(
        "sponsor_inquiry_confirmation",
        "Inquiry received",
        f"We received your sponsorship inquiry on {BRAND}.",
        "/sponsorships",
    ),
    "sponsor_inquiry_host_alert": _t(
        "sponsor_inquiry_host_alert",
        "Sponsor inquiry",
        f"New sponsor inquiry for your event on {BRAND}.",
        "/host",
    ),
    "sponsor_inquiry_status_update": _t(
        "sponsor_inquiry_status_update",
        "Inquiry update",
        f"Your sponsorship inquiry status changed on {BRAND}.",
        "/sponsorships",
    ),
    "sponsor_deal_proposal": _t(
        "sponsor_deal_proposal",
        "Sponsor deal proposal",
        f"A new sponsorship deal proposal on {BRAND}.",
        "/sponsorships",
    ),
    "sponsor_deal_active": _t(
        "sponsor_deal_active",
        "Sponsor deal active",
        f"Your sponsorship deal is now active on {BRAND}.",
        "/sponsorships",
    ),
    "sponsor_deliverable_submitted": _t(
        "sponsor_deliverable_submitted",
        "Deliverable submitted",
        f"A sponsorship deliverable was submitted on {BRAND}.",
        "/sponsorships",
    ),
    "sponsor_deliverable_approved": _t(
        "sponsor_deliverable_approved",
        "Deliverable approved",
        f"A sponsorship deliverable was approved on {BRAND}.",
        "/sponsorships",
    ),
    "sponsor_deliverable_rejected": _t(
        "sponsor_deliverable_rejected",
        "Deliverable rejected",
        f"A sponsorship deliverable needs changes on {BRAND}.",
        "/sponsorships",
    ),
    "sponsor_deliverables_completed": _t(
        "sponsor_deliverables_completed",
        "Deliverables complete",
        f"All sponsorship deliverables are complete on {BRAND}.",
        "/sponsorships",
    ),
    # --- Admin ---
    "admin_new_report": _t(
        "admin_new_report",
        "New report",
        f"A new report needs review on {BRAND}.",
        "/admin",
    ),
    "admin_payment_issue": _t(
        "admin_payment_issue",
        "Payment issue",
        f"A payment issue needs attention on {BRAND}.",
        "/admin/payments",
    ),
    "admin_support_ticket": _t(
        "admin_support_ticket",
        "Support case",
        f"A support case needs attention on {BRAND}.",
        "/admin/support",
    ),
    "admin_new_user_registered": _t(
        "admin_new_user_registered",
        "New user registered",
        f"A new account was created on {BRAND}.",
        "/admin/users",
    ),
    "admin_new_ticket_sale": _t(
        "admin_new_ticket_sale",
        "New ticket sale",
        f"A verified ticket order was paid on {BRAND}.",
        "/admin/payments",
    ),
    # --- Admin team ---
    "admin_team_invite": _t(
        "admin_team_invite",
        f"{BRAND} admin team",
        lambda c: (
            f"You’ve been added to the {BRAND} admin team"
            + (
                f" as {_ctx_str(c, 'role_label', 'a teammate')}."
                if str(c.get("role_label") or "").strip()
                else "."
            )
        ),
        lambda c: _ctx_str(c, "action_url", "/admin"),
    ),
    # --- Host team ---
    "team_invite": _t(
        "team_invite",
        f"You're invited to a {BRAND} host team",
        lambda c: (
            (
                f"{_ctx_str(c, 'host_display_name', 'A host')} invited your "
                f"{BRAND} account @{str(c.get('invited_username') or '').lstrip('@')} "
                "to join their team."
            )
            if (str(c.get("invite_method") or "").lower() == "username"
                and str(c.get("invited_username") or "").strip())
            else (
                f"You’ve been invited to join "
                f"{_ctx_str(c, 'host_display_name', 'a host')}’s {BRAND} team."
            )
        ),
        lambda c: _ctx_str(c, "action_url", "/team/invite"),
    ),
    "team_invite_accepted": _t(
        "team_invite_accepted",
        "Team invite accepted",
        lambda c: (
            f"{_ctx_str(c, 'member_name', 'A teammate')} joined "
            f"{_ctx_str(c, 'host_display_name', 'your workspace')}."
        ),
        "/host/team",
    ),
    "team_invite_revoked": _t(
        "team_invite_revoked",
        "Team invite revoked",
        lambda c: (
            f"Your invite to {_ctx_str(c, 'host_display_name', 'a host workspace')} "
            "was revoked."
        ),
        "/dashboard",
    ),
    "team_member_removed": _t(
        "team_member_removed",
        "Removed from host team",
        lambda c: (
            f"You were removed from {_ctx_str(c, 'host_display_name', 'a host workspace')}."
        ),
        "/dashboard",
    ),
    "team_permission_updated": _t(
        "team_permission_updated",
        "Team permissions updated",
        lambda c: (
            f"Your access on {_ctx_str(c, 'host_display_name', 'a host workspace')} "
            "was updated."
        ),
        "/host",
    ),
    "team_security_alert": _t(
        "team_security_alert",
        "Security alert",
        f"A security-related change was made to your {BRAND} account.",
        "/dashboard/settings",
    ),
    "ticket_event_updated": _t(
        "ticket_event_updated",
        "Event updated",
        lambda c: f"{_event(c)} was updated. See details in {BRAND}.",
        "/dashboard/tickets",
    ),
    "ticket_transferred": _t(
        "ticket_transferred",
        "Ticket received",
        f"You received a ticket on {BRAND}. Open the app for details.",
        "/dashboard/tickets",
    ),
    "ticket_transfer_accepted": _t(
        "ticket_transfer_accepted",
        "Transfer accepted",
        f"Your ticket transfer was accepted on {BRAND}.",
        "/dashboard/tickets",
    ),
    "ticket_checked_in": _t(
        "ticket_checked_in",
        "You're checked in",
        lambda c: f"You've been checked in for {_event(c)}.",
        lambda c: _ctx_str(c, "action_url", "/dashboard/tickets"),
    ),
    "event_published": _t(
        "event_published",
        "New event",
        f"A new event is live on {BRAND}.",
        "/events",
    ),
    "merch_listing_published": _t(
        "merch_listing_published",
        "New merch",
        f"New merch is available on {BRAND}.",
        "/merch",
    ),
    "host_announcement": _t(
        "host_announcement",
        "Host update",
        f"A host you follow shared an update on {BRAND}.",
        "/dashboard/notifications",
    ),
    "ambassador_campaign_new": _t(
        "ambassador_campaign_new",
        "New Ambassador campaign",
        lambda c: f"A new Ambassador campaign for {_event(c)} is live.",
        "/dashboard/ambassador",
    ),
    "fan_connect_declined": _t(
        "fan_connect_declined",
        "Fan Connect update",
        f"A Fan Connect request was declined on {BRAND}.",
        "/connect",
    ),
    "fan_connect_removed": _t(
        "fan_connect_removed",
        "Connection removed",
        f"A Fan Connect connection was removed on {BRAND}.",
        "/connect/connections",
    ),
    "support_ticket_updated": _t(
        "support_ticket_updated",
        "Support update",
        f"You have a support update on {BRAND}.",
        lambda c: _ctx_str(c, "action_url", "/dashboard/support"),
    ),
    "merch_vault_unlocked": _t(
        "merch_vault_unlocked",
        "Vault unlock",
        f"New merch is available for you on {BRAND}.",
        "/dashboard/merchandise",
    ),
    "vault_item_published": _t(
        "vault_item_published",
        "Vault drop",
        f"A host published new Vault content on {BRAND}.",
        "/vault",
    ),
    "account_suspended": _t(
        "account_suspended",
        "Account notice",
        f"There's an update about your {BRAND} account. Sign in for details.",
        "/dashboard/settings",
    ),
    "account_appeal_decision": _t(
        "account_appeal_decision",
        "Appeal update",
        f"Your account appeal status changed on {BRAND}.",
        "/dashboard/settings",
    ),
    "system_maintenance": _t(
        "system_maintenance",
        "Scheduled maintenance",
        f"{BRAND} has a maintenance update. Open the app for details.",
        "/maintenance",
    ),
    "merch_host_sale": _t(
        "merch_host_sale",
        "Merch sale",
        lambda c: f"New merch sale for {_event(c)}.",
        "/host/merchandise",
    ),
    "merch_badge_earned": _t(
        "merch_badge_earned",
        "Badge earned",
        f"You earned a new badge on {BRAND}.",
        "/dashboard/passport",
    ),
    "merch_sold_out": _t(
        "merch_sold_out",
        "Merch sold out",
        lambda c: f"A merch item for {_event(c)} sold out.",
        "/host/merchandise",
    ),
    "merch_low_stock": _t(
        "merch_low_stock",
        "Low stock",
        lambda c: f"A merch item for {_event(c)} is running low.",
        "/host/merchandise",
    ),
    "merch_host_pickup": _t(
        "merch_host_pickup",
        "Merch pickup",
        f"A merch order was picked up on {BRAND}.",
        "/host/merchandise",
    ),
    "merch_host_cart_summary": _t(
        "merch_host_cart_summary",
        "Cart activity",
        f"Fans left items in merch carts for your event on {BRAND}.",
        "/host/merchandise",
    ),
    # --- System / fallback ---
    "admin_push_test": _t(
        "admin_push_test",
        f"{BRAND} test notification",
        "Push notifications are working.",
        "/dashboard/notifications",
    ),
    "generic": _t(
        "generic",
        lambda c: _ctx_str(c, "title", BRAND),
        lambda c: _ctx_str(c, "body", f"You have a new notification on {BRAND}."),
        lambda c: _ctx_str(c, "action_url", "/dashboard/notifications"),
    ),
    # --- Ambassadors ---
    "ambassador_joined": _t(
        "ambassador_joined",
        "Ambassador joined",
        lambda c: f"You’re promoting {_event(c)} on {BRAND}.",
        "/dashboard/ambassador",
    ),
    "ambassador_first_sale": _t(
        "ambassador_first_sale",
        "First sale",
        lambda c: f"Your first Ambassador sale for {_event(c)} is in.",
        "/dashboard/ambassador/earnings",
    ),
    "ambassador_commission_payable": _t(
        "ambassador_commission_payable",
        "Reward approved",
        lambda c: f"Your Ambassador reward for {_event(c)} was approved.",
        "/dashboard/ambassador/earnings",
    ),
    "ambassador_payout_ready": _t(
        "ambassador_payout_ready",
        "Reward marked paid",
        lambda c: f"An Ambassador reward for {_event(c)} was marked paid.",
        "/dashboard/ambassador/payouts",
    ),
    "ambassador_reward_rejected": _t(
        "ambassador_reward_rejected",
        "Reward not approved",
        lambda c: f"An Ambassador reward for {_event(c)} was not approved.",
        "/dashboard/ambassador/earnings",
    ),
    "ambassador_reward_reversed": _t(
        "ambassador_reward_reversed",
        "Reward reversed",
        lambda c: f"An Ambassador reward for {_event(c)} was reversed.",
        "/dashboard/ambassador/earnings",
    ),
    "ambassador_campaign_paused": _t(
        "ambassador_campaign_paused",
        "Campaign paused",
        lambda c: f"Ambassadors for {_event(c)} is paused.",
        "/dashboard/ambassador",
    ),
    "ambassador_campaign_ended": _t(
        "ambassador_campaign_ended",
        "Campaign ended",
        lambda c: f"Ambassadors for {_event(c)} has ended.",
        "/dashboard/ambassador",
    ),
    "host_ambassador_milestone": _t(
        "host_ambassador_milestone",
        "Ambassadors milestone",
        lambda c: (
            f"Ambassadors hit {_ctx_str(c, 'sale_count', 'a')} verified "
            f"sale(s) for {_event(c)}."
        ),
        "/host/ambassadors/campaigns",
    ),
    "host_ambassador_team_reward_action": _t(
        "host_ambassador_team_reward_action",
        "Team Ambassadors update",
        lambda c: (
            f"A team member {_ctx_str(c, 'action_verb', 'updated a reward')} "
            f"for {_event(c)}."
        ),
        "/host/ambassadors/conversions",
    ),
    "host_ambassador_suspicious_reversal": _t(
        "host_ambassador_suspicious_reversal",
        "Ambassadors reversal flagged",
        lambda c: (
            f"A reward reversal for {_event(c)} was flagged for review."
        ),
        "/host/ambassadors/conversions",
    ),
}

# Dotted in-app kinds → snake_case push template names
KIND_ALIASES: dict[str, str] = {
    "ticket.confirmed": "ticket_confirmed",
    "ticket.qr_ready": "ticket_qr_ready",
    "ticket.event_reminder": "ticket_event_reminder",
    "ticket.event_cancelled": "ticket_event_cancelled",
    "ticket.refund_update": "ticket_refund_update",
    "ticket.refunded": "ticket_refund_update",
    "ticket.transferred": "ticket_transferred",
    "ticket.transfer_accepted": "ticket_transfer_accepted",
    "ticket.checked_in": "ticket_checked_in",
    "checkin.successful": "ticket_checked_in",
    "event.published": "event_published",
    "event.cancelled": "ticket_event_cancelled",
    "event.reminder": "ticket_event_reminder",
    "refund.requested": "ticket_refund_update",
    "refund.approved": "ticket_refund_update",
    "refund.rejected": "ticket_refund_update",
    "ticket.purchase_confirmed": "ticket_confirmed",
    "ticket_purchase_confirmed": "ticket_confirmed",
    "merch.listing_published": "merch_listing_published",
    "merch.post_event_drop_live": "post_event_drop_available",
    "host.announcement": "host_announcement",
    "review.request": "host_new_review",
    "review.approved": "host_new_review",
    "review.rejected": "host_new_review",
    "appeal.submitted": "account_appeal_decision",
    "appeal.approved": "account_appeal_decision",
    "appeal.rejected": "account_appeal_decision",
    "sponsor.inquiry": "sponsor_inquiry_host_alert",
    "host_sponsor_inquiry": "host_sponsor_inquiry",
    "ambassador.campaign_new": "ambassador_campaign_new",
    "ambassador.reward_earned": "ambassador_commission_payable",
    "event.updated": "ticket_event_updated",
    "event.rescheduled": "ticket_event_updated",
    "ticket.event_updated": "ticket_event_updated",
    "merch.confirmed": "merch_order_confirmed",
    "merch.paid": "merch_order_confirmed",
    "merch.ready_for_pickup": "merch_pickup_ready",
    "merch.shipping_update": "merch_shipping_update",
    "merch.shipped": "merch_shipping_update",
    "merch.delivered": "merch_shipping_update",
    "merch.picked_up": "merch_picked_up",
    "merch.refunded": "merch_refund_update",
    "merch.refund_update": "merch_refund_update",
    "merch.post_event_drop": "post_event_drop_available",
    "merch.cart_reminder": "merch_cart_reminder",
    "merch.vault_unlocked": "merch_vault_unlocked",
    "vault.merch_unlocked": "merch_vault_unlocked",
    "vault.item_published": "vault_item_published",
    "merch.host_sale": "merch_host_sale",
    "merch.badge_earned": "merch_badge_earned",
    "merch.sold_out": "merch_sold_out",
    "merch.low_stock": "merch_low_stock",
    "merch.host_pickup": "merch_host_pickup",
    "merch.host_cart_summary": "merch_host_cart_summary",
    "merch.review_received": "host_new_review",
    "message.new": "new_message",
    "message.message_request": "message_request",
    "message_request_accepted": "message_request",
    "message.attachment": "attachment_received",
    "message.attachment_received": "attachment_received",
    "messaging.new": "new_message",
    "fan_connect.request": "fan_connect_request",
    "fan_connect.accepted": "fan_connect_accepted",
    "fan_connect.message": "fan_connect_message",
    "fan_connect.declined": "fan_connect_declined",
    "fan_connect.removed": "fan_connect_removed",
    "host.ticket_sale": "host_ticket_sale",
    "host.merch_sale": "host_merch_sale",
    "host.new_follower": "host_new_follower",
    "host.sponsor_inquiry": "host_sponsor_inquiry",
    "review.new": "host_new_review",
    "review.reply": "host_new_review",
    "sponsor.inquiry_received": "sponsor_inquiry_confirmation",
    "sponsor.inquiry_host": "sponsor_inquiry_host_alert",
    "sponsor.inquiry_status": "sponsor_inquiry_status_update",
    "sponsor.deal_proposal": "sponsor_deal_proposal",
    "sponsor.deal_active": "sponsor_deal_active",
    "sponsor.deliverable_submitted": "sponsor_deliverable_submitted",
    "sponsor.deliverable_approved": "sponsor_deliverable_approved",
    "sponsor.deliverable_rejected": "sponsor_deliverable_rejected",
    "sponsor.deliverables_completed": "sponsor_deliverables_completed",
    "admin.report": "admin_new_report",
    "admin.payment_issue": "admin_payment_issue",
    "admin.support_ticket": "admin_support_ticket",
    "admin_support_ticket": "admin_support_ticket",
    "admin.user_registered": "admin_new_user_registered",
    "admin.ticket_sale": "admin_new_ticket_sale",
    "support.ticket_updated": "support_ticket_updated",
    "account.suspended": "account_suspended",
    "account.appeal_decision": "account_appeal_decision",
    "account.restricted": "account_suspended",
    "system.maintenance": "system_maintenance",
    "admin.push_test": "admin_push_test",
    "admin_team.invite": "admin_team_invite",
    "team.invite": "team_invite",
    "team.invite_accepted": "team_invite_accepted",
    "team.invite_revoked": "team_invite_revoked",
    "team.member_removed": "team_member_removed",
    "team.permission_updated": "team_permission_updated",
    "team.security_alert": "team_security_alert",
    "host.team_invite_accepted": "team_invite_accepted",
    "ambassador.joined": "ambassador_joined",
    "ambassador.first_sale": "ambassador_first_sale",
    "ambassador.commission_payable": "ambassador_commission_payable",
    "ambassador.reward_approved": "ambassador_commission_payable",
    "ambassador.payout_ready": "ambassador_payout_ready",
    "ambassador.reward_marked_paid": "ambassador_payout_ready",
    "ambassador.reward_rejected": "ambassador_reward_rejected",
    "ambassador.reward_reversed": "ambassador_reward_reversed",
    "ambassador.campaign_paused": "ambassador_campaign_paused",
    "ambassador.campaign_ended": "ambassador_campaign_ended",
    "host.ambassador_milestone": "host_ambassador_milestone",
    "host.ambassador_team_reward": "host_ambassador_team_reward_action",
    "host.ambassador_suspicious_reversal": "host_ambassador_suspicious_reversal",
}

# Templates that count toward message push rate limits
MESSAGE_PUSH_TEMPLATES = frozenset(
    {
        "new_message",
        "message_request",
        "attachment_received",
        "fan_connect_message",
    }
)


def resolve_template_name(name: str) -> str:
    """Normalize kind or template name to a registered push template key."""
    key = (name or "").strip()
    if not key:
        return "generic"
    if key in TEMPLATES:
        return key
    aliased = KIND_ALIASES.get(key) or KIND_ALIASES.get(key.lower())
    if aliased:
        return aliased
    # message.<anything> → new_message (except explicit aliases above)
    lower = key.lower()
    if lower.startswith("message.") or lower.startswith("messaging."):
        if "request" in lower:
            return "message_request"
        if "attachment" in lower:
            return "attachment_received"
        return "new_message"
    return key if key in TEMPLATES else "generic"


def get_template(name: str) -> PushTemplate:
    resolved = resolve_template_name(name)
    return TEMPLATES.get(resolved) or TEMPLATES["generic"]


def list_template_names() -> list[str]:
    return sorted(n for n in TEMPLATES if n not in ("generic", "admin_push_test"))


def _resolve(value: str | Callable[[dict[str, Any]], str], ctx: dict[str, Any]) -> str:
    return value(ctx) if callable(value) else value


def render_push(
    template: str,
    context: dict[str, Any] | None = None,
) -> tuple[str, str, str, str, str]:
    """Return title, body, action_url, icon_url, badge_url.

    Known templates own short push copy. Context is sanitized first — never
    pass chat bodies, codes, venues, or payment refs.
    """
    from app.push.privacy import safe_action_url, sanitize_push_context, scrub_push_copy

    ctx = sanitize_push_context(context)
    tmpl = get_template(template)
    title = scrub_push_copy(_resolve(tmpl.title, ctx), limit=160)
    body = scrub_push_copy(_resolve(tmpl.body, ctx), limit=240)
    action = safe_action_url(
        _ctx_str(ctx, "action_url") or _resolve(tmpl.action_url, ctx)
    )
    icon = _ctx_str(ctx, "icon_url") or tmpl.icon_url
    badge = _ctx_str(ctx, "badge_url") or tmpl.badge_url
    return title or BRAND, body or f"You have a new notification on {BRAND}.", action, icon, badge
