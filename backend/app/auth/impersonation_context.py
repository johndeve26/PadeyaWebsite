"""Request-scoped impersonation context for audited admin sessions.

Uses threading.local (not contextvars) because FastAPI runs sync dependencies
in a threadpool where ContextVar tokens cannot be reset across contexts.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ImpersonationContext:
    """Active impersonation session metadata (admin remains the audit actor).

    Effective/current user is always the target (``actual_user_id``).
    ``actor_admin_id`` is stored separately and must never grant admin RBAC.
    """

    actor_admin_id: UUID
    impersonation_id: UUID
    actual_user_id: UUID
    reason: str | None = None
    support_ticket_id: str | None = None
    started_at: datetime | None = None
    expires_at: datetime | None = None
    scopes: tuple[str, ...] = field(default_factory=tuple)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    @property
    def is_impersonating(self) -> bool:
        return True

    @property
    def current_user_id(self) -> UUID:
        """Effective user for the request (= target user)."""
        return self.actual_user_id

    @property
    def impersonator_id(self) -> UUID:
        """Alias used by audit helpers."""
        return self.actor_admin_id

    @property
    def target_user_id(self) -> UUID:
        """Alias used by audit helpers."""
        return self.actual_user_id


_local = threading.local()


def get_impersonation_context() -> ImpersonationContext | None:
    return getattr(_local, "impersonation", None)


def set_impersonation_context(ctx: ImpersonationContext | None) -> None:
    _local.impersonation = ctx


def clear_impersonation_context() -> None:
    _local.impersonation = None
