"""Local demo asset URL helpers (frontend/public/demo)."""

from __future__ import annotations

from app.core.config import get_settings


def demo_asset_url(relative_path: str) -> str:
    """Absolute http(s) URL to a local frontend demo asset."""
    base = get_settings().frontend_url.rstrip("/")
    path = relative_path.lstrip("/")
    if path.startswith("demo/"):
        return f"{base}/{path}"
    return f"{base}/demo/{path}"


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
