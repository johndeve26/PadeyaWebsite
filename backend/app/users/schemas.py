"""User-facing Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImpersonationPublic(BaseModel):
    """Present on /auth/me when the access token is an audited impersonation session."""

    active: bool = True
    is_impersonating: bool = True
    impersonation_id: UUID
    actual_user_id: UUID
    actor_admin_id: UUID
    impersonator_id: UUID | None = None
    impersonator_email: str | None = None
    impersonator_full_name: str | None = None
    target_user_id: UUID | None = None
    reason: str | None = None
    support_ticket_id: str | None = None
    started_at: datetime | None = None
    expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)
    pack: str | None = None


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # Plain str: reserved TLDs (e.g. .test demo accounts) are rejected by EmailStr.
    email: str
    full_name: str
    username: str | None = None
    avatar_url: str | None = None
    # Owner/settings: always present for /me; may be null when unset.
    gender: str | None = None
    gender_short: str | None = None
    gender_label: str | None = None
    gender_visible: bool = True
    gender_visibility: str = "public"
    is_active: bool
    is_verified: bool
    ambassadors_blocked: bool = False
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    deactivated_at: datetime | None = None
    security_locked: bool = False
    security_lock_reason: str | None = None
    under_review: bool = False
    under_review_reason: str | None = None
    under_review_at: datetime | None = None
    account_status: str = "active"
    account_restrictions: list[str] = Field(default_factory=list)
    # Active restriction keys only — never reason / internal_note (end-user FE).
    restriction_keys: list[str] = Field(default_factory=list)
    suspension: dict | None = None
    impersonation: ImpersonationPublic | None = None


class AdminUserRowPublic(BaseModel):
    """Safe admin directory row — no passwords, tokens, or private payloads."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    ambassadors_blocked: bool = False
    roles: list[str] = Field(default_factory=list)
    created_at: datetime
    deactivated_at: datetime | None = None
    security_locked: bool = False
    security_lock_reason: str | None = None
    under_review: bool = False
    account_status: str = "active"


class AdminUserListPublic(BaseModel):
    items: list[AdminUserRowPublic] = Field(default_factory=list)
    page: int = 1
    limit: int = 40
    total: int = 0


class AdminUserProfileSection(BaseModel):
    avatar_url: str | None = None
    tagline: str | None = None
    bio: str | None = None
    passport_visibility: str | None = None
    passport_admin_hidden: bool = False
    fan_connect_enabled: bool = False
    fan_connect_status: str = "not_configured"
    ambassador_profile_status: str | None = None
    ambassadors_program_blocked: bool = False
    campaigns_joined: int = 0
    gender: str | None = None
    gender_label: str | None = None
    gender_visibility: str | None = None
    gender_unset: bool = True


class AdminUserAccountSection(BaseModel):
    email_verified: bool = False
    auth_provider: str = "password"
    roles: list[str] = Field(default_factory=list)
    phone_masked: str | None = None
    phone_available: bool = False
    two_factor_status: str = "not_implemented"
    active_sessions: int = 0
    last_active_at: datetime | None = None


class AdminUserActivitySection(BaseModel):
    tickets_count: int = 0
    orders_count: int = 0
    merch_count: int = 0
    refunds_count: int = 0
    reviews_count: int = 0
    host_workspaces_owned: int = 0
    host_teams_joined: int = 0
    ambassador_campaigns_joined: int = 0


class AdminUserNotePublic(BaseModel):
    id: UUID
    user_id: UUID
    note_type: str
    body: str
    created_by_admin_id: UUID
    created_at: datetime
    updated_at: datetime | None = None


class AdminUserNoteCreate(BaseModel):
    note_type: str = Field(default="general", min_length=2, max_length=32)
    body: str = Field(min_length=3, max_length=4000)


class AdminUserFlagPublic(BaseModel):
    id: UUID
    user_id: UUID
    flag_type: str
    severity: str
    status: str
    reason: str
    internal_note: str | None = None
    created_by_admin_id: UUID
    created_at: datetime
    resolved_by_admin_id: UUID | None = None
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    updated_at: datetime


class AdminUserModerationSection(BaseModel):
    flags: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    suspensions: list[str] = Field(default_factory=list)
    internal_notes: list[AdminUserNotePublic] = Field(default_factory=list)
    admin_flags: list[AdminUserFlagPublic] = Field(default_factory=list)
    under_review: bool = False
    under_review_reason: str | None = None
    under_review_at: datetime | None = None


