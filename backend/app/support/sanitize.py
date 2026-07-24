"""Sanitize support message bodies — strip HTML / dangerous URLs."""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_JS_URL_RE = re.compile(r"javascript\s*:", re.I)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_support_text(raw: str, *, max_len: int = 8000) -> str:
    text = raw or ""
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _JS_URL_RE.sub("", text)
    text = _CTRL_RE.sub("", text)
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text
