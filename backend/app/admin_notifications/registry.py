"""Admin-controlled notification type registry for Pàdéyá."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Channel = Literal["in_app", "push", "email"]
AudienceKey = Literal[
    "all_users",
    "selected_users",
    "host_followers",
    "event_ticket_buyers",
    "checked_in_attendees",
    "vip_ticket_holders",
    "past_buyers",
    "past_merch_buyers",
    "vault_members",
    "ambassadors",
    "host_team_members",
    "role",
    "geo",
    "context_recipients",  # callers pass explicit user ids
]

Classification = Literal["transactional", "marketing", "critical"]


@dataclass(frozen=True)
class NotificationTypeDef:
    key: str
    label: str
    description: str
    classification: Classification
    default_enabled: bool = True
    default_channels: tuple[Channel, ...] = ("in_app", "push", "email")
    default_audience: AudienceKey = "context_recipients"
    # Only super_admin (admin.full_access) may disable critical types.
    critical: bool = False
    # Respect user marketing prefs when classification=marketing.
    respect_user_prefs: bool = True
    default_cooldown_seconds: int = 0
    default_queued: bool = False
    # Maps to existing email template name when email channel on (optional).
    email_template: str | None = None
    # Maps to existing push/in-app kind aliases.
    kind_aliases: tuple[str, ...] = ()


NOTIFICATION_TYPES: tuple[NotificationTypeDef, ...] = (
    NotificationTypeDef(
        "event.published",
        "New event published",
        "When a host event is published.",
        "marketing",
        default_audience="host_followers",
        default_cooldown_seconds=3600,
        email_template=None,
        kind_aliases=("event.published",),
    ),
    NotificationTypeDef(
        "event.updated",
        "Event updated",
        "Material updates to a published event.",
        "transactional",
        default_audience="event_ticket_buyers",
        email_template="ticket_event_updated",
        kind_aliases=("ticket_event_updated", "event.updated"),
    ),
    NotificationTypeDef(
        "event.cancelled",
        "Event cancelled",
        "Event cancellation notices to ticket holders.",
        "transactional",
        default_audience="event_ticket_buyers",
        email_template="ticket_event_cancelled",
        kind_aliases=("ticket_event_cancelled", "event.cancelled"),
    ),
    NotificationTypeDef(
        "event.rescheduled",
        "Event rescheduled",
        "Date/time changes for ticket holders.",
        "transactional",
        default_audience="event_ticket_buyers",
        email_template="ticket_event_updated",
        kind_aliases=("event.rescheduled",),
    ),
    NotificationTypeDef(
        "event.reminder",
        "Event reminder",
        "Reminders before events.",
        "transactional",
        default_audience="event_ticket_buyers",
        email_template="ticket_event_reminder",
        default_cooldown_seconds=86400,
        kind_aliases=("ticket_event_reminder", "event.reminder"),
    ),
    NotificationTypeDef(
        "ticket.purchase_confirmed",
        "Ticket purchase confirmed",
        "After verified payment.",
        "transactional",
        default_audience="context_recipients",
        respect_user_prefs=False,
        email_template="ticket_purchase_confirmed",
        kind_aliases=("ticket.confirmed", "ticket_purchase_confirmed"),
    ),
    NotificationTypeDef(
        "ticket.transferred",
        "Ticket transferred",
        "Ticket transfer completed.",
        "transactional",
        default_audience="context_recipients",
        email_template="ticket_transfer_received",
        kind_aliases=("ticket.transferred",),
    ),
    NotificationTypeDef(
        "ticket.transfer_accepted",
        "Ticket transfer accepted",
        "When a recipient claims a ticket you transferred.",
        "transactional",
        default_audience="context_recipients",
        email_template="ticket_transfer_accepted",
        kind_aliases=("ticket.transfer_accepted",),
    ),
    NotificationTypeDef(
        "refund.requested",
        "Refund requested",
        "Buyer/host/admin refund request notice.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("refund.requested",),
    ),
    NotificationTypeDef(
        "refund.approved",
        "Refund approved",
        "Refund approved.",
        "transactional",
        default_audience="context_recipients",
        email_template="ticket_refund_update",
        kind_aliases=("refund.approved", "ticket_refund_update"),
    ),
    NotificationTypeDef(
        "refund.rejected",
        "Refund rejected",
        "Refund rejected.",
        "transactional",
        default_audience="context_recipients",
        email_template="ticket_refund_update",
        kind_aliases=("refund.rejected",),
    ),
    NotificationTypeDef(
        "checkin.successful",
        "Check-in successful",
        "Attendee checked in.",
        "transactional",
        default_channels=("in_app", "push"),
        default_audience="context_recipients",
        email_template="ticket_checked_in",
        kind_aliases=("ticket.checked_in", "checkin.successful"),
    ),
    NotificationTypeDef(
        "merch.listing_published",
        "Host posts new merch listing",
        "New merch product goes live.",
        "marketing",
        default_audience="host_followers",
        default_cooldown_seconds=1800,
        kind_aliases=("merch.listing_published",),
    ),
    NotificationTypeDef(
        "merch.post_event_drop_live",
        "Post-event merch drop goes live",
        "Recap drop becomes available.",
        "marketing",
        default_audience="context_recipients",
        email_template="post_event_drop_available",
        kind_aliases=("merch.post_event_drop", "post_event_drop_available"),
    ),
    NotificationTypeDef(
        "vault.item_published",
        "Host publishes Vault item",
        "New Vault drop published.",
        "marketing",
        default_audience="host_followers",
        default_cooldown_seconds=1800,
        kind_aliases=("vault.item_published",),
    ),
    NotificationTypeDef(
        "vault.merch_unlocked",
        "Vault merch unlocked",
        "Buyer becomes eligible for vault-exclusive merch.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("merch.vault_unlocked", "vault.merch_unlocked"),
    ),
    NotificationTypeDef(
        "host.announcement",
        "Host announcement",
        "CRM host announcement fan-out.",
        "marketing",
        default_audience="context_recipients",
        kind_aliases=("host.announcement",),
    ),
    NotificationTypeDef(
        "ambassador.campaign_new",
        "New ambassador campaign",
        "Ambassador campaign opens.",
        "marketing",
        default_audience="ambassadors",
        kind_aliases=("ambassador.campaign_new",),
    ),
    NotificationTypeDef(
        "ambassador.reward_earned",
        "Ambassador reward earned",
        "Commission / reward earned.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("ambassador.reward_earned",),
    ),
    NotificationTypeDef(
        "sponsor.inquiry",
        "Sponsorship inquiry",
        "New sponsor inquiry to host.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("sponsor.inquiry", "host_sponsor_inquiry"),
    ),
    NotificationTypeDef(
        "fan_connect.request",
        "Fan Connect request",
        "New connection request.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("fan_connect.request", "fan_connect_request"),
    ),
    NotificationTypeDef(
        "fan_connect.accepted",
        "Fan Connect accepted",
        "Connection accepted.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("fan_connect.accepted", "fan_connect_accepted"),
    ),
    NotificationTypeDef(
        "message.new",
        "New message",
        "Messaging away-from-chat alert.",
        "transactional",
        default_channels=("in_app", "push", "email"),
        default_audience="context_recipients",
        default_cooldown_seconds=45,
        kind_aliases=("new_message", "message.new"),
    ),
    NotificationTypeDef(
        "review.request",
        "Review request",
        "Ask attendee to leave a review.",
        "marketing",
        default_audience="context_recipients",
        kind_aliases=("review.request",),
    ),
    NotificationTypeDef(
        "review.approved",
        "Review approved",
        "Review moderation approved.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("review.approved",),
    ),
    NotificationTypeDef(
        "review.rejected",
        "Review rejected",
        "Review moderation rejected.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("review.rejected",),
    ),
    NotificationTypeDef(
        "account.restricted",
        "Account restricted",
        "Selective account restriction applied.",
        "critical",
        critical=True,
        respect_user_prefs=False,
        default_audience="context_recipients",
        kind_aliases=("account.restricted",),
    ),
    NotificationTypeDef(
        "account.suspended",
        "Account suspended",
        "Account suspension notice.",
        "critical",
        critical=True,
        respect_user_prefs=False,
        default_audience="context_recipients",
        kind_aliases=("account.suspended",),
    ),
    NotificationTypeDef(
        "appeal.submitted",
        "Suspension appeal submitted",
        "Appeal received (user + admins).",
        "critical",
        critical=True,
        respect_user_prefs=False,
        default_audience="context_recipients",
        kind_aliases=("appeal.submitted",),
    ),
    NotificationTypeDef(
        "appeal.approved",
        "Suspension appeal approved",
        "Appeal approved.",
        "critical",
        critical=True,
        respect_user_prefs=False,
        default_audience="context_recipients",
        kind_aliases=("appeal.approved",),
    ),
    NotificationTypeDef(
        "appeal.rejected",
        "Suspension appeal rejected",
        "Appeal rejected.",
        "critical",
        critical=True,
        respect_user_prefs=False,
        default_audience="context_recipients",
        kind_aliases=("appeal.rejected",),
    ),
    NotificationTypeDef(
        "support.ticket_updated",
        "Support ticket updated",
        "Support case status / reply update.",
        "transactional",
        default_audience="context_recipients",
        kind_aliases=("support.ticket_updated",),
    ),
    NotificationTypeDef(
        "admin.custom_campaign",
        "Custom admin campaign",
        "Admin-composed custom notification.",
        "marketing",
        default_audience="selected_users",
        kind_aliases=("admin.campaign", "admin.custom"),
    ),
)

NOTIFICATION_TYPE_BY_KEY: dict[str, NotificationTypeDef] = {
    t.key: t for t in NOTIFICATION_TYPES
}

# Alias → canonical type key
KIND_TO_TYPE_KEY: dict[str, str] = {}
for _t in NOTIFICATION_TYPES:
    KIND_TO_TYPE_KEY[_t.key] = _t.key
    for alias in _t.kind_aliases:
        KIND_TO_TYPE_KEY[alias] = _t.key


def resolve_type_key(kind_or_key: str) -> str | None:
    k = (kind_or_key or "").strip()
    if not k:
        return None
    if k in NOTIFICATION_TYPE_BY_KEY:
        return k
    return KIND_TO_TYPE_KEY.get(k)


def get_type_def(key: str) -> NotificationTypeDef | None:
    return NOTIFICATION_TYPE_BY_KEY.get(key)
