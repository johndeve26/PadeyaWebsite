"""Local demo asset URL helpers (frontend/public/demo).

Static demo assets are stored as site-relative paths (`/demo/...`) so the same
seed works on localhost, previews, and https://padeya.com without baking a
hostname into the database.
"""

from __future__ import annotations

import re

# Retired staging / marketing host that previously powered FRONTEND_URL.
_LEGACY_SMARTLANCE_DEMO = re.compile(
    r"^https?://(?:www\.)?padeya\.smartlancedesigns\.com(/demo/.+?)(?:\?.*)?$",
    re.IGNORECASE,
)


def demo_asset_url(relative_path: str) -> str:
    """Site-relative path to a local frontend demo asset under /demo/."""
    path = relative_path.lstrip("/")
    if path.startswith("demo/"):
        return f"/{path}"
    return f"/demo/{path}"


def extract_demo_static_path(url: str | None) -> str | None:
    """Return `/demo/...` when url points at a Pàdéyá demo static asset."""
    if not url or not str(url).strip():
        return None
    value = str(url).strip()
    legacy = _LEGACY_SMARTLANCE_DEMO.match(value)
    if legacy:
        return legacy.group(1)
    if value.startswith("/demo/"):
        return value.split("?", 1)[0]
    marker = "/demo/"
    idx = value.find(marker)
    if idx >= 0:
        # Absolute URL on any host that embeds our static demo path.
        return value[idx:].split("?", 1)[0]
    return None


def rewrite_legacy_smartlance_demo_url(url: str | None) -> str | None:
    """Rewrite only padeya.smartlancedesigns.com/demo/... → /demo/...

    Leaves media.padeya.com, other absolute URLs, and already-relative paths alone.
    """
    if not url or not str(url).strip():
        return url
    value = str(url).strip()
    legacy = _LEGACY_SMARTLANCE_DEMO.match(value)
    if legacy:
        return legacy.group(1)
    return value


def normalize_demo_asset_url(url: str | None) -> str | None:
    """Normalize stored demo asset URLs to site-relative `/demo/...` paths."""
    if not url or not str(url).strip():
        return url
    value = str(url).strip()
    demo_path = extract_demo_static_path(value)
    if demo_path is not None:
        return demo_path
    return value


# New showcase keys reuse nearby artwork until dedicated SVGs exist.
_EVENT_ASSET_FALLBACKS: dict[str, str] = {
    "mainland-after-dark": "detty-friday-live",
}


def _event_asset_key(slug_key: str) -> str:
    return _EVENT_ASSET_FALLBACKS.get(slug_key, slug_key)


def event_banner(slug_key: str) -> str:
    return demo_asset_url(f"events/{_event_asset_key(slug_key)}.svg")


def event_gallery(slug_key: str) -> str:
    return demo_asset_url(f"events/{_event_asset_key(slug_key)}-gallery.svg")


def host_avatar(slug: str) -> str:
    return demo_asset_url(f"hosts/{slug}-avatar.svg")


def host_cover(slug: str) -> str:
    return demo_asset_url(f"hosts/{slug}-cover.svg")


def fan_avatar(username: str) -> str:
    return demo_asset_url(f"fans/{username}-avatar.svg")


def vault_cover(key: str) -> str:
    return demo_asset_url(f"vault/{key}.svg")


def sponsor_logo(key: str) -> str:
    return demo_asset_url(f"sponsors/{key}.svg")


def memory_image(key: str) -> str:
    return demo_asset_url(f"memories/{key}.svg")


def merch_image(kind: str) -> str:
    """Local demo merch product placeholder (frontend/public/demo/merch)."""
    safe = (kind or "apparel").strip().lower().replace(" ", "-")
    allowed = {
        "tee",
        "hoodie",
        "cap",
        "tote",
        "wristband",
        "poster",
        "mask",
        "sticker",
        "digital",
        "mug",
        "lanyard",
        "voucher",
        "bundle",
        "apparel",
    }
    if safe not in allowed:
        safe = "apparel"
    return demo_asset_url(f"merch/{safe}.svg")
