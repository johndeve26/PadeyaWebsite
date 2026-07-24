"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional
from app.auth.email_verification import (
    EMAIL_VERIFICATION_REQUEST_MESSAGE,
    confirm_email_verification,
    request_email_verification_for_user,
)
from app.auth.rate_limit import (
    rate_limit_email_verification,
    rate_limit_login,
    rate_limit_password_reset,
    rate_limit_register,
)
from app.auth.schemas import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    EmailVerifyConfirmRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.auth.service import (
    PASSWORD_RESET_REQUEST_MESSAGE,
    authenticate_user,
    build_user_public,
    issue_token_pair,
    logout_user,
    refresh_access_token,
    register_user,
    request_password_reset,
    verify_password_reset_code,
)
from app.core.database import get_db
from app.users.admin_actions_service import confirm_password_reset
from app.users.models import User
from app.users.schemas import MessageResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("/health")
async def auth_module_health() -> dict[str, str]:
    return {"module": "auth", "status": "ok"}


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_register)],
)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    ip, ua = _client_meta(request)
    _, tokens = register_user(
        db,
        email=payload.email,
        password=payload.password,
        username=payload.username,
        ip_address=ip,
        user_agent=ua,
    )
    return TokenResponse(**tokens)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_login)],
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    ip, ua = _client_meta(request)
    _, tokens = authenticate_user(
        db,
        login=payload.login,
        password=payload.password,
        ip_address=ip,
        user_agent=ua,
    )
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    ip, ua = _client_meta(request)
    tokens = refresh_access_token(
        db,
        refresh_token=payload.refresh_token,
        ip_address=ip,
        user_agent=ua,
    )
    return TokenResponse(**tokens)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> MessageResponse:
    ip, ua = _client_meta(request)
    from app.auth.impersonation_context import get_impersonation_context
    from app.admin.impersonation_service import end_impersonation_on_logout

    ctx = get_impersonation_context()
    if ctx is not None:
        end_impersonation_on_logout(
            db,
            ctx=ctx,
            ip_address=ip,
            user_agent=ua,
        )
    if payload.refresh_token:
        logout_user(
            db,
            refresh_token=payload.refresh_token,
            actor_user_id=user.id if user else None,
            ip_address=ip,
            user_agent=ua,
        )
    return MessageResponse(message="Logged out")


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_password_reset)],
)
def password_reset_request(
    payload: PasswordResetRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Request a reset link by email. Response is identical whether or not the email exists."""
    ip, ua = _client_meta(request)
    request_password_reset(
        db,
        email=payload.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message=PASSWORD_RESET_REQUEST_MESSAGE)


@router.post(
    "/password-reset/verify",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_password_reset)],
)
def password_reset_verify(
    payload: PasswordResetVerifyRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    ip, ua = _client_meta(request)
    verify_password_reset_code(
        db,
        email=payload.email,
        code=payload.code,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Code accepted. You can set a new password.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Consume a password-reset token. Never echoes the token or password."""
    confirm_password_reset(
        db,
        email=payload.email,
        code=payload.code,
        new_password=payload.new_password,
    )
    return MessageResponse(message="Password updated")


@router.post(
    "/email/verify/request",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_email_verification)],
)
def email_verify_request(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    ip, ua = _client_meta(request)
    request_email_verification_for_user(
        db, user=user, ip_address=ip, user_agent=ua
    )
    return MessageResponse(message=EMAIL_VERIFICATION_REQUEST_MESSAGE)


@router.post(
    "/email/verify/confirm",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_email_verification)],
)
def email_verify_confirm(
    payload: EmailVerifyConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> TokenResponse:
    ip, ua = _client_meta(request)
    verified_user = confirm_email_verification(
        db,
        token=payload.token,
        code=payload.code,
        user=user,
        ip_address=ip,
        user_agent=ua,
    )
    tokens = issue_token_pair(
        db,
        user=verified_user,
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return TokenResponse(**tokens)


@router.post("/change-password", response_model=MessageResponse)
def change_password_route(
    payload: ChangePasswordRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    from app.auth.account_credentials import change_password

    ip, ua = _client_meta(request)
    change_password(
        db,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Password updated")


@router.post("/change-email", response_model=UserPublic)
def change_email_route(
    payload: ChangeEmailRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> UserPublic:
    from app.auth.account_credentials import change_email

    ip, ua = _client_meta(request)
    updated = change_email(
        db,
        user=user,
        new_email=payload.new_email,
        current_password=payload.current_password,
        ip_address=ip,
        user_agent=ua,
    )
    return UserPublic.model_validate(build_user_public(updated, db=db))


@router.get("/me", response_model=UserPublic)
def me(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserPublic:
    return UserPublic.model_validate(build_user_public(user, db=db))
