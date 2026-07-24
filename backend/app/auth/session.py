"""Request-scoped auth/session identity for normal and impersonation sessions.

Impersonation uses a Bearer access token (not a cookie). Admin tokens stay
stashed client-side; this module never mixes admin RBAC into the effective user.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from starlette.requests import Request

from app.auth.impersonation_context import (
    ImpersonationContext,
    clear_impersonation_context,
    get_impersonation_context,
)


@dataclass(frozen=True)
class RequestAuthIdentity:
    """Per-request identity snapshot (safe for handlers / middleware)."""

    current_user_id: UUID | None = None
    actor_admin_id: UUID | None = None
    impersonation_id: UUID | None = None
    is_impersonating: bool = False

    @property
    def target_user_id(self) -> UUID | None:
        """During impersonation, current user is the target."""
        return self.current_user_id if self.is_impersonating else None


def init_request_auth_state(request: Request) -> None:
    """Reset request.state identity at the start of a request."""
    request.state.current_user_id = None
    request.state.actor_admin_id = None
    request.state.impersonation_id = None
    request.state.is_impersonating = False


def attach_request_auth_identity(
    request: Request,
    *,
    current_user_id: UUID,
    impersonation: ImpersonationContext | None = None,
) -> RequestAuthIdentity:
    """Attach resolved identity to ``request.state`` for the rest of the request.

    - ``current_user_id`` is always the effective user (target while impersonating)
    - ``actor_admin_id`` / ``impersonation_id`` are set only while impersonating
    - Admin permissions are never implied by these fields
    """
    if impersonation is not None:
        identity = RequestAuthIdentity(
            current_user_id=current_user_id,
            actor_admin_id=impersonation.actor_admin_id,
            impersonation_id=impersonation.impersonation_id,
            is_impersonating=True,
        )
    else:
        identity = RequestAuthIdentity(
            current_user_id=current_user_id,
            actor_admin_id=None,
            impersonation_id=None,
            is_impersonating=False,
        )

    request.state.current_user_id = identity.current_user_id
    request.state.actor_admin_id = identity.actor_admin_id
    request.state.impersonation_id = identity.impersonation_id
    request.state.is_impersonating = identity.is_impersonating
    return identity


def get_request_auth_identity(request: Request) -> RequestAuthIdentity:
    """Read identity previously attached to ``request.state`` (may be empty)."""
    return RequestAuthIdentity(
        current_user_id=getattr(request.state, "current_user_id", None),
        actor_admin_id=getattr(request.state, "actor_admin_id", None),
        impersonation_id=getattr(request.state, "impersonation_id", None),
        is_impersonating=bool(getattr(request.state, "is_impersonating", False)),
    )


def resolve_session_identity(
    *,
    current_user_id: UUID,
    impersonation: ImpersonationContext | None,
) -> RequestAuthIdentity:
    """Build identity from the active context (no Request required)."""
    if impersonation is None:
        return RequestAuthIdentity(
            current_user_id=current_user_id,
            is_impersonating=False,
        )
    return RequestAuthIdentity(
        current_user_id=current_user_id,
        actor_admin_id=impersonation.actor_admin_id,
        impersonation_id=impersonation.impersonation_id,
        is_impersonating=True,
    )


def clear_auth_session() -> None:
    """Clear thread-local impersonation context (call between requests / on exit)."""
    clear_impersonation_context()


def get_active_impersonation() -> ImpersonationContext | None:
    return get_impersonation_context()
