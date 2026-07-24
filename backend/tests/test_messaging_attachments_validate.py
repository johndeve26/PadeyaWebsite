"""Unit tests for safe chat attachment validation."""

from __future__ import annotations

import hashlib
import io
import zipfile

import pytest
from PIL import Image

from app.messaging.attachment_scan import NoOpAttachmentScanner, get_attachment_scanner
from app.messaging.attachments import (
    AttachmentValidationError,
    content_disposition_for,
    sanitize_original_filename,
    validate_attachment_bytes,
)


# Minimal valid 1x1 PNG (CRC-correct; Pillow-verifiable)
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _minimal_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        zf.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


def test_accepts_png_and_pdf_and_docx():
    png = validate_attachment_bytes(
        filename="a.png", declared_content_type="image/png", data=_PNG
    )
    assert png.content_type == "image/png"
    assert png.category == "image"
    assert png.width == 1 and png.height == 1
    assert png.checksum_sha256 == hashlib.sha256(png.data).hexdigest()
    assert png.data == _PNG

    pdf = validate_attachment_bytes(
        filename="a.pdf",
        declared_content_type="application/pdf",
        data=b"%PDF-1.4 hello",
    )
    assert pdf.content_type == "application/pdf"
    assert pdf.category == "document"

    docx = validate_attachment_bytes(
        filename="a.docx",
        declared_content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        data=_minimal_docx(),
    )
    assert docx.extension == ".docx"


def test_rejects_zip_html_exe_and_mismatch():
    with pytest.raises(AttachmentValidationError):
        validate_attachment_bytes(
            filename="a.zip",
            declared_content_type="application/zip",
            data=b"PK\x03\x04not-a-docx",
        )
    with pytest.raises(AttachmentValidationError):
        validate_attachment_bytes(
            filename="a.html",
            declared_content_type="text/html",
            data=b"<html><body>hi</body></html>",
        )
    with pytest.raises(AttachmentValidationError):
        validate_attachment_bytes(
            filename="a.exe",
            declared_content_type="application/octet-stream",
            data=b"MZ\x90\x00",
        )
    with pytest.raises(AttachmentValidationError):
        validate_attachment_bytes(
            filename="a.png",
            declared_content_type="image/png",
            data=b"%PDF-1.4",
        )


def test_rejects_script_and_path_traversal_names():
    with pytest.raises(AttachmentValidationError):
        validate_attachment_bytes(
            filename="evil.sh",
            declared_content_type="text/plain",
            data=b"#!/bin/sh\nrm -rf /\n",
        )
    with pytest.raises(AttachmentValidationError):
        validate_attachment_bytes(
            filename="../../etc/passwd",
            declared_content_type="text/plain",
            data=b"root:x:0:0\n",
        )
    assert sanitize_original_filename("../../weird name!.png") == "weird-name-.png"


def test_rejects_corrupt_image_magic():
    # Valid PNG magic + truncated body — Pillow verify fails.
    bogus = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    with pytest.raises(AttachmentValidationError):
        validate_attachment_bytes(
            filename="bad.png",
            declared_content_type="image/png",
            data=bogus,
        )


def test_strips_jpeg_exif_when_present():
    img = Image.new("RGB", (8, 8), color=(10, 20, 30))
    buf = io.BytesIO()
    # Minimal EXIF APP1 marker payload (Pillow accepts via exif= bytes on save in some versions)
    exif = Image.Exif()
    exif[271] = "PadeyaTestCam"  # Make
    img.save(buf, format="JPEG", quality=90, exif=exif)
    raw = buf.getvalue()
    assert b"PadeyaTestCam" in raw or len(raw) > 100

    validated = validate_attachment_bytes(
        filename="shot.jpg",
        declared_content_type="image/jpeg",
        data=raw,
    )
    assert validated.content_type == "image/jpeg"
    assert validated.width == 8 and validated.height == 8
    assert validated.metadata_stripped is True
    assert b"PadeyaTestCam" not in validated.data


def test_pdf_disposition_is_attachment_images_inline():
    assert content_disposition_for("application/pdf", "doc.pdf").startswith(
        "attachment;"
    )
    assert content_disposition_for("image/png", "x.png").startswith("inline;")
    disp = content_disposition_for("image/png", "../../x.png")
    assert ".." not in disp
    assert "x.png" in disp


def test_scanner_hook_defaults_to_noop():
    scanner = get_attachment_scanner()
    assert isinstance(scanner, NoOpAttachmentScanner)
    result = scanner.scan(
        data=_PNG, content_type="image/png", filename="a.png"
    )
    assert result.clean is True
    assert result.engine == "noop"
