"""Validate blog content_document structure and security."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException

from app.blog.document.constants import (
    ALIGNMENTS,
    ALLOWED_BLOCK_TYPES,
    ALLOWED_EMBED_PROVIDERS,
    BACKGROUNDS,
    CONTENT_WIDTHS,
    DOCUMENT_VERSION,
    HERO_VARIANTS,
    LAYOUT_CONTAINER_TYPES,
    MAX_BLOCKS,
    MAX_COLUMNS_PER_ROW,
    MAX_DOCUMENT_BYTES,
    MAX_NESTING_DEPTH,
    SAFE_URL_SCHEMES,
    SPACING_PRESETS,
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)
_DANGEROUS_HTML = re.compile(
    r"(<script\b|javascript:|on\w+\s*=|<iframe\b(?![^>]*data-provider=))",
    re.I,
)


class DocumentValidationError(Exception):
    def __init__(self, message: str, *, path: str = "") -> None:
        self.message = message
        self.path = path
        super().__init__(message)


def _check_url(url: str | None, *, field: str) -> None:
    if not url:
        return
    parsed = urlparse(url.strip())
    if parsed.scheme and parsed.scheme.lower() not in SAFE_URL_SCHEMES:
        raise DocumentValidationError(f"Unsafe URL scheme in {field}: {url}")
    if url.strip().lower().startswith("data:"):
        raise DocumentValidationError(f"data: URLs not allowed in {field}")


def _check_rich_html(html: str | None, *, field: str) -> None:
    if not html:
        return
    if _DANGEROUS_HTML.search(html):
        raise DocumentValidationError(f"Unsafe HTML in {field}")


def _validate_settings(settings: Any) -> dict[str, Any]:
    if not isinstance(settings, dict):
        raise DocumentValidationError("settings must be an object")
    out: dict[str, Any] = {}
    cw = settings.get("content_width", "standard")
    if cw not in CONTENT_WIDTHS:
        raise DocumentValidationError(f"Invalid content_width: {cw}")
    out["content_width"] = cw
    for key in ("show_table_of_contents", "sticky_table_of_contents", "reading_progress"):
        val = settings.get(key, key != "sticky_table_of_contents")
        if not isinstance(val, bool):
            raise DocumentValidationError(f"{key} must be boolean")
        out[key] = val
    return out


def _validate_block_props(block_type: str, props: Any) -> dict[str, Any]:
    if props is None:
        props = {}
    if not isinstance(props, dict):
        raise DocumentValidationError("block props must be an object")
    out: dict[str, Any] = {}
    allowed_keys = {
        "content_width",
        "alignment",
        "background",
        "spacing",
        "padding_top",
        "padding_bottom",
        "border_style",
        "image_position",
        "column_ratio",
        "vertical_alignment",
        "mobile_stack_order",
        "anchor_id",
        "include_in_toc",
        "locked",
        "movable_when_locked",
        "visible",
        "variant",
        "label",
        "href",
        "url",
        "alt",
        "caption",
        "focal_x",
        "focal_y",
        "provider",
        "embed_id",
        "event_slug",
        "host_username",
        "level",
        "width",
        "items",
        "rows",
        "question",
        "answer",
        "stat_value",
        "stat_label",
        "sources",
        "text",
        "tone",
    }
    for key, val in props.items():
        if key not in allowed_keys:
            raise DocumentValidationError(f"Unknown prop '{key}' on block type {block_type}")
        out[key] = val
    if "content_width" in out and out["content_width"] not in CONTENT_WIDTHS:
        raise DocumentValidationError(f"Invalid content_width prop: {out['content_width']}")
    if "alignment" in out and out["alignment"] not in ALIGNMENTS:
        raise DocumentValidationError(f"Invalid alignment: {out['alignment']}")
    if "background" in out and out["background"] not in BACKGROUNDS:
        raise DocumentValidationError(f"Invalid background: {out['background']}")
    if "spacing" in out and out["spacing"] not in SPACING_PRESETS:
        raise DocumentValidationError(f"Invalid spacing: {out['spacing']}")
    if "url" in out:
        _check_url(str(out["url"]), field="url")
    if "href" in out:
        _check_url(str(out["href"]), field="href")
    if "provider" in out and out["provider"] not in ALLOWED_EMBED_PROVIDERS:
        raise DocumentValidationError(f"Invalid embed provider: {out['provider']}")
    if "locked" in out and not isinstance(out["locked"], bool):
        raise DocumentValidationError("locked must be boolean")
    return out


def _validate_content(block_type: str, content: Any) -> dict[str, Any]:
    if content is None:
        content = {}
    if not isinstance(content, dict):
        raise DocumentValidationError("block content must be an object")
    out: dict[str, Any] = {}
    if block_type in ("rich_text", "legacy_rich_text"):
        html = content.get("html", "")
        md = content.get("markdown", "")
        if html:
            _check_rich_html(str(html), field="content.html")
            out["html"] = str(html)[:200_000]
        if md:
            out["markdown"] = str(md)[:200_000]
    elif block_type == "heading":
        text = str(content.get("text", ""))[:500]
        level = content.get("level", 2)
        if level not in (2, 3):
            raise DocumentValidationError("heading level must be 2 or 3")
        out = {"text": text, "level": level}
    elif block_type == "image":
        _check_url(content.get("url"), field="image url")
        out = {
            "url": str(content.get("url", ""))[:500],
            "alt": str(content.get("alt", ""))[:500],
            "caption": str(content.get("caption", ""))[:1000],
        }
    elif block_type == "faq":
        items = content.get("items", [])
        if not isinstance(items, list):
            raise DocumentValidationError("faq items must be a list")
        out["items"] = [
            {
                "id": str(it.get("id", uuid.uuid4())),
                "question": str(it.get("question", ""))[:500],
                "answer": str(it.get("answer", ""))[:5000],
            }
            for it in items[:50]
            if isinstance(it, dict)
        ]
    elif block_type == "table":
        headers = content.get("headers", [])
        rows = content.get("rows", [])
        if not isinstance(headers, list) or not isinstance(rows, list):
            raise DocumentValidationError("table headers/rows must be lists")
        out = {
            "headers": [str(h)[:200] for h in headers[:20]],
            "rows": [[str(c)[:2000] for c in row[:20]] for row in rows[:100] if isinstance(row, list)],
        }
    elif block_type == "cta":
        _check_url(content.get("href"), field="cta href")
        out = {
            "label": str(content.get("label", ""))[:120],
            "href": str(content.get("href", ""))[:500],
        }
    elif block_type == "quote":
        out = {
            "text": str(content.get("text", ""))[:5000],
            "attribution": str(content.get("attribution", ""))[:200],
        }
    elif block_type == "list":
        items = content.get("items", [])
        ordered = bool(content.get("ordered", False))
        if not isinstance(items, list):
            raise DocumentValidationError("list items must be a list")
        out = {"items": [str(i)[:2000] for i in items[:100]], "ordered": ordered}
    elif block_type in EDITORIAL_TONE_BLOCKS:
        out = {"text": str(content.get("text", ""))[:10000]}
    elif block_type == "table_of_contents":
        out = {"include_h3": bool(content.get("include_h3", True))}
    elif block_type in ("event_promotion", "featured_event"):
        out = {"event_slug": str(content.get("event_slug", ""))[:120]}
    elif block_type in ("host_promotion", "featured_host"):
        out = {"host_username": str(content.get("host_username", ""))[:120]}
    elif block_type == "video_embed":
        provider = content.get("provider", "")
        if provider and provider not in ALLOWED_EMBED_PROVIDERS:
            raise DocumentValidationError(f"Invalid embed provider: {provider}")
        out = {
            "provider": str(provider)[:32],
            "embed_id": str(content.get("embed_id", ""))[:120],
        }
    elif block_type == "image_gallery":
        images = content.get("images", [])
        if not isinstance(images, list):
            raise DocumentValidationError("gallery images must be a list")
        out["images"] = []
        for img in images[:20]:
            if isinstance(img, dict):
                _check_url(img.get("url"), field="gallery url")
                out["images"].append(
                    {
                        "url": str(img.get("url", ""))[:500],
                        "alt": str(img.get("alt", ""))[:500],
                        "caption": str(img.get("caption", ""))[:500],
                    }
                )
    else:
        # Layout containers and minor blocks — store limited text if present
        if "text" in content:
            out["text"] = str(content["text"])[:10000]
    return out


EDITORIAL_TONE_BLOCKS = frozenset(
    {
        "key_takeaway",
        "important_note",
        "warning",
        "tip",
        "statistic",
        "pull_quote",
        "sources",
        "author_note",
    }
)


def _validate_block(
    block: Any,
    *,
    depth: int,
    seen_ids: set[str],
    block_count: list[int],
) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise DocumentValidationError("Each block must be an object")
    block_count[0] += 1
    if block_count[0] > MAX_BLOCKS:
        raise DocumentValidationError(f"Document exceeds {MAX_BLOCKS} blocks")
    if depth > MAX_NESTING_DEPTH:
        raise DocumentValidationError(f"Nesting exceeds max depth {MAX_NESTING_DEPTH}")

    block_id = block.get("id")
    if not block_id or not isinstance(block_id, str):
        raise DocumentValidationError("Each block must have a string id")
    if not _UUID_RE.match(block_id) and len(block_id) < 8:
        raise DocumentValidationError(f"Invalid block id: {block_id}")
    if block_id in seen_ids:
        raise DocumentValidationError(f"Duplicate block id: {block_id}")
    seen_ids.add(block_id)

    block_type = block.get("type")
    if block_type not in ALLOWED_BLOCK_TYPES:
        raise DocumentValidationError(f"Unknown block type: {block_type}")

    variant = block.get("variant", "default")
    if variant is not None and not isinstance(variant, str):
        raise DocumentValidationError("variant must be a string")

    props = _validate_block_props(block_type, block.get("props"))
    content = _validate_content(block_type, block.get("content"))

    children_raw = block.get("children", [])
    if children_raw is None:
        children_raw = []
    if not isinstance(children_raw, list):
        raise DocumentValidationError("children must be a list")

    if block_type in ("two_column_row", "three_column_row", "row", "image_text", "text_image"):
        max_cols = 2 if block_type in ("two_column_row", "image_text", "text_image") else (
            3 if block_type == "three_column_row" else MAX_COLUMNS_PER_ROW
        )
        if len(children_raw) > max_cols:
            raise DocumentValidationError(
                f"Block {block_type} allows at most {max_cols} columns"
            )

    children = [
        _validate_block(
            child, depth=depth + 1, seen_ids=seen_ids, block_count=block_count
        )
        for child in children_raw
    ]

    if block_type in LAYOUT_CONTAINER_TYPES and block_type not in (
        "hero",
        "divider",
        "spacer",
    ):
        # Non-container blocks should not appear as direct children of rows without columns
        pass

    return {
        "id": block_id,
        "type": block_type,
        "variant": variant or "default",
        "props": props,
        "content": content,
        "children": children,
    }


def validate_document(doc: Any, *, strict: bool = True) -> dict[str, Any]:
    """Validate and normalize a content document. Raises DocumentValidationError."""
    if doc is None:
        raise DocumentValidationError("Document is required")
    if not isinstance(doc, dict):
        raise DocumentValidationError("Document must be an object")

    raw_bytes = len(json.dumps(doc, default=str))
    if raw_bytes > MAX_DOCUMENT_BYTES:
        raise DocumentValidationError(f"Document exceeds {MAX_DOCUMENT_BYTES} bytes")

    version = doc.get("version", DOCUMENT_VERSION)
    if version != DOCUMENT_VERSION:
        if strict:
            raise DocumentValidationError(f"Unsupported document version: {version}")

    settings = _validate_settings(doc.get("settings", {}))
    blocks_raw = doc.get("blocks", [])
    if not isinstance(blocks_raw, list):
        raise DocumentValidationError("blocks must be a list")

    seen_ids: set[str] = set()
    block_count = [0]
    blocks = [
        _validate_block(b, depth=0, seen_ids=seen_ids, block_count=block_count)
        for b in blocks_raw
    ]

    return {
        "version": DOCUMENT_VERSION,
        "settings": settings,
        "blocks": blocks,
    }


def validate_document_or_http(doc: Any) -> dict[str, Any]:
    try:
        return validate_document(doc)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc


def validate_hero_settings(settings: Any) -> dict[str, Any] | None:
    if settings is None:
        return None
    if not isinstance(settings, dict):
        raise DocumentValidationError("hero_settings must be an object")
    variant = settings.get("variant", "standard")
    if variant not in HERO_VARIANTS:
        raise DocumentValidationError(f"Invalid hero variant: {variant}")
    out: dict[str, Any] = {"variant": variant}
    for key in ("focal_x", "focal_y"):
        if key in settings:
            val = float(settings[key])
            if not 0 <= val <= 1:
                raise DocumentValidationError(f"{key} must be between 0 and 1")
            out[key] = val
    if "show_reading_time" in settings:
        out["show_reading_time"] = bool(settings["show_reading_time"])
    if "show_author" in settings:
        out["show_author"] = bool(settings["show_author"])
    if "show_date" in settings:
        out["show_date"] = bool(settings["show_date"])
    return out
