"""Public media role policies — server-side, testable variant dimensions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaRole(StrEnum):
    AVATAR = "avatar"
    PROFILE_COVER = "profile_cover"
    HOST_LOGO = "host_logo"
    HOST_COVER = "host_cover"
    EVENT_COVER = "event_cover"
    EVENT_GALLERY = "event_gallery"
    MERCH_PRODUCT = "merch_product"
    BLOG_COVER = "blog_cover"
    BLOG_INLINE = "blog_inline"
    TAXONOMY_CARD = "taxonomy_card"
    TAXONOMY_HERO = "taxonomy_hero"
    SPONSOR_LOGO = "sponsor_logo"
    SPONSOR_COVER = "sponsor_cover"
    MEMORY = "memory"
    SOCIAL_OG = "social_og"
    GENERAL = "general"


class VariantType(StrEnum):
    THUMBNAIL = "thumbnail"
    CARD = "card"
    DISPLAY = "display"
    FULL = "full"
    OG = "og"


@dataclass(frozen=True)
class VariantSpec:
    variant: VariantType
    long_edge: int
    quality: int
    """lossy WebP quality; ignored for lossless logo outputs."""


@dataclass(frozen=True)
class MediaRolePolicy:
    role: MediaRole
    variants: tuple[VariantSpec, ...]
    preserve_alpha: bool = False
    flatten_animation: bool = True
    allow_lightbox: bool = True
    max_source_bytes: int = 5 * 1024 * 1024
    max_pixels: int = 40_000_000  # decompression-bomb guard
    max_dimension: int = 20_000


# Starting guidance from MEDIAOPT brief — do not upscale beyond source.
_PHOTO = (
    VariantSpec(VariantType.THUMBNAIL, 320, 75),
    VariantSpec(VariantType.CARD, 960, 80),
    VariantSpec(VariantType.DISPLAY, 1800, 84),
    VariantSpec(VariantType.FULL, 2400, 86),
)

_AVATAR = (
    VariantSpec(VariantType.THUMBNAIL, 160, 78),
    VariantSpec(VariantType.DISPLAY, 512, 84),
)

_LOGO = (
    VariantSpec(VariantType.THUMBNAIL, 160, 90),
    VariantSpec(VariantType.DISPLAY, 512, 92),
)

_MEMORY = (
    VariantSpec(VariantType.THUMBNAIL, 400, 75),
    VariantSpec(VariantType.DISPLAY, 1800, 80),
    VariantSpec(VariantType.FULL, 1800, 80),  # same bound as current memories display
)

_OG = (VariantSpec(VariantType.OG, 1200, 85),)

_COVER = (
    VariantSpec(VariantType.THUMBNAIL, 320, 75),
    VariantSpec(VariantType.CARD, 960, 80),
    VariantSpec(VariantType.DISPLAY, 1920, 84),
    VariantSpec(VariantType.FULL, 2400, 86),
)

ROLE_POLICIES: dict[MediaRole, MediaRolePolicy] = {
    MediaRole.AVATAR: MediaRolePolicy(
        MediaRole.AVATAR, _AVATAR, allow_lightbox=False, max_source_bytes=5 * 1024 * 1024
    ),
    MediaRole.PROFILE_COVER: MediaRolePolicy(MediaRole.PROFILE_COVER, _COVER),
    MediaRole.HOST_LOGO: MediaRolePolicy(
        MediaRole.HOST_LOGO, _LOGO, preserve_alpha=True, allow_lightbox=False
    ),
    MediaRole.HOST_COVER: MediaRolePolicy(MediaRole.HOST_COVER, _COVER),
    MediaRole.EVENT_COVER: MediaRolePolicy(
        MediaRole.EVENT_COVER,
        _COVER + (VariantSpec(VariantType.OG, 1200, 85),),
    ),
    MediaRole.EVENT_GALLERY: MediaRolePolicy(MediaRole.EVENT_GALLERY, _PHOTO),
    MediaRole.MERCH_PRODUCT: MediaRolePolicy(MediaRole.MERCH_PRODUCT, _PHOTO),
    MediaRole.BLOG_COVER: MediaRolePolicy(
        MediaRole.BLOG_COVER,
        _COVER + (VariantSpec(VariantType.OG, 1200, 85),),
    ),
    MediaRole.BLOG_INLINE: MediaRolePolicy(MediaRole.BLOG_INLINE, _PHOTO),
    MediaRole.TAXONOMY_CARD: MediaRolePolicy(
        MediaRole.TAXONOMY_CARD,
        (
            VariantSpec(VariantType.THUMBNAIL, 320, 75),
            VariantSpec(VariantType.CARD, 960, 80),
            VariantSpec(VariantType.DISPLAY, 1600, 84),
        ),
    ),
    MediaRole.TAXONOMY_HERO: MediaRolePolicy(MediaRole.TAXONOMY_HERO, _COVER),
    MediaRole.SPONSOR_LOGO: MediaRolePolicy(
        MediaRole.SPONSOR_LOGO, _LOGO, preserve_alpha=True, allow_lightbox=False
    ),
    MediaRole.SPONSOR_COVER: MediaRolePolicy(MediaRole.SPONSOR_COVER, _COVER),
    MediaRole.MEMORY: MediaRolePolicy(
        MediaRole.MEMORY, _MEMORY, max_source_bytes=10 * 1024 * 1024
    ),
    MediaRole.SOCIAL_OG: MediaRolePolicy(
        MediaRole.SOCIAL_OG, _OG, allow_lightbox=False
    ),
    MediaRole.GENERAL: MediaRolePolicy(MediaRole.GENERAL, _PHOTO),
}


def policy_for(role: MediaRole | str) -> MediaRolePolicy:
    if isinstance(role, str):
        role = MediaRole(role)
    return ROLE_POLICIES[role]


def map_upload_kind_to_role(kind: str) -> MediaRole:
    """Map legacy host/event media_type strings to MediaRole."""
    k = (kind or "gallery").strip().lower()
    return {
        "avatar": MediaRole.AVATAR,
        "logo": MediaRole.HOST_LOGO,
        "banner": MediaRole.EVENT_COVER,
        "mobile_banner": MediaRole.EVENT_COVER,
        "cover": MediaRole.HOST_COVER,
        "gallery": MediaRole.EVENT_GALLERY,
        "social_share": MediaRole.SOCIAL_OG,
        "sponsor": MediaRole.SPONSOR_LOGO,
        "teaser": MediaRole.EVENT_GALLERY,
        "other": MediaRole.GENERAL,
        "blog_cover": MediaRole.BLOG_COVER,
        "blog_inline": MediaRole.BLOG_INLINE,
        "blog_og": MediaRole.SOCIAL_OG,
        "taxonomy_primary": MediaRole.TAXONOMY_CARD,
        "taxonomy_hero": MediaRole.TAXONOMY_HERO,
        "merch": MediaRole.MERCH_PRODUCT,
        "memory": MediaRole.MEMORY,
    }.get(k, MediaRole.GENERAL)
