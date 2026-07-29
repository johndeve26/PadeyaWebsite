"""Authoritative content_document ↔ body synchronization.

Rules
-----
BLOCK_DOCUMENT_MODE (post has a non-legacy content_document):
  - content_document is the single source of truth
  - body and body_html are always derived server-side
  - client-supplied body is ignored on save when content_document is present

LEGACY_MODE (no content_document, or legacy_rich_text-only wrapper):
  - body markdown is authoritative
  - document endpoint may return a legacy wrapper for editing
  - explicit conversion promotes to BLOCK_DOCUMENT_MODE
"""

from __future__ import annotations

from typing import Any

from app.blog.document.conversion import document_has_legacy_only
from app.blog.document.render import document_to_markdown
from app.blog.markdown import estimate_reading_minutes
from app.blog.models import BlogPost

CONTENT_MODE_LEGACY = "legacy"
CONTENT_MODE_BLOCK = "block_document"


def resolve_content_mode(post: BlogPost) -> str:
    doc = getattr(post, "content_document", None)
    if doc is None:
        return CONTENT_MODE_LEGACY
    if document_has_legacy_only(doc):
        return CONTENT_MODE_LEGACY
    return CONTENT_MODE_BLOCK


def is_block_document_mode(post: BlogPost) -> bool:
    return resolve_content_mode(post) == CONTENT_MODE_BLOCK


def derive_body_from_document(doc: dict[str, Any]) -> str:
    return document_to_markdown(doc)


def apply_content_document(
    post: BlogPost,
    doc: dict[str, Any],
    *,
    editor_mode: str | None = None,
    hero_settings: dict[str, Any] | None = None,
) -> None:
    """Persist validated document and derive searchable body fields."""
    post.content_document = doc
    post.content_document_version = int(getattr(post, "content_document_version", None) or 1) + 1
    md = derive_body_from_document(doc)
    post.body = md
    post.reading_time_minutes = estimate_reading_minutes(md)
    if editor_mode is not None:
        post.editor_mode = editor_mode
    if hero_settings is not None:
        post.hero_settings = hero_settings


def apply_autosave_content(
    post: BlogPost,
    *,
    body: str | None,
    content_document: dict[str, Any] | None,
) -> None:
    """Apply autosave fields respecting content authority rules."""
    mode = resolve_content_mode(post)

    if content_document is not None:
        # New or updated document always wins; ignore client body.
        from app.blog.document.validation import validate_document

        doc = validate_document(content_document)
        apply_content_document(post, doc)
        return

    if is_block_document_mode(post):
        # Block post without document in payload: re-derive body from stored document.
        if post.content_document:
            md = derive_body_from_document(post.content_document)
            post.body = md
            post.reading_time_minutes = estimate_reading_minutes(md)
        return

    # Legacy mode: body is authoritative.
    if body is not None:
        post.body = body
        post.reading_time_minutes = estimate_reading_minutes(body)
