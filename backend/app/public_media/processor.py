"""Shared public raster processor — variants, EXIF strip, no upscale."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from app.core.public_image_validation import (
    PublicImageValidationError,
    looks_like_active_content,
    sniff_public_raster_mime,
)
from app.public_media.roles import (
    MediaRole,
    MediaRolePolicy,
    VariantSpec,
    VariantType,
    policy_for,
)

logger = logging.getLogger(__name__)

PROCESSING_VERSION = "v1"

# Ordinary photo roles: static only (flatten / reject animation).
_STATIC_ONLY_MIMES = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
)


class PublicMediaProcessingError(ValueError):
    """Validation or processing failure for a public media upload."""


@dataclass(frozen=True)
class EncodedVariant:
    variant: VariantType
    data: bytes
    width: int
    height: int
    mime_type: str
    extension: str
    quality: int


@dataclass(frozen=True)
class ProcessedPublicImage:
    role: MediaRole
    source_mime: str
    source_width: int
    source_height: int
    source_bytes: int
    processing_version: str
    variants: tuple[EncodedVariant, ...]


def _normalize_mime(value: str | None) -> str:
    return (value or "").split(";")[0].strip().lower()


def _canonical_mime(mime: str) -> str:
    return "image/jpeg" if mime == "image/jpg" else mime


def encode_variants(
    *,
    data: bytes,
    declared_content_type: str | None,
    role: MediaRole | str,
) -> ProcessedPublicImage:
    """Validate source and encode all role variants in-memory (no storage)."""
    policy = policy_for(role)
    if not data:
        raise PublicMediaProcessingError("Empty file")
    source_bytes = len(data)
    if source_bytes > policy.max_source_bytes:
        raise PublicMediaProcessingError(
            f"Image must be {policy.max_source_bytes // (1024 * 1024)}MB or smaller"
        )

    sniffed = sniff_public_raster_mime(data)
    if sniffed is None:
        if looks_like_active_content(data):
            raise PublicMediaProcessingError("Unsupported or active content")
        raise PublicMediaProcessingError("Unrecognized or unsupported image")

    declared = _normalize_mime(declared_content_type)
    sniffed_c = _canonical_mime(sniffed)
    if declared:
        declared_c = _canonical_mime(declared)
        if declared_c not in _STATIC_ONLY_MIMES:
            raise PublicMediaProcessingError("Unsupported image type")
        if declared_c != sniffed_c:
            raise PublicMediaProcessingError(
                "File content does not match declared type"
            )

    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover
        raise PublicMediaProcessingError("Image processing unavailable") from exc

    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise PublicMediaProcessingError("Invalid or corrupt image") from exc

    try:
        with Image.open(io.BytesIO(data)) as img:
            # Animation policy: flatten first frame for ordinary public roles.
            if getattr(img, "is_animated", False) and policy.flatten_animation:
                img.seek(0)
            img = ImageOps.exif_transpose(img)
            source_width, source_height = img.size
            if (
                source_width < 1
                or source_height < 1
                or source_width > policy.max_dimension
                or source_height > policy.max_dimension
            ):
                raise PublicMediaProcessingError("Image dimensions are not allowed")
            if source_width * source_height > policy.max_pixels:
                raise PublicMediaProcessingError("Image pixel count exceeds limit")

            prepared = _prepare_mode(img, preserve_alpha=policy.preserve_alpha)
            encoded: list[EncodedVariant] = []
            for spec in policy.variants:
                encoded.append(
                    _encode_one(prepared, spec=spec, preserve_alpha=policy.preserve_alpha)
                )
    except PublicMediaProcessingError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise PublicMediaProcessingError("Failed to process image") from exc

    if not encoded:
        raise PublicMediaProcessingError("No variants generated")

    return ProcessedPublicImage(
        role=policy.role,
        source_mime=sniffed_c,
        source_width=int(source_width),
        source_height=int(source_height),
        source_bytes=source_bytes,
        processing_version=PROCESSING_VERSION,
        variants=tuple(encoded),
    )


def _prepare_mode(img, *, preserve_alpha: bool):
    from PIL import Image

    if preserve_alpha:
        if img.mode in {"RGBA", "LA"}:
            return img.convert("RGBA")
        if img.mode == "P" and "transparency" in img.info:
            return img.convert("RGBA")
        if img.mode != "RGB":
            return img.convert("RGB")
        return img

    if img.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if img.mode == "P":
        if "transparency" in img.info:
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[-1])
            return background
        return img.convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _encode_one(img, *, spec: VariantSpec, preserve_alpha: bool) -> EncodedVariant:
    from PIL import Image

    frame = img.copy()
    # Never upscale.
    target = (spec.long_edge, spec.long_edge)
    if max(frame.size) > spec.long_edge:
        frame.thumbnail(target, Image.Resampling.LANCZOS)

    if spec.variant == VariantType.OG:
        frame = _fit_og_canvas(frame, preserve_alpha=preserve_alpha)

    buf = io.BytesIO()
    if preserve_alpha and frame.mode == "RGBA":
        frame.save(buf, format="WEBP", lossless=True, method=4)
        mime = "image/webp"
        ext = ".webp"
    else:
        if frame.mode != "RGB":
            frame = frame.convert("RGB")
        frame.save(buf, format="WEBP", quality=spec.quality, method=4)
        mime = "image/webp"
        ext = ".webp"

    payload = buf.getvalue()
    if not payload:
        raise PublicMediaProcessingError("Failed to encode image variant")
    w, h = frame.size
    return EncodedVariant(
        variant=spec.variant,
        data=payload,
        width=int(w),
        height=int(h),
        mime_type=mime,
        extension=ext,
        quality=spec.quality,
    )


def _fit_og_canvas(img, *, preserve_alpha: bool):
    """Letterbox into 1200×630 for social cards (exact crop role)."""
    from PIL import Image

    target_w, target_h = 1200, 630
    src = img.convert("RGBA") if preserve_alpha and img.mode == "RGBA" else img.convert("RGB")
    src_w, src_h = src.size
    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if preserve_alpha and resized.mode == "RGBA":
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    else:
        canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        if resized.mode == "RGBA":
            resized = resized.convert("RGB")
    offset = ((target_w - new_w) // 2, (target_h - new_h) // 2)
    canvas.paste(resized, offset, resized if resized.mode == "RGBA" else None)
    return canvas
