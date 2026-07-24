"""Safe video URL validation for knowledge base embeds."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_YOUTUBE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{6,})",
    re.I,
)
_VIMEO = re.compile(
    r"^(?:https?://)?(?:www\.)?vimeo\.com/(?:video/)?(\d+)",
    re.I,
)


def parse_video_url(url: str | None) -> dict[str, str | None]:
    """Return provider, canonical watch URL, embed URL, thumbnail — or empty if invalid."""
    raw = (url or "").strip()
    if not raw:
        return {
            "provider": None,
            "video_url": None,
            "embed_url": None,
            "thumbnail_url": None,
        }
    if "javascript:" in raw.lower() or "data:" in raw.lower():
        raise ValueError("Unsafe video URL")

    yt = _YOUTUBE.search(raw)
    if yt:
        vid = yt.group(1)
        return {
            "provider": "youtube",
            "video_url": f"https://www.youtube.com/watch?v={vid}",
            "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}",
            "thumbnail_url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        }

    vm = _VIMEO.search(raw)
    if vm:
        vid = vm.group(1)
        return {
            "provider": "vimeo",
            "video_url": f"https://vimeo.com/{vid}",
            "embed_url": f"https://player.vimeo.com/video/{vid}",
            "thumbnail_url": None,
        }

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        # External link only — never iframe unknown hosts
        host = parsed.netloc.lower()
        if host.endswith("youtube.com") or host.endswith("youtu.be"):
            qs = parse_qs(parsed.query)
            vid = (qs.get("v") or [None])[0]
            if vid:
                return {
                    "provider": "youtube",
                    "video_url": f"https://www.youtube.com/watch?v={vid}",
                    "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}",
                    "thumbnail_url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                }
        return {
            "provider": "external",
            "video_url": raw,
            "embed_url": None,
            "thumbnail_url": None,
        }

    raise ValueError("Invalid video URL")
