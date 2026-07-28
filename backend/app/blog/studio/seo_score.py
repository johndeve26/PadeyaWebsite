"""Local SEO indicator scoring for Blog AI Studio (no network AI)."""

from __future__ import annotations

import re

from app.blog.studio.schemas import BlogSeoScore, SeoIndicator, SeoScoreRequest


def _words(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def compute_seo_score(payload: SeoScoreRequest) -> BlogSeoScore:
    title = (payload.title or "").strip()
    meta_title = (payload.seo_title or title).strip()
    desc = (payload.seo_description or "").strip()
    slug = (payload.slug or "").strip()
    body = payload.body or ""
    kw = (payload.focus_keyword or "").strip().lower()
    intro = body[:400].lower()
    headings = re.findall(r"^#{2,3}\s+(.+)$", body, flags=re.MULTILINE)

    def title_length() -> SeoIndicator:
        n = len(title)
        if 30 <= n <= 70:
            return SeoIndicator(status="ok", message=f"Title length {n} is in range")
        if n == 0:
            return SeoIndicator(status="fail", message="Title is empty")
        return SeoIndicator(status="warn", message=f"Title length {n} is outside 30–70")

    def meta_title_length() -> SeoIndicator:
        n = len(meta_title)
        if 30 <= n <= 60:
            return SeoIndicator(status="ok", message=f"Meta title length {n} is in range")
        if n == 0:
            return SeoIndicator(status="fail", message="Meta title is empty")
        return SeoIndicator(status="warn", message=f"Meta title length {n} is outside 30–60")

    def description_length() -> SeoIndicator:
        n = len(desc)
        if 70 <= n <= 160:
            return SeoIndicator(status="ok", message=f"Meta description length {n} is in range")
        if n == 0:
            return SeoIndicator(status="fail", message="Meta description is empty")
        return SeoIndicator(status="warn", message=f"Meta description length {n} is outside 70–160")

    def keyword_in_title() -> SeoIndicator:
        if not kw:
            return SeoIndicator(status="warn", message="No focus keyword set")
        if kw in title.lower():
            return SeoIndicator(status="ok", message="Focus keyword appears in title")
        return SeoIndicator(status="warn", message="Focus keyword missing from title")

    def keyword_in_intro() -> SeoIndicator:
        if not kw:
            return SeoIndicator(status="warn", message="No focus keyword set")
        if kw in intro:
            return SeoIndicator(status="ok", message="Focus keyword appears near the intro")
        return SeoIndicator(status="warn", message="Focus keyword missing from intro")

    def keyword_in_headings() -> SeoIndicator:
        if not kw:
            return SeoIndicator(status="warn", message="No focus keyword set")
        if any(kw in h.lower() for h in headings):
            return SeoIndicator(status="ok", message="Focus keyword appears in a heading")
        return SeoIndicator(status="warn", message="Focus keyword missing from headings")

    def slug_quality() -> SeoIndicator:
        if not slug:
            return SeoIndicator(status="fail", message="Slug is empty")
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) and len(slug) <= 80:
            return SeoIndicator(status="ok", message="Slug looks clean")
        return SeoIndicator(status="warn", message="Slug should be lowercase-hyphenated")

    def heading_hierarchy() -> SeoIndicator:
        if not headings:
            return SeoIndicator(status="warn", message="No H2/H3 headings found")
        return SeoIndicator(status="ok", message=f"Found {len(headings)} headings")

    def article_length() -> SeoIndicator:
        n = _words(body)
        if n >= 800:
            return SeoIndicator(status="ok", message=f"Approx {n} words")
        if n >= 300:
            return SeoIndicator(status="warn", message=f"Approx {n} words — consider expanding")
        return SeoIndicator(status="fail", message=f"Approx {n} words — too short for SEO draft")

    def internal_links() -> SeoIndicator:
        links = re.findall(r"\[[^\]]+\]\((/[^)]+)\)", body)
        if links:
            return SeoIndicator(status="ok", message=f"Found {len(links)} internal markdown links")
        return SeoIndicator(status="warn", message="No internal markdown links found")

    def image_alt() -> SeoIndicator:
        if payload.cover_url:
            return SeoIndicator(
                status="warn",
                message="Cover URL set — confirm alt text before publish",
            )
        alts = re.findall(r"!\[[^\]]*\]\(", body)
        if alts:
            empty = re.findall(r"!\[\s*\]\(", body)
            if empty:
                return SeoIndicator(status="fail", message="Image markdown missing alt text")
            return SeoIndicator(status="ok", message="Inline images include alt text")
        return SeoIndicator(status="warn", message="No images detected")

    return BlogSeoScore(
        title_length=title_length(),
        meta_title_length=meta_title_length(),
        description_length=description_length(),
        keyword_in_title=keyword_in_title(),
        keyword_in_intro=keyword_in_intro(),
        keyword_in_headings=keyword_in_headings(),
        slug_quality=slug_quality(),
        heading_hierarchy=heading_hierarchy(),
        article_length=article_length(),
        internal_links=internal_links(),
        image_alt=image_alt(),
    )
