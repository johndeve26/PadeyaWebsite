"""HTML allowlist sanitizer for blog output (XSS-safe)."""

from __future__ import annotations

import re
from html.parser import HTMLParser

ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "hr",
        "h1",
        "h2",
        "h3",
        "h4",
        "ul",
        "ol",
        "li",
        "blockquote",
        "strong",
        "em",
        "b",
        "i",
        "code",
        "pre",
        "a",
        "img",
        "div",
        "span",
    }
)

ALLOWED_ATTRS: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "rel", "class", "target"}),
    "img": frozenset({"src", "alt", "loading", "class"}),
    "div": frozenset({"class", "data-event-slug", "data-host-username"}),
    "span": frozenset({"class"}),
    "p": frozenset({"class"}),
    "pre": frozenset({"class"}),
    "code": frozenset({"class"}),
}

SAFE_HREF = re.compile(r"^(https?:|mailto:|/|#)", re.I)
SAFE_SRC = re.compile(r"^(https?:|/)", re.I)


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in ALLOWED_TAGS:
            return
        if tag == "br":
            self._out.append("<br />")
            return
        if tag == "hr":
            self._out.append("<hr />")
            return
        allowed = ALLOWED_ATTRS.get(tag, frozenset())
        parts = [f"<{tag}"]
        for key, val in attrs:
            key = key.lower()
            if key not in allowed or val is None:
                continue
            if key in {"href", "src"}:
                v = val.strip()
                if key == "href" and not SAFE_HREF.match(v):
                    continue
                if key == "src" and not SAFE_SRC.match(v):
                    continue
                if "javascript:" in v.lower() or "data:" in v.lower():
                    continue
            # Escape attribute values
            safe = (
                val.replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            parts.append(f' {key}="{safe}"')
        if tag == "a" and "rel=" not in " ".join(parts):
            parts.append(' rel="noopener noreferrer"')
        parts.append(">")
        self._out.append("".join(parts))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ALLOWED_TAGS and tag not in {"br", "hr", "img"}:
            self._out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self._out.append(
            data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    def handle_entityref(self, name: str) -> None:
        self._out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._out.append(f"&#{name};")

    def result(self) -> str:
        return "".join(self._out)


def sanitize_html(raw: str) -> str:
    parser = _Sanitizer()
    try:
        parser.feed(raw or "")
        parser.close()
    except Exception:  # noqa: BLE001
        return ""
    return parser.result()


def validate_image_url(url: str | None) -> str | None:
    if not url:
        return None
    u = url.strip()
    if len(u) > 500:
        raise ValueError("Image URL too long")
    if not SAFE_SRC.match(u):
        raise ValueError("Image URL must be http(s) or site-relative")
    if any(x in u.lower() for x in ("javascript:", "data:", "<", ">")):
        raise ValueError("Invalid image URL")
    return u
