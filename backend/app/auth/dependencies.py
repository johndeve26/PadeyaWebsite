"""Auth dependencies for current user, roles, and permissions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.impersonation_context import (
    ImpersonationContext,
    clear_impersonation_context,
    get_impersonation_context,
    set_impersonation_context,
)
from app.auth.session import (
    RequestAuthIdentity,
    attach_request_auth_identity,
    get_request_auth_identity,
    init_request_auth_state,
)
from app.core.database import get_db
from app.core.security import decode_access_token
from app.users.models import User
from app.users.service import get_user_by_id, user_has_permission, user_has_role

bearer_scheme = HTTPBearer(auto_error=False)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value), tz=UTC)
        except (TypeError, ValueError, OSError):
            return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _parse_impersonation_payload(
    payload: dict[str, Any],
) -> ImpersonationContext | None:
    if not payload.get("is_impersonating"):
        return None

    try:
        actual_user_id = UUID(
            str(payload.get("actual_user_id") or payload["sub"])
        )
        actor_admin_id = UUID(
            str(payload.get("actor_admin_id") or payload["impersonator_id"])
        )
        impersonation_id = UUID(str(payload["impersonation_id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid impersonation token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Subject must be the target — never the admin.
    try:
        sub = UUID(str(payload["sub"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid impersonation token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if sub != actual_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid impersonation token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if actor_admin_id == actual_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid impersonation token actors",
            headers={"WWW-Authenticate": "Bearer"},
        )

    reason = payload.get("reason") or payload.get("impersonation_reason")
    if reason is not None and not isinstance(reason, str):
        reason = None

    ticket = payload.get("support_ticket_id")
    if ticket is not None and not isinstance(ticket, str):
        ticket = None

    return ImpersonationContext(
        actor_admin_id=actor_admin_id,
        impersonation_id=impersonation_id,
        actual_user_id=actual_user_id,
        reason=reason,
        support_ticket_id=ticket,
        started_at=_parse_datetime(payload.get("started_at")),
        expires_at=_parse_datetime(payload.get("expires_at"))
        or _parse_datetime(payload.get("exp")),
    )


def _validate_impersonation_session(
    db: Session,
    *,
    impersonation: ImpersonationContext,
    target: User,
) -> None:
    """Ensure the DB session is active, not expired, and parties are still enabled."""
    from app.admin.impersonation_models import IMPERSONATION_STATUS_ACTIVE
    from app.admin.impersonation_service import revoke_impersonation_for_safety
    from app.admin.impersonation_store import (
        get_impersonation_session,
        mark_impersonation_session_expired,
    )
    from app.users.service import get_user_by_id

    session_row = get_impersonation_session(db, impersonation.impersonation_id)
    if session_row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impersonation session not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (
        session_row.target_user_id != impersonation.actual_user_id
        or session_row.actor_admin_id != impersonation.actor_admin_id
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impersonation session mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(UTC)
    expires = session_row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)

    if session_row.status != IMPERSONATION_STATUS_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impersonation session is no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if expires < now:
        mark_impersonation_session_expired(
            db, session_id=impersonation.impersonation_id
        )
        from app.admin.impersonation_audit import (
            ADMIN_IMPERSONATION_EXPIRED,
            record_impersonation_audit,
        )

        record_impersonation_audit(
            db,
            action=ADMIN_IMPERSONATION_EXPIRED,
            impersonation_id=impersonation.impersonation_id,
            actor_admin_id=impersonation.actor_admin_id,
            target_user_id=impersonation.actual_user_id,
            reason=impersonation.reason or session_row.reason,
            support_ticket_id=session_row.support_ticket_id
            or impersonation.support_ticket_id,
            method=None,
            path=None,
            status_code=401,
            action_attempted="use_expired_impersonation_token",
            metadata={
                "started_at": (
                    session_row.started_at.isoformat()
                    if session_row.started_at
                    else None
                ),
                "ended_at": (
                    session_row.ended_at.isoformat()
                    if session_row.ended_at
                    else None
                ),
                "expires_at": expires.isoformat(),
            },
            ip_address=None,
            user_agent=None,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impersonation session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = get_user_by_id(db, impersonation.actor_admin_id)
    if admin is None or not admin.is_active or admin.deactivated_at is not None:
        revoke_impersonation_for_safety(
            db,
            ctx=impersonation,
            cause="admin_account_disabled",
            detail="Admin account is disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impersonation ended because the admin account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Mid-session disable: end if the target was deactivated at/after session start.
    # Sessions intentionally started against an already-suspended user may continue.
    started = session_row.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    target_disabled_mid_session = False
    if target.deactivated_at is not None:
        deactivated = target.deactivated_at
        if deactivated.tzinfo is None:
            deactivated = deactivated.replace(tzinfo=UTC)
        if deactivated >= started:
            target_disabled_mid_session = True
    elif not target.is_active:
        # is_active flipped without deactivated_at (unusual) — treat as mid-session disable.
        target_disabled_mid_session = True

    if target_disabled_mid_session:
        revoke_impersonation_for_safety(
            db,
            ctx=impersonation,
            cause="target_account_disabled",
            detail="Target account is disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impersonation ended because the target account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the effective user for this request.

    While impersonating:
    - ``current_user`` / ``request.state.current_user_id`` = target user
    - ``request.state.actor_admin_id`` / context = admin (audit only)
    - ``request.state.impersonation_id`` = session id
    - RBAC uses the target user's DB roles/permissions only (JWT claims ignored)
    """
    # Always reset first so threadpool workers never leak prior request state.
    clear_impersonation_context()
    init_request_auth_state(request)

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        # Effective user is always the target during impersonation.
        user_id = UUID(
            str(payload.get("actual_user_id") or payload["sub"])
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    impersonation = _parse_impersonation_payload(payload)

    # Authorization uses the *target* user loaded from DB — never the admin,
    # and never JWT ``roles`` / ``permissions`` claims (which are informational).
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Suspended users may authenticate for appeal / status pages only.
    if impersonation is None:
        from app.appeals.middleware import _path_allowed
        from app.users.account_status_service import effective_account_status
        from app.users.account_status_constants import (
            ACCOUNT_STATUS_BANNED,
            ACCOUNT_STATUS_DELETED,
            ACCOUNT_STATUS_SUSPENDED,
        )

        acct = effective_account_status(user)
        if acct in {ACCOUNT_STATUS_BANNED, ACCOUNT_STATUS_DELETED}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not available.",
            )
        if acct == ACCOUNT_STATUS_SUSPENDED or not user.is_active:
            if acct == ACCOUNT_STATUS_SUSPENDED and _path_allowed(request.url.path):
                pass  # appeal / me / auth surface
            elif not user.is_active and acct != ACCOUNT_STATUS_SUSPENDED:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account suspended. You can appeal or sign out.",
                )

    if impersonation is not None:
        _validate_impersonation_session(
            db, impersonation=impersonation, target=user
        )

    user._impersonation_expires_at = (  # type: ignore[attr-defined]
        impersonation.expires_at if impersonation else None
    ) or _parse_datetime(payload.get("exp"))
    user._impersonation_payload = payload  # type: ignore[attr-defined]

    set_impersonation_context(impersonation)
    attach_request_auth_identity(
        request,
        current_user_id=user.id,
        impersonation=impersonation,
    )
    return user


