"""Render content_document to safe HTML and markdown."""

from __future__ import annotations

import html
import re
from typing import Any

from app.blog.markdown import markdown_to_html
from app.blog.sanitize import sanitize_html

_WIDTH_CLASS = {
    "narrow": "blog-width-narrow",
    "standard": "blog-width-standard",
    "wide": "blog-width-wide",
    "full": "blog-width-full",
}
_SPACING_CLASS = {
    "none": "blog-spacing-none",
    "compact": "blog-spacing-compact",
    "normal": "blog-spacing-normal",
    "spacious": "blog-spacing-spacious",
}
_BG_CLASS = {
    "default": "",
    "muted": "blog-bg-muted",
    "primary_subtle": "blog-bg-primary-subtle",
    "surface": "blog-bg-surface",
    "elevated": "blog-bg-elevated",
}
_EDITORIAL_CLASS = {
    "key_takeaway": "blog-callout blog-callout-key",
    "important_note": "blog-callout blog-callout-note",
    "warning": "blog-callout blog-callout-warning",
    "tip": "blog-callout blog-callout-tip",
    "statistic": "blog-stat",
    "pull_quote": "blog-pull-quote",
    "sources": "blog-sources",
    "author_note": "blog-author-note",
}


def _esc(text: str) -> str:
    return html.escape(text or "")


def _render_rich_content(content: dict[str, Any]) -> str:
    md = content.get("markdown") or ""
    raw_html = content.get("html") or ""
    if raw_html.strip():
        return sanitize_html(raw_html)
    if md.strip():
        return sanitize_html(markdown_to_html(md))
    return ""


def _render_block(block: dict[str, Any], *, toc_headings: list[dict[str, str]] | None = None) -> str:
    btype = block.get("type", "")
    props = block.get("props") or {}
    content = block.get("content") or {}
    children = block.get("children") or []
    variant = block.get("variant", "default")
    block_id = block.get("id", "")

    if props.get("visible") is False:
        return ""

    classes: list[str] = ["blog-block", f"blog-block-{btype.replace('_', '-')}"]
    if variant != "default":
        classes.append(f"blog-block-variant-{variant}")
    width = props.get("content_width")
    if width in _WIDTH_CLASS:
        classes.append(_WIDTH_CLASS[width])
    spacing = props.get("spacing")
    if spacing in _SPACING_CLASS:
        classes.append(_SPACING_CLASS[spacing])
    bg = props.get("background")
    if bg in _BG_CLASS and _BG_CLASS[bg]:
        classes.append(_BG_CLASS[bg])

    anchor = props.get("anchor_id") or ""
    anchor_attr = f' id="{_esc(anchor)}"' if anchor else ""

    inner = ""

    if btype in ("rich_text", "legacy_rich_text"):
        inner = _render_rich_content(content)
        if inner:
            inner = f'<div class="blog-prose">{inner}</div>'

    elif btype == "heading":
        level = int(content.get("level", 2))
        text = content.get("text", "")
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or block_id[:8]
        if toc_headings is not None and props.get("include_in_toc", True):
            toc_headings.append({"text": text, "id": slug, "level": level})
        tag = f"h{min(max(level, 2), 3)}"
        inner = f'<{tag} id="{_esc(slug)}">{_esc(text)}</{tag}>'

    elif btype == "image":
        url = _esc(content.get("url", ""))
        alt = _esc(content.get("alt", ""))
        cap = content.get("caption", "")
        inner = f'<figure class="blog-figure"><img src="{url}" alt="{alt}" loading="lazy" />'
        if cap:
            inner += f"<figcaption>{_esc(cap)}</figcaption>"
        inner += "</figure>"

    elif btype == "quote":
        text = _esc(content.get("text", ""))
        attr = content.get("attribution", "")
        inner = f"<blockquote><p>{text}</p>"
        if attr:
            inner += f"<cite>{_esc(attr)}</cite>"
        inner += "</blockquote>"

    elif btype == "cta":
        label = _esc(content.get("label", "Learn more"))
        href = _esc(content.get("href", "/events"))
        inner = (
            f'<div class="blog-cta"><a class="blog-cta-btn" href="{href}">{label}</a></div>'
        )

    elif btype == "divider":
        inner = '<hr class="blog-divider" />'

    elif btype == "spacer":
        inner = '<div class="blog-spacer" aria-hidden="true"></div>'

    elif btype == "faq":
        items = content.get("items") or []
        parts = ['<div class="blog-faq">']
        for item in items:
            q = _esc(item.get("question", ""))
            a_md = item.get("answer", "")
            a_html = sanitize_html(markdown_to_html(a_md)) if a_md else ""
            parts.append(f'<details class="blog-faq-item"><summary>{q}</summary><div>{a_html}</div></details>')
        parts.append("</div>")
        inner = "".join(parts)

    elif btype == "table":
        headers = content.get("headers") or []
        rows = content.get("rows") or []
        parts = ['<div class="blog-table-wrap"><table class="blog-table"><thead><tr>']
        for h in headers:
            parts.append(f"<th>{_esc(str(h))}</th>")
        parts.append("</tr></thead><tbody>")
        for row in rows:
            parts.append("<tr>")
            for cell in row:
                parts.append(f"<td>{_esc(str(cell))}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table></div>")
        inner = "".join(parts)

    elif btype == "list":
        tag = "ol" if content.get("ordered") else "ul"
        items = content.get("items") or []
        parts = [f"<{tag} class=\"blog-list\">"]
        for item in items:
            parts.append(f"<li>{_esc(str(item))}</li>")
        parts.append(f"</{tag}>")
        inner = "".join(parts)

    elif btype in _EDITORIAL_CLASS:
        text = content.get("text", "")
        if btype == "statistic":
            val = _esc(content.get("stat_value", props.get("stat_value", "")))
            lbl = _esc(content.get("stat_label", props.get("stat_label", "")))
            inner = f'<div class="{_EDITORIAL_CLASS[btype]}"><span class="blog-stat-value">{val}</span><span class="blog-stat-label">{lbl}</span></div>'
        else:
            body = sanitize_html(markdown_to_html(text)) if text else ""
            inner = f'<div class="{_EDITORIAL_CLASS[btype]}">{body}</div>'

    elif btype == "table_of_contents":
        if toc_headings:
            parts = ['<nav class="blog-toc-block" aria-label="Table of contents"><ol>']
            for h in toc_headings:
                if h["level"] == 3 and not content.get("include_h3", True):
                    continue
                indent = ' class="blog-toc-h3"' if h["level"] == 3 else ""
                parts.append(f'<li{indent}><a href="#{_esc(h["id"])}">{_esc(h["text"])}</a></li>')
            parts.append("</ol></nav>")
            inner = "".join(parts)

    elif btype == "video_embed":
        provider = content.get("provider", "")
        embed_id = _esc(content.get("embed_id", ""))
        if provider == "youtube":
            inner = f'<div class="blog-embed blog-embed-youtube"><iframe data-provider="youtube" src="https://www.youtube-nocookie.com/embed/{embed_id}" title="Video" loading="lazy" allowfullscreen></iframe></div>'
        elif provider == "vimeo":
            inner = f'<div class="blog-embed blog-embed-vimeo"><iframe data-provider="vimeo" src="https://player.vimeo.com/video/{embed_id}" title="Video" loading="lazy" allowfullscreen></iframe></div>'

    elif btype in ("event_promotion", "featured_event"):
        slug = _esc(content.get("event_slug", ""))
        inner = f'<div class="blog-embed blog-embed-event" data-event-slug="{slug}"></div>'

    elif btype in ("host_promotion", "featured_host"):
        username = _esc(content.get("host_username", ""))
        inner = f'<div class="blog-embed blog-embed-host" data-host-username="{username}"></div>'

    elif btype == "image_gallery":
        images = content.get("images") or []
        parts = ['<div class="blog-gallery">']
        for img in images:
            url = _esc(img.get("url", ""))
            alt = _esc(img.get("alt", ""))
            parts.append(f'<figure><img src="{url}" alt="{alt}" loading="lazy" /></figure>')
        parts.append("</div>")
        inner = "".join(parts)

    elif btype in (
        "section",
        "standard_section",
        "narrow_section",
        "full_width_section",
        "row",
        "two_column_row",
        "three_column_row",
        "column",
        "image_text",
        "text_image",
        "hero",
    ):
        child_html = "".join(_render_block(c, toc_headings=toc_headings) for c in children)
        row_class = ""
        if btype in ("two_column_row", "three_column_row", "row", "image_text", "text_image"):
            cols = len(children)
            row_class = f" blog-row blog-row-cols-{min(cols, 3)}"
            stack = props.get("mobile_stack_order", "default")
            if stack != "default":
                row_class += f" blog-stack-{stack}"
        inner = child_html
        if btype == "column":
            return f'<div class="blog-column">{inner}</div>'
        classes.append(row_class.strip())
        return f'<section{anchor_attr} class="{" ".join(c for c in classes if c)}">{inner}</section>'

    if not inner and children:
        inner = "".join(_render_block(c, toc_headings=toc_headings) for c in children)

    if not inner:
        return ""

    cls = " ".join(c for c in classes if c)
    return f'<div{anchor_attr} class="{cls}">{inner}</div>'


