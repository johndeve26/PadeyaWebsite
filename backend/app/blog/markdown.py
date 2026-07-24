"""Safe markdown → HTML for blog bodies (no external deps)."""

from __future__ import annotations

import html
import re


_HEADING = re.compile(r"^(#{1,3})\s+(.+)$")
_UL = re.compile(r"^[-*]\s+(.+)$")
_OL = re.compile(r"^(\d+)\.\s+(.+)$")
_BQ = re.compile(r"^>\s?(.*)$")
_FENCE = re.compile(r"^```")
_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_CODE = re.compile(r"`([^`]+)`")
_CTA = re.compile(
    r"^::cta\{label=\"([^\"]+)\";\s*href=\"([^\"]+)\"\}$", re.IGNORECASE
)
_EVENT = re.compile(r"^::event\{slug=\"([^\"]+)\"\}$", re.IGNORECASE)
_HOST = re.compile(r"^::host\{username=\"([^\"]+)\"\}$", re.IGNORECASE)


def _inline(text: str) -> str:
    text = html.escape(text)

    def _img(m: re.Match[str]) -> str:
        alt = m.group(1)
        src = m.group(2)
        if not _safe_url(src):
            return alt
        return f'<img src="{html.escape(src, quote=True)}" alt="{alt}" loading="lazy" />'

    def _link(m: re.Match[str]) -> str:
        label = m.group(1)
        href = m.group(2)
        if not _safe_url(href):
            return label
        return (
            f'<a href="{html.escape(href, quote=True)}" rel="noopener noreferrer">'
            f"{label}</a>"
        )

    # Order: images, links, then emphasis on remaining text (already escaped)
    # Re-run on original escaped text with patterns that match escaped content poorly —
    # instead process before escape for structured tokens.
    return text


def _inline_md(raw: str) -> str:
    """Escape then restore safe markdown inline tokens."""
    # Protect images/links first via placeholders
    placeholders: list[str] = []

    def keep(html_frag: str) -> str:
        placeholders.append(html_frag)
        return f"\x00PH{len(placeholders) - 1}\x00"

    def repl_img(m: re.Match[str]) -> str:
        alt, src = html.escape(m.group(1)), m.group(2)
        if not _safe_url(src):
            return html.escape(m.group(0))
        return keep(
            f'<img src="{html.escape(src, quote=True)}" alt="{alt}" loading="lazy" />'
        )

    def repl_link(m: re.Match[str]) -> str:
        label, href = html.escape(m.group(1)), m.group(2)
        if not _safe_url(href):
            return html.escape(m.group(0))
        return keep(
            f'<a href="{html.escape(href, quote=True)}" rel="noopener noreferrer">{label}</a>'
        )

    s = _IMG.sub(repl_img, raw)
    s = _LINK.sub(repl_link, s)
    s = html.escape(s)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    s = _ITALIC.sub(r"<em>\1</em>", s)
    s = _CODE.sub(r"<code>\1</code>", s)
    for i, frag in enumerate(placeholders):
        s = s.replace(f"\x00PH{i}\x00", frag)
    return s


def _safe_url(url: str) -> bool:
    u = (url or "").strip().lower()
    if not u or u.startswith("javascript:") or u.startswith("data:"):
        return False
    return (
        u.startswith("https://")
        or u.startswith("http://")
        or u.startswith("/")
        or u.startswith("#")
        or u.startswith("mailto:")
    )


def estimate_reading_minutes(markdown: str) -> int:
    words = len(re.findall(r"\w+", markdown or ""))
    return max(1, round(words / 220))


def markdown_to_html(markdown: str) -> str:
    """Convert a constrained markdown dialect to HTML (pre-sanitize)."""
    lines = (markdown or "").replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    in_ul = False
    in_ol = False
    in_code = False
    code_buf: list[str] = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line):
            if in_code:
                close_lists()
                code = html.escape("\n".join(code_buf))
                out.append(f"<pre><code>{code}</code></pre>")
                code_buf = []
                in_code = False
            else:
                close_lists()
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        cta = _CTA.match(line.strip())
        if cta:
            close_lists()
            label, href = cta.group(1), cta.group(2)
            if _safe_url(href):
                out.append(
                    '<p class="blog-cta">'
                    f'<a class="blog-cta-btn" href="{html.escape(href, quote=True)}">'
                    f"{html.escape(label)}</a></p>"
                )
            i += 1
            continue
        ev = _EVENT.match(line.strip())
        if ev:
            close_lists()
            slug = html.escape(ev.group(1), quote=True)
            out.append(
                f'<div class="blog-embed blog-embed-event" data-event-slug="{slug}"></div>'
            )
            i += 1
            continue
        ho = _HOST.match(line.strip())
        if ho:
            close_lists()
            un = html.escape(ho.group(1), quote=True)
            out.append(
                f'<div class="blog-embed blog-embed-host" data-host-username="{un}"></div>'
            )
            i += 1
            continue

        if not line.strip():
            close_lists()
            i += 1
            continue

        hm = _HEADING.match(line)
        if hm:
            close_lists()
            level = len(hm.group(1))
            out.append(f"<h{level}>{_inline_md(hm.group(2).strip())}</h{level}>")
            i += 1
            continue

        bq = _BQ.match(line)
        if bq:
            close_lists()
            out.append(f"<blockquote><p>{_inline_md(bq.group(1))}</p></blockquote>")
            i += 1
            continue

        um = _UL.match(line)
        if um:
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_md(um.group(1))}</li>")
            i += 1
            continue

        om = _OL.match(line)
        if om:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{_inline_md(om.group(2))}</li>")
            i += 1
            continue

        close_lists()
        out.append(f"<p>{_inline_md(line.strip())}</p>")
        i += 1

    close_lists()
    if in_code:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>")
    return "\n".join(out)
