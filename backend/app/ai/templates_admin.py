"""Admin CRUD for AI prompt templates — usage logs remain read-only."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.models import AIPromptTemplate, AIUsageLog
from app.core.audit import write_audit_log
from app.users.models import User


def list_prompt_templates(db: Session, *, include_inactive: bool = True) -> list[AIPromptTemplate]:
    q = select(AIPromptTemplate).order_by(AIPromptTemplate.audience, AIPromptTemplate.slug)
    if not include_inactive:
        q = q.where(AIPromptTemplate.is_active.is_(True))
    return list(db.scalars(q))


def create_prompt_template(
    db: Session,
    *,
    user: User,
    slug: str,
    name: str,
    audience: str,
    system_prompt: str,
    user_template: str,
    description: str | None = None,
) -> AIPromptTemplate:
    existing = db.scalar(select(AIPromptTemplate).where(AIPromptTemplate.slug == slug))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Template slug already exists")
    row = AIPromptTemplate(
        slug=slug.strip(),
        name=name.strip(),
        audience=audience.strip(),
        system_prompt=system_prompt,
        user_template=user_template,
        description=description,
        is_active=True,
    )
    db.add(row)
    write_audit_log(
        db,
        action="ai.template_create",
        actor_user_id=user.id,
        resource_type="ai_prompt_template",
        resource_id=str(row.id),
        details={"slug": row.slug},
    )
    db.commit()
    db.refresh(row)
    return row


def update_prompt_template(
    db: Session,
    *,
    user: User,
    template_id: UUID,
    **fields,
) -> AIPromptTemplate:
    row = db.get(AIPromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in fields.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    write_audit_log(
        db,
        action="ai.template_update",
        actor_user_id=user.id,
        resource_type="ai_prompt_template",
        resource_id=str(row.id),
        details={"fields": list(fields.keys())},
    )
    db.commit()
    db.refresh(row)
    return row


def deactivate_prompt_template(
    db: Session, *, user: User, template_id: UUID
) -> AIPromptTemplate:
    row = db.get(AIPromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    row.is_active = False
    write_audit_log(
        db,
        action="ai.template_deactivate",
        actor_user_id=user.id,
        resource_type="ai_prompt_template",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def list_usage_logs(db: Session, *, limit: int = 100) -> list[AIUsageLog]:
    return list(
        db.scalars(
            select(AIUsageLog).order_by(AIUsageLog.created_at.desc()).limit(limit)
        )
    )
