"""Push template catalog — short copy, aliases, no chat bodies."""

from __future__ import annotations

from app.push.templates import (
    KIND_ALIASES,
    TEMPLATES,
    list_template_names,
    render_push,
    resolve_template_name,
)

REQUIRED = [
    # Tickets
    "ticket_confirmed",
    "ticket_qr_ready",
    "ticket_event_reminder",
    "ticket_event_cancelled",
    "ticket_refund_update",
    # Merch
    "merch_order_confirmed",
    "merch_pickup_ready",
    "merch_shipping_update",
    "merch_picked_up",
    "merch_refund_update",
    "post_event_drop_available",
    "merch_cart_reminder",
    # Messaging
    "new_message",
    "message_request",
    "attachment_received",
    # Fan Connect
    "fan_connect_request",
    "fan_connect_accepted",
    "fan_connect_message",
    # Host
    "host_ticket_sale",
    "host_merch_sale",
    "host_new_review",
    "host_sponsor_inquiry",
    # Sponsor
    "sponsor_inquiry_confirmation",
    "sponsor_inquiry_host_alert",
    "sponsor_inquiry_status_update",
    # Admin
    "admin_new_report",
    "admin_payment_issue",
    "admin_support_ticket",
    # Ambassadors
    "ambassador_joined",
    "ambassador_first_sale",
    "ambassador_commission_payable",
    "ambassador_payout_ready",
    "ambassador_campaign_paused",
    "ambassador_campaign_ended",
    "host_ambassador_milestone",
]


def test_required_push_templates_exist():
    names = set(list_template_names())
    missing = [n for n in REQUIRED if n not in names]
    assert missing == [], f"missing templates: {missing}"


def test_render_push_short_copy_and_brand():
    title, body, action, icon, badge = render_push(
        "ticket_confirmed",
        {"event_title": "Lagos Night"},
    )
    assert title == "Ticket confirmed"
    assert "Lagos Night" in body
    assert "Pàdéyá" in body
    assert len(title) <= 80
    assert len(body) <= 160
    assert action == "/dashboard/tickets"
    assert icon.startswith("/brand/")
    assert badge.startswith("/brand/")


def test_kind_aliases_resolve():
    assert resolve_template_name("ticket.confirmed") == "ticket_confirmed"
    assert resolve_template_name("merch.ready_for_pickup") == "merch_pickup_ready"
    assert resolve_template_name("fan_connect.request") == "fan_connect_request"
    assert resolve_template_name("message.host_reply") == "new_message"
    assert resolve_template_name("admin.report") == "admin_new_report"
    for kind, template in KIND_ALIASES.items():
        assert template in TEMPLATES, f"{kind} → {template}"


def test_message_templates_never_include_chat_body():
    from app.push.privacy import GENERIC_MESSAGE_BODY

    title, body, *_ = render_push(
        "new_message",
        {"title": "Secret chat", "body": "PRIVATE MESSAGE BODY DO NOT LEAK"},
    )
    assert title == "New message"
    assert body == GENERIC_MESSAGE_BODY
    assert "PRIVATE" not in body
    assert "Secret chat" not in title


def test_all_required_templates_render():
    for name in REQUIRED:
        title, body, action, *_ = render_push(name, {"event_title": "Demo"})
        assert title.strip()
        assert body.strip()
        assert action.startswith("/")
        assert len(body) <= 240
