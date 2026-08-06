"""Extract title/description/headings/body from untrusted HTML (stdlib only)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser


_SCRIPT_STYLE = frozenset({"script", "style", "noscript", "svg", "iframe"})
_STRIP_TAGS = frozenset({"nav", "footer", "header", "aside", "form"})


@dataclass
class ExtractedPage:
    title: str = ""
    description: str = ""
    headings: list[str] = field(default_factory=list)
    body_text: str = ""


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.description = ""
        self.headings: list[str] = []
        self.body_parts: list[str] = []
        self._in_title = False
        self._heading_buf: list[str] | None = None
        self._skip_depth = 0
        self._in_body = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr = {k.lower(): (v or "") for k, v in attrs}
        if t == "body":
            self._in_body = True
        if t in _SCRIPT_STYLE or t in _STRIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if t == "title":
            self._in_title = True
        if t == "meta":
            name = (attr.get("name") or attr.get("property") or "").lower()
            content = attr.get("content") or ""
            if name in {"description", "og:description"} and content and not self.description:
                self.description = content.strip()[:500]
        if t in {"h1", "h2", "h3"}:
            self._heading_buf = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in _SCRIPT_STYLE or t in _STRIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if t == "title":
            self._in_title = False
        if t in {"h1", "h2", "h3"} and self._heading_buf is not None:
            text = " ".join(self._heading_buf).strip()
            if text:
                self.headings.append(text[:200])
            self._heading_buf = None
        if t == "body":
            self._in_body = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if self._heading_buf is not None:
            self._heading_buf.append(text)
        if self._in_body or not self.title_parts:
            self.body_parts.append(text)


def extract_from_html(html: str) -> ExtractedPage:
    """Parse HTML; treat all content as untrusted."""
    if not html:
        return ExtractedPage()
    # Cheap pre-strip of script/style blocks before parse
    cleaned = re.sub(
        r"(?is)<(script|style|noscript)[^>]*>.*?</\1>",
        " ",
        html,
    )
    parser = _PageParser()
    try:
        parser.feed(cleaned)
    except Exception:
        # Fallback: regex title + strip tags
        title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
        title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
        text = re.sub(r"(?is)<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return ExtractedPage(title=title[:300], body_text=text[:50000])

    title = " ".join(parser.title_parts).strip()[:300]
    body = re.sub(r"\s+", " ", " ".join(parser.body_parts)).strip()
    return ExtractedPage(
        title=title,
        description=parser.description[:500],
        headings=parser.headings[:40],
        body_text=body[:50000],
    )