class AdminUserAuditItemPublic(BaseModel):
    id: UUID
    action: str
    actor_user_id: UUID | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    created_at: datetime


class AdminUserDetailPublic(BaseModel):
    """Safe admin user detail — no passwords, tokens, QR secrets, or private bodies."""

    id: UUID
    email: str
    email_masked: str
    full_name: str
    display_name: str
    username: str | None = None
    is_active: bool
    is_verified: bool
    account_status: str
    verification_status: str
    created_at: datetime
    deactivated_at: datetime | None = None
    last_active_at: datetime | None = None
    risk_level: str
    risk_label: str
    security_locked: bool = False
    security_lock_reason: str | None = None
    ambassadors_blocked: bool = False
    under_review: bool = False
    under_review_reason: str | None = None
    under_review_at: datetime | None = None
    account_restrictions: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    profile: AdminUserProfileSection = Field(default_factory=AdminUserProfileSection)
    account: AdminUserAccountSection = Field(default_factory=AdminUserAccountSection)
    activity: AdminUserActivitySection = Field(default_factory=AdminUserActivitySection)
    moderation: AdminUserModerationSection = Field(
        default_factory=AdminUserModerationSection
    )
    recent_audit: list[AdminUserAuditItemPublic] = Field(default_factory=list)


class UserLifecycleReasonBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AdminAccountStatusChangeBody(BaseModel):
    status: str = Field(min_length=3, max_length=32)
    reason: str = Field(min_length=3, max_length=500)
    restrictions: list[str] | None = None
    # User-facing suspension category (never fraud internals).
    reason_category: str | None = Field(default=None, max_length=64)
    ends_at: datetime | None = None


class AdminUserRestrictionPublic(BaseModel):
    id: UUID
    user_id: UUID
    restriction_key: str
    label: str | None = None
    category: str | None = None
    category_label: str | None = None
    status: str
    reason: str
    internal_note: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    created_by_admin_id: UUID
    created_by_admin_name: str | None = None
    revoked_by_admin_id: UUID | None = None
    revoked_by_admin_name: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminUserRestrictionsListPublic(BaseModel):
    user_id: UUID
    account_status: str
    active_keys: list[str] = Field(default_factory=list)
    created_count: int | None = None
    items: list[AdminUserRestrictionPublic] = Field(default_factory=list)


class AdminUserRestrictionsApplyBody(BaseModel):
    restriction_keys: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=3, max_length=500)
    internal_note: str | None = Field(default=None, max_length=4000)
    ends_at: datetime | None = None
    # Admin preset only — not the default moderation path.
    # When true (or preset=full_suspension): status=suspended + major keys.
    preset: str | None = Field(default=None, max_length=64)
    force_full_suspension: bool = False


class AdminUserRestrictionPatchBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    ends_at: datetime | None = None
    internal_note: str | None = Field(default=None, max_length=4000)


class AdminUserRestrictionRevokeBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AdminUserFlagCreate(BaseModel):
    flag_type: str = Field(min_length=2, max_length=64)
    severity: str = Field(default="medium", min_length=3, max_length=16)
    reason: str = Field(min_length=3, max_length=500)
    internal_note: str | None = Field(default=None, max_length=4000)


class AdminUserFlagCloseBody(BaseModel):
    resolution_note: str | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=500)


class AdminUserFlagPatchBody(BaseModel):
    status: str = Field(min_length=3, max_length=32)
    reason: str = Field(min_length=3, max_length=500)
    resolution_note: str | None = Field(default=None, max_length=500)


class AdminSensitiveReasonBody(BaseModel):
    """Required reason for force-logout, force-password-reset, and similar."""

    reason: str = Field(min_length=3, max_length=500)


class AdminSessionsRevokeResponse(BaseModel):
    user_id: UUID
    revoked_count: int


class AdminPasswordResetForcedResponse(BaseModel):
    user_id: str
    email_sent: bool = True


class AdminUserActivityDetailListPublic(BaseModel):
    """Paginated Activity tab drill-down. Finance fields may be null when gated."""

    kind: str
    items: list[dict] = Field(default_factory=list)
    page: int = 1
    limit: int = 20
    total: int = 0
    finance_fields_included: bool = False


class MessageResponse(BaseModel):
    message: str
