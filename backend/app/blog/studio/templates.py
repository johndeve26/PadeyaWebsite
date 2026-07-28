"""Deterministic structured JSON builders for Blog AI Studio offline / fallback."""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.blog.studio.schemas import (
    BlogContentBrief,
    BlogFactClaim,
    BlogFaqItem,
    BlogGeneratedSection,
    BlogImagePrompt,
    BlogInternalLinkSuggestion,
    BlogOutline,
    BlogOutlineSection,
    BlogQualityReview,
    BlogSeoBrief,
    BlogSimilarityReview,
    BlogTitleSuggestion,
    QualityFinding,
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:80] or "padeya-guide"


def _topic(brief: BlogContentBrief | None, title: str | None = None) -> str:
    if brief and brief.topic.strip():
        return brief.topic.strip()
    if title and title.strip():
        return title.strip()
    return "events on Pàdéyá"


def _keyword(brief: BlogContentBrief | None) -> str:
    if brief and brief.primary_keyword.strip():
        return brief.primary_keyword.strip()
    return "Pàdéyá events"


def template_seo_brief(
    brief: BlogContentBrief | None = None, *, title: str | None = None
) -> BlogSeoBrief:
    topic = _topic(brief, title)
    kw = _keyword(brief)
    slug = _slugify(kw)
    return BlogSeoBrief(
        title_options=[
            f"How to discover {topic} on Pàdéyá",
            f"A practical guide to {topic}",
            f"{topic}: tips for fans and hosts",
        ],
        primary_keyword=kw,
        secondary_keywords=list((brief.secondary_keywords if brief else [])[:6]),
        search_intent=(brief.search_intent if brief and brief.search_intent else "informational"),
        article_angle=f"Practical editorial guide about {topic} for the Pàdéyá community",
        audience_questions=[
            f"What is {topic}?",
            "How do I get started on Pàdéyá?",
            "What should I review before publishing?",
        ],
        recommended_headings=[
            f"What {topic} means on Pàdéyá",
            "Practical steps",
            "Common mistakes to avoid",
            "Next actions",
        ],
        faq_questions=[
            "Is this advice official Pàdéyá policy?",
            "Do I need an account?",
        ],
        suggested_word_count=1200,
        proposed_slug=slug,
        meta_title=f"{topic[:50]} | Pàdéyá"[:70],
        meta_description=(
            f"A draft guide to {topic} on Pàdéyá — for fans and hosts. "
            "Editors must review before publishing."
        )[:160],
        internal_link_topics=["events", "hosts", "help", "pricing"],
        content_risks=[
            "Do not invent refund or safety guarantees",
            "Mark unverified claims as Needs verification",
        ],
    )


def template_titles(
    brief: BlogContentBrief | None = None,
    *,
    title: str | None = None,
    count: int = 5,
) -> list[BlogTitleSuggestion]:
    topic = _topic(brief, title)
    kw = _keyword(brief)
    raw = [
        f"Discover {topic} on Pàdéyá",
        f"A clearer way to explore {topic}",
        f"{topic} without the guesswork",
        f"From discovery to check-in: {topic}",
        f"Guides for fans and hosts: {topic}",
        f"Weekend-ready tips for {topic}",
        f"Hosting nights that feel local: {topic}",
    ]
    out: list[BlogTitleSuggestion] = []
    for t in raw[: max(1, min(count, 10))]:
        out.append(
            BlogTitleSuggestion(
                title=t[:120],
                angle="practical discovery",
                estimated_intent="informational",
                length=len(t),
                keyword_included=kw.lower() in t.lower() or "pàdéyá" in t.lower(),
                click_appeal="medium",
                warning=None,
            )
        )
    return out


