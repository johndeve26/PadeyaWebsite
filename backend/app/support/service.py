"""Support ticket lifecycle — archive preferred; never hard-delete tickets."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.hosts.models import Host
from app.support.constants import (
    ALLOWED_ATTACHMENT_TYPES,
    CATEGORIES,
    MAX_ATTACHMENT_BYTES,
    PRIORITIES,
    REQUESTER_CONTEXTS,
    STATUSES,
)
from app.support.models import (
    SupportCase,
    SupportDeflectionEvent,
    SupportInternalNote,
    SupportMessage,
    SupportSettings,
    SupportTicketAssignment,
    SupportTicketAttachment,
    SupportTicketEvent,
)
from app.support import notifications as support_notify
from app.support.sanitize import sanitize_support_text
from app.support.schemas import (
    SupportAssignRequest,
    SupportCaseCreate,
    SupportCategoryUpdate,
    SupportDeflectionEventCreate,
    SupportDeflectionMeta,
    SupportEscalateRequest,
    SupportInternalNoteCreate,
    SupportMessageCreate,
    SupportPriorityUpdate,
    SupportPublicCreate,
    SupportPublicReply,
    SupportSettingsUpdate,
    SupportStatusUpdate,
)
from app.users.models import User
from app.users.service import user_has_permission, user_has_role

OPEN_STATUSES = {"open", "pending", "waiting_on_user", "escalated", "in_progress"}


def _perm(user: User, *codes: str) -> bool:
    if user_has_permission(user, "admin.full_access") or user_has_role(
        user, "super_admin"
    ):
        return True
    return any(user_has_permission(user, c) for c in codes)


def is_support_staff(user: User) -> bool:
    return _perm(
        user,
        "admin.support.view",
        "admin.support.view_all",
        "support.reply",
    ) or user_has_role(user, "support_agent", "finance_admin")


def can_view_all(user: User) -> bool:
    return _perm(user, "admin.support.view_all", "admin.support.view", "support.reply")


def can_reply(user: User) -> bool:
    return _perm(user, "admin.support.reply", "support.reply")


def can_assign(user: User) -> bool:
    return _perm(user, "admin.support.assign", "support.assign", "support.reply")


def can_resolve(user: User) -> bool:
    return _perm(user, "admin.support.resolve", "support.resolve", "support.reply")


def can_close(user: User) -> bool:
    return _perm(user, "admin.support.close", "admin.support.resolve", "support.reply")


def can_internal_notes(user: User) -> bool:
    return _perm(
        user, "admin.support.internal_notes", "support.reply", "admin.support.reply"
    )


def can_manage_settings(user: User) -> bool:
    return _perm(user, "admin.support.manage_settings")


def can_delete_attachment(user: User) -> bool:
    return _perm(user, "admin.support.delete_attachment", "admin.support.view_all")


def _case_number() -> str:
    return f"SUP-{secrets.token_hex(4).upper()}"


def _public_token() -> str:
    return secrets.token_urlsafe(24)


def _user_name(db: Session, user_id: UUID | None) -> str | None:
    if not user_id:
        return None
    user = db.get(User, user_id)
    return user.full_name if user else None


def _normalize_category(raw: str) -> str:
    cat = raw.strip().lower().replace(" ", "_").replace("/", "_")
    aliases = {
        "account": "account_login",
        "login": "account_login",
        "tickets": "tickets_orders",
        "orders": "tickets_orders",
        "payments": "payments_refunds",
        "refunds": "payments_refunds",
        "event": "event_issue",
        "host": "host_issue",
        "abuse": "messaging_abuse",
        "messaging": "messaging_abuse",
        "tech": "technical",
        "technical_issue": "technical",
    }
    cat = aliases.get(cat, cat)
    if cat not in CATEGORIES:
        # Allow legacy free-text categories used by older clients
        if len(cat) < 2:
            raise HTTPException(status_code=400, detail="Invalid category")
    return cat


def _normalize_priority(raw: str | None) -> str:
    p = (raw or "normal").strip().lower()
    if p not in PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")
    return p


def _normalize_status(raw: str) -> str:
    s = raw.strip().lower()
    if s == "in_progress":
        s = "pending"
    if s not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    return s


def _record_event(
    db: Session,
    *,
    case: SupportCase,
    actor_user_id: UUID | None,
    event_type: str,
    summary: str,
    is_public: bool = True,
    meta: dict | None = None,
) -> None:
    db.add(
        SupportTicketEvent(
            case_id=case.id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            summary=summary[:400],
            meta_json=json.dumps(meta) if meta else None,
            is_public=is_public,
        )
    )


def serialize_case(
    db: Session, case: SupportCase, *, include_internal: bool
) -> dict:
    messages = []
    for m in case.messages or []:
        if m.is_internal and not include_internal:
            continue
        messages.append(
            {
                "id": m.id,
                "case_id": m.case_id,
                "author_user_id": m.author_user_id,
                "author_name": m.author_label
                or _user_name(db, m.author_user_id),
                "body": m.body,
                "is_internal": m.is_internal,
                "created_at": m.created_at,
            }
        )
    notes = []
    if include_internal:
        for n in case.internal_notes or []:
            notes.append(
                {
                    "id": n.id,
                    "case_id": n.case_id,
                    "author_user_id": n.author_user_id,
                    "author_name": _user_name(db, n.author_user_id),
                    "body": n.body,
                    "created_at": n.created_at,
                }
            )
    attachments = []
    for a in case.attachments or []:
        if a.deleted_at is not None:
            continue
        if a.is_internal and not include_internal:
            continue
        attachments.append(
            {
                "id": a.id,
                "case_id": a.case_id,
                "filename": a.filename,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
                "is_internal": a.is_internal,
                "created_at": a.created_at,
            }
        )
    events = []
    for e in case.events or []:
        if not e.is_public and not include_internal:
            continue
        events.append(
            {
                "id": e.id,
                "case_id": e.case_id,
                "event_type": e.event_type,
                "summary": e.summary,
                "is_public": e.is_public,
                "created_at": e.created_at,
                "actor_user_id": e.actor_user_id,
            }
        )
    return {
        "id": case.id,
        "case_number": case.case_number,
        "ticket_number": case.case_number,
        "requester_user_id": case.requester_user_id,
        "requester_email": case.requester_email,
        "requester_name": case.requester_name,
        "requester_context": case.requester_context,
        "assignee_user_id": case.assignee_user_id,
        "subject": case.subject,
        "category": case.category,
        "status": "pending" if case.status == "in_progress" else case.status,
        "priority": case.priority,
        "related_order_id": case.related_order_id,
        "related_event_id": case.related_event_id,
        "related_host_id": case.related_host_id,
        "escalation_level": case.escalation_level,
        "help_suggestions_shown": bool(
            getattr(case, "help_suggestions_shown", False)
        ),
        "deflection_meta": (
            getattr(case, "deflection_meta", None) if include_internal else None
        ),
        "resolved_at": case.resolved_at,
        "closed_at": case.closed_at,
        "archived_at": case.archived_at,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "messages": messages,
        "internal_notes": notes if include_internal else [],
        "attachments": attachments,
        "events": events,
        "public_token": case.public_token if include_internal else None,
    }


def _load_case(db: Session, case_id: UUID) -> SupportCase | None:
    return db.scalar(
        select(SupportCase)
        .where(SupportCase.id == case_id)
        .options(
            selectinload(SupportCase.messages),
            selectinload(SupportCase.internal_notes),
            selectinload(SupportCase.attachments),
            selectinload(SupportCase.events),
        )
    )


def _host_ids_for_user(db: Session, user: User) -> set[UUID]:
    rows = db.scalars(select(Host.id).where(Host.user_id == user.id)).all()
    return set(rows)


def _can_access_case(db: Session, user: User, case: SupportCase) -> bool:
    if is_support_staff(user) and can_view_all(user):
        return True
    if case.requester_user_id and case.requester_user_id == user.id:
        return True
    if case.related_host_id and case.related_host_id in _host_ids_for_user(db, user):
        return True
    return False


def _require_case_access(db: Session, user: User, case_id: UUID) -> SupportCase:
    case = _load_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    if not _can_access_case(db, user, case):
        raise HTTPException(status_code=403, detail="Not allowed")
    return case


def _infer_context(user: User, explicit: str | None) -> str:
    if explicit and explicit in REQUESTER_CONTEXTS:
        return explicit
    if user_has_role(user, "support_agent", "super_admin", "finance_admin") or _perm(
        user, "admin.full_access"
    ):
        return "admin"
    if user_has_role(user, "host"):
        return "host"
    return "fan"


def _apply_deflection(case: SupportCase, deflection: SupportDeflectionMeta | None) -> None:
    if deflection is None:
        return
    meta = {
        "topic": deflection.topic,
        "suggested_article_ids": list(deflection.suggested_article_ids or [])[:20],
        "suggested_article_slugs": list(deflection.suggested_article_slugs or [])[:20],
        "articles_clicked": list(deflection.articles_clicked or [])[:20],
        "referrer": (deflection.referrer or "")[:500] or None,
        "session_key": (deflection.session_key or "")[:64] or None,
    }
    case.help_suggestions_shown = bool(deflection.help_suggestions_shown)
    case.deflection_meta = meta


DEFLECTION_EVENT_TYPES = frozenset(
    {
        "support_topic_selected",
        "support_help_articles_shown",
        "support_article_clicked",
        "support_issue_solved_without_ticket",
        "support_ticket_started_after_help",
        "support_ticket_created",
    }
)


def record_deflection_event(
    db: Session,
    *,
    payload: SupportDeflectionEventCreate,
    user_id: UUID | None = None,
) -> dict:
    event_type = (payload.event_type or "").strip().lower()
    if event_type not in DEFLECTION_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid deflection event type")
    topic = None
    if payload.topic:
        try:
            topic = _normalize_category(payload.topic)
        except HTTPException:
            topic = payload.topic.strip()[:64]
    safe_meta = None
    if payload.meta and isinstance(payload.meta, dict):
        safe_meta = {
            str(k)[:40]: str(v)[:200] if not isinstance(v, (int, float, bool)) else v
            for k, v in list(payload.meta.items())[:20]
        }
    row = SupportDeflectionEvent(
        event_type=event_type,
        topic=topic,
        session_key=(payload.session_key or "")[:64] or None,
        user_id=user_id,
        article_id=payload.article_id,
        article_slug=(payload.article_slug or "")[:200] or None,
        meta=safe_meta,
    )
    db.add(row)
    db.commit()
    return {"ok": True, "event_type": event_type}


def create_case(db: Session, *, user: User, payload: SupportCaseCreate) -> dict:
    body = sanitize_support_text(payload.body)
    if len(body) < 5:
        raise HTTPException(status_code=400, detail="Message too short")
    case = SupportCase(
        case_number=_case_number(),
        requester_user_id=user.id,
        requester_email=user.email,
        requester_name=user.full_name,
        requester_context=_infer_context(user, payload.requester_context),
        subject=sanitize_support_text(payload.subject, max_len=200),
        category=_normalize_category(payload.category),
        status="open",
        priority=_normalize_priority(payload.priority),
        related_order_id=payload.related_order_id,
        related_event_id=payload.related_event_id,
        related_host_id=payload.related_host_id,
        public_token=_public_token(),
    )
    _apply_deflection(case, payload.deflection)
    db.add(case)
    db.flush()
    db.add(
        SupportMessage(
            case_id=case.id,
            author_user_id=user.id,
            body=body,
            is_internal=False,
        )
    )
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="created",
        summary="Ticket created",
    )
    if case.help_suggestions_shown:
        _record_event(
            db,
            case=case,
            actor_user_id=user.id,
            event_type="help_deflection",
            summary="Opened after Help suggestions",
            is_public=False,
            meta=case.deflection_meta,
        )
        db.add(
            SupportDeflectionEvent(
                event_type="support_ticket_created",
                topic=case.category,
                session_key=(case.deflection_meta or {}).get("session_key"),
                user_id=user.id,
                case_id=case.id,
                meta=case.deflection_meta,
            )
        )
    write_audit_log(
        db,
        action="support.case_create",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"case_number": case.case_number, "category": case.category},
    )
    support_notify.notify_ticket_created(db, case)
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=False)  # type: ignore[arg-type]


def create_public_ticket(db: Session, *, payload: SupportPublicCreate) -> dict:
    if (payload.website or "").strip():
        # Honeypot tripped — pretend success without storing
        now = datetime.now(UTC)
        return {
            "id": uuid.uuid4(),
            "case_number": "SUP-OK",
            "ticket_number": "SUP-OK",
            "requester_user_id": None,
            "requester_email": str(payload.requester_email).lower().strip(),
            "requester_name": payload.requester_name,
            "requester_context": "visitor",
            "assignee_user_id": None,
            "status": "open",
            "subject": sanitize_support_text(payload.subject, max_len=200),
            "category": _normalize_category(payload.category),
            "priority": "normal",
            "related_order_id": None,
            "related_event_id": None,
            "related_host_id": None,
            "escalation_level": None,
            "help_suggestions_shown": False,
            "deflection_meta": None,
            "resolved_at": None,
            "closed_at": None,
            "archived_at": None,
            "messages": [],
            "internal_notes": [],
            "attachments": [],
            "events": [],
            "created_at": now,
            "updated_at": now,
            "public_token": None,
        }
    settings = get_settings_dict(db)
    if not settings.get("public_form_enabled", True):
        raise HTTPException(status_code=403, detail="Public support form is disabled")
    body = sanitize_support_text(payload.body)
    case = SupportCase(
        case_number=_case_number(),
        requester_user_id=None,
        requester_email=str(payload.requester_email).lower().strip(),
        requester_name=sanitize_support_text(payload.requester_name, max_len=160),
        requester_context="visitor",
        subject=sanitize_support_text(payload.subject, max_len=200),
        category=_normalize_category(payload.category),
        status="open",
        priority=_normalize_priority(payload.priority or settings.get("default_priority")),
        public_token=_public_token(),
    )
    _apply_deflection(case, payload.deflection)
    db.add(case)
    db.flush()
    db.add(
        SupportMessage(
            case_id=case.id,
            author_user_id=None,
            author_label=case.requester_name,
            body=body,
            is_internal=False,
        )
    )
    _record_event(
        db,
        case=case,
        actor_user_id=None,
        event_type="created",
        summary="Public ticket created",
    )
    if case.help_suggestions_shown:
        _record_event(
            db,
            case=case,
            actor_user_id=None,
            event_type="help_deflection",
            summary="Opened after Help suggestions",
            is_public=False,
            meta=case.deflection_meta,
        )
        db.add(
            SupportDeflectionEvent(
                event_type="support_ticket_created",
                topic=case.category,
                session_key=(case.deflection_meta or {}).get("session_key"),
                user_id=None,
                case_id=case.id,
                meta=case.deflection_meta,
            )
        )
    write_audit_log(
        db,
        action="support.case_create_public",
        actor_user_id=None,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"case_number": case.case_number, "email": case.requester_email},
    )
    support_notify.notify_ticket_created(db, case)
    db.commit()
    loaded = _load_case(db, case.id)
    data = serialize_case(db, loaded, include_internal=False)  # type: ignore[arg-type]
    data["public_token"] = case.public_token
    return data


def list_my_cases(db: Session, user: User) -> list[dict]:
    host_ids = _host_ids_for_user(db, user)
    filters = [SupportCase.requester_user_id == user.id]
    if host_ids:
        filters.append(SupportCase.related_host_id.in_(host_ids))
    rows = db.scalars(
        select(SupportCase)
        .where(SupportCase.archived_at.is_(None), or_(*filters))
        .order_by(SupportCase.created_at.desc())
        .options(
            selectinload(SupportCase.messages),
            selectinload(SupportCase.internal_notes),
            selectinload(SupportCase.attachments),
            selectinload(SupportCase.events),
        )
    ).all()
    return [serialize_case(db, c, include_internal=False) for c in rows]


def list_staff_cases(
    db: Session,
    user: User,
    *,
    status_filter: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    requester_context: str | None = None,
    assigned_to: UUID | None = None,
    q: str | None = None,
) -> list[dict]:
    if not is_support_staff(user):
        raise HTTPException(status_code=403, detail="Support staff only")
    query = select(SupportCase).where(SupportCase.archived_at.is_(None))
    if status_filter:
        st = _normalize_status(status_filter)
        if st == "pending":
            query = query.where(SupportCase.status.in_(["pending", "in_progress"]))
        else:
            query = query.where(SupportCase.status == st)
    if priority:
        query = query.where(SupportCase.priority == _normalize_priority(priority))
    if category:
        query = query.where(SupportCase.category == _normalize_category(category))
    if requester_context:
        query = query.where(SupportCase.requester_context == requester_context)
    if assigned_to:
        query = query.where(SupportCase.assignee_user_id == assigned_to)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            or_(
                SupportCase.case_number.ilike(like),
                SupportCase.subject.ilike(like),
                SupportCase.requester_email.ilike(like),
                SupportCase.requester_name.ilike(like),
            )
        )
    # Finance-scoped: payments/refunds only if they lack view_all but have finance role
    if (
        user_has_role(user, "finance_admin")
        and not _perm(user, "admin.support.view_all", "admin.full_access")
        and not user_has_role(user, "support_agent", "super_admin")
    ):
        query = query.where(SupportCase.category == "payments_refunds")

    rows = db.scalars(
        query.order_by(SupportCase.created_at.desc()).options(
            selectinload(SupportCase.messages),
            selectinload(SupportCase.internal_notes),
            selectinload(SupportCase.attachments),
            selectinload(SupportCase.events),
        )
    ).all()
    return [serialize_case(db, c, include_internal=True) for c in rows]


def get_case(db: Session, *, user: User, case_id: UUID) -> dict:
    case = _require_case_access(db, user, case_id)
    return serialize_case(db, case, include_internal=is_support_staff(user))


def _load_case_by_number(db: Session, ticket_number: str) -> SupportCase | None:
    return db.scalar(
        select(SupportCase)
        .where(SupportCase.case_number == ticket_number.upper().strip())
        .options(
            selectinload(SupportCase.messages),
            selectinload(SupportCase.internal_notes),
            selectinload(SupportCase.attachments),
            selectinload(SupportCase.events),
        )
    )


def _assert_public_ticket_access(
    case: SupportCase, *, email: str | None, token: str | None
) -> None:
    email_ok = (
        email
        and case.requester_email
        and email.lower().strip() == case.requester_email.lower()
    )
    token_ok = (
        token
        and case.public_token
        and secrets.compare_digest(token, case.public_token)
    )
    if not email_ok and not token_ok:
        raise HTTPException(status_code=403, detail="Email or tracking token required")


def get_case_by_number_public(
    db: Session, *, ticket_number: str, email: str | None, token: str | None
) -> dict:
    case = _load_case_by_number(db, ticket_number)
    if case is None:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    _assert_public_ticket_access(case, email=email, token=token)
    return serialize_case(db, case, include_internal=False)


def add_public_message(
    db: Session, *, ticket_number: str, payload: SupportPublicReply
) -> dict:
    """Requester follow-up via public track page (email and/or tracking token)."""
    case = _load_case_by_number(db, ticket_number)
    if case is None:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    _assert_public_ticket_access(
        case, email=payload.email, token=payload.token
    )
    if case.status in {"closed", "archived"} or case.archived_at is not None:
        raise HTTPException(status_code=400, detail="Ticket is closed")
    body = sanitize_support_text(payload.body)
    if len(body) < 1:
        raise HTTPException(status_code=400, detail="Empty message")
    db.add(
        SupportMessage(
            case_id=case.id,
            author_user_id=case.requester_user_id,
            author_label=(
                None
                if case.requester_user_id
                else (case.requester_name or "Requester")
            ),
            body=body,
            is_internal=False,
        )
    )
    if case.status == "waiting_on_user":
        case.status = "pending"
    _record_event(
        db,
        case=case,
        actor_user_id=case.requester_user_id,
        event_type="reply",
        summary="Public reply added",
    )
    write_audit_log(
        db,
        action="support.message_public",
        actor_user_id=case.requester_user_id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"case_number": case.case_number},
    )
    support_notify.notify_user_reply_to_assignee(db, case)
    db.commit()
    return serialize_case(
        db, _load_case(db, case.id), include_internal=False  # type: ignore[arg-type]
    )


def add_message(
    db: Session, *, user: User, case_id: UUID, payload: SupportMessageCreate
) -> dict:
    case = _require_case_access(db, user, case_id)
    if case.status in {"closed", "archived"} or case.archived_at is not None:
        raise HTTPException(status_code=400, detail="Ticket is closed")
    staff = is_support_staff(user)
    if staff and not can_reply(user) and case.requester_user_id != user.id:
        raise HTTPException(status_code=403, detail="Reply permission required")
    body = sanitize_support_text(payload.body)
    if len(body) < 1:
        raise HTTPException(status_code=400, detail="Empty message")
    db.add(
        SupportMessage(
            case_id=case.id,
            author_user_id=user.id,
            body=body,
            is_internal=False,
        )
    )
    if staff and case.requester_user_id != user.id:
        if case.status in {"open", "pending", "escalated"}:
            case.status = "waiting_on_user"
        support_notify.notify_staff_reply(db, case)
    else:
        if case.status == "waiting_on_user":
            case.status = "pending"
        support_notify.notify_user_reply_to_assignee(db, case)
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="reply",
        summary="Reply added",
    )
    write_audit_log(
        db,
        action="support.message",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
    )
    db.commit()
    return serialize_case(
        db, _load_case(db, case.id), include_internal=staff  # type: ignore[arg-type]
    )


def add_internal_note(
    db: Session, *, user: User, case_id: UUID, payload: SupportInternalNoteCreate
) -> dict:
    if not can_internal_notes(user):
        raise HTTPException(status_code=403, detail="Internal notes permission required")
    case = _require_case_access(db, user, case_id)
    body = sanitize_support_text(payload.body)
    db.add(
        SupportInternalNote(
            case_id=case.id,
            author_user_id=user.id,
            body=body,
        )
    )
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="internal_note",
        summary="Internal note added",
        is_public=False,
    )
    write_audit_log(
        db,
        action="support.internal_note",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
    )
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def assign_case(
    db: Session, *, user: User, case_id: UUID, payload: SupportAssignRequest
) -> dict:
    if not can_assign(user):
        raise HTTPException(status_code=403, detail="Assign permission required")
    case = _require_case_access(db, user, case_id)
    case.assignee_user_id = payload.assignee_user_id
    if case.status == "open":
        case.status = "pending"
    db.add(
        SupportTicketAssignment(
            case_id=case.id,
            assignee_user_id=payload.assignee_user_id,
            assigned_by_user_id=user.id,
        )
    )
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="assign",
        summary="Assignment updated",
        is_public=False,
        meta={
            "assignee_user_id": str(payload.assignee_user_id)
            if payload.assignee_user_id
            else None
        },
    )
    write_audit_log(
        db,
        action="support.assign",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={
            "assignee_user_id": str(payload.assignee_user_id)
            if payload.assignee_user_id
            else None
        },
    )
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def escalate_case(
    db: Session, *, user: User, case_id: UUID, payload: SupportEscalateRequest
) -> dict:
    if not can_assign(user) and not can_reply(user):
        raise HTTPException(status_code=403, detail="Escalate permission required")
    case = _require_case_access(db, user, case_id)
    case.status = "escalated"
    case.escalation_level = payload.escalation_level.strip()
    if payload.note:
        db.add(
            SupportInternalNote(
                case_id=case.id,
                author_user_id=user.id,
                body=f"[Escalation] {sanitize_support_text(payload.note, max_len=2000)}",
            )
        )
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="escalate",
        summary=f"Escalated to {case.escalation_level}",
    )
    write_audit_log(
        db,
        action="support.escalate",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"level": case.escalation_level},
    )
    support_notify.notify_status_change(db, case, status="escalated")
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def resolve_case(db: Session, *, user: User, case_id: UUID) -> dict:
    if not can_resolve(user):
        raise HTTPException(status_code=403, detail="Resolve permission required")
    case = _require_case_access(db, user, case_id)
    case.status = "resolved"
    case.resolved_at = datetime.now(UTC)
    _record_event(
        db, case=case, actor_user_id=user.id, event_type="resolve", summary="Resolved"
    )
    write_audit_log(
        db,
        action="support.resolve",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
    )
    support_notify.notify_status_change(db, case, status="resolved")
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def close_case(db: Session, *, user: User, case_id: UUID) -> dict:
    case = _require_case_access(db, user, case_id)
    staff = is_support_staff(user)
    if case.requester_user_id != user.id and not (staff and can_close(user)):
        raise HTTPException(status_code=403, detail="Not allowed")
    case.status = "closed"
    case.closed_at = datetime.now(UTC)
    _record_event(
        db, case=case, actor_user_id=user.id, event_type="close", summary="Closed"
    )
    write_audit_log(
        db,
        action="support.close",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
    )
    support_notify.notify_status_change(db, case, status="closed")
    db.commit()
    return serialize_case(
        db,
        _load_case(db, case.id),  # type: ignore[arg-type]
        include_internal=staff,
    )


def reopen_case(db: Session, *, user: User, case_id: UUID) -> dict:
    if not can_resolve(user):
        raise HTTPException(status_code=403, detail="Reopen permission required")
    case = _require_case_access(db, user, case_id)
    case.status = "open"
    case.resolved_at = None
    case.closed_at = None
    _record_event(
        db, case=case, actor_user_id=user.id, event_type="reopen", summary="Reopened"
    )
    write_audit_log(
        db,
        action="support.reopen",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
    )
    support_notify.notify_status_change(db, case, status="open")
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def update_status(
    db: Session, *, user: User, case_id: UUID, payload: SupportStatusUpdate
) -> dict:
    if not can_resolve(user) and not can_reply(user):
        raise HTTPException(status_code=403, detail="Status permission required")
    case = _require_case_access(db, user, case_id)
    new_status = _normalize_status(payload.status)
    case.status = new_status
    if new_status == "resolved":
        case.resolved_at = datetime.now(UTC)
    if new_status == "closed":
        case.closed_at = datetime.now(UTC)
    if new_status == "open":
        case.resolved_at = None
        case.closed_at = None
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="status",
        summary=f"Status → {new_status}",
    )
    write_audit_log(
        db,
        action="support.status",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"status": new_status},
    )
    support_notify.notify_status_change(db, case, status=new_status)
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def update_priority(
    db: Session, *, user: User, case_id: UUID, payload: SupportPriorityUpdate
) -> dict:
    if not can_assign(user) and not can_reply(user):
        raise HTTPException(status_code=403, detail="Priority permission required")
    case = _require_case_access(db, user, case_id)
    case.priority = _normalize_priority(payload.priority)
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="priority",
        summary=f"Priority → {case.priority}",
        is_public=False,
    )
    write_audit_log(
        db,
        action="support.priority",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"priority": case.priority},
    )
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def update_category(
    db: Session, *, user: User, case_id: UUID, payload: SupportCategoryUpdate
) -> dict:
    if not can_assign(user) and not can_reply(user):
        raise HTTPException(status_code=403, detail="Category permission required")
    case = _require_case_access(db, user, case_id)
    case.category = _normalize_category(payload.category)
    if case.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="category",
        summary=f"Category → {case.category}",
        is_public=False,
    )
    write_audit_log(
        db,
        action="support.category",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"category": case.category},
    )
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def archive_case(db: Session, *, user: User, case_id: UUID) -> dict:
    if not _perm(user, "support.archive", "admin.support.close", "admin.support.view_all"):
        raise HTTPException(status_code=403, detail="Archive permission required")
    case = _require_case_access(db, user, case_id)
    if case.status not in {"resolved", "closed"}:
        raise HTTPException(
            status_code=400, detail="Only resolved/closed tickets can be archived"
        )
    case.status = "archived"
    case.archived_at = datetime.now(UTC)
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="archive",
        summary="Archived",
        is_public=False,
    )
    write_audit_log(
        db,
        action="support.archive",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
    )
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


def _storage_root() -> Path:
    root = Path(get_settings().media_root if hasattr(get_settings(), "media_root") else ".")
    # Prefer project-relative storage
    path = Path("storage/support_attachments")
    path.mkdir(parents=True, exist_ok=True)
    return path


async def add_attachment(
    db: Session,
    *,
    user: User,
    case_id: UUID,
    file: UploadFile,
    is_internal: bool = False,
) -> dict:
    case = _require_case_access(db, user, case_id)
    if is_internal and not can_internal_notes(user):
        raise HTTPException(status_code=403, detail="Not allowed")
    data = await file.read()
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=400, detail="Attachment too large (max 5MB)")
    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(status_code=400, detail="Attachment type not allowed")
    filename = sanitize_support_text(file.filename or "upload.bin", max_len=200) or "upload.bin"
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    checksum = hashlib.sha256(data).hexdigest()
    key = f"{case.id}/{uuid.uuid4().hex}_{filename}"
    dest = _storage_root() / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    db.add(
        SupportTicketAttachment(
            case_id=case.id,
            uploaded_by_user_id=user.id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            storage_key=key,
            checksum_sha256=checksum,
            is_internal=is_internal,
        )
    )
    _record_event(
        db,
        case=case,
        actor_user_id=user.id,
        event_type="attachment",
        summary=f"Attachment uploaded: {filename}",
        is_public=not is_internal,
    )
    write_audit_log(
        db,
        action="support.attachment",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"filename": filename, "size": len(data)},
    )
    db.commit()
    return serialize_case(
        db, _load_case(db, case.id), include_internal=is_support_staff(user)  # type: ignore[arg-type]
    )


def soft_delete_attachment(
    db: Session, *, user: User, case_id: UUID, attachment_id: UUID
) -> dict:
    if not can_delete_attachment(user):
        raise HTTPException(status_code=403, detail="Delete attachment permission required")
    case = _require_case_access(db, user, case_id)
    att = db.get(SupportTicketAttachment, attachment_id)
    if att is None or att.case_id != case.id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    att.deleted_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="support.attachment_delete",
        actor_user_id=user.id,
        resource_type="support_case",
        resource_id=str(case.id),
        details={"attachment_id": str(attachment_id)},
    )
    db.commit()
    return serialize_case(db, _load_case(db, case.id), include_internal=True)  # type: ignore[arg-type]


DEFAULT_SETTINGS = {
    "auto_assign_enabled": False,
    "notify_on_urgent": True,
    "public_form_enabled": True,
    "default_priority": "normal",
}


def get_settings_dict(db: Session) -> dict:
    row = db.scalar(select(SupportSettings).where(SupportSettings.key == "global"))
    if row is None:
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(row.value_json or "{}")
    except json.JSONDecodeError:
        data = {}
    return {**DEFAULT_SETTINGS, **data}


def update_settings(
    db: Session, *, user: User, payload: SupportSettingsUpdate
) -> dict:
    if not can_manage_settings(user):
        raise HTTPException(status_code=403, detail="Manage settings permission required")
    current = get_settings_dict(db)
    updates = payload.model_dump(exclude_unset=True)
    current.update(updates)
    row = db.scalar(select(SupportSettings).where(SupportSettings.key == "global"))
    if row is None:
        row = SupportSettings(key="global", value_json=json.dumps(current))
        db.add(row)
    else:
        row.value_json = json.dumps(current)
    row.updated_by_user_id = user.id
    write_audit_log(
        db,
        action="support.settings_update",
        actor_user_id=user.id,
        resource_type="support_settings",
        resource_id="global",
        details=updates,
    )
    db.commit()
    return current


# Back-compat alias used by older imports
_is_support_staff = is_support_staff
