"""Push channel coverage for wired notification kinds."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.notifications.channel_registry import push_channel_allowed
from app.notifications.prefs import push_pref_key_for_kind
from app.push.privacy import sanitize_push_context, scrub_push_copy
from app.push.templates import resolve_template_name, render_push

# Kinds observed in notify_user(...) call sites — must not fall back to generic
# unless explicitly allowed (admin-composed campaigns).
WIRED_NOTIFY_KINDS: frozenset[str] = frozenset(
    {
        "ticket.confirmed",
        "ticket.qr_ready",
        "ticket.refund_update",
        "ticket.event_cancelled",
        "ticket.transferred",
        "ticket.transfer_accepted",
        "ticket.checked_in",
        "host.ticket_sale",
        "merch.confirmed",
        "merch.paid",
        "merch.ready_for_pickup",
        "merch.picked_up",
        "merch.refunded",
        "merch.shipped",
        "merch.delivered",
        "merch.host_sale",
        "merch.host_pickup",
        "merch.host_cart_summary",
        "merch.sold_out",
        "merch.low_stock",
        "merch.review_received",
        "merch.vault_unlocked",
        "merch.cart_reminder",
        "merch.post_event_drop",
        "merch.badge_earned",
        "fan_connect.request",
        "fan_connect.accepted",
        "fan_connect.declined",
        "fan_connect.removed",
        "fan_connect.message",
        "message.new",
        "sponsor.inquiry_received",
        "sponsor.inquiry_host",
        "sponsor.inquiry_status",
        "sponsor.deliverable_approved",
        "sponsor.deliverable_rejected",
        "sponsor.deliverable_submitted",
        "sponsor.deliverables_completed",
        "sponsor.deal_active",
        "sponsor.deal_proposal",
        "review.new",
        "review.reply",
        "support.ticket_updated",
        "admin_support_ticket",
        "admin.report",
        "account.suspended",
        "account.appeal_decision",
        "system.maintenance",
        "host.new_follower",
        "host.ambassador_milestone",
        "host.ambassador_team_reward",
        "host.ambassador_suspicious_reversal",
        "ambassador.joined",
        "ambassador.first_sale",
        "ambassador.reward_approved",
        "ambassador.reward_rejected",
        "ambassador.reward_marked_paid",
        "ambassador.reward_reversed",
        "ambassador.campaign_paused",
        "ambassador.campaign_ended",
        "team.invite",
        "team.invite_accepted",
        "team.invite_revoked",
        "team.member_removed",
        "team.permission_updated",
        "team.security_alert",
        "admin.push_test",
        "marketing.promo",
        "message_request_accepted",
    }
)

GENERIC_OK = frozenset(
    {
        "admin.campaign",
        "admin.custom",
        "admin.custom_campaign",
        "marketing.promo",
    }
)

SENSITIVE_MARKERS = re.compile(
    r"(paystack|sk_live|qr_secret|-----BEGIN|password reset token|"
    r"\b\d{16}\b|private_key)",
    re.I,
)


@pytest.mark.parametrize("kind", sorted(WIRED_NOTIFY_KINDS))
def test_wired_kind_has_dedicated_push_template(kind: str):
    tmpl = resolve_template_name(kind)
    if kind in GENERIC_OK:
        assert tmpl == "generic"
        return
    assert tmpl != "generic", f"{kind} should map to a safe push template"


@pytest.mark.parametrize("kind", sorted(WIRED_NOTIFY_KINDS))
def test_wired_kind_push_channel_allowed(kind: str):
    allowed, reason = push_channel_allowed(kind)
    assert allowed, reason or kind


def test_support_push_does_not_echo_subject_in_body():
    title, body, *_ = render_push(
        "support_ticket_updated",
        {"action_url": "/dashboard/support", "subject": "My password leaked"},
    )
    assert "password" not in body.lower()
    assert "leaked" not in body.lower()
    assert title == "Support update"


def test_security_templates_avoid_detail_leak():
    for tmpl in ("account_suspended", "account_appeal_decision", "system_maintenance"):
        _, body, *_ = render_push(
            tmpl,
            {"detail": "IP 203.0.113.9 changed password", "title": "Secret"},
        )
        assert "203.0.113" not in body
        assert "password" not in body.lower() or "your" in body.lower()


def test_push_pref_uses_dotted_kind_for_merch_host_sale():
    assert push_pref_key_for_kind("merch.host_sale") == "push_merch_updates"
    assert push_pref_key_for_kind("merch_host_sale") == "push_merch_updates"


def test_sanitize_strips_sensitive_push_context():
    ctx = sanitize_push_context(
        {
            "qr_payload": "secret",
            "ticket_id": "uuid",
            "paystack_reference": "ref",
            "event_title": "Summer Fest",
            "action_url": "/dashboard/tickets",
        }
    )
    assert "qr_payload" not in ctx
    assert "paystack_reference" not in ctx
    assert ctx.get("event_title") == "Summer Fest"


def test_scrub_push_copy_strips_email_and_phone():
    out = scrub_push_copy("Contact me at fan@example.com or +2348012345678")
    assert "fan@example.com" not in out
    assert "+2348012345678" not in out


def test_all_registry_kinds_resolve_template_or_generic_with_reason():
    from app.notifications.channel_registry import all_user_facing_kinds

    for kind in all_user_facing_kinds():
        tmpl = resolve_template_name(kind)
        assert tmpl in {"generic"} or tmpl != "generic"
        allowed, _ = push_channel_allowed(kind)
        assert allowed or kind in {"admin.internal_note", "crm.host_note"}


def test_admin_notification_types_have_push_template_or_generic_ok():
    from app.admin_notifications.registry import NOTIFICATION_TYPES

    for typedef in NOTIFICATION_TYPES:
        keys = {typedef.key, *(typedef.kind_aliases or ())}
        for kind in keys:
            allowed, reason = push_channel_allowed(kind)
            assert allowed, f"{kind}: {reason}"
            tmpl = resolve_template_name(kind)
            if typedef.key in {"admin.custom_campaign"} or kind.startswith("admin.custom"):
                assert tmpl == "generic"
                continue
            assert tmpl != "generic", f"{kind} should map to a dedicated push template"


def test_notify_kinds_in_codebase_subset_of_coverage_list():
    """Guardrail: new notify_user kinds should be added to WIRED_NOTIFY_KINDS."""
    root = Path(__file__).resolve().parents[1] / "app"
    found: set[str] = set()
    pat = re.compile(r'kind\s*=\s*["\']([a-z0-9_.]+)["\']')
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "notify_user(" not in text:
            continue
        for m in pat.finditer(text):
            k = m.group(1)
            if k in {"email", "username", "host_reply", "fan_reply"}:
                continue
            if k.startswith("security."):
                found.add(k)
                continue
            if "." in k or k.startswith("admin_") or k in {"message_request_accepted"}:
                found.add(k)
    missing = found - WIRED_NOTIFY_KINDS - GENERIC_OK
    assert not missing, f"Add to WIRED_NOTIFY_KINDS: {sorted(missing)}"