def template_outline(
    brief: BlogContentBrief | None = None, *, title: str | None = None
) -> BlogOutline:
    topic = _topic(brief, title)
    sections = [
        BlogOutlineSection(
            id="sec-intro-context",
            heading=f"What {topic} means on Pàdéyá",
            level=2,
            key_point="Set context without overclaiming",
            examples=["Local discovery", "Ticket clarity"],
            data_source_needs=["Needs verification for any stats"],
        ),
        BlogOutlineSection(
            id="sec-steps",
            heading="Practical steps",
            level=2,
            key_point="Actionable checklist readers can follow",
            examples=["Browse events", "Compare hosts"],
        ),
        BlogOutlineSection(
            id="sec-mistakes",
            heading="Common mistakes to avoid",
            level=2,
            key_point="Keep expectations honest",
            examples=["No guaranteed attendance claims"],
        ),
        BlogOutlineSection(
            id="sec-next",
            heading="Next actions on Pàdéyá",
            level=2,
            key_point="Point to real product routes",
            examples=["/events", "/hosts", "/help"],
        ),
    ]
    return BlogOutline(
        introduction_purpose=f"Orient readers to {topic} on Pàdéyá",
        sections=sections,
        conclusion_direction="Invite exploration; remind editors to review before publish",
        cta_placement="end",
        faq_section=True,
        approved=False,
    )


def template_outline_section(
    outline: BlogOutline,
    section_id: str,
    brief: BlogContentBrief | None = None,
) -> BlogOutlineSection:
    for sec in outline.sections:
        if sec.id == section_id:
            if sec.locked:
                return sec
            return BlogOutlineSection(
                id=sec.id,
                heading=sec.heading,
                level=sec.level,
                key_point=sec.key_point or f"Refined key point for {sec.heading}",
                examples=sec.examples or ["Example detail for editors to verify"],
                data_source_needs=["Needs verification"],
                locked=False,
            )
    topic = _topic(brief)
    return BlogOutlineSection(
        id=section_id or f"sec-{uuid.uuid4().hex[:8]}",
        heading=f"Updated section on {topic}",
        level=2,
        key_point="Template-regenerated section",
        examples=[],
        data_source_needs=["Needs verification"],
        locked=False,
    )


def template_section(
    outline_section: BlogOutlineSection | None = None,
    brief: BlogContentBrief | None = None,
    *,
    section_id: str | None = None,
) -> BlogGeneratedSection:
    sec = outline_section
    sid = section_id or (sec.id if sec else f"sec-{uuid.uuid4().hex[:8]}")
    heading = sec.heading if sec else f"About {_topic(brief)}"
    body = (
        f"{heading}\n\n"
        f"This draft section covers {heading.lower()} for readers on Pàdéyá. "
        "Keep claims modest and mark anything unverified. "
        "Editors must review before publishing — AI never auto-publishes.\n\n"
        "Needs verification: any attendance, revenue, or safety statistics."
    )
    return BlogGeneratedSection(
        id=sid,
        heading=heading,
        body=body,
        bullets=[
            "Stay practical and local",
            "Link only to real Pàdéyá routes",
            "Needs verification for factual claims",
        ],
        internal_link_anchor="Explore events on Pàdéyá",
        fact_markers=["Needs verification"],
        locked=bool(sec.locked) if sec else False,
    )


def template_full_draft(
    outline: BlogOutline,
    *,
    locked_section_ids: list[str] | None = None,
    brief: BlogContentBrief | None = None,
) -> list[BlogGeneratedSection]:
    locked = set(locked_section_ids or [])
    out: list[BlogGeneratedSection] = []
    for sec in outline.sections:
        if sec.id in locked or sec.locked:
            out.append(
                BlogGeneratedSection(
                    id=sec.id,
                    heading=sec.heading,
                    body="",
                    bullets=[],
                    locked=True,
                    fact_markers=[],
                )
            )
            continue
        out.append(template_section(sec, brief, section_id=sec.id))
    return out


