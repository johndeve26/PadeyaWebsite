"""Convert legacy markdown body to block document."""

from __future__ import annotations

import uuid
from typing import Any

from app.blog.document.constants import DOCUMENT_VERSION


def new_block_id() -> str:
    return str(uuid.uuid4())


def blank_document() -> dict[str, Any]:
    return {
        "version": DOCUMENT_VERSION,
        "settings": {
            "content_width": "standard",
            "show_table_of_contents": True,
            "sticky_table_of_contents": False,
            "reading_progress": True,
        },
        "blocks": [
            {
                "id": new_block_id(),
                "type": "rich_text",
                "variant": "default",
                "props": {},
                "content": {"markdown": "", "html": ""},
                "children": [],
            }
        ],
    }


def wrap_legacy_body(body: str) -> dict[str, Any]:
    """Wrap existing markdown body in a legacy_rich_text block (strategy A)."""
    doc = blank_document()
    doc["blocks"] = [
        {
            "id": new_block_id(),
            "type": "legacy_rich_text",
            "variant": "default",
            "props": {"locked": False},
            "content": {"markdown": body or "", "html": ""},
            "children": [],
        }
    ]
    return doc


def _split_markdown_sections(body: str) -> list[tuple[str, str]]:
    """Split markdown on ## headings into (heading, content) pairs."""
    import re

    parts = re.split(r"(?=^## )", body.strip(), flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        first = lines[0]
        if first.startswith("## "):
            heading = first[3:].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            sections.append((heading, content))
        else:
            sections.append(("", part))
    return sections


def convert_legacy_markdown(body: str) -> dict[str, Any]:
    """Convert markdown body to structured block document."""
    if not (body or "").strip():
        return blank_document()

    sections = _split_markdown_sections(body)
    if not sections:
        return wrap_legacy_body(body)

    blocks: list[dict[str, Any]] = []
    for heading, content in sections:
        section_id = new_block_id()
        children: list[dict[str, Any]] = []
        if heading:
            children.append(
                {
                    "id": new_block_id(),
                    "type": "heading",
                    "variant": "default",
                    "props": {"include_in_toc": True},
                    "content": {"text": heading, "level": 2},
                    "children": [],
                }
            )
        if content:
            # Detect special blocks
            if content.strip().startswith("::cta{"):
                import re

                m = re.search(
                    r'::cta\{label="([^"]*?)"(?:;\s*href="([^"]*?)")?\}',
                    content,
                )
                if m:
                    children.append(
                        {
                            "id": new_block_id(),
                            "type": "cta",
                            "variant": "default",
                            "props": {},
                            "content": {
                                "label": m.group(1),
                                "href": m.group(2) or "/events",
                            },
                            "children": [],
                        }
                    )
                    continue
            children.append(
                {
                    "id": new_block_id(),
                    "type": "rich_text",
                    "variant": "default",
                    "props": {},
                    "content": {"markdown": content, "html": ""},
                    "children": [],
                }
            )
        if children:
            blocks.append(
                {
                    "id": section_id,
                    "type": "standard_section",
                    "variant": "default",
                    "props": {"spacing": "normal", "content_width": "standard"},
                    "content": {},
                    "children": children,
                }
            )

    if not blocks:
        return wrap_legacy_body(body)

    return {
        "version": DOCUMENT_VERSION,
        "settings": {
            "content_width": "standard",
            "show_table_of_contents": True,
            "sticky_table_of_contents": False,
            "reading_progress": True,
        },
        "blocks": blocks,
    }


def document_has_legacy_only(doc: dict[str, Any] | None) -> bool:
    if not doc:
        return False
    blocks = doc.get("blocks") or []
    return len(blocks) == 1 and blocks[0].get("type") == "legacy_rich_text"
