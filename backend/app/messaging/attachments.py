"""Safe chat attachment validation (v1).

Allowed: JPEG/PNG/WebP images, PDF, text/plain, CSV, DOCX.
Rejected: executables, scripts, HTML, generic ZIP, SVG, unknown binaries,
MIME/extension/content mismatches, oversized files, path-traversal names.

Images are verified with Pillow when available (dimensions + optional EXIF strip).
Checksum (SHA-256) is computed on the bytes that will be stored.

Antivirus: not configured in v1 — see ``attachment_scan.py`` for the future hook.
Files are type/size/MIME/magic validated only until a scanner is wired.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import struct
import uuid
import zipfile
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ATT_STATUS_PENDING = "pending"
ATT_STATUS_READY = "ready"
ATT_STATUS_REJECTED = "rejected"
ATT_STATUS_HIDDEN = "hidden"
ATT_STATUS_DELETED = "deleted"
ATT_STATUS_FAILED = "failed"

# Soft-moderation markers (kept on the row; files are not hard-deleted).
REASON_HIDDEN_MODERATION = "Hidden by moderation"
REASON_HIDDEN_WITH_MESSAGE = "Hidden with message"
REASON_DISABLED_MODERATION = "Disabled by moderation"

# Canonical MIME allowlist (declared + sniffed must resolve here).
IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }
)
DOC_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
ALLOWED_CONTENT_TYPES = IMAGE_CONTENT_TYPES | DOC_CONTENT_TYPES

# Normalize aliases → canonical.
_MIME_ALIASES = {
    "image/jpg": "image/jpeg",
    "application/x-pdf": "application/pdf",
    "text/x-csv": "text/csv",
    "application/csv": "text/csv",
}

_EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

_BLOCKED_EXTENSIONS = frozenset(
    {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".msi",
        ".dll",
        ".scr",
        ".ps1",
        ".sh",
        ".bash",
        ".zsh",
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".php",
        ".py",
        ".rb",
        ".pl",
        ".jar",
        ".apk",
        ".html",
        ".htm",
        ".xhtml",
        ".svg",
        ".svgz",
        ".zip",
        ".rar",
        ".7z",
        ".gz",
        ".tgz",
        ".tar",
        ".bz2",
        ".xz",
        ".iso",
        ".dmg",
        ".pkg",
        ".deb",
        ".rpm",
        ".wasm",
        ".bin",
        ".dat",
        ".so",
        ".dylib",
    }
)

# MIME → Pillow expected format name
_PIL_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


@dataclass(frozen=True)
class AttachmentLimits:
    max_image_bytes: int
    max_doc_bytes: int
    max_total_bytes: int
    max_count: int


@dataclass(frozen=True)
class ValidatedAttachment:
    """Result of safety checks — ``data`` is what should be stored (may be re-encoded)."""

    content_type: str
    extension: str
    byte_size: int
    category: str  # "image" | "document"
    data: bytes
    checksum_sha256: str
    width: int | None = None
    height: int | None = None
    metadata_stripped: bool = False


class AttachmentValidationError(ValueError):
    """Raised when an upload fails safety checks."""


def get_attachment_limits(db: Session | None = None) -> AttachmentLimits:
    from app.runtime_settings import get_runtime_setting

    return AttachmentLimits(
        max_image_bytes=int(
            get_runtime_setting("messaging_attachment_max_image_bytes", db=db) or 5 * 1024 * 1024
        ),
        max_doc_bytes=int(
            get_runtime_setting("messaging_attachment_max_doc_bytes", db=db) or 10 * 1024 * 1024
        ),
        max_total_bytes=int(
            get_runtime_setting("messaging_attachment_max_total_bytes", db=db) or 15 * 1024 * 1024
        ),
        max_count=int(get_runtime_setting("messaging_attachment_max_count", db=db) or 4),
    )


def orphan_expiry_hours(db: Session | None = None) -> int:
    from app.runtime_settings import get_runtime_setting

    return max(1, int(get_runtime_setting("messaging_attachment_orphan_hours", db=db) or 24))


def normalize_content_type(value: str | None) -> str:
    ctype = (value or "").split(";")[0].strip().lower()
    return _MIME_ALIASES.get(ctype, ctype)


def _extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    # Use basename only — ignore path segments from hostile clients.
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if "." not in base:
        return ""
    return "." + base.rsplit(".", 1)[-1].strip().lower()


def sanitize_original_filename(name: str | None) -> str | None:
    """Client-facing display name only — never used as a storage key."""
    if not name:
        return None
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    if ".." in base:
        base = base.replace("..", "")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip("-.")
    return (cleaned[:200] or None)


def _looks_like_docx(data: bytes) -> bool:
    if len(data) < 4 or data[:2] != b"PK":
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if "[Content_Types].xml" not in names:
                return False
            # Reject zip-slip style member names.
            for n in names:
                if n.startswith("/") or ".." in n.replace("\\", "/").split("/"):
                    return False
            return any(n.startswith("word/") for n in names)
    except (zipfile.BadZipFile, RuntimeError):
        return False


def _sniff_content_type(data: bytes) -> str | None:
    if len(data) < 12:
        head = data
    else:
        head = data[:64]

    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if _looks_like_docx(data):
        return (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # Reject common dangerous / unknown binaries early.
    if head.startswith(b"MZ") or head.startswith(b"\x7fELF"):
        return None
    if head.startswith(b"PK"):
        # Generic ZIP (not a validated DOCX).
        return None
    lower = data[:4096].lower()
    if b"<html" in lower or b"<!doctype html" in lower or b"<svg" in lower:
        return None
    if data.startswith(b"#!") or data.lstrip().startswith(b"<?php"):
        return None

    # UTF-8 / ASCII text — allow as text/plain (CSV checked via extension/MIME).
    try:
        sample = data[:8192].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if "\x00" in sample:
        return None
    # Reject HTML-ish text even if not caught above.
    if re.search(r"<\s*(script|iframe|object|embed)\b", sample, re.I):
        return None
    return "text/plain"


def _validate_pdf(data: bytes) -> None:
    """MIME/magic already checked — reject obviously hostile PDF wrappers."""
    if not data.startswith(b"%PDF-"):
        raise AttachmentValidationError("Invalid PDF content.")
    # Cheap heuristic: HTML smuggled after a fake header in the first chunk.
    sample = data[:8192].lower()
    if b"<html" in sample or b"<!doctype html" in sample or b"<script" in sample:
        raise AttachmentValidationError("PDF content looks unsafe.")


def _pillow_available() -> bool:
    try:
        from PIL import Image  # noqa: F401

        return True
    except ImportError:
        return False


def _verify_and_prepare_image(
    data: bytes, content_type: str
) -> tuple[bytes, int | None, int | None, bool]:
    """Verify image bytes; optionally strip metadata via re-encode.

    Returns (bytes_to_store, width, height, metadata_stripped).
    """
    expected = _PIL_FORMATS.get(normalize_content_type(content_type))
    settings = get_settings()
    from app.runtime_settings import get_runtime_setting

    strip = bool(
        get_runtime_setting("messaging_attachment_strip_image_metadata", settings=settings)
    )

    if not _pillow_available():
        w, h = image_dimensions(data, content_type)
        return data, w, h, False

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise AttachmentValidationError("Invalid or corrupt image.") from exc

    try:
        with Image.open(io.BytesIO(data)) as img:
            if expected and (img.format or "").upper() != expected:
                raise AttachmentValidationError(
                    "Image format does not match declared type."
                )
            width, height = img.size
            if width < 1 or height < 1 or width > 20000 or height > 20000:
                raise AttachmentValidationError("Image dimensions are not allowed.")

            exif = img.getexif() if hasattr(img, "getexif") else None
            has_meta = bool(exif) or bool(
                img.info.get("exif") or img.info.get("icc_profile")
            )
            if not strip or not has_meta:
                return data, int(width), int(height), False

            # Re-encode without EXIF / ICC when present.
            out = io.BytesIO()
            fmt = expected or (img.format or "PNG").upper()
            if fmt == "JPEG":
                rgb = img.convert("RGB")
                rgb.save(out, format="JPEG", quality=90, optimize=True)
            elif fmt == "PNG":
                if img.mode in {"P", "RGBA", "LA"}:
                    img = img.convert("RGBA")
                img.save(out, format="PNG", optimize=True)
            elif fmt == "WEBP":
                img.save(out, format="WEBP", quality=90, method=4)
            else:
                return data, int(width), int(height), False
            cleaned = out.getvalue()
            if not cleaned:
                raise AttachmentValidationError("Failed to process image.")
            return cleaned, int(width), int(height), True
    except AttachmentValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise AttachmentValidationError("Invalid or corrupt image.") from exc


def validate_attachment_bytes(
    *,
    filename: str | None,
    declared_content_type: str | None,
    data: bytes,
) -> ValidatedAttachment:
    limits = get_attachment_limits()
    if not data:
        raise AttachmentValidationError("Empty file.")

    # Path traversal / absolute paths in the client filename must not affect storage.
    if filename:
        normalized = filename.replace("\\", "/")
        parts = [p for p in normalized.split("/") if p not in ("", ".")]
        if normalized.startswith("/") or any(p == ".." for p in parts):
            raise AttachmentValidationError("Invalid filename.")

    ext = _extension(filename)
    if ext in _BLOCKED_EXTENSIONS:
        raise AttachmentValidationError("This file type is not allowed.")

    declared = normalize_content_type(declared_content_type)
    sniffed = _sniff_content_type(data)
    if sniffed is None:
        raise AttachmentValidationError(
            "Unrecognized or unsafe file content."
        )

    # Extension → MIME when present must agree with sniffed content.
    if ext:
        ext_mime = _EXT_TO_MIME.get(ext)
        if ext_mime is None:
            raise AttachmentValidationError("This file type is not allowed.")
        if normalize_content_type(ext_mime) != sniffed and not (
            sniffed == "text/plain" and ext_mime in {"text/plain", "text/csv"}
        ):
            # CSV sniffed as text/plain is OK with .csv
            if not (ext == ".csv" and sniffed == "text/plain"):
                raise AttachmentValidationError(
                    "File extension does not match file content."
                )

    # Declared MIME must match sniffed (with text/csv ↔ text/plain flexibility).
    if declared:
        if declared not in ALLOWED_CONTENT_TYPES:
            raise AttachmentValidationError(
                "Only images (JPEG, PNG, WebP), PDF, text, CSV, or DOCX are allowed."
            )
        declared_n = normalize_content_type(declared)
        sniffed_n = normalize_content_type(sniffed)
        compatible = declared_n == sniffed_n or (
            sniffed_n == "text/plain"
            and declared_n in {"text/plain", "text/csv"}
        )
        if not compatible:
            raise AttachmentValidationError(
                "Declared file type does not match file content."
            )

    # Resolve final MIME (prefer CSV when extension/declared says so).
    final = sniffed
    if sniffed == "text/plain" and (
        ext == ".csv" or declared in {"text/csv", "application/csv", "text/x-csv"}
    ):
        final = "text/csv"
    final = normalize_content_type(final)
    if final not in ALLOWED_CONTENT_TYPES:
        raise AttachmentValidationError(
            "Only images (JPEG, PNG, WebP), PDF, text, CSV, or DOCX are allowed."
        )

    category = "image" if final in IMAGE_CONTENT_TYPES else "document"
    max_bytes = (
        limits.max_image_bytes if category == "image" else limits.max_doc_bytes
    )
    if len(data) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        kind = "Image" if category == "image" else "Document"
        raise AttachmentValidationError(f"{kind} must be {mb}MB or smaller.")

    store_data = data
    width: int | None = None
    height: int | None = None
    stripped = False

    if category == "image":
        store_data, width, height, stripped = _verify_and_prepare_image(data, final)
        if len(store_data) > max_bytes:
            mb = max_bytes // (1024 * 1024)
            raise AttachmentValidationError(f"Image must be {mb}MB or smaller.")
    elif final == "application/pdf":
        _validate_pdf(data)

    # Future AV hook (noop by default — does not replace type validation).
    from app.messaging.attachment_scan import get_attachment_scanner

    scan = get_attachment_scanner().scan(
        data=store_data, content_type=final, filename=filename
    )
    if not scan.clean:
        raise AttachmentValidationError(
            scan.detail or "File failed security scan."
        )

    return ValidatedAttachment(
        content_type=final,
        extension=_MIME_TO_EXT[final],
        byte_size=len(store_data),
        category=category,
        data=store_data,
        checksum_sha256=sha256_hex(store_data),
        width=width,
        height=height,
        metadata_stripped=stripped,
    )


def preview_label_for_attachments(content_types: list[str]) -> str:
    if not content_types:
        return "Sent an attachment"
    if all(normalize_content_type(t) in IMAGE_CONTENT_TYPES for t in content_types):
        return "Sent an image" if len(content_types) == 1 else "Sent images"
    if len(content_types) == 1:
        return "Sent a file"
    return "Sent files"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename_for(extension: str) -> str:
    """Server-generated name only — never derived from user input paths."""
    ext = extension if extension.startswith(".") else f".{extension}"
    ext = re.sub(r"[^a-zA-Z0-9.]+", "", ext)[:16] or ".bin"
    return f"{uuid.uuid4().hex}{ext}"


def content_disposition_for(mime_type: str | None, filename: str) -> str:
    """Images may render inline; PDFs/docs force download (no unsafe inline render)."""
    ctype = normalize_content_type(mime_type)
    disposition = "inline" if ctype in IMAGE_CONTENT_TYPES else "attachment"
    safe = sanitize_original_filename(filename) or "attachment"
    return f'{disposition}; filename="{safe}"'


def image_dimensions(data: bytes, content_type: str) -> tuple[int | None, int | None]:
    """Best-effort width/height without Pillow (PNG / JPEG / WebP)."""
    ctype = normalize_content_type(content_type)
    try:
        if ctype == "image/png" and len(data) >= 24 and data.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            w, h = struct.unpack(">II", data[16:24])
            return int(w), int(h)
        if ctype == "image/jpeg" and data.startswith(b"\xff\xd8"):
            return _jpeg_dimensions(data)
        if ctype == "image/webp" and len(data) >= 30 and data[:4] == b"RIFF":
            return _webp_dimensions(data)
    except Exception:
        return None, None
    return None, None


def _jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB}:
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return int(w), int(h)
        if marker == 0xD9 or marker == 0xDA:
            break
        if marker == 0x00 or marker == 0xFF:
            i += 1
            continue
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + length
    return None, None


def _webp_dimensions(data: bytes) -> tuple[int | None, int | None]:
    # VP8X
    if data[12:16] == b"VP8X" and len(data) >= 30:
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return w, h
    # VP8 lossy
    if data[12:16] == b"VP8 " and len(data) >= 30:
        w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return int(w), int(h)
    # VP8L lossless
    if data[12:16] == b"VP8L" and len(data) >= 25:
        bits = struct.unpack("<I", data[21:25])[0]
        w = (bits & 0x3FFF) + 1
        h = ((bits >> 14) & 0x3FFF) + 1
        return int(w), int(h)
    return None, None
