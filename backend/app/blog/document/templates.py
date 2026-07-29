"""Built-in blog layout templates."""

from __future__ import annotations

from typing import Any

from app.blog.document.conversion import blank_document, new_block_id


def _section(
    spacing: str = "normal",
    width: str = "standard",
    *,
    children: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "standard_section",
        "variant": "default",
        "props": {"spacing": spacing, "content_width": width},
        "content": {},
        "children": children,
    }


def _heading(text: str, level: int = 2) -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "heading",
        "variant": "default",
        "props": {"include_in_toc": True},
        "content": {"text": text, "level": level},
        "children": [],
    }


def _rich(markdown: str) -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "rich_text",
        "variant": "default",
        "props": {},
        "content": {"markdown": markdown, "html": ""},
        "children": [],
    }


def _cta(label: str = "Explore events", href: str = "/events") -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "cta",
        "variant": "default",
        "props": {},
        "content": {"label": label, "href": href},
        "children": [],
    }


def _faq() -> dict[str, Any]:
    return {
        "id": new_block_id(),
        "type": "faq",
        "variant": "default",
        "props": {},
        "content": {
            "items": [
                {
                    "id": new_block_id(),
                    "question": "Question placeholder",
                    "answer": "Answer placeholder — replace with factual content.",
                }
            ]
        },
        "children": [],
    }


def _doc(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    base = blank_document()
    base["blocks"] = blocks
    return base


BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Blank article",
        "slug": "blank",
        "description": "Start with a single rich text block.",
        "category": "general",
        "document": blank_document(),
    },
    {
        "name": "How-to guide",
        "slug": "how-to-guide",
        "description": "Step-by-step structure with intro, steps, and FAQ.",
        "category": "guide",
        "document": _doc([
            _section(children=[
                _heading("Introduction"),
                _rich("Explain what readers will learn and why it matters."),
            ]),
            _section(children=[
                _heading("What you'll need"),
                _rich("- Item one\n- Item two\n- Item three"),
            ]),
            _section(children=[
                _heading("Step 1"),
                _rich("Describe the first step in detail."),
            ]),
            _section(children=[
                _heading("Step 2"),
                _rich("Describe the second step."),
            ]),
            _section(children=[_heading("FAQ"), _faq()]),
            _section(children=[_cta()]),
        ]),
    },
    {
        "name": "List article",
        "slug": "list-article",
        "description": "Numbered or curated list format.",
        "category": "editorial",
        "document": _doc([
            _section(children=[
                _heading("Introduction"),
                _rich("Set up the list and why these items matter."),
            ]),
            _section(children=[
                _heading("1. First item"),
                _rich("Description of the first item."),
            ]),
            _section(children=[
                _heading("2. Second item"),
                _rich("Description of the second item."),
            ]),
            _section(children=[
                _heading("3. Third item"),
                _rich("Description of the third item."),
            ]),
        ]),
    },
    {
        "name": "Event planning guide",
        "slug": "event-planning-guide",
        "description": "Guide for hosts planning events on Pàdéyá.",
        "category": "host",
        "document": _doc([
            _section(children=[
                _heading("Planning your event"),
                _rich("Overview for hosts creating memorable experiences."),
            ]),
            _section(children=[
                _heading("Before you publish"),
                _rich("Checklist of pre-launch tasks."),
            ]),
            _section(children=[_cta("Create your event", "/host/events/new")]),
        ]),
    },
    {
        "name": "Venue guide",
        "slug": "venue-guide",
        "description": "Venue-focused editorial template.",
        "category": "guide",
        "document": _doc([
            _section(children=[
                _heading("About this venue"),
                _rich("Location, capacity, and vibe."),
            ]),
            _section(children=[
                _heading("Getting there"),
                _rich("Directions and accessibility notes."),
            ]),
        ]),
    },
    {
        "name": "Host resource",
        "slug": "host-resource",
        "description": "Resource article for event hosts.",
        "category": "host",
        "document": _doc([
            _section(children=[
                _heading("Host resource"),
                _rich("Practical tips for hosts."),
            ]),
            _section(children=[
                _heading("Key takeaway"),
                {
                    "id": new_block_id(),
                    "type": "key_takeaway",
                    "variant": "default",
                    "props": {},
                    "content": {"text": "Summarize the main point here."},
                    "children": [],
                },
            ]),
            _section(children=[_cta("Host on Pàdéyá", "/for-hosts")]),
        ]),
    },
    {
        "name": "Attendee guide",
        "slug": "attendee-guide",
        "description": "Guide for event attendees.",
        "category": "guide",
        "document": _doc([
            _section(children=[
                _heading("What to expect"),
                _rich("Help attendees prepare for the experience."),
            ]),
            _section(children=[_cta("Discover events", "/events")]),
        ]),
    },
    {
        "name": "Case study",
        "slug": "case-study",
        "description": "Problem → approach → results structure.",
        "category": "editorial",
        "document": _doc([
            _section(children=[
                _heading("Overview"),
                _rich("Brief summary of the case."),
            ]),
            _section(children=[
                _heading("The challenge"),
                _rich("What problem needed solving?"),
            ]),
            _section(children=[
                _heading("The approach"),
                _rich("How it was addressed."),
            ]),
            _section(children=[
                _heading("Results"),
                _rich("Outcomes and metrics."),
            ]),
        ]),
    },
    {
        "name": "Product update",
        "slug": "product-update",
        "description": "Ship notes and feature announcements.",
        "category": "product",
        "document": _doc([
            _section(children=[
                _heading("What's new"),
                _rich("Lead with the headline feature or change."),
            ]),
            _section(children=[
                _heading("Details"),
                _rich("Expand on changes and how to use them."),
            ]),
        ]),
    },
    {
        "name": "News / editorial",
        "slug": "news-editorial",
        "description": "News analysis or editorial commentary.",
        "category": "editorial",
        "document": _doc([
            _section(children=[
                _heading("Summary"),
                _rich("Lead paragraph with the key news angle."),
            ]),
            _section(children=[
                _heading("Analysis"),
                _rich("Context and implications."),
            ]),
        ]),
    },
    {
        "name": "Interview",
        "slug": "interview",
        "description": "Q&A interview format.",
        "category": "editorial",
        "document": _doc([
            _section(children=[
                _heading("Introduction"),
                _rich("Introduce the interviewee and topic."),
            ]),
            _section(children=[
                _heading("Q: First question?"),
                _rich("A: Answer placeholder."),
            ]),
            _section(children=[
                _heading("Q: Second question?"),
                _rich("A: Answer placeholder."),
            ]),
        ]),
    },
    {
        "name": "Comparison article",
        "slug": "comparison",
        "description": "Compare options side by side.",
        "category": "editorial",
        "document": _doc([
            _section(children=[
                _heading("Introduction"),
                _rich("What are we comparing and why."),
            ]),
            {
                "id": new_block_id(),
                "type": "two_column_row",
                "variant": "default",
                "props": {"spacing": "normal", "mobile_stack_order": "default"},
                "content": {},
                "children": [
                    {
                        "id": new_block_id(),
                        "type": "column",
                        "variant": "default",
                        "props": {},
                        "content": {},
                        "children": [
                            _heading("Option A", 3),
                            _rich("Pros and cons of option A."),
                        ],
                    },
                    {
                        "id": new_block_id(),
                        "type": "column",
                        "variant": "default",
                        "props": {},
                        "content": {},
                        "children": [
                            _heading("Option B", 3),
                            _rich("Pros and cons of option B."),
                        ],
                    },
                ],
            },
            _section(children=[_heading("Verdict"), _rich("Your recommendation.")]),
        ]),
    },
]