def document_to_html(doc: dict[str, Any] | None) -> str:
    if not doc:
        return ""
    toc_headings: list[dict[str, str]] = []
    # First pass: collect headings for TOC blocks
    blocks = doc.get("blocks") or []

    def _collect_headings(block: dict[str, Any]) -> None:
        if block.get("type") == "heading":
            content = block.get("content") or {}
            props = block.get("props") or {}
            if props.get("include_in_toc", True):
                text = content.get("text", "")
                level = int(content.get("level", 2))
                slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or block.get("id", "")[:8]
                toc_headings.append({"text": text, "id": slug, "level": level})
        for child in block.get("children") or []:
            _collect_headings(child)

    for b in blocks:
        _collect_headings(b)

    parts = ['<article class="blog-document">']
    for block in blocks:
        parts.append(_render_block(block, toc_headings=toc_headings))
    parts.append("</article>")
    return sanitize_html("".join(parts))


def document_to_markdown(doc: dict[str, Any] | None) -> str:
    """Flatten document to markdown for backward compatibility / search."""
    if not doc:
        return ""

    lines: list[str] = []

    def _walk(block: dict[str, Any]) -> None:
        btype = block.get("type", "")
        content = block.get("content") or {}
        if btype == "heading":
            level = int(content.get("level", 2))
            prefix = "##" if level == 2 else "###"
            lines.append(f"{prefix} {content.get('text', '')}\n")
        elif btype in ("rich_text", "legacy_rich_text"):
            md = content.get("markdown") or ""
            if md:
                lines.append(md + "\n")
        elif btype == "cta":
            label = content.get("label", "")
            href = content.get("href", "")
            lines.append(f'::cta{{label="{label}"; href="{href}"}}\n')
        elif btype == "quote":
            lines.append(f"> {content.get('text', '')}\n")
        for child in block.get("children") or []:
            _walk(child)

    for block in doc.get("blocks") or []:
        _walk(block)
    return "\n".join(lines).strip()
