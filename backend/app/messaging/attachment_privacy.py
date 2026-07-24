"""Public attachment metadata allowlist.

Never expose storage keys, filesystem paths, checksums, EXIF, uploader ids,
rejection internals, or contact/payment/venue fields via attachment payloads.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.messaging.attachment_storage import (
    attachment_api_path,
    signed_attachment_url,
)
from app.messaging.attachments import (
    ATT_STATUS_DELETED,
    ATT_STATUS_FAILED,
    ATT_STATUS_HIDDEN,
    ATT_STATUS_PENDING,
    ATT_STATUS_READY,
    ATT_STATUS_REJECTED,
)
from app.messaging.models import MessageAttachment

# Exact keys allowed on attachment objects returned to clients / WS.
PUBLIC_ATTACHMENT_KEYS = frozenset(
    {
        "id",
        "url",
        "content_type",  # mime_type
        "byte_size",  # file_size
        "original_filename",
        "width",
        "height",
        "status",
        "reviewed_at",  # moderation view / admin only (ISO string)
    }
)

# Keys that must never appear on attachment objects (or be smuggled beside them).
FORBIDDEN_ATTACHMENT_KEYS = frozenset(
    {
        "storage_key",
        "checksum",
        "checksum_sha256",
        "file_path",
        "filepath",
        "local_path",
        "absolute_path",
        "media_root",
        "rejection_reason",
        "uploader_user_id",
        "uploader_id",
        "safe_filename",
        "deleted_at",
        "message_id",
        "exif",
        "gps",
    }
)

_MODERATION_STATUSES = frozenset(
    {
        ATT_STATUS_READY,
        ATT_STATUS_HIDDEN,
        ATT_STATUS_REJECTED,
        ATT_STATUS_DELETED,
        ATT_STATUS_FAILED,
        ATT_STATUS_PENDING,
    }
)


def display_filename(row: MessageAttachment) -> str | None:
    """Client-facing name only — never a storage key or absolute path."""
    name = row.original_filename or row.safe_filename
    if not name:
        return None
    cleaned = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return cleaned[:200] or None


def serialize_attachment_public(
    row: MessageAttachment,
    *,
    viewer_id: UUID | None = None,
    ready_only: bool = True,
    moderation_view: bool = False,
) -> dict[str, Any] | None:
    """Return allowlisted metadata, or None when not publicly viewable.

    Signed download URLs are only emitted when ``viewer_id`` is provided
    (authorized participant / moderation viewer). Without a viewer, only the
    Bearer auth route is returned (never a signed capability URL for strangers).
    """
    status = row.status or ATT_STATUS_READY

    if moderation_view:
        if status not in _MODERATION_STATUSES:
            return None
        # Skip unbound staging noise unless already moderated.
        if (
            row.message_id is None
            and status == ATT_STATUS_PENDING
            and row.deleted_at is None
        ):
            return None
    else:
        if row.deleted_at is not None:
            return None
        if ready_only and status != ATT_STATUS_READY:
            return None
        if status not in {ATT_STATUS_READY, ATT_STATUS_PENDING, ATT_STATUS_REJECTED, ATT_STATUS_FAILED}:
            return None

    url: str | None = None
    downloadable = (
        row.deleted_at is None
        and bool(row.storage_key)
        and status in {ATT_STATUS_READY, ATT_STATUS_HIDDEN}
    )
    # Participants only get URLs for ready; moderation may open hidden too.
    if downloadable and (status == ATT_STATUS_READY or moderation_view):
        if status == ATT_STATUS_HIDDEN and not moderation_view:
            url = None
        elif viewer_id is not None:
            url = signed_attachment_url(row.id, viewer_id=viewer_id)
        elif status == ATT_STATUS_READY:
            url = attachment_api_path(row.id)

    item: dict[str, Any] = {
        "id": str(row.id),
        "url": url,
        "content_type": row.mime_type,
        "byte_size": int(row.file_size or 0),
        "original_filename": display_filename(row),
        "status": status,
    }
    if row.width is not None:
        item["width"] = int(row.width)
    if row.height is not None:
        item["height"] = int(row.height)
    if moderation_view and row.reviewed_at is not None:
        item["reviewed_at"] = row.reviewed_at.isoformat()
    return clip_attachment_public(item)


def clip_attachment_public(payload: dict[str, Any]) -> dict[str, Any]:
    """Defense-in-depth: keep only allowlisted keys."""
    return {k: payload[k] for k in PUBLIC_ATTACHMENT_KEYS if k in payload}


def strip_forbidden_attachment_fields(payload: Any) -> Any:
    """Recursively drop forbidden attachment-related keys from a dict/list tree."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, child in payload.items():
            if not isinstance(key, str):
                continue
            if key.lower() in FORBIDDEN_ATTACHMENT_KEYS:
                continue
            out[key] = strip_forbidden_attachment_fields(child)
        if "content_type" in out and "byte_size" in out and "id" in out:
            return clip_attachment_public(out)
        return out
    if isinstance(payload, list):
        return [strip_forbidden_attachment_fields(x) for x in payload]
    if isinstance(payload, tuple):
        return [strip_forbidden_attachment_fields(x) for x in payload]
    return payload
