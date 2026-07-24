"""Attachment public metadata must stay on the privacy allowlist."""

from __future__ import annotations

from uuid import uuid4

from app.messaging.attachment_privacy import (
    PUBLIC_ATTACHMENT_KEYS,
    clip_attachment_public,
    serialize_attachment_public,
)
from app.messaging.attachments import ATT_STATUS_READY
from app.messaging.models import MessageAttachment


def test_clip_drops_private_attachment_fields():
    clipped = clip_attachment_public(
        {
            "id": "a1",
            "url": "/api/v1/messages/attachments/a1",
            "content_type": "image/png",
            "byte_size": 10,
            "original_filename": "x.png",
            "status": "ready",
            "width": 1,
            "height": 1,
            "storage_key": "thread/user/file.png",
            "checksum_sha256": "deadbeef",
            "rejection_reason": "x",
            "uploader_user_id": str(uuid4()),
            "email": "leak@example.com",
        }
    )
    assert set(clipped.keys()) <= PUBLIC_ATTACHMENT_KEYS
    assert "storage_key" not in clipped
    assert "checksum_sha256" not in clipped
    assert "email" not in clipped


def test_serialize_omits_signed_url_without_viewer():
    row = MessageAttachment(
        id=uuid4(),
        thread_id=uuid4(),
        uploader_user_id=uuid4(),
        status=ATT_STATUS_READY,
        mime_type="image/png",
        file_size=10,
        original_filename="pic.png",
        storage_key="never/expose/this.png",
        checksum_sha256="abc",
    )
    public = serialize_attachment_public(row, viewer_id=None)
    assert public is not None
    assert public["url"] == f"/api/v1/messages/attachments/{row.id}"
    assert "?d=" not in (public["url"] or "")
    assert set(public.keys()) <= PUBLIC_ATTACHMENT_KEYS


def test_serialize_signs_only_for_viewer():
    row = MessageAttachment(
        id=uuid4(),
        thread_id=uuid4(),
        uploader_user_id=uuid4(),
        status=ATT_STATUS_READY,
        mime_type="application/pdf",
        file_size=100,
        original_filename="note.pdf",
        storage_key="private/key.pdf",
    )
    viewer = uuid4()
    public = serialize_attachment_public(row, viewer_id=viewer)
    assert public is not None
    assert public["url"] and "?d=" in public["url"]
    assert "storage_key" not in public
    assert public["status"] == "ready"
