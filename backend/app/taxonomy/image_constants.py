"""Marketplace taxonomy imagery constants and helpers.

Blog taxonomy media is out of scope — do not import blog media roles here.
"""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlparse

from fastapi import HTTPException

# Kinds that may receive admin-managed imagery (backend allowlist).
# Collections remain CMS/FE browse tiles; tags/vibes/audiences/host/venue types
# do not render image cards today.
TAXONOMY_IMAGE_CAPABLE_KINDS = frozenset(
    {
        "category",
        "city",
        "state",
        "area",
    }
)

IMAGE_ROLES = frozenset({"primary", "hero"})

ALT_MAX_LEN = 240
FOCAL_MIN = Decimal("0")
FOCAL_MAX = Decimal("1")
DEFAULT_FOCAL = Decimal("0.500")

# Public visual fields exposed on API responses (never storage keys / buckets).
PUBLIC_IMAGE_FIELD_NAMES = (
    "primary_image_url",
    "primary_image_alt",
    "primary_image_focal_x",
    "primary_image_focal_y",
    "hero_image_url",
    "hero_image_alt",
    "hero_image_focal_x",
    "hero_image_focal_y",
)


def assert_image_capable_kind(kind: str) -> str:
    key = (kind or "").strip().lower()
    if key not in TAXONOMY_IMAGE_CAPABLE_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"Taxonomy kind '{kind}' does not support imagery",
        )
    return key


def assert_image_role(role: str) -> str:
    key = (role or "primary").strip().lower()
    if key not in IMAGE_ROLES:
        raise HTTPException(
            status_code=400,
            detail="image_role must be 'primary' or 'hero'",
        )
    return key


def clamp_focal(value: Decimal | float | None, *, default: Decimal = DEFAULT_FOCAL) -> Decimal:
    if value is None:
        return default
    dec = Decimal(str(value))
    if dec < FOCAL_MIN or dec > FOCAL_MAX:
        raise HTTPException(
            status_code=400,
            detail="Focal point values must be between 0.0 and 1.0",
        )
    return dec


def normalize_alt(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > ALT_MAX_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Alt text must be at most {ALT_MAX_LEN} characters",
        )
    return cleaned


def assert_approved_public_media_url(url: str | None, *, allow_null: bool = True) -> str | None:
    """Reject arbitrary external URLs; allow null clear or same-origin media paths."""
    if url is None:
        if allow_null:
            return None
        raise HTTPException(status_code=400, detail="Image URL required")
    cleaned = url.strip()
    if not cleaned:
        return None
    if len(cleaned) > 1000:
        raise HTTPException(status_code=400, detail="Image URL too long")
    # Relative public media path (local storage served under /media)
    if cleaned.startswith("/media/"):
        if ".." in cleaned or cleaned.startswith("//"):
            raise HTTPException(status_code=400, detail="Unsafe media URL")
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid media URL")
    # Absolute URLs must look like stored public media (path contains /media/ or R2 public host)
    path = parsed.path or ""
    if ".." in path:
        raise HTTPException(status_code=400, detail="Unsafe media URL")
    # Allow only paths that include media-style object keys (taxonomy/, events/, hosts/, …)
    # Full host allowlisting happens via upload flow; PATCH of uploaded URLs is trusted if path-safe.
    if not any(
        segment in path
        for segment in (
            "/media/",
            "/taxonomy/",
            "/events/",
            "/hosts/",
            "/users/",
            "/blog/",
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Image URL must reference approved public media storage",
        )
    return cleaned
