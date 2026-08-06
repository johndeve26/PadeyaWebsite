"""Sync knowledge documents from sitemap into FTS chunks."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.assistant.constants import CHUNK_TARGET_CHARS
from app.assistant.knowledge.extract import extract_from_html
from app.assistant.knowledge.sitemap import (
    collect_sitemap_urls,
    fetch_url_text,
    is_allowed_knowledge_url,
    normalize_url,
)
from app.assistant.models import AssistantKnowledgeChunk, AssistantKnowledgeDocument
from app.assistant.schemas import KnowledgeSyncReport
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _sitemap_url() -> str:
    settings = get_settings()
    configured = (getattr(settings, "assistant_knowledge_sitemap_url", "") or "").strip()
    if configured:
        return configured
    base = (getattr(settings, "frontend_url", None) or "http://localhost:3000").rstrip("/")
    return f"{base}/sitemap.xml"


def _content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()


def chunk_text(body: str, *, target_chars: int = CHUNK_TARGET_CHARS) -> list[str]:
    text_in = (body or "").strip()
    if not text_in:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text_in)
    while start < n:
        end = min(start + target_chars, n)
        if end < n:
            # Prefer break on sentence/space
            window = text_in[start:end]
            br = max(window.rfind(". "), window.rfind("\n"), window.rfind(" "))
            if br > target_chars // 3:
                end = start + br + 1
        piece = text_in[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end
    return chunks


def _route_group_for_url(url: str) -> str | None:
    path = urlparse(url).path or "/"
    if path.startswith("/events"):
        return "events"
    if path.startswith("/hosts") or path.startswith("/u/"):
        return "hosts"
    if path.startswith("/help") or path.startswith("/faq") or path.startswith("/support"):
        return "help"
    if path.startswith("/blog") or path.startswith("/resources"):
        return "resources"
    if path.startswith("/shop"):
        return "shop"
    if path.startswith("/memories"):
        return "memories"
    return "marketing"


def _upsert_document(
    db: Session,
    *,
    url: str,
    extracted_title: str,
    description: str,
    body: str,
    report: KnowledgeSyncReport,
) -> None:
    digest = _content_hash(body or extracted_title or url)
    existing = db.scalars(
        select(AssistantKnowledgeDocument).where(
            AssistantKnowledgeDocument.canonical_url == url
        )
    ).first()
    now = datetime.now(UTC)
    if existing and existing.content_hash == digest and existing.status == "active":
        report.documents_unchanged += 1
        return

    if existing is None:
        doc = AssistantKnowledgeDocument(
            source_type="sitemap",
            canonical_url=url,
            title=extracted_title or url,
            description=description or None,
            content_type="text/html",
            route_group=_route_group_for_url(url),
            content_hash=digest,
            indexed_at=now,
            last_modified_at=now,
            status="active",
            fetch_status="ok",
            body_text=body,
            metadata_json={"source": "sitemap"},
        )
        db.add(doc)
        db.flush()
        report.documents_created += 1
    else:
        doc = existing
        doc.title = extracted_title or doc.title
        doc.description = description or doc.description
        doc.content_hash = digest
        doc.indexed_at = now
        doc.last_modified_at = now
        doc.status = "active"
        doc.fetch_status = "ok"
        doc.body_text = body
        doc.route_group = _route_group_for_url(url)
        # Replace chunks
        db.execute(
            delete(AssistantKnowledgeChunk).where(
                AssistantKnowledgeChunk.document_id == doc.id
            )
        )
        report.documents_updated += 1

    pieces = chunk_text(body)
    for idx, piece in enumerate(pieces):
        chunk = AssistantKnowledgeChunk(
            document_id=doc.id,
            chunk_index=idx,
            heading_path=None,
            content=piece,
            token_count=max(1, len(piece.split())),
            metadata_json={"url": url},
        )
        db.add(chunk)
        db.flush()
        # Populate FTS vector in SQL
        db.execute(
            text(
                "UPDATE assistant_knowledge_chunks "
                "SET search_vector = to_tsvector('english', coalesce(content, '')) "
                "WHERE id = :id"
            ),
            {"id": str(chunk.id)},
        )
        report.chunks_upserted += 1


def sync_knowledge(
    db: Session,
    *,
    sitemap_url: str | None = None,
    max_urls: int = 500,
) -> KnowledgeSyncReport:
    started = datetime.now(UTC)
    report = KnowledgeSyncReport(started_at=started)
    settings = get_settings()
    if not bool(getattr(settings, "assistant_knowledge_sync_enabled", False)):
        report.errors.append("assistant_knowledge_sync_enabled is false")
        report.finished_at = datetime.now(UTC)
        return report

    sm_url = sitemap_url or _sitemap_url()
    urls = collect_sitemap_urls(sm_url, max_urls=max_urls)
    report.urls_seen = len(urls)
    seen: set[str] = set()

    for url in urls:
        if not is_allowed_knowledge_url(url):
            continue
        norm = normalize_url(url)
        seen.add(norm)
        try:
            html = fetch_url_text(norm)
            extracted = extract_from_html(html)
            body = extracted.body_text
            if extracted.headings:
                body = "\n".join(extracted.headings) + "\n\n" + body
            _upsert_document(
                db,
                url=norm,
                extracted_title=extracted.title,
                description=extracted.description,
                body=body,
                report=report,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            report.documents_failed += 1
            if len(report.errors) < 20:
                report.errors.append(f"{norm}: {type(exc).__name__}")
            logger.exception("assistant.knowledge_sync_url_failed")

    # Archive missing
    if seen:
        active_docs = db.scalars(
            select(AssistantKnowledgeDocument).where(
                AssistantKnowledgeDocument.status == "active",
                AssistantKnowledgeDocument.source_type == "sitemap",
            )
        ).all()
        for doc in active_docs:
            if doc.canonical_url not in seen:
                doc.status = "archived"
                report.documents_archived += 1
        db.commit()

    report.finished_at = datetime.now(UTC)
    return report


def knowledge_status(db: Session) -> dict[str, Any]:
    settings = get_settings()
    counts = dict(
        db.execute(
            select(
                AssistantKnowledgeDocument.status,
                func.count(),
            ).group_by(AssistantKnowledgeDocument.status)
        ).all()
    )
    chunk_count = db.scalar(select(func.count()).select_from(AssistantKnowledgeChunk)) or 0
    last_indexed = db.scalar(
        select(func.max(AssistantKnowledgeDocument.indexed_at))
    )
    return {
        "enabled": bool(getattr(settings, "assistant_knowledge_sync_enabled", False)),
        "document_count": sum(int(v) for v in counts.values()),
        "active_count": int(counts.get("active", 0)),
        "archived_count": int(counts.get("archived", 0)),
        "failed_count": int(counts.get("failed", 0)),
        "chunk_count": int(chunk_count),
        "last_indexed_at": last_indexed,
        "sitemap_url": _sitemap_url(),
    }
