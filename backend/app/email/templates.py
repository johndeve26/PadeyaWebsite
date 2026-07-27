"""Template registry — subjects + content builders. Brand: Pàdéyá only."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
from typing import Any, Callable

from app.email.config import BRAND_NAME, FORBIDDEN_BRAND_SPELLINGS

# Domain is allowed in footers / links; never treat it as a brand misspelling.
_ALLOWED_DOMAIN_FRAGMENTS = ("padeya.com", "Padeya.com", "PADEYA.COM")


@dataclass(frozen=True)
class TemplateDef:
    name: str
    subject: str
    # Preference key, or None for always-send transactional/security
    preference_key: str | None
    # True = cannot be suppressed by prefs (purchase confirm / security)
    required: bool
    headline: str
    # Context keys used in body paragraphs (documentation)
    body_fn: Callable[[dict[str, Any]], list[str]]
    cta_label: str | None = None
    cta_path: str | None = None


def _ctx(context: dict[str, Any], key: str, default: str = "") -> str:
    val = context.get(key, default)
    if val is None:
        return default
    return str(val)


def assert_brand_safe(text: str, *, scrub: Iterable[str] = ()) -> None:
    """Reject ASCII/wrong brand spellings in *our* copy.

    User-controlled fragments (names, titles, host blast body, etc.) must be
    passed via ``scrub`` so a person named \"Admin Padeya\" does not block
    transactional email.
    """
    scrubbed = text
    for fragment in scrub:
        if fragment:
            scrubbed = scrubbed.replace(str(fragment), "")
    for domain in _ALLOWED_DOMAIN_FRAGMENTS:
        scrubbed = scrubbed.replace(domain, "")
    for bad in FORBIDDEN_BRAND_SPELLINGS:
        if bad in scrubbed:
            raise ValueError(f"Forbidden brand spelling {bad!r} in email copy")


def _welcome(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "full_name", "there")
    return [
        f"Hi {name},",
        f"Welcome to {BRAND_NAME} — discover events, claim tickets, and connect with hosts and fans.",
        "Your account is ready. Explore what’s happening near you.",
    ]


def _verify_email(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "full_name", "there")
    code = _ctx(c, "verification_code")
    hours = _ctx(c, "expiry_hours", "24")
    lines = [
        f"Hi {name},",
        f"Confirm your email to secure your {BRAND_NAME} account and receive ticket, merch, Vault, and host updates.",
    ]
    if code:
        lines.append(
            f"Your verification code is {code}. It expires in {hours} hours."
        )
        lines.append(
            "Open the verification page from the button below, or enter this code while signed in."
        )
    else:
        lines.append(f"Use the link below to verify. It expires in {hours} hours.")
    lines.append(
        "If you did not create a Pàdéyá account, you can ignore this message."
    )
    return lines


def _password_reset(c: dict[str, Any]) -> list[str]:
    code = _ctx(c, "reset_code")
    lines = [
        f"We received a request to reset your {BRAND_NAME} password.",
    ]
    if code:
        lines.extend(
            [
                f"Your reset code is {code}. It expires in 5 minutes.",
                "Enter this code on the reset password page with your account email and a new password.",
                "If you did not ask for this, you can ignore this email.",
            ]
        )
    else:
        lines.append(
            "Open the reset password page on Pàdéyá to continue. If you did not ask for this, ignore this email."
        )
    return lines


def _security_alert(c: dict[str, Any]) -> list[str]:
    detail = _ctx(c, "detail", "We noticed an important security update on your account.")
    return [detail, f"If this was not you, contact {BRAND_NAME} support immediately."]


def _account_suspended(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "full_name", "there")
    category = _ctx(c, "reason_category_label", "Account review")
    duration = _ctx(c, "duration_label", "Indefinite")
    started = _ctx(c, "starts_at", "")
    lines = [
        f"Hi {name},",
        f"Your {BRAND_NAME} account has been suspended.",
        f"Reason category: {category}.",
        f"Duration: {duration}.",
    ]
    if started:
        lines.append(f"Started: {started}.")
    lines.append(
        "You can sign in to view details and submit an appeal. "
        "This message does not include internal admin notes."
    )
    return lines


def _account_appeal_approved(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "full_name", "there")
    return [
        f"Hi {name},",
        f"Your suspension appeal on {BRAND_NAME} was approved. "
        "Your account access has been restored.",
    ]


def _account_appeal_rejected(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "full_name", "there")
    reply = _ctx(c, "admin_reply", "")
    lines = [
        f"Hi {name},",
        f"Your suspension appeal on {BRAND_NAME} was not approved.",
    ]
    if reply:
        lines.append(reply)
    lines.append("You can contact support if you need further help.")
    return lines


def _ticket_confirmed(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    codes = _ctx(c, "ticket_codes", "")
    is_gift = bool(c.get("is_gift"))
    is_guest = bool(c.get("is_guest"))
    lines = [
        f"Hi {_ctx(c, 'buyer_name', 'there')},",
        f"Payment confirmed — your tickets for {title} are ready on {BRAND_NAME}.",
    ]
    if is_gift:
        lines.append("You bought these tickets for someone else. A buyer copy is included below.")
    if codes:
        lines.append(f"Ticket codes: {codes}")
    lines.append(
        "Your ticket PDF is attached to this email. Open My Tickets anytime on "
        f"{BRAND_NAME} for the latest QR pass."
    )
    if is_guest:
        lines.append(
            f"We also opened a dashboard account for this email — use the set-password "
            "link we sent separately, then sign in."
        )
    return lines


def _checkout_account_ready(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "full_name", "there")
    ref = _ctx(c, "order_reference", "your order")
    return [
        f"Hi {name}, your {BRAND_NAME} order ({ref}) is confirmed.",
        "We opened a dashboard account for this email so your tickets and merch live in one place.",
        "Your order PDF is attached. Check your inbox for a separate message with a code to set your password, then sign in.",
    ]


def _ticket_claim_link(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    token = _ctx(c, "claim_token", "")
    ref = _ctx(c, "order_reference", "")
    lines = [
        f"Hi {_ctx(c, 'buyer_name', 'there')},",
        f"Use this secure link to claim your {title} tickets on {BRAND_NAME}.",
        "Log in or create an account with the same buyer email, then open the claim link.",
    ]
    if ref:
        lines.append(f"Order reference: {ref}")
    if token:
        lines.append(f"Claim path: /checkout/claim?token={token}&order={ref}")
    lines.append("This link expires. Do not share it.")
    return lines


def _ticket_transfer_invite(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    buyer = _ctx(c, "buyer_name", "Someone")
    code = _ctx(c, "ticket_code", "")
    email = _ctx(c, "recipient_email", "")
    lines = [
        f"Hi {_ctx(c, 'recipient_name', 'there')},",
        f"{buyer} transferred a ticket to you for {title} on {BRAND_NAME}.",
    ]
    if code:
        lines.append(f"Ticket code: {code}")
    lines.extend(
        [
            f"Create a free {BRAND_NAME} account with {email or 'this email address'}, "
            "then use the claim button in this email to accept the ticket and get your QR pass.",
            "Use the same email address shown above when you sign up or log in.",
            "Do not share your claim link or QR publicly.",
        ]
    )
    return lines


def _ticket_transfer_received(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    buyer = _ctx(c, "buyer_name", "Someone")
    code = _ctx(c, "ticket_code", "")
    lines = [
        f"Hi {_ctx(c, 'recipient_name', 'there')},",
        f"{buyer} transferred a ticket for {title} to your {BRAND_NAME} account.",
    ]
    if code:
        lines.append(f"Ticket code: {code}")
    lines.append("Open My tickets to view your QR pass for entry.")
    return lines


def _ticket_transfer_accepted(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    recipient = _ctx(c, "recipient_name", "The recipient")
    code = _ctx(c, "ticket_code", "")
    lines = [
        f"Hi {_ctx(c, 'sender_name', 'there')},",
        f"{recipient} accepted your ticket transfer for {title} on {BRAND_NAME}.",
    ]
    if code:
        lines.append(f"Ticket code: {code}")
    lines.append("The ticket is no longer on your account.")
    return lines


def _ticket_gift_received(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    buyer = _ctx(c, "buyer_name", "A friend")
    codes = _ctx(c, "ticket_codes", "")
    gift = _ctx(c, "gift_message", "")
    lines = [
        f"Hi {_ctx(c, 'recipient_name', 'there')},",
        f"{buyer} sent you tickets for {title} on {BRAND_NAME}.",
    ]
    if gift:
        lines.append(f"Message: {gift}")
    if codes:
        lines.append(f"Ticket codes: {codes}")
    lines.append("Your ticket PDF is attached to this email.")
    lines.extend(
        [
            f"Create a free {BRAND_NAME} account with this email address, then open My tickets for your QR pass.",
            "If you already have an account under a different email, ask the buyer to transfer the ticket from their dashboard.",
            "Do not share your QR publicly.",
        ]
    )
    return lines


def _ticket_qr_ready(c: dict[str, Any]) -> list[str]:
    return _ticket_confirmed(c)


def _ticket_event_reminder(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    when = _ctx(c, "starts_at_label", "soon")
    return [
        f"Reminder: {title} starts {when}.",
        f"Have your {BRAND_NAME} ticket QR ready at the door.",
    ]


def _ticket_event_updated(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    summary = _ctx(c, "update_summary", "Event details were updated.")
    return [f"Update for {title}:", summary, f"Check the event page on {BRAND_NAME} for the latest details."]


def _ticket_event_cancelled(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"{title} has been cancelled.",
        f"Open {BRAND_NAME} for refund or next-step guidance from the host.",
    ]


def _ticket_checked_in(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "the event")
    return [f"You’re checked in for {title}. Enjoy the night."]


def _ticket_refund_update(c: dict[str, Any]) -> list[str]:
    status = _ctx(c, "refund_status", "updated")
    title = _ctx(c, "event_title", "your order")
    return [
        f"Refund update for {title}: {status}.",
        f"See details in your {BRAND_NAME} dashboard.",
    ]


def _merch_order_confirmed(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    items = _ctx(c, "item_summary", "your merch")
    return [
        f"Hi {_ctx(c, 'buyer_name', 'there')},",
        f"Your merch order for {title} is confirmed on {BRAND_NAME}.",
        f"Items: {items}",
        "Pickup and shipping details are in Merchandise — nothing is released before verified payment.",
    ]


def _merch_pickup_ready(c: dict[str, Any]) -> list[str]:
    product = _ctx(c, "product_name", "Your merch")
    title = _ctx(c, "event_title", "the event")
    code = _ctx(c, "pickup_code_short", "")
    lines = [f"{product} for {title} is ready for pickup."]
    if code:
        lines.append(f"Pickup code: {code}")
    lines.append(f"Show your pickup QR in the {BRAND_NAME} app at the merch stand.")
    return lines


def _merch_shipping_update(c: dict[str, Any]) -> list[str]:
    product = _ctx(c, "product_name", "Your merch")
    status = _ctx(c, "shipping_status", "updated")
    tracking = _ctx(c, "tracking_number", "")
    lines = [f"{product} shipping update: {status}."]
    if tracking:
        lines.append(f"Tracking: {tracking}")
    return lines


def _merch_picked_up(c: dict[str, Any]) -> list[str]:
    product = _ctx(c, "product_name", "Your merch")
    return [f"{product} was marked picked up. Thanks for shopping on {BRAND_NAME}."]


def _merch_refund_update(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your merch order")
    status = _ctx(c, "refund_status", "updated")
    return [f"Merch refund update for {title}: {status}."]


def _post_event_drop(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"A post-event merch drop is live for {title}.",
        f"Shop exclusive recap gear on {BRAND_NAME}.",
    ]


def _merch_cart_reminder(c: dict[str, Any]) -> list[str]:
    return [
        f"Your event merch is still waiting in your {BRAND_NAME} cart.",
        "Nothing is purchased until payment succeeds.",
    ]


def _host_ticket_sale(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    count = _ctx(c, "ticket_count", "1")
    return [f"New ticket sale for {title}: {count} ticket(s).", f"See sales in your {BRAND_NAME} host dashboard."]


def _host_merch_sale(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    count = _ctx(c, "item_count", "1")
    return [f"New merch sale for {title}: {count} item(s)."]


def _host_new_review(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "subject_label", "your event or merch")
    return [f"You received a new review for {title}.", f"Reply from your {BRAND_NAME} host inbox."]


def _host_new_message(c: dict[str, Any]) -> list[str]:
    return [f"You have a new message on {BRAND_NAME}.", "Open your inbox to reply."]


def _host_sponsor_inquiry(c: dict[str, Any]) -> list[str]:
    brand = _ctx(c, "brand_name", "A brand")
    return [f"{brand} sent a sponsorship inquiry.", f"Review it in {BRAND_NAME} Sponsorships."]


def _host_payout_update(c: dict[str, Any]) -> list[str]:
    status = _ctx(c, "payout_status", "updated")
    return [f"Payout update: {status}.", f"Details are in your {BRAND_NAME} payouts page."]


def _team_invite(c: dict[str, Any]) -> list[str]:
    host_name = _ctx(c, "host_display_name", "A host")
    method = (_ctx(c, "invite_method", "email") or "email").strip().lower()
    username = _ctx(c, "invited_username", "").lstrip("@")
    if method == "username" and username:
        lead = (
            f"{host_name} invited your {BRAND_NAME} account @{username} "
            "to join their team."
        )
        accept_line = (
            f"Sign in as @{username} to accept. The invite expires in 7 days."
        )
    else:
        lead = f"You’ve been invited to join {host_name}’s {BRAND_NAME} team."
        accept_line = (
            "Sign in or create an account with this email to accept. "
            "The invite expires in 7 days."
        )
    return [
        lead,
        accept_line,
        "If you did not expect this, you can ignore this email.",
    ]


def _team_invite_accepted(c: dict[str, Any]) -> list[str]:
    member = _ctx(c, "member_name") or _ctx(c, "member_email", "A teammate")
    role = _ctx(c, "role_label") or _ctx(c, "role", "team member")
    host_name = _ctx(c, "host_display_name", "your host workspace")
    return [
        f"{member} accepted your team invite for {host_name} as {role}.",
        "Review their permissions anytime from your host team page.",
    ]


def _team_invite_revoked(c: dict[str, Any]) -> list[str]:
    host_name = _ctx(c, "host_display_name", "A host")
    return [
        f"Your invite to join {host_name} on {BRAND_NAME} was revoked.",
        "You can no longer accept this invite. Contact the host owner if this was unexpected.",
    ]


def _team_member_removed(c: dict[str, Any]) -> list[str]:
    host_name = _ctx(c, "host_display_name", "a host workspace")
    return [
        f"You were removed from the {host_name} team on {BRAND_NAME}.",
        "You no longer have access to that host workspace.",
    ]


def _team_permission_updated(c: dict[str, Any]) -> list[str]:
    host_name = _ctx(c, "host_display_name", "a host workspace")
    role = _ctx(c, "role_label") or _ctx(c, "role", "your role")
    return [
        f"Your permissions on {host_name} were updated.",
        f"Your current role is {role}. Open the host workspace to see what you can access.",
    ]


def _team_security_alert(c: dict[str, Any]) -> list[str]:
    host_name = _ctx(c, "host_display_name", "a host workspace")
    detail = _ctx(
        c,
        "detail",
        f"There was a security-related change to your access on {host_name}.",
    )
    return [
        detail,
        f"If you did not expect this, contact the host owner or {BRAND_NAME} support.",
    ]


# Legacy body builders (aliases keep old imports/tests working).
_host_team_invite = _team_invite
_host_team_invite_accepted = _team_invite_accepted



def _fan_connect_request(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "requester_name", "A fan")
    return [
        f"{name} sent you a Fan Connect request on {BRAND_NAME}.",
        "Chat unlocks only if you both accept. No phone numbers required.",
    ]


def _fan_connect_accepted(c: dict[str, Any]) -> list[str]:
    name = _ctx(c, "acceptor_name", "A fan")
    return [f"{name} accepted your Fan Connect request.", f"You can message on {BRAND_NAME}."]


def _fan_connect_message(c: dict[str, Any]) -> list[str]:
    return [f"You have a new Fan Connect message on {BRAND_NAME}.", "Open your inbox to read it."]


def _new_message(c: dict[str, Any]) -> list[str]:
    return [f"You have a new message on {BRAND_NAME}.", "Open your inbox to read it."]


def _message_request(c: dict[str, Any]) -> list[str]:
    return [f"You have a new message request on {BRAND_NAME}.", "Accept or decline in your inbox."]


def _attachment_received(c: dict[str, Any]) -> list[str]:
    return [
        f"You received a new message with an attachment on {BRAND_NAME}.",
        "Open the conversation in the app to view it securely.",
    ]


def _sponsor_inquiry_confirmation(c: dict[str, Any]) -> list[str]:
    host = _ctx(c, "host_name", "the host")
    return [
        f"Your sponsorship inquiry to {host} was received.",
        f"You’ll hear back through {BRAND_NAME}.",
    ]


def _sponsor_inquiry_host_alert(c: dict[str, Any]) -> list[str]:
    return _host_sponsor_inquiry(c)


def _sponsor_inquiry_status_update(c: dict[str, Any]) -> list[str]:
    status = _ctx(c, "inquiry_status", "updated")
    return [f"Your sponsorship inquiry was {status}.", f"See details on {BRAND_NAME}."]


def _admin_new_report(c: dict[str, Any]) -> list[str]:
    kind = _ctx(c, "report_kind", "content")
    return [f"New {kind} report needs moderation on {BRAND_NAME}."]


def _admin_support_ticket(c: dict[str, Any]) -> list[str]:
    ref = _ctx(c, "case_ref", "a support case")
    return [f"Support update: {ref}."]


def _admin_payment_issue(c: dict[str, Any]) -> list[str]:
    detail = _ctx(c, "detail", "A payment or webhook issue needs attention.")
    return [detail]


def _email_preferences_updated(c: dict[str, Any]) -> list[str]:
    return [f"Your {BRAND_NAME} email preferences were updated."]


def _review_host_reply(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"A host replied to your review for {title}.",
        f"Open {BRAND_NAME} to read the reply.",
    ]


def _ambassador_joined(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    campaign = _ctx(c, "campaign_name", "Ambassadors")
    return [
        f"You’re now promoting {title} as a {BRAND_NAME} Ambassador.",
        f"Campaign: {campaign}. Share your Ambassador link — earnings appear after verified paid sales.",
        "You never get host dashboard, scanner, or buyer private data.",
    ]


def _ambassador_first_sale(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"Your first verified Ambassador sale for {title} is in.",
        f"Open your {BRAND_NAME} Ambassadors dashboard to track earnings.",
    ]


def _ambassador_commission_payable(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"Your Ambassador reward for {title} was approved.",
        "Open your Ambassadors earnings to review status. Buyer details are never shared.",
    ]


def _ambassador_payout_ready(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"An Ambassador reward for {title} was marked paid.",
        f"Open {BRAND_NAME} to view payout status.",
    ]


def _ambassador_reward_rejected(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"An Ambassador reward for {title} was not approved.",
        f"Open your {BRAND_NAME} Ambassadors earnings for status details.",
    ]


def _ambassador_reward_reversed(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"An Ambassador reward for {title} was reversed.",
        f"Open your {BRAND_NAME} Ambassadors earnings for status details.",
    ]


def _host_ambassador_team_reward_action(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    verb = _ctx(c, "action_verb", "updated a reward")
    return [
        f"A team member {verb} for {title}.",
        f"Open your {BRAND_NAME} Ambassadors dashboard to review.",
    ]


def _host_ambassador_suspicious_reversal(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"A reward reversal for {title} was flagged for review.",
        "Suspicious Ambassadors activity was detected on this campaign.",
        f"Open {BRAND_NAME} Ambassadors to review — buyer private data is never included.",
    ]


def _ambassador_campaign_paused(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"The Ambassadors campaign for {title} is paused.",
        "New joins and attribution may be limited until the host resumes it.",
    ]


def _ambassador_campaign_ended(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    return [
        f"The Ambassadors campaign for {title} has ended.",
        "Thanks for promoting on Pàdéyá. Existing earnings stay in your dashboard.",
    ]


def _host_ambassador_milestone(c: dict[str, Any]) -> list[str]:
    title = _ctx(c, "event_title", "your event")
    count = _ctx(c, "sale_count", "a")
    return [
        f"Ambassadors hit {count} verified sale(s) for {title}.",
        f"Open your {BRAND_NAME} Ambassadors campaign to see the leaderboard.",
    ]


TEMPLATES: dict[str, TemplateDef] = {
    "welcome": TemplateDef(
        "welcome", f"Welcome to {BRAND_NAME}", None, True, f"Welcome to {BRAND_NAME}", _welcome, "Explore events", "/events"
    ),
    "verify_email": TemplateDef(
        "verify_email", f"Verify your {BRAND_NAME} email", "email_security", True, "Verify your email", _verify_email, "Verify email", "/verify"
    ),
    "password_reset": TemplateDef(
        "password_reset", f"Reset your {BRAND_NAME} password", "email_security", True, "Reset your password", _password_reset, "Reset password", "/reset-password"
    ),
    "security_alert": TemplateDef(
        "security_alert", f"{BRAND_NAME} security alert", "email_security", True, "Security alert", _security_alert, "Open account", "/dashboard/settings"
    ),
    "account_suspended": TemplateDef(
        "account_suspended",
        f"Your {BRAND_NAME} account was suspended",
        None,
        True,
        "Account suspended",
        _account_suspended,
        "View status / appeal",
        "/account/suspended",
    ),
    "account_appeal_approved": TemplateDef(
        "account_appeal_approved",
        f"Your {BRAND_NAME} appeal was approved",
        None,
        True,
        "Appeal approved",
        _account_appeal_approved,
        "Open dashboard",
        "/dashboard",
    ),
    "account_appeal_rejected": TemplateDef(
        "account_appeal_rejected",
        f"Update on your {BRAND_NAME} appeal",
        None,
        True,
        "Appeal update",
        _account_appeal_rejected,
        "View status",
        "/account/suspended",
    ),
    "ticket_confirmed": TemplateDef(
        "ticket_confirmed", f"Your {BRAND_NAME} tickets are confirmed", None, True, "Tickets confirmed", _ticket_confirmed, "View tickets", "/dashboard/tickets"
    ),
    "ticket_claim_link": TemplateDef(
        "ticket_claim_link",
        f"Claim your {BRAND_NAME} tickets",
        None,
        True,
        "Claim tickets",
        _ticket_claim_link,
        "Claim tickets",
        "/checkout/claim",
    ),
    "checkout_account_ready": TemplateDef(
        "checkout_account_ready",
        f"Your {BRAND_NAME} order is ready in your dashboard",
        None,
        True,
        "Order confirmed",
        _checkout_account_ready,
        "Open dashboard",
        "/dashboard",
    ),
    "ticket_gift_received": TemplateDef(
        "ticket_gift_received",
        f"You received tickets on {BRAND_NAME}",
        None,
        True,
        "Gift tickets",
        _ticket_gift_received,
        "View tickets",
        "/dashboard/tickets",
    ),
    "ticket_transfer_invite": TemplateDef(
        "ticket_transfer_invite",
        f"A ticket for {{event_title}} is waiting on {BRAND_NAME}",
        None,
        True,
        "Claim your ticket",
        _ticket_transfer_invite,
        "Claim ticket",
        "/tickets/claim",
    ),
    "ticket_transfer_received": TemplateDef(
        "ticket_transfer_received",
        "Ticket transfer for {event_title}",
        None,
        True,
        "Ticket transferred to you",
        _ticket_transfer_received,
        "View tickets",
        "/dashboard/tickets",
    ),
    "ticket_transfer_accepted": TemplateDef(
        "ticket_transfer_accepted",
        "Ticket transfer accepted for {event_title}",
        None,
        True,
        "Transfer accepted",
        _ticket_transfer_accepted,
        "View tickets",
        "/dashboard/tickets",
    ),
    "ticket_qr_ready": TemplateDef(
        "ticket_qr_ready", f"Your {BRAND_NAME} ticket QR is ready", None, True, "Ticket QR ready", _ticket_qr_ready, "View tickets", "/dashboard/tickets"
    ),
    "ticket_event_reminder": TemplateDef(
        "ticket_event_reminder", f"Reminder: your event is coming up", "email_event_reminders", False, "Event reminder", _ticket_event_reminder, "View ticket", "/dashboard/tickets"
    ),
    "ticket_event_updated": TemplateDef(
        "ticket_event_updated", f"Event update on {BRAND_NAME}", "email_ticket_updates", False, "Event updated", _ticket_event_updated, "View event", "/events"
    ),
    "ticket_event_cancelled": TemplateDef(
        "ticket_event_cancelled", f"Event cancelled on {BRAND_NAME}", "email_ticket_updates", False, "Event cancelled", _ticket_event_cancelled, "Open dashboard", "/dashboard/tickets"
    ),
    "ticket_checked_in": TemplateDef(
        "ticket_checked_in", f"Checked in on {BRAND_NAME}", "email_ticket_updates", False, "You’re checked in", _ticket_checked_in, "View ticket", "/dashboard/tickets"
    ),
    "ticket_refund_update": TemplateDef(
        "ticket_refund_update", f"Refund update on {BRAND_NAME}", "email_ticket_updates", False, "Refund update", _ticket_refund_update, "View refunds", "/dashboard/refunds"
    ),
    "merch_order_confirmed": TemplateDef(
        "merch_order_confirmed", f"Your {BRAND_NAME} merch order is confirmed", None, True, "Merch confirmed", _merch_order_confirmed, "View merch", "/dashboard/merchandise"
    ),
    "merch_pickup_ready": TemplateDef(
        "merch_pickup_ready", f"Merch ready for pickup", "email_merch_updates", False, "Ready for pickup", _merch_pickup_ready, "Open pickup", "/dashboard/merchandise"
    ),
    "merch_shipping_update": TemplateDef(
        "merch_shipping_update", f"Merch shipping update", "email_merch_updates", False, "Shipping update", _merch_shipping_update, "Track order", "/dashboard/merchandise"
    ),
    "merch_picked_up": TemplateDef(
        "merch_picked_up", f"Merch picked up", "email_merch_updates", False, "Picked up", _merch_picked_up, "View merch", "/dashboard/merchandise"
    ),
    "merch_refund_update": TemplateDef(
        "merch_refund_update", f"Merch refund update", "email_merch_updates", False, "Merch refund", _merch_refund_update, "View merch", "/dashboard/merchandise"
    ),
    "post_event_drop_available": TemplateDef(
        "post_event_drop_available", f"New post-event drop on {BRAND_NAME}", "email_marketing", False, "Post-event drop", _post_event_drop, "Shop drop", "/dashboard/merchandise"
    ),
    "merch_cart_reminder": TemplateDef(
        "merch_cart_reminder", f"Your {BRAND_NAME} merch cart is waiting", "email_marketing", False, "Cart reminder", _merch_cart_reminder, "Open cart", "/dashboard/cart"
    ),
    "host_ticket_sale": TemplateDef(
        "host_ticket_sale", f"New ticket sale on {BRAND_NAME}", "email_host_activity", False, "New ticket sale", _host_ticket_sale, "View sales", "/host"
    ),
    "host_merch_sale": TemplateDef(
        "host_merch_sale", f"New merch sale on {BRAND_NAME}", "email_host_activity", False, "New merch sale", _host_merch_sale, "View orders", "/host/merchandise"
    ),
    "host_new_review": TemplateDef(
        "host_new_review", f"New review on {BRAND_NAME}", "email_host_activity", False, "New review", _host_new_review, "View reviews", "/host/reviews"
    ),
    "host_new_message": TemplateDef(
        "host_new_message", f"New message on {BRAND_NAME}", "email_messages", False, "New message", _host_new_message, "Open inbox", "/host/messages"
    ),
    "host_sponsor_inquiry": TemplateDef(
        "host_sponsor_inquiry", f"New sponsor inquiry", "email_host_activity", False, "Sponsor inquiry", _host_sponsor_inquiry, "View inquiry", "/host"
    ),
    "host_payout_update": TemplateDef(
        "host_payout_update", f"Payout update on {BRAND_NAME}", "email_host_activity", False, "Payout update", _host_payout_update, "View payouts", "/host/payouts"
    ),
    "team_invite": TemplateDef(
        "team_invite",
        f"You're invited to join a {BRAND_NAME} host team",
        None,
        True,
        "Host team invite",
        _team_invite,
        "Accept invite",
        "/team/invite",
    ),
    "team_invite_accepted": TemplateDef(
        "team_invite_accepted",
        f"Team invite accepted on {BRAND_NAME}",
        "email_host_activity",
        False,
        "Team invite accepted",
        _team_invite_accepted,
        "View team",
        "/host/team",
    ),
    "team_invite_revoked": TemplateDef(
        "team_invite_revoked",
        f"Team invite revoked on {BRAND_NAME}",
        None,
        True,
        "Invite revoked",
        _team_invite_revoked,
        "Open Pàdéyá",
        "/dashboard",
    ),
    "team_member_removed": TemplateDef(
        "team_member_removed",
        f"Removed from a {BRAND_NAME} host team",
        None,
        True,
        "Removed from team",
        _team_member_removed,
        "Open dashboard",
        "/dashboard",
    ),
    "team_permission_updated": TemplateDef(
        "team_permission_updated",
        f"Your {BRAND_NAME} team permissions were updated",
        "email_host_activity",
        False,
        "Permissions updated",
        _team_permission_updated,
        "Open workspace",
        "/host",
    ),
    "team_security_alert": TemplateDef(
        "team_security_alert",
        f"{BRAND_NAME} team security alert",
        "email_security",
        True,
        "Team security alert",
        _team_security_alert,
        "Open account",
        "/dashboard/settings",
    ),
    # Legacy aliases (same registry entries under old names).
    "host_team_invite": TemplateDef(
        "host_team_invite",
        f"You're invited to join a {BRAND_NAME} host team",
        None,
        True,
        "Host team invite",
        _team_invite,
        "Accept invite",
        "/team/invite",
    ),
    "host_team_invite_accepted": TemplateDef(
        "host_team_invite_accepted",
        f"Team invite accepted on {BRAND_NAME}",
        "email_host_activity",
        False,
        "Team invite accepted",
        _team_invite_accepted,
        "View team",
        "/host/team",
    ),
    "fan_connect_request": TemplateDef(
        "fan_connect_request", f"New Fan Connect request", "email_fan_connect", True, "Fan Connect request", _fan_connect_request, "Review request", "/connect/requests"
    ),
    "fan_connect_accepted": TemplateDef(
        "fan_connect_accepted", f"Fan Connect accepted", "email_fan_connect", True, "Connected", _fan_connect_accepted, "Open connections", "/connect/connections"
    ),
    "fan_connect_message": TemplateDef(
        "fan_connect_message", f"New Fan Connect message", "email_fan_connect", False, "New message", _fan_connect_message, "Open inbox", "/dashboard/messages"
    ),
    "new_message": TemplateDef(
        "new_message", f"New message on {BRAND_NAME}", "email_messages", False, "New message", _new_message, "Open inbox", "/dashboard/messages"
    ),
    "message_request": TemplateDef(
        "message_request", f"New message request", "email_messages", False, "Message request", _message_request, "Open requests", "/dashboard/messages"
    ),
    "attachment_received": TemplateDef(
        "attachment_received", f"New attachment on {BRAND_NAME}", "email_messages", False, "Attachment received", _attachment_received, "Open inbox", "/dashboard/messages"
    ),
    "sponsor_inquiry_confirmation": TemplateDef(
        "sponsor_inquiry_confirmation", f"Inquiry received on {BRAND_NAME}", "email_sponsor_updates", False, "Inquiry received", _sponsor_inquiry_confirmation, "Open sponsorships", "/sponsorships"
    ),
    "sponsor_inquiry_host_alert": TemplateDef(
        "sponsor_inquiry_host_alert", f"New sponsor inquiry", "email_host_activity", False, "Sponsor inquiry", _sponsor_inquiry_host_alert, "Review", "/host"
    ),
    "sponsor_inquiry_status_update": TemplateDef(
        "sponsor_inquiry_status_update", f"Sponsorship inquiry update", "email_sponsor_updates", False, "Inquiry update", _sponsor_inquiry_status_update, "View status", "/sponsorships"
    ),
    "admin_new_report": TemplateDef(
        "admin_new_report", f"New report on {BRAND_NAME}", None, True, "New report", _admin_new_report, "Open admin", "/admin"
    ),
    "admin_support_ticket": TemplateDef(
        "admin_support_ticket", f"Support case on {BRAND_NAME}", None, True, "Support case", _admin_support_ticket, "Open support", "/admin/support"
    ),
    "admin_payment_issue": TemplateDef(
        "admin_payment_issue", f"Payment issue on {BRAND_NAME}", None, True, "Payment issue", _admin_payment_issue, "Open payments", "/admin/payments"
    ),
    "email_preferences_updated": TemplateDef(
        "email_preferences_updated", f"Email preferences updated", None, True, "Preferences saved", _email_preferences_updated, "Manage preferences", "/dashboard/settings/notifications"
    ),
    "review_host_reply": TemplateDef(
        "review_host_reply",
        f"Host reply on {BRAND_NAME}",
        "email_ticket_updates",
        False,
        "Host replied to your review",
        _review_host_reply,
        "View review",
        "/dashboard/reviews",
    ),
    # Ambassadors (phase 15)
    "ambassador_joined": TemplateDef(
        "ambassador_joined",
        f"You’re promoting on {BRAND_NAME} Ambassadors",
        "email_ticket_updates",
        False,
        "You’re an Ambassador",
        _ambassador_joined,
        "Open dashboard",
        "/dashboard/ambassador",
    ),
    "ambassador_first_sale": TemplateDef(
        "ambassador_first_sale",
        f"First Ambassador sale on {BRAND_NAME}",
        "email_ticket_updates",
        False,
        "First sale recorded",
        _ambassador_first_sale,
        "View earnings",
        "/dashboard/ambassador/earnings",
    ),
    "ambassador_commission_payable": TemplateDef(
        "ambassador_commission_payable",
        f"Ambassador earnings ready on {BRAND_NAME}",
        "email_ticket_updates",
        False,
        "Commission payable",
        _ambassador_commission_payable,
        "View earnings",
        "/dashboard/ambassador/earnings",
    ),
    "ambassador_payout_ready": TemplateDef(
        "ambassador_payout_ready",
        f"Ambassador reward marked paid on {BRAND_NAME}",
        "email_ticket_updates",
        False,
        "Reward marked paid",
        _ambassador_payout_ready,
        "View payouts",
        "/dashboard/ambassador/payouts",
    ),
    "ambassador_reward_rejected": TemplateDef(
        "ambassador_reward_rejected",
        f"Ambassador reward update on {BRAND_NAME}",
        "email_ticket_updates",
        False,
        "Reward not approved",
        _ambassador_reward_rejected,
        "View earnings",
        "/dashboard/ambassador/earnings",
    ),
    "ambassador_reward_reversed": TemplateDef(
        "ambassador_reward_reversed",
        f"Ambassador reward reversed on {BRAND_NAME}",
        "email_ticket_updates",
        False,
        "Reward reversed",
        _ambassador_reward_reversed,
        "View earnings",
        "/dashboard/ambassador/earnings",
    ),
    "host_ambassador_team_reward_action": TemplateDef(
        "host_ambassador_team_reward_action",
        f"Team Ambassadors update on {BRAND_NAME}",
        "email_host_activity",
        False,
        "Team Ambassadors update",
        _host_ambassador_team_reward_action,
        "View Ambassadors",
        "/host/ambassadors/conversions",
    ),
    "host_ambassador_suspicious_reversal": TemplateDef(
        "host_ambassador_suspicious_reversal",
        f"Ambassadors reversal flagged on {BRAND_NAME}",
        "email_host_activity",
        False,
        "Ambassadors reversal flagged",
        _host_ambassador_suspicious_reversal,
        "Review Ambassadors",
        "/host/ambassadors/conversions",
    ),
    "ambassador_campaign_paused": TemplateDef(
        "ambassador_campaign_paused",
        f"Ambassadors campaign paused",
        "email_ticket_updates",
        False,
        "Campaign paused",
        _ambassador_campaign_paused,
        "Open dashboard",
        "/dashboard/ambassador",
    ),
    "ambassador_campaign_ended": TemplateDef(
        "ambassador_campaign_ended",
        f"Ambassadors campaign ended",
        "email_ticket_updates",
        False,
        "Campaign ended",
        _ambassador_campaign_ended,
        "Open dashboard",
        "/dashboard/ambassador",
    ),
    "host_ambassador_milestone": TemplateDef(
        "host_ambassador_milestone",
        f"Ambassadors milestone on {BRAND_NAME}",
        "email_host_activity",
        False,
        "Ambassadors milestone",
        _host_ambassador_milestone,
        "View campaign",
        "/host/ambassadors/campaigns",
    ),
}


def _admin_platform_notice(c: dict[str, Any]) -> list[str]:
    lines = c.get("admin_lines")
    if isinstance(lines, list) and lines:
        return [str(x) for x in lines]
    if isinstance(lines, str) and lines.strip():
        return [p.strip() for p in lines.split("\n") if p.strip()]
    preview = _ctx(c, "preview_text")
    if preview:
        return [preview]
    return [f"Platform notice on {BRAND_NAME}."]


def _register_admin_catalog_templates() -> None:
    from app.email.admin_catalog import ADMIN_TEMPLATE_CATALOG

    for key, entry in ADMIN_TEMPLATE_CATALOG.items():
        if key in TEMPLATES:
            continue
        TEMPLATES[key] = TemplateDef(
            key,
            entry.subject,
            None,
            entry.required,
            entry.headline,
            _admin_platform_notice,
            entry.cta_label,
            entry.cta_path,
        )


_register_admin_catalog_templates()


def get_template(name: str) -> TemplateDef:
    if name not in TEMPLATES:
        raise KeyError(f"Unknown email template: {name}")
    return TEMPLATES[name]


def render_subject(template: TemplateDef, context: dict[str, Any]) -> str:
    custom = context.get("subject")
    subject = str(custom) if custom else template.subject
    # Light format for event titles in subject overrides
    try:
        subject = subject.format(**{k: v for k, v in context.items() if isinstance(v, (str, int))})
    except (KeyError, ValueError):
        pass
    assert_brand_safe(subject)
    return subject[:255]
