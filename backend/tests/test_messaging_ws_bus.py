"""Messaging WS fan-out bus: sanitize + in-memory fallback."""

from __future__ import annotations

from uuid import uuid4

from app.messaging.ws_bus import MessagingEventBus, thread_channel, user_channel
from app.messaging.ws_sanitize import sanitize_event_payload


def test_sanitize_strips_private_fields():
    raw = {
        "type": "message.created",
        "thread_id": "t1",
        "message": {
            "body": "Hello on Pàdéyá",
            "email": "leak@example.com",
            "phone": "+234",
            "attachments": [
                {
                    "id": "a1",
                    "url": "/api/v1/messages/attachments/a1",
                    "content_type": "image/png",
                    "byte_size": 12,
                    "storage_key": "secret/path.png",
                    "checksum_sha256": "abc",
                    "rejection_reason": "nope",
                    "uploader_user_id": "u1",
                }
            ],
        },
        "order_id": "ord_1",
        "shipping_address": "12 Secret St",
        "private_venue": "Hidden Hall",
        "paystack_reference": "psk_x",
        "nested": {"whatsapp": "bad", "ok": True},
    }
    clean = sanitize_event_payload(raw)
    assert clean["type"] == "message.created"
    assert clean["message"]["body"] == "Hello on Pàdéyá"
    att = clean["message"]["attachments"][0]
    assert att["url"].startswith("/api/v1/messages/attachments/")
    assert "storage_key" not in att
    assert "checksum_sha256" not in att
    assert "rejection_reason" not in att
    assert "uploader_user_id" not in att
    assert "email" not in clean["message"]
    assert "phone" not in clean["message"]
    assert "order_id" not in clean
    assert "shipping_address" not in clean
    assert "private_venue" not in clean
    assert "paystack_reference" not in clean
    assert "whatsapp" not in clean["nested"]
    assert clean["nested"]["ok"] is True


def test_channel_names():
    uid = uuid4()
    tid = uuid4()
    assert user_channel(uid) == f"user:{uid}:messages"
    assert thread_channel(tid) == f"thread:{tid}:messages"


def test_memory_bus_delivers_to_handlers():
    bus = MessagingEventBus()
    seen_users: list = []
    seen_threads: list = []

    def on_users(user_ids, payload):
        seen_users.append((list(user_ids), payload))

    def on_thread(thread_id, allowed, payload, fallback):
        seen_threads.append((thread_id, list(allowed), payload, fallback))

    mode = bus.start(on_users=on_users, on_thread=on_thread)
    assert mode == "memory"

    u1, u2 = uuid4(), uuid4()
    tid = uuid4()
    bus.publish_users(
        [u1, u2],
        {
            "type": "thread.updated",
            "thread_id": str(tid),
            "email": "nope@example.com",
            "last_message_preview": "Hi",
        },
    )
    assert len(seen_users) == 1
    ids, payload = seen_users[0]
    assert set(ids) == {u1, u2}
    assert payload["last_message_preview"] == "Hi"
    assert "email" not in payload

    bus.publish_thread(
        tid,
        allowed_user_ids=[u1],
        payload={"type": "message.typing", "thread_id": str(tid), "phone": "x"},
        fallback_to_users=False,
    )
    assert len(seen_threads) == 1
    assert seen_threads[0][0] == tid
    assert "phone" not in seen_threads[0][2]

    bus.stop()
