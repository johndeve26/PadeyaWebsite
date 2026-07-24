"""Shared FastAPI dependencies for team host context."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.teams.workspace_pref import resolve_host_id_for_request


def resolve_request_host_id(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: UUID | None = Query(
        default=None,
        description="Host workspace id (overrides active workspace)",
    ),
    x_padeya_host_id: Annotated[
        UUID | None,
        Header(alias="X-Padeya-Host-Id"),
    ] = None,
) -> UUID | None:
    return resolve_host_id_for_request(
        db,
        user=user,
        host_id=host_id,
        header_host_id=x_padeya_host_id,
    )


ResolvedHostId = Annotated[UUID | None, Depends(resolve_request_host_id)]
