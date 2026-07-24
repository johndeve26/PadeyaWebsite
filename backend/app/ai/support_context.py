"""Build and scrub support-ticket context for staff AI assists."""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.context_scrubber import scrub_context, scrub_value
from app.events.models import Event
from app.support.constants import CATEGORIES, CATEGORY_LABELS, PRIORITIES
from app.support.models import SupportCase, SupportMessage
from app.support.service import _require_case_access, can_reply
from app.users.models import User
from app.users.service import user_has_permission

SUPPORT_STUDIO_SAFE_KEYS = frozenset(
    {
        "subject",
        "category",
        "priority",
        "status",
        "requester_context",
        "conversation",
        "related_order_ref",
        "related_event_title",
        "related_merch_title",
        "catalog_categories",
        "catalog_priorities",
        "article_catalog",
        "notes",
    }
)

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s\-().]{7,}\d)\b")
_PAY_REF_RE = re.compile(
    r"(?i)\b(paystack|authorization_code|sk_live|sk_test|pk_live|pk_test|"
    r"card\s*number|cvv|pan)\b[^\n]{0,40}"
)
_QR_RE = re.compile(
    r"(?i)\b(qr[_\s-]?(secret|token|payload)|jti\s*[:=]|device_binding)\b[^\n]{0,80}"
)


def redact_support_text(text: str, *, max_len: int = 6000) -> str:
    """Extra redaction for ticket conversation bodies."""
    out = scrub_value(text, max_len=max_len)
    if out == "[redacted]":
        return out
    out = _EMAIL_RE.sub("[email]", out)
    out = _PHONE_RE.sub("[phone]", out)
    out = _PAY_REF_RE.sub("[payment_ref]", out)
    out = _QR_RE.sub("[ticket_secret]", out)
    return out


def _safe_order_ref(order_id: UUID | None) -> str:
    if order_id is None:
        return ""
    # Short display ref only — not a payment payload
    return f"order…{str(order_id)[-8:]}"


def _related_event_title(db: Session, event_id: UUID | None) -> str:
    if event_id is None:
        return ""
    event = db.get(Event, event_id)
    if event is None:
        return ""
    return (event.title or "")[:160]


def _related_merch_title(db: Session, case: SupportCase) -> str:
    # Best-effort: if subject/body mentions a product we already linked via related ids
    # Prefer not to invent — leave empty unless we can resolve from known product links.
    # No dedicated merch_id on case today; skip private shipping/fulfillment entirely.
    _ = case
    return ""


def catalog_categories_text() -> str:
    return ", ".join(f"{slug} ({CATEGORY_LABELS.get(slug, slug)})" for slug in CATEGORIES)


def catalog_priorities_text() -> str:
    return ", ".join(PRIORITIES)


def build_article_catalog(db: Session, *, category: str, subject: str) -> list[dict]:
    """Deterministic KB candidates — AI may only pick from this list."""
    from app.knowledge_base.service import list_public_articles, suggestions_for_topic

    found: list[dict] = []
    seen: set[str] = set()

    for row in suggestions_for_topic(db, topic=category or "other", limit=8):
        key = str(row.id)
        if key in seen:
            continue
        seen.add(key)
        found.append(
            {
                "id": key,
                "slug": row.slug,
                "title": row.title,
                "path": f"/help/articles/{row.slug}",
            }
        )

    # Keyword pass from subject tokens
    tokens = [t for t in re.split(r"\W+", subject or "") if len(t) >= 4][:4]
    for tok in tokens:
        if len(found) >= 10:
            break
        for row in list_public_articles(db, q=tok, limit=3):
            key = str(row.id)
            if key in seen:
                continue
            seen.add(key)
            found.append(
                {
                    "id": key,
                    "slug": row.slug,
                    "title": row.title,
                    "path": f"/help/articles/{row.slug}",
                }
            )
            if len(found) >= 10:
                break
    return found[:10]


def build_support_ticket_context(
    db: Session,
    *,
    user: User,
    ticket_id: UUID,
    include_internal_notes: bool = False,
) -> tuple[dict[str, str], list[str], list[dict]]:
    """Load ticket server-side; return scrubbed context, redactions, article catalog."""
    if not (
        user_has_permission(user, "ai.use_platform")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="AI permission required")
    if not (
        user_has_permission(user, "admin.support.view")
        or user_has_permission(user, "admin.support.view_all")
        or user_has_permission(user, "support.reply")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Support view permission required")

    case = _require_case_access(db, user, ticket_id)

    # Public conversation only by default (not internal notes)
    messages = list(
        db.scalars(
            select(SupportMessage)
            .where(
                SupportMessage.case_id == case.id,
                SupportMessage.is_internal.is_(False),
            )
            .order_by(SupportMessage.created_at.asc())
            .limit(40)
        ).all()
    )
    convo_parts: list[str] = []
    for m in messages:
        author = "Staff" if m.author_user_id and m.author_user_id != case.requester_user_id else "Requester"
        body = redact_support_text(m.body or "", max_len=1200)
        convo_parts.append(f"{author}: {body}")
    conversation = "\n".join(convo_parts)[:6000]

    # Internal notes only when explicitly allowed and staff has note permission
    notes_blob = ""
    if include_internal_notes and (
        user_has_permission(user, "admin.support.internal_notes")
        or user_has_permission(user, "admin.full_access")
    ):
        # Still do not send raw notes to model in Phase 1 — keep empty for safety
        notes_blob = ""
        _ = include_internal_notes

    articles = build_article_catalog(db, category=case.category, subject=case.subject)
    article_catalog = "; ".join(
        f"{a['slug']}|{a['title']}|{a['id']}" for a in articles
    ) or "none"

    raw = {
        "subject": redact_support_text(case.subject or "", max_len=240),
        "category": case.category or "",
        "priority": case.priority or "normal",
        "status": case.status or "",
        "requester_context": case.requester_context or "",
        "conversation": conversation,
        "related_order_ref": _safe_order_ref(case.related_order_id),
        "related_event_title": _related_event_title(db, case.related_event_id),
        "related_merch_title": _related_merch_title(db, case),
        "catalog_categories": catalog_categories_text(),
        "catalog_priorities": catalog_priorities_text(),
        "article_catalog": article_catalog,
        "notes": notes_blob,
    }
    scrubbed, redactions = scrub_context(raw, allowlist=SUPPORT_STUDIO_SAFE_KEYS)
    # Re-apply conversation redaction after scrub
    if scrubbed.get("conversation"):
        scrubbed["conversation"] = redact_support_text(scrubbed["conversation"])
    return scrubbed, redactions, articles


def assert_support_reply_permission(user: User) -> None:
    if not (
        can_reply(user)
        or user_has_permission(user, "admin.support.reply")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Support reply permission required")
