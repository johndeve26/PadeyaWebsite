"""Push privacy — no sensitive fields on wire or in outbox context."""

from __future__ import annotations

import json

from app.push.privacy import (
    GENERIC_MESSAGE_BODY,
    message_push_copy,
    sanitize_delivery_error,
    sanitize_push_context,
    scrub_push_copy,
)
from app.push.provider import PushPayload
from app.push.templates import render_push


def test_sanitize_context_drops_sensitive_keys():
    clean = sanitize_push_context(
        {
            "event_title": "Lagos Night",
            "pickup_code": "ABC123XYZ",
            "entry_code": "ENTRY99",
            "shipping_address": "12 Hidden St",
            "phone": "+2348012345678",
            "email": "secret@example.com",
            "venue": "Secret warehouse",
            "order_id": "ord_abc123456",
            "attachment_url": "https://cdn.example/file.png",
            "vault_path": "/vault/locked",
            "message_body": "private chat text",
            "action_url": "/dashboard/messages/abc",
            "sender_name": "DJ Maze",
            "allow_message_preview": True,
        }
    )
    assert clean["event_title"] == "Lagos Night"
    assert clean["sender_name"] == "DJ Maze"
    assert clean["allow_message_preview"] is True
    assert "pickup_code" not in clean
    assert "entry_code" not in clean
    assert "shipping_address" not in clean
    assert "phone" not in clean
    assert "email" not in clean
    assert "venue" not in clean
    assert "order_id" not in clean
    assert "attachment_url" not in clean
    assert "message_body" not in clean
    assert clean["action_url"].startswith("/dashboard/messages")


def test_scrub_removes_emails_phones_urls_codes():
    raw = (
        "Meet at secret@place.com call +234 801 234 5678 "
        "https://evil.example/x code: AB12CD34 order_ref_abcdef"
    )
    out = scrub_push_copy(raw)
    assert "secret@place.com" not in out
    assert "801" not in out or "+234" not in out
    assert "https://" not in out
    assert "AB12CD34" not in out
    assert "order_ref" not in out.lower()


def test_message_copy_generic_by_default():
    title, body = message_push_copy(sender_name="DJ Maze", allow_preview=False)
    assert title == "New message"
    assert body == GENERIC_MESSAGE_BODY
    assert "DJ Maze" not in body


def test_message_copy_optional_safer_preview():
    title, body = message_push_copy(sender_name="DJ Maze", allow_preview=True)
    assert title == "New message"
    assert body == "DJ Maze sent you a message."
    assert "hello" not in body.lower()


def test_message_preview_never_includes_full_message_text():
    title, body = message_push_copy(
        sender_name="DJ Maze",
        allow_preview=True,
    )
    # Even if a caller tried to stuff chat into the name, scrub keeps it short.
    assert len(body) < 80
    assert "sent you a message" in body


def test_render_new_message_generic():
    title, body, *_ = render_push("new_message", {"body": "SECRET CHAT BODY"})
    assert title == "New message"
    assert body == GENERIC_MESSAGE_BODY
    assert "SECRET" not in body


def test_render_new_message_with_preview_pref():
    title, body, *_ = render_push(
        "new_message",
        {"sender_name": "DJ Maze", "allow_message_preview": True},
    )
    assert body == "DJ Maze sent you a message."


def test_push_payload_json_whitelist_only():
    payload = PushPayload(
        title="Ticket confirmed",
        body="Your tickets for Lagos Night are ready on Pàdéyá.",
        url="/dashboard/tickets",
        kind="ticket_confirmed",
        notification_id="nid-1",
    )
    data = json.loads(payload.to_json())
    assert set(data.keys()) <= {
        "title",
        "body",
        "action_url",
        "notification_id",
        "tag",
        "timestamp",
        "icon",
        "badge",
    }
    assert data["action_url"] == "/dashboard/tickets"
    assert "pickup" not in json.dumps(data).lower()


def test_vault_action_url_blocked():
    payload = PushPayload(
        title="Pàdéyá",
        body="test",
        url="/vault/secret",
        kind="generic",
    )
    data = json.loads(payload.to_json())
    assert data["action_url"] == "/dashboard/notifications"


def test_sanitize_delivery_error_strips_endpoints():
    raw = (
        "Push failed for "
        "https://fcm.googleapis.com/fcm/send/AbCdEfGhIjKlMnOp: 410 Gone"
    )
    safe = sanitize_delivery_error(raw)
    assert safe is not None
    assert "https://" not in safe
    assert "fcm.googleapis.com" not in safe
    assert "endpoint" in safe or "Gone" in safe or "410" in safe
    assert sanitize_delivery_error("user@example.com leaked") is not None
    assert "@" not in (sanitize_delivery_error("user@example.com leaked") or "")