def template_rewrite(selection: str, action: str) -> str:
    text = (selection or "").strip()
    if action == "shorter":
        return text[: max(40, len(text) // 2)] + ("…" if len(text) > 40 else "")
    if action == "expand":
        return (
            f"{text}\n\nIn practice on Pàdéyá, keep this guidance concrete and "
            "review before publishing. Needs verification for any statistics."
        )
    if action == "to_bullets":
        parts = [p.strip() for p in re.split(r"[.\n]+", text) if p.strip()]
        return "\n".join(f"- {p}" for p in parts[:8]) or f"- {text}"
    if action == "to_prose":
        lines = [ln.lstrip("-• ").strip() for ln in text.splitlines() if ln.strip()]
        return " ".join(lines) or text
    if action == "summarize":
        return f"Summary: {text[:280]}"
    if action == "heading":
        return text.strip().split("\n", 1)[0][:80]
    return f"{text}\n\n(Edited for {action} — draft only; review on Pàdéyá before publishing.)"


def template_faqs(
    brief: BlogContentBrief | None = None, *, count: int = 5
) -> list[BlogFaqItem]:
    topic = _topic(brief)
    items = [
        (
            f"What is this guide about?",
            f"A draft editorial overview of {topic} on Pàdéyá. Editors must review before publishing.",
        ),
        (
            "Does Pàdéyá auto-publish AI drafts?",
            "No. AI Studio suggestions are draft-only and never auto-publish.",
        ),
        (
            "Are refunds guaranteed?",
            "No. Do not invent refund promises. Follow published Pàdéyá policies.",
        ),
        (
            "Where can I explore events?",
            "Use the real /events route on Pàdéyá after human review of this draft.",
        ),
        (
            "How should factual claims be handled?",
            "Mark uncertain claims as Needs verification and require sources before publish.",
        ),
        (
            "Who should edit this?",
            "CMS editors with blog create/edit permission on Pàdéyá.",
        ),
    ]
    out: list[BlogFaqItem] = []
    for i, (q, a) in enumerate(items[: max(1, min(count, 12))]):
        out.append(BlogFaqItem(id=f"faq-{i+1}", question=q, answer=a))
    return out


def template_image_prompt(
    brief: BlogContentBrief | None = None, *, title: str | None = None
) -> BlogImagePrompt:
    topic = _topic(brief, title)
    return BlogImagePrompt(
        concept=f"Editorial cover for {topic}",
        prompt=(
            f"Warm evening street scene suggesting local nightlife discovery, "
            f"related to {topic}, no logos invented, no readable fake brand text, "
            "photoreal editorial style"
        ),
        aspect_ratio="16:9",
        overlay_text=None,
        alt_text=f"Editorial image concept for {topic} on Pàdéyá",
        caption=f"Draft cover concept for {topic} — replace with licensed media before publish",
        focal_point="center",
    )


def template_review(*, body: str | None = None) -> BlogQualityReview:
    text = body or ""
    weak = len(text.strip()) < 200
    return BlogQualityReview(
        clarity=QualityFinding(status="ok", message="Readable draft tone"),
        repetition=QualityFinding(status="ok", message="No major repetition detected in template pass"),
        weak_intro=QualityFinding(
            status="warn" if weak else "ok",
            message="Intro may be thin" if weak else "Intro length looks fine",
            suggestion="Expand the opening with a concrete reader benefit" if weak else None,
        ),
        unsupported_claims=QualityFinding(
            status="warn",
            message="Treat statistics as Needs verification",
            suggestion="Add sources or remove unverified numbers",
        ),
        promotional=QualityFinding(status="ok", message="Promotional tone within editorial bounds"),
        keyword_stuffing=QualityFinding(status="ok", message="No stuffing detected"),
        heading_quality=QualityFinding(status="ok", message="Use clear H2/H3 hierarchy"),
        logical_flow=QualityFinding(status="ok", message="Template structure is sequential"),
        missing_conclusion=QualityFinding(
            status="warn" if "next" not in text.lower() else "ok",
            message="Ensure a conclusion / next-step section",
        ),
        cta_quality=QualityFinding(
            status="ok",
            message="Prefer real routes like /events — never invent URLs",
        ),
        reading_difficulty=QualityFinding(status="ok", message="Aim for accessible plain language"),
        accessibility=QualityFinding(status="ok", message="Add alt text for images before publish"),
        missing_alt=QualityFinding(
            status="warn",
            message="Confirm cover/image alt text before publish",
        ),
        broken_internal_links=QualityFinding(
            status="ok",
            message="Only suggest verified inventory routes",
        ),
        summary="Template quality review — human editors must still review before publishing on Pàdéyá.",
        suggested_changes=[
            "Mark unverified claims as Needs verification",
            "Confirm internal links against real routes",
            "Never auto-publish AI output",
        ],
    )


def template_similarity() -> BlogSimilarityReview:
    return BlogSimilarityReview(
        duplicated_headings=[],
        repeated_paragraphs=[],
        similar_posts=[],
        cannibalization_risks=[],
        conflicting_slugs=[],
        disclaimer=(
            "This is an editorial similarity check only — not legal plagiarism detection."
        ),
    )


def template_internal_links(
    links: list[dict[str, str]] | None = None,
) -> list[BlogInternalLinkSuggestion]:
    """Build suggestions from real URLs only (caller supplies inventory)."""
    out: list[BlogInternalLinkSuggestion] = []
    for item in links or []:
        url = (item.get("target_url") or "").strip()
        if not url.startswith("/"):
            continue
        out.append(
            BlogInternalLinkSuggestion(
                target_url=url,
                target_title=item.get("target_title") or url,
                suggested_anchor=item.get("suggested_anchor") or item.get("target_title") or url,
                insertion_location=item.get("insertion_location") or "relevant body section",
                relevance_reason=item.get("relevance_reason") or "Matches published inventory",
            )
        )
    return out


def template_fact_review(*, body: str | None = None) -> list[BlogFactClaim]:
    """Never invent verified citations — always Needs verification."""
    text = (body or "").strip()
    claims: list[BlogFactClaim] = []
    if text:
        # Heuristic: sentences with numbers look like claim candidates
        for m in re.finditer(r"([^.!?\n]*\d+[^.!?\n]*[.!?]?)", text):
            claim = m.group(1).strip()
            if len(claim) < 12:
                continue
            claims.append(
                BlogFactClaim(
                    claim=claim[:500],
                    section="body",
                    confidence="low",
                    source_required=True,
                    review_status="Needs verification",
                    source_urls=[],
                )
            )
            if len(claims) >= 8:
                break
    if not claims:
        claims.append(
            BlogFactClaim(
                claim="Any attendance, revenue, or safety statistics in this draft",
                section="general",
                confidence="low",
                source_required=True,
                review_status="Needs verification",
                source_urls=[],
            )
        )
    return claims


def template_payload_for_task(task_hint: str, **kwargs: Any) -> str:
    """Return JSON string for provider `_template_draft` studio branches."""
    import json

    hint = (task_hint or "").lower()
    brief = kwargs.get("brief")
    if isinstance(brief, dict):
        brief = BlogContentBrief.model_validate(brief)
    title = kwargs.get("title")

    if "seo_brief" in hint or "seo brief" in hint:
        return template_seo_brief(brief, title=title).model_dump_json()
    if "title suggestion" in hint or "blog titles json" in hint:
        return json.dumps(
            {"titles": [t.model_dump() for t in template_titles(brief, title=title)]}
        )
    if "outline section" in hint:
        outline = kwargs.get("outline") or template_outline(brief, title=title)
        if isinstance(outline, dict):
            outline = BlogOutline.model_validate(outline)
        sec = template_outline_section(
            outline, str(kwargs.get("section_id") or "sec-steps"), brief
        )
        return sec.model_dump_json()
    if "blog outline json" in hint or "generate outline json" in hint:
        return template_outline(brief, title=title).model_dump_json()
    if "full draft" in hint:
        outline = kwargs.get("outline") or template_outline(brief, title=title)
        if isinstance(outline, dict):
            outline = BlogOutline.model_validate(outline)
        sections = template_full_draft(outline, brief=brief)
        return json.dumps({"sections": [s.model_dump() for s in sections]})
    if "section body json" in hint or "generate section json" in hint:
        return template_section(brief=brief, section_id=kwargs.get("section_id")).model_dump_json()
    if "rewrite selection" in hint:
        return json.dumps(
            {
                "text": template_rewrite(
                    str(kwargs.get("selection") or ""),
                    str(kwargs.get("action") or "rewrite"),
                ),
                "action": kwargs.get("action") or "rewrite",
            }
        )
    if "quality review" in hint or "review article json" in hint:
        return template_review(body=kwargs.get("body")).model_dump_json()
    if "similarity review" in hint:
        return template_similarity().model_dump_json()
    if "faq json" in hint or "generate faqs" in hint:
        return json.dumps({"faqs": [f.model_dump() for f in template_faqs(brief)]})
    if "image prompt" in hint:
        return template_image_prompt(brief, title=title).model_dump_json()
    if "internal links" in hint:
        return json.dumps({"links": []})
    if "fact review" in hint:
        return json.dumps(
            {"claims": [c.model_dump() for c in template_fact_review(body=kwargs.get("body"))]}
        )
    return template_seo_brief(brief, title=title).model_dump_json()
