"""Admin platform email template catalog — defaults, categories, variables.

Copy defaults live here and in ``templates.py`` registry entries.
Admins override subject/body via ``email_admin_templates`` rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

AdminRecipientGroup = Literal[
    "super_admin",
    "support",
    "moderation",
    "finance",
    "operations",
    "marketing",
    "custom",
]

AdminDeliveryMode = Literal["instant", "disabled", "digest"]

AdminTemplateCategory = Literal[
    "account",
    "tickets",
    "merch",
    "hosts_events",
    "support_safety",
    "sponsors_ambassadors",
    "payments",
]


@dataclass(frozen=True)
class AdminTemplateCatalogEntry:
    key: str
    title: str
    category: AdminTemplateCategory
    subject: str
    headline: str
    preview_text: str
    cta_label: str
    cta_path: str
    variables: tuple[str, ...]
    required: bool
    default_enabled: bool
    default_recipient_group: AdminRecipientGroup
    delivery_mode: AdminDeliveryMode
    """Minimum order amount (same currency units as context ``amount``) for instant send."""
    threshold_amount: float | None = None


def _entry(
    key: str,
    title: str,
    category: AdminTemplateCategory,
    subject: str,
    headline: str,
    preview: str,
    cta: str,
    path: str,
    variables: tuple[str, ...],
    *,
    required: bool = False,
    enabled: bool = True,
    group: AdminRecipientGroup = "operations",
    delivery: AdminDeliveryMode = "instant",
    threshold: float | None = None,
) -> AdminTemplateCatalogEntry:
    return AdminTemplateCatalogEntry(
        key=key,
        title=title,
        category=category,
        subject=subject,
        headline=headline,
        preview_text=preview,
        cta_label=cta,
        cta_path=path,
        variables=variables,
        required=required,
        default_enabled=enabled,
        default_recipient_group=group,
        delivery_mode=delivery,
        threshold_amount=threshold,
    )


ADMIN_TEMPLATE_CATALOG: dict[str, AdminTemplateCatalogEntry] = {
    e.key: e
    for e in (
        _entry(
            "admin_new_user_registered",
            "New user registered",
            "account",
            "New user on Pàdéyá",
            "New user registered",
            "A new fan account was created on Pàdéyá.",
            "View user",
            "/admin/users",
            ("user_name", "user_email", "username", "registered_at", "user_id_safe", "admin_user_url"),
            enabled=True,
            group="operations",
        ),
        _entry(
            "admin_user_email_verified",
            "User email verified",
            "account",
            "Email verified on Pàdéyá",
            "Email verified",
            "A user verified their email address.",
            "View user",
            "/admin/users",
            ("user_name", "user_email", "username", "verified_at", "admin_user_url"),
            enabled=False,
            group="operations",
        ),
        _entry(
            "admin_user_restricted",
            "User restricted",
            "account",
            "User restriction on Pàdéyá",
            "User restricted",
            "An account restriction was applied.",
            "View user",
            "/admin/users",
            ("user_name", "user_email", "restriction_label", "admin_user_url"),
            group="moderation",
        ),
        _entry(
            "admin_user_suspended",
            "User suspended",
            "account",
            "User suspended on Pàdéyá",
            "User suspended",
            "An account was suspended.",
            "View user",
            "/admin/users",
            ("user_name", "user_email", "reason_category", "admin_user_url"),
            required=True,
            group="moderation",
        ),
        _entry(
            "admin_user_appeal_submitted",
            "Appeal submitted",
            "account",
            "New appeal on Pàdéyá",
            "Appeal submitted",
            "A suspended user submitted an appeal.",
            "Review appeal",
            "/admin/appeals",
            ("user_name", "user_email", "appeal_id_safe", "admin_appeal_url"),
            group="moderation",
        ),
        _entry(
            "admin_new_ticket_sale",
            "New ticket sale",
            "tickets",
            "Ticket sale on Pàdéyá",
            "New ticket sale",
            "A verified ticket order was paid.",
            "View order",
            "/admin/payments",
            (
                "event_title",
                "host_name",
                "buyer_name",
                "order_reference",
                "ticket_count",
                "amount",
                "currency",
                "payment_status",
                "admin_order_url",
                "admin_event_url",
            ),
            enabled=True,
            group="finance",
        ),
        _entry(
            "admin_large_ticket_order",
            "Large ticket order",
            "tickets",
            "High-value ticket order on Pàdéyá",
            "Large ticket order",
            "A high-value ticket order was paid.",
            "View order",
            "/admin/payments",
            (
                "event_title",
                "host_name",
                "buyer_name",
                "order_reference",
                "ticket_count",
                "amount",
                "currency",
                "payment_status",
                "admin_order_url",
            ),
            group="finance",
            threshold=250_000.0,
        ),
        _entry(
            "admin_ticket_refund_requested",
            "Ticket refund requested",
            "tickets",
            "Ticket refund requested",
            "Refund requested",
            "A ticket refund was requested.",
            "Review refund",
            "/admin/refunds",
            ("event_title", "order_reference", "amount", "currency", "admin_refund_url"),
            group="finance",
        ),
        _entry(
            "admin_ticket_refund_completed",
            "Ticket refund completed",
            "tickets",
            "Ticket refund completed",
            "Refund completed",
            "A ticket refund was completed.",
            "View refund",
            "/admin/refunds",
            ("event_title", "order_reference", "amount", "currency", "admin_refund_url"),
            enabled=False,
            group="finance",
        ),
        _entry(
            "admin_payment_failed",
            "Payment failed",
            "payments",
            "Payment failed on Pàdéyá",
            "Payment failed",
            "A payment attempt failed after checkout.",
            "View payments",
            "/admin/payments",
            ("order_reference", "amount", "currency", "failure_reason_safe", "admin_order_url"),
            group="finance",
        ),
        _entry(
            "admin_chargeback_or_dispute",
            "Chargeback or dispute",
            "payments",
            "Payment dispute on Pàdéyá",
            "Dispute opened",
            "A chargeback or dispute needs finance review.",
            "View payments",
            "/admin/payments",
            ("order_reference", "amount", "currency", "dispute_status", "admin_order_url"),
            required=True,
            group="finance",
        ),
        _entry(
            "admin_payment_issue",
            "Payment issue",
            "payments",
            "Payment issue on Pàdéyá",
            "Payment issue",
            "A payment or webhook issue needs attention.",
            "Open payments",
            "/admin/payments",
            ("detail", "admin_payments_url"),
            required=True,
            group="finance",
        ),
        _entry(
            "admin_new_merch_sale",
            "New merch sale",
            "merch",
            "Merch sale on Pàdéyá",
            "New merch sale",
            "A verified merch order was paid.",
            "View order",
            "/admin/merch",
            (
                "product_title",
                "host_name",
                "buyer_name",
                "order_reference",
                "quantity",
                "amount",
                "currency",
                "fulfillment_type",
                "admin_order_url",
                "admin_merch_url",
            ),
            enabled=False,
            group="finance",
        ),
        _entry(
            "admin_merch_refund_requested",
            "Merch refund requested",
            "merch",
            "Merch refund requested",
            "Merch refund requested",
            "A merch refund was requested.",
            "Review refund",
            "/admin/refunds",
            ("product_title", "order_reference", "amount", "currency", "admin_refund_url"),
            group="finance",
        ),
        _entry(
            "admin_merch_fulfillment_issue",
            "Merch fulfillment issue",
            "merch",
            "Merch fulfillment issue",
            "Fulfillment issue",
            "A merch fulfillment issue was reported.",
            "View merch",
            "/admin/merch",
            ("product_title", "host_name", "order_reference", "issue_summary", "admin_merch_url"),
            group="operations",
        ),
        _entry(
            "admin_low_stock_alert",
            "Low stock alert",
            "merch",
            "Low merch stock on Pàdéyá",
            "Low stock",
            "Merch inventory dropped below the alert threshold.",
            "View product",
            "/admin/merch",
            ("product_title", "host_name", "quantity_remaining", "admin_merch_url"),
            enabled=False,
            group="operations",
        ),
        _entry(
            "admin_merch_sold_out",
            "Merch sold out",
            "merch",
            "Merch sold out",
            "Sold out",
            "A merch product sold out.",
            "View product",
            "/admin/merch",
            ("product_title", "host_name", "admin_merch_url"),
            enabled=False,
            group="operations",
        ),
        _entry(
            "admin_new_host_created",
            "New host created",
            "hosts_events",
            "New host on Pàdéyá",
            "New host",
            "A new host workspace was created.",
            "View host",
            "/admin/hosts",
            ("host_name", "username", "city", "admin_host_url"),
            enabled=False,
            group="operations",
        ),
        _entry(
            "admin_host_verification_requested",
            "Host verification requested",
            "hosts_events",
            "Host verification requested",
            "Verification requested",
            "A host requested verification review.",
            "Review host",
            "/admin/hosts",
            ("host_name", "username", "admin_host_url"),
            group="operations",
        ),
        _entry(
            "admin_new_event_created",
            "New event created",
            "hosts_events",
            "New event draft on Pàdéyá",
            "New event",
            "A host created a new event.",
            "View event",
            "/admin/events",
            (
                "event_title",
                "host_name",
                "event_date",
                "status",
                "city",
                "admin_event_url",
            ),
            enabled=False,
            group="operations",
        ),
        _entry(
            "admin_event_published",
            "Event published",
            "hosts_events",
            "Event published on Pàdéyá",
            "Event published",
            "An event was published to the marketplace.",
            "View event",
            "/admin/events",
            ("event_title", "host_name", "event_date", "city", "admin_event_url"),
            enabled=False,
            group="operations",
        ),
        _entry(
            "admin_event_cancelled",
            "Event cancelled",
            "hosts_events",
            "Event cancelled on Pàdéyá",
            "Event cancelled",
            "An event was cancelled.",
            "View event",
            "/admin/events",
            ("event_title", "host_name", "admin_event_url"),
            group="operations",
        ),
        _entry(
            "admin_event_flagged",
            "Event flagged",
            "hosts_events",
            "Event flagged on Pàdéyá",
            "Event flagged",
            "An event was flagged for admin review.",
            "Review event",
            "/admin/events",
            ("event_title", "host_name", "flag_reason_safe", "admin_event_url"),
            group="moderation",
        ),
        _entry(
            "admin_new_support_ticket",
            "New support ticket",
            "support_safety",
            "New support ticket on Pàdéyá",
            "Support ticket",
            "A new support ticket was opened.",
            "Open ticket",
            "/admin/support",
            (
                "ticket_number",
                "subject",
                "requester_name",
                "category",
                "priority",
                "admin_ticket_url",
            ),
            group="support",
        ),
        _entry(
            "admin_new_report",
            "New report",
            "support_safety",
            "New report on Pàdéyá",
            "New report",
            "A new moderation report was submitted.",
            "Open admin",
            "/admin",
            ("report_kind", "report_id_safe", "admin_report_url"),
            required=True,
            group="moderation",
        ),
        _entry(
            "admin_safety_report",
            "Safety report",
            "support_safety",
            "Safety report on Pàdéyá",
            "Safety report",
            "A safety report needs moderation review.",
            "Open reports",
            "/admin",
            ("report_kind", "report_id_safe", "admin_report_url"),
            required=True,
            group="moderation",
        ),
        _entry(
            "admin_abuse_report",
            "Abuse report",
            "support_safety",
            "Abuse report on Pàdéyá",
            "Abuse report",
            "An abuse report was submitted.",
            "Open reports",
            "/admin",
            ("report_kind", "report_id_safe", "admin_report_url"),
            required=True,
            group="moderation",
        ),
        _entry(
            "admin_message_report",
            "Message report",
            "support_safety",
            "Message report on Pàdéyá",
            "Message report",
            "A message thread was reported.",
            "Review report",
            "/admin",
            ("report_kind", "thread_id_safe", "admin_report_url"),
            required=True,
            group="moderation",
        ),
        _entry(
            "admin_new_sponsor_inquiry",
            "New sponsor inquiry",
            "sponsors_ambassadors",
            "Sponsor inquiry on Pàdéyá",
            "Sponsor inquiry",
            "A new sponsor inquiry was submitted.",
            "View inquiry",
            "/admin/sponsors",
            ("host_name", "brand_name", "inquiry_id_safe", "admin_inquiry_url"),
            group="marketing",
        ),
        _entry(
            "admin_new_ambassador_joined",
            "Ambassador joined",
            "sponsors_ambassadors",
            "Ambassador joined campaign",
            "Ambassador joined",
            "A fan joined an ambassador campaign.",
            "View campaign",
            "/admin/ambassadors",
            ("event_title", "host_name", "campaign_name", "admin_campaign_url"),
            enabled=False,
            group="operations",
        ),
        _entry(
            "admin_ambassador_click_inflation_suspect",
            "Ambassador click fraud suspect",
            "sponsors_ambassadors",
            "Ambassador fraud signal",
            "Suspicious ambassador activity",
            "Suspicious ambassador click patterns were detected.",
            "Review campaign",
            "/admin/ambassadors",
            ("event_title", "host_name", "campaign_name", "signal_summary", "admin_campaign_url"),
            group="moderation",
        ),
        _entry(
            "admin_ambassador_reward_issue",
            "Ambassador reward issue",
            "sponsors_ambassadors",
            "Ambassador reward issue",
            "Reward issue",
            "An ambassador reward needs review.",
            "View rewards",
            "/admin/ambassadors",
            ("event_title", "host_name", "issue_summary", "admin_campaign_url"),
            group="finance",
        ),
    )
}

# Legacy registry alias
ADMIN_TEMPLATE_CATALOG["admin_support_ticket"] = _entry(
    "admin_support_ticket",
    "Support case (legacy key)",
    "support_safety",
    "Support case on Pàdéyá",
    "Support case",
    "Support case update for admins.",
    "Open support",
    "/admin/support",
    ("case_ref", "admin_ticket_url"),
    group="support",
)


def catalog_entry(key: str) -> AdminTemplateCatalogEntry | None:
    return ADMIN_TEMPLATE_CATALOG.get(key)


def is_admin_platform_template(key: str) -> bool:
    return key in ADMIN_TEMPLATE_CATALOG


def build_admin_lines(entry: AdminTemplateCatalogEntry, context: dict[str, Any]) -> list[str]:
    lines: list[str] = [entry.preview_text]
    for var in entry.variables:
        val = context.get(var)
        if val is None or val == "":
            continue
        label = var.replace("_", " ").strip().title()
        lines.append(f"{label}: {val}")
    return lines


def sample_context_for(entry: AdminTemplateCatalogEntry) -> dict[str, str]:
    samples: dict[str, str] = {}
    for var in entry.variables:
        samples[var] = f"[{var}]"
    samples["admin_lines"] = "\n".join(build_admin_lines(entry, samples))
    return samples
