"""Auth request/response schemas."""

import re

from typing import Self

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from app.auth.register_username import resolve_register_username
from app.passport.privacy import is_valid_passport_username, normalize_username

# Allow reserved TLDs (e.g. .test) used by local demo accounts. EmailStr rejects them.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_auth_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL_RE.match(email) or len(email) > 320:
        raise ValueError("Invalid email address")
    return email


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    username: str | None = Field(default=None, min_length=3, max_length=32)
    full_name: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _normalize_auth_email(value)

    @model_validator(mode="after")
    def resolve_username(self) -> Self:
        try:
            resolved = resolve_register_username(
                username=self.username,
                full_name=self.full_name,
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        object.__setattr__(self, "username", resolved)
        return self


class LoginRequest(BaseModel):
    login: str = Field(
        min_length=3,
        max_length=320,
        validation_alias=AliasChoices("login", "email"),
    )
    password: str = Field(min_length=1, max_length=128)

    @field_validator("login")
    @classmethod
    def normalize_login(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Enter your email or username.")
        if "@" in stripped:
            return _normalize_auth_email(stripped)
        key = normalize_username(stripped)
        if not is_valid_passport_username(key):
            raise ValueError(
                "Usernames must be 3–32 characters: lowercase letters, numbers, underscore."
            )
        return key


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)


class LogoutRequest(BaseModel):
    # Optional: impersonation sessions have no refresh token; logout still ends them.
    refresh_token: str | None = Field(default=None, min_length=20, max_length=512)


class PasswordResetVerifyRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=6, max_length=16)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _normalize_auth_email(value)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        from app.core.security import normalize_password_reset_code

        code = normalize_password_reset_code(value)
        if len(code) != 6:
            raise ValueError("Reset code must be 6 characters.")
        return code


class PasswordResetConfirmRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=6, max_length=16)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _normalize_auth_email(value)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        from app.core.security import normalize_password_reset_code

        code = normalize_password_reset_code(value)
        if len(code) != 6:
            raise ValueError("Reset code must be 6 characters.")
        return code


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _normalize_auth_email(value)


class EmailVerifyConfirmRequest(BaseModel):
    token: str | None = Field(default=None, max_length=512)
    code: str | None = Field(default=None, min_length=6, max_length=16)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        from app.core.security import normalize_password_reset_code

        code = normalize_password_reset_code(value)
        if len(code) != 6:
            raise ValueError("Verification code must be 6 characters.")
        return code

    @model_validator(mode="after")
    def require_token_or_code(self) -> Self:
        has_token = bool((self.token or "").strip())
        has_code = bool(self.code)
        if not has_token and not has_code:
            raise ValueError("Enter your verification code or use the link from your email.")
        return self


class ChangePasswordRequest(BaseModel):
    # Empty allowed only during admin impersonation (validated in service).
    current_password: str = Field(default="", max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ChangeEmailRequest(BaseModel):
    new_email: str = Field(min_length=3, max_length=320)
    # Empty allowed only during admin impersonation (validated in service).
    current_password: str = Field(default="", max_length=128)

    @field_validator("new_email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _normalize_auth_email(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