BUILTIN_REUSABLE_SECTIONS: list[dict[str, Any]] = [
    {
        "name": "Newsletter CTA",
        "slug": "newsletter-cta",
        "description": "Newsletter signup call to action.",
        "section": _section(children=[
            _heading("Stay in the loop"),
            _rich("Get event highlights and host tips in your inbox."),
            _cta("Subscribe", "/newsletter"),
        ]),
    },
    {
        "name": "Host signup CTA",
        "slug": "host-signup-cta",
        "description": "Encourage readers to host events.",
        "section": _section(children=[
            _heading("Ready to host?"),
            _rich("Create your first event on Pàdéyá."),
            _cta("Start hosting", "/for-hosts"),
        ]),
    },
    {
        "name": "Event discovery CTA",
        "slug": "event-discovery-cta",
        "description": "Drive readers to discover events.",
        "section": _section(children=[_cta("Discover events near you", "/events")]),
    },
    {
        "name": "Standard author note",
        "slug": "author-note",
        "description": "Editorial author note block.",
        "section": _section(children=[
            {
                "id": new_block_id(),
                "type": "author_note",
                "variant": "default",
                "props": {},
                "content": {"text": "Author note — add context or disclosure here."},
                "children": [],
            },
        ]),
    },
    {
        "name": "Safety disclaimer",
        "slug": "safety-disclaimer",
        "description": "Standard safety disclaimer.",
        "section": _section(children=[
            {
                "id": new_block_id(),
                "type": "important_note",
                "variant": "default",
                "props": {},
                "content": {
                    "text": "Always follow local guidelines and venue policies. "
                    "Stay aware of your surroundings at events."
                },
                "children": [],
            },
        ]),
    },
]
