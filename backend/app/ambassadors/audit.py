"""Append-only ambassador domain audit helper."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.promos.ambassador_domain import AmbassadorAuditLog


def write_ambassador_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | UUID,
    actor_user_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AmbassadorAuditLog:
    row = AmbassadorAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        metadata_json=metadata,
    )
    db.add(row)
    return row
