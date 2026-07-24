"""Safe demo chat attachments — generated placeholders only.

Never seeds private venue maps, street addresses, phone/email screenshots,
or executable/HTML/SVG payloads. Files live under private attachment storage.
"""

from __future__ import annotations

import io
import logging
from datetime import UTC, datetime
from uuid import UUID

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.messaging_privacy import assert_safe_demo_copy
from app.messaging.attachment_storage import (
    attachment_api_path,
    get_attachment_storage,
)
from app.messaging.attachments import (
    ATT_STATUS_READY,
    sha256_hex,
)
from app.messaging.models import Message, MessageAttachment, MessageThread
from app.users.models import User

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _demo_png_bytes(*, label: str, fill: tuple[int, int, int]) -> bytes:
    """Simple branded placeholder image — no maps, GPS, or venue photos."""
    assert_safe_demo_copy(label, context="demo attachment label")
    img = Image.new("RGB", (640, 360), color=fill)
    draw = ImageDraw.Draw(img)
    draw.rectangle((24, 24, 616, 336), outline=(255, 255, 255), width=3)
    draw.text((40, 48), "Padeya demo", fill=(255, 255, 255))
    draw.text((40, 100), label[:48], fill=(255, 255, 255))
    draw.text((40, 160), "Placeholder only - not a real venue map.", fill=(230, 230, 230))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _demo_pdf_bytes(*, title: str) -> bytes:
    """Minimal one-page PDF with safe title text only."""
    assert_safe_demo_copy(title, context="demo pdf title")
    # Hand-rolled PDF (no external deps). Content is plain title — no URLs.
    safe_title = "".join(c for c in title if c.isprintable() and c not in "()\\")[:80]
    stream = f"BT /F1 18 Tf 50 750 Td ({safe_title}) Tj ET\n"
    stream += "BT /F1 12 Tf 50 720 Td (Padeya demo schedule placeholder.) Tj ET\n"
    stream += "BT /F1 12 Tf 50 700 Td (No private addresses or venue secrets.) Tj ET\n"
    stream_b = stream.encode("latin-1", errors="replace")
    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream_b)} >>stream\n".encode("ascii")
        + stream_b
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def _entry_flow_png_bytes() -> bytes:
    """Public entry-flow graphic — gates/check-in labels only, no street address."""
    img = Image.new("RGB", (640, 400), color=(20, 24, 32))
    draw = ImageDraw.Draw(img)
    draw.rectangle((30, 30, 610, 370), outline=(142, 240, 18), width=2)
    draw.text((48, 48), "Afrobeats Night Live — public entry flow", fill=(255, 255, 255))
    boxes = [
        (60, 120, 200, 220, "Gate"),
        (240, 120, 400, 220, "Check-in"),
        (440, 120, 580, 220, "Hall"),
    ]
    for x0, y0, x1, y1, label in boxes:
        draw.rectangle((x0, y0, x1, y1), outline=(255, 255, 255), width=2)
        draw.text((x0 + 24, y0 + 40), label, fill=(142, 240, 18))
    draw.text(
        (48, 280),
        "Demo graphic only. No private venue or street details.",
        fill=(200, 200, 200),
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def ensure_message_attachment(
    db: Session,
    *,
    message: Message,
    uploader: User,
    filename: str,
    content_type: str,
    extension: str,
    data: bytes,
    width: int | None = None,
    height: int | None = None,
) -> MessageAttachment | None:
    """Idempotently attach a ready file to a message (private storage)."""
    assert_safe_demo_copy(filename, context="demo attachment filename")
    if message.thread_id is None:
        return None
    existing = db.scalar(
        select(MessageAttachment).where(
            MessageAttachment.message_id == message.id,
            MessageAttachment.original_filename == filename,
            MessageAttachment.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return existing

    try:
        stored = get_attachment_storage().store(
            data=data,
            extension=extension,
            thread_id=message.thread_id,
            uploader_id=uploader.id,
        )
    except Exception:
        logger.exception("demo attachment store failed filename=%s", filename)
        return None

    row = MessageAttachment(
        message_id=message.id,
        thread_id=message.thread_id,
        uploader_user_id=uploader.id,
        storage_key=stored.key,
        url=None,
        original_filename=filename[:200],
        safe_filename=f"demo-{filename}"[:200],
        mime_type=content_type[:120],
        file_size=len(data),
        file_extension=extension if extension.startswith(".") else f".{extension}",
        checksum_sha256=sha256_hex(data),
        width=width,
        height=height,
        status=ATT_STATUS_READY,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(row)
    db.flush()
    row.url = attachment_api_path(row.id)
    if not message.body and message.message_type == "text":
        if content_type.startswith("image/"):
            message.message_type = "image"
        else:
            message.message_type = "attachment"
    elif message.body and content_type.startswith("image/"):
        # Keep text; type stays text/image hybrid as text with attachments.
        pass
    db.flush()
    return row


def _message_by_body(
    db: Session, thread_id: UUID, body_substr: str
) -> Message | None:
    return db.scalar(
        select(Message)
        .where(
            Message.thread_id == thread_id,
            Message.body.contains(body_substr),
        )
        .order_by(Message.created_at.asc())
        .limit(1)
    )


def seed_chidi_bayo_attachments(
    db: Session,
    *,
    thread: MessageThread,
    chidi: User,
    bayo: User,
) -> int:
    """Fan↔fan: agenda PNG + schedule PDF on Product Demo Night chat."""
    agenda_msg = _message_by_body(db, thread.id, "demo circle")
    if agenda_msg is None:
        agenda_msg = _message_by_body(db, thread.id, "both going to Product Demo Night")
    schedule_msg = _message_by_body(db, thread.id, "watch first")
    if schedule_msg is None:
        schedule_msg = agenda_msg
    if agenda_msg is None:
        return 0

    n = 0
    png = _demo_png_bytes(
        label="product-demo-night-agenda",
        fill=(18, 48, 32),
    )
    if ensure_message_attachment(
        db,
        message=agenda_msg,
        uploader=chidi,
        filename="product-demo-night-agenda.png",
        content_type="image/png",
        extension=".png",
        data=png,
        width=640,
        height=360,
    ):
        n += 1

    if schedule_msg is not None:
        pdf = _demo_pdf_bytes(title="Demo Night Schedule")
        if ensure_message_attachment(
            db,
            message=schedule_msg,
            uploader=bayo,
            filename="demo-night-schedule.pdf",
            content_type="application/pdf",
            extension=".pdf",
            data=pdf,
        ):
            n += 1

    if n and thread.last_message_preview:
        # Keep preview privacy-safe; optionally note attachment.
        pass
    return n


def seed_tolu_maze_attachments(
    db: Session,
    *,
    thread: MessageThread,
    maze_user: User,
) -> int:
    """Fan↔host: public entry-flow image — no private venue/address data."""
    host_msg = _message_by_body(db, thread.id, "Doors open at 7 PM")
    if host_msg is None:
        host_msg = _message_by_body(db, thread.id, "check-in is fastest")
    if host_msg is None:
        return 0
    png = _entry_flow_png_bytes()
    row = ensure_message_attachment(
        db,
        message=host_msg,
        uploader=maze_user,
        filename="afrobeats-entry-map.png",
        content_type="image/png",
        extension=".png",
        data=png,
        width=640,
        height=400,
    )
    return 1 if row else 0


def seed_reported_thread_attachments(
    db: Session,
    *,
    thread: MessageThread,
    uploader: User,
) -> int:
    """Admin moderation demo — ready attachment metadata on a reported thread."""
    msg = _message_by_body(db, thread.id, "arrive late")
    if msg is None:
        msg = db.scalar(
            select(Message)
            .where(
                Message.thread_id == thread.id,
                Message.sender_role != "system",
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
    if msg is None:
        return 0
    png = _demo_png_bytes(
        label="moderation-sample",
        fill=(48, 24, 24),
    )
    row = ensure_message_attachment(
        db,
        message=msg,
        uploader=uploader,
        filename="demo-moderation-sample.png",
        content_type="image/png",
        extension=".png",
        data=png,
        width=640,
        height=360,
    )
    return 1 if row else 0