def get_current_user_optional(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if credentials is None:
        clear_impersonation_context()
        init_request_auth_state(request)
        return None
    try:
        return get_current_user(request, credentials, db)
    except HTTPException:
        clear_impersonation_context()
        init_request_auth_state(request)
        return None


def get_request_identity(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> RequestAuthIdentity:
    """Authenticated request identity (current + optional impersonation fields)."""
    identity = get_request_auth_identity(request)
    if identity.current_user_id is None:
        # Fallback if middleware order skipped attach (should not happen).
        return attach_request_auth_identity(
            request,
            current_user_id=user.id,
            impersonation=get_impersonation_context(),
        )
    return identity


def require_role(*role_names: str) -> Callable[..., User]:
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        # Uses DB roles of the effective (possibly impersonated) user only.
        if not user_has_role(user, *role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return dependency


def require_permission(*permission_codes: str) -> Callable[..., User]:
    """Global RBAC on the user's roles.

    Host/sponsor **team** grants (``HostTeamMember.permissions_json``) are enforced
    in domain services via ``require_host_for_permission`` / sponsor team access.
    Do not use this on ``/host/*`` routes that already delegate to those services —
    use ``CurrentUser`` / ``get_current_user`` instead.
    """
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        # Uses DB permissions of the effective (possibly impersonated) user only.
        if not any(user_has_permission(user, code) for code in permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission",
            )
        return user

    return dependency


def require_not_impersonating(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Block sensitive mutations while an impersonation session is active."""
    ctx = get_impersonation_context()
    if ctx is not None:
        from app.admin.impersonation_audit import (
            ADMIN_IMPERSONATION_SENSITIVE_ACTION_BLOCKED,
            record_impersonation_audit,
        )
        from app.admin.impersonation_guards import (
            IMPERSONATION_SENSITIVE_ACTION_DETAIL,
        )

        path = request.url.path
        record_impersonation_audit(
            db,
            action=ADMIN_IMPERSONATION_SENSITIVE_ACTION_BLOCKED,
            impersonation_id=ctx.impersonation_id,
            actor_admin_id=ctx.actor_admin_id,
            target_user_id=ctx.actual_user_id,
            reason=ctx.reason,
            method=request.method,
            path=path[:512],
            status_code=403,
            action_attempted=f"{request.method} {path}",
            metadata={"blocked": True, "guard": "dependency"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=IMPERSONATION_SENSITIVE_ACTION_DETAIL,
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
RequestIdentity = Annotated[RequestAuthIdentity, Depends(get_request_identity)]
