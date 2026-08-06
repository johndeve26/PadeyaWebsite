"""Support ticket draft / create tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.users.models import User


def create_support_ticket_draft(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    args = args or {}
    subject = str(args.get("subject") or "Help with Pàdéyá").strip()[:200]
    category = str(args.get("category") or "general").strip()[:64]
    body = str(args.get("body") or args.get("message") or "").strip()[:4000]
    if not body:
        body = (
            "Hi Support,\n\nI need help with the following:\n\n"
            "[Please describe what happened and what you expected.]\n\n"
            "Thanks."
        )
    return {
        "ok": True,
        "draft": {
            "subject": subject,
            "category": category,
            "body": body,
        },
        "note": "Draft only — not submitted. Confirm to create a ticket, or open /support.",
        "support_url": "/support",
    }


def create_support_ticket(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    confirmed: bool = False,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not confirmed:
        return {
            "ok": False,
            "error": "confirmation_required",
            "message": "Confirm to submit this support ticket.",
        }
    args = args or {}
    subject = str(args.get("subject") or "Help with Pàdéyá").strip()[:200]
    category = str(args.get("category") or "general").strip()[:64]
    body = str(args.get("body") or args.get("message") or "").strip()[:8000]
    if len(body) < 5:
        return {"ok": False, "error": "body_too_short"}
    try:
        from app.support.schemas import SupportCaseCreate
        from app.support.service import create_case

        payload = SupportCaseCreate(
            subject=subject if len(subject) >= 3 else "Help with Pàdéyá",
            category=category,
            body=body,
            priority=str(args.get("priority") or "normal"),
        )
        case = create_case(db, user=user, payload=payload)
        return {
            "ok": True,
            "case": {
                "id": str(case.get("id")),
                "case_number": case.get("case_number") or case.get("ticket_number"),
                "status": case.get("status"),
            },
            "support_url": "/support",
        }
    except Exception as exc:
        return {"ok": False, "error": "create_failed", "detail": type(exc).__name__}
