"""Typed allowlist registry — single source of truth for Admin Runtime Settings.

Only keys that exist on ``Settings`` or specialist email/push admin today.
Boot-critical Class A keys are either omitted or ``editable=False`` and
hard-rejected on write.

Deferred (not in Settings — do not invent): S3/Cloudinary/Slack/reCAPTCHA,
``PAYSTACK_ENABLED``, ``MAINTENANCE_MODE``, maps provider keys.
Email SMTP / Push VAPID secrets stay in specialist tables; registry may
expose them with ``managed_by`` + ``specialist_route`` for unified GET/PUT
delegation (no duplicate secret columns in ``runtime_settings``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

ValueType = Literal["string", "number", "boolean", "json", "secret"]
SensitiveLevel = Literal["public", "internal", "secret", "boot_critical"]
ManagedBy = Literal[
    "runtime_settings",
    "email_provider_settings",
    "push_provider_settings",
    "env_only",
]
# Admin form display unit. Storage/env remain in native units (e.g. bytes).
AdminUnit = Literal["mb"]

Validator = Callable[[Any], Any]

BYTES_PER_MB = 1024 * 1024


def bytes_to_admin_mb(value: Any) -> int | float | None:
    """Convert stored bytes → whole MB for admin UI (nearest MB, min 0)."""
    if value is None or value == "":
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    mb = n / BYTES_PER_MB
    # Prefer whole MB for easy tracking; keep one decimal if fractional.
    rounded = round(mb)
    if abs(mb - rounded) < 1e-9:
        return int(rounded)
    return round(mb, 1)


def admin_mb_to_bytes(value: Any) -> int:
    """Convert admin MB input → bytes for persistence."""
    n = float(value)
    if n < 0:
        raise ValueError("Must be >= 0")
    return int(round(n * BYTES_PER_MB))


@dataclass(frozen=True)
class RuntimeSettingDefinition:
    key: str
    category: str
    label: str
    description: str
    value_type: ValueType
    is_secret: bool
    editable: bool
    env_var: str
    default: Any
    settings_attr: str
    required_for_feature: str | None = None
    restart_required: bool = False
    sensitive_level: SensitiveLevel = "internal"
    managed_by: ManagedBy = "runtime_settings"
    specialist_route: str | None = None
    validation_schema_json: dict[str, Any] | None = None
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: frozenset[str] | None = None
    # When set, admin GET/PUT use this unit; DB/env stay in settings native units.
    admin_unit: AdminUnit | None = None


# ---------------------------------------------------------------------------
# Class A — never editable via runtime_settings (hard-block on write)
# ---------------------------------------------------------------------------
CLASS_A_BLOCKLIST: frozenset[str] = frozenset(
    {
        "database_url",
        "redis_url",
        "secret_key",
        "qr_signing_secret",
        "email_settings_encryption_key",
        "app_env",
        "debug",
        "demo_mode",
        "cors_origins",
        "frontend_url",
        "api_prefix",
        "jwt_algorithm",
        "access_token_expire_minutes",
        "refresh_token_expire_days",
        "impersonation_token_expire_minutes",
        "ai_api_key",
        "media_storage_provider",
        "media_root",
        "private_media_root",
        "r2_bucket_name",
        "r2_endpoint",
        "r2_access_key_id",
        "r2_secret_access_key",
        "r2_public_url",
        "r2_private_bucket_name",
        "r2_private_endpoint",
        "r2_private_access_key_id",
        "r2_private_secret_access_key",
        "messaging_attachment_storage_provider",
        "messaging_attachment_storage_root",
        "postgres_user",
        "postgres_password",
        "postgres_db",
    }
)

CLASS_A_ENV_VARS: frozenset[str] = frozenset(
    {
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "QR_SIGNING_SECRET",
        "EMAIL_SETTINGS_ENCRYPTION_KEY",
        "APP_ENV",
        "DEBUG",
        "DEMO_MODE",
        "CORS_ORIGINS",
        "FRONTEND_URL",
        "API_PREFIX",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "IMPERSONATION_TOKEN_EXPIRE_MINUTES",
        "AI_API_KEY",
        "MEDIA_STORAGE_PROVIDER",
        "MEDIA_ROOT",
        "PRIVATE_MEDIA_ROOT",
        "R2_BUCKET_NAME",
        "R2_ENDPOINT",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_PUBLIC_URL",
        "R2_PRIVATE_BUCKET_NAME",
        "R2_PRIVATE_ENDPOINT",
        "R2_PRIVATE_ACCESS_KEY_ID",
        "R2_PRIVATE_SECRET_ACCESS_KEY",
        "MESSAGING_ATTACHMENT_STORAGE_PROVIDER",
        "MESSAGING_ATTACHMENT_STORAGE_ROOT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    }
)

# Categories aligned with FE routes under /admin/settings/*
CATEGORIES: tuple[str, ...] = (
    "runtime",
    "email",
    "push",
    "ai",
    "payments",
    "notifications",
    "storage",
    "integrations",
    "security-runtime",
    "system-status",
)

RESERVED_PATH_NAMES: frozenset[str] = frozenset({"audit", "status", "runtime"})


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    text = str(v).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError("Expected boolean")


def _int(v: Any, *, min_v: int | None = None, max_v: int | None = None) -> int:
    n = int(v)
    if min_v is not None and n < min_v:
        raise ValueError(f"Must be >= {min_v}")
    if max_v is not None and n > max_v:
        raise ValueError(f"Must be <= {max_v}")
    return n


def _str(v: Any, *, max_len: int = 500) -> str:
    text = str(v).strip()
    if len(text) > max_len:
        raise ValueError(f"Must be <= {max_len} characters")
    return text


_URL_KEYS = frozenset(
    {
        "app_base_url",
        "media_public_base_url",
        "ai_base_url",
        "paystack_base_url",
    }
)


def _url(v: Any, *, allow_empty: bool = True) -> str:
    text = _str(v, max_len=2000)
    if not text:
        if allow_empty:
            return ""
        raise ValueError("URL is required")
    lower = text.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        raise ValueError("Must be a valid http(s) URL")
    return text


def _def(
    *,
    key: str,
    category: str,
    label: str,
    description: str,
    value_type: ValueType,
    env_var: str,
    default: Any,
    settings_attr: str | None = None,
    is_secret: bool = False,
    editable: bool = True,
    required_for_feature: str | None = None,
    restart_required: bool = False,
    sensitive_level: SensitiveLevel = "internal",
    managed_by: ManagedBy = "runtime_settings",
    specialist_route: str | None = None,
    validation_schema_json: dict[str, Any] | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    allowed_values: frozenset[str] | None = None,
    admin_unit: AdminUnit | None = None,
) -> RuntimeSettingDefinition:
    return RuntimeSettingDefinition(
        key=key,
        category=category,
        label=label,
        description=description,
        value_type=value_type,
        is_secret=is_secret,
        editable=editable,
        env_var=env_var,
        default=default,
        settings_attr=settings_attr or key,
        required_for_feature=required_for_feature,
        restart_required=restart_required,
        sensitive_level=sensitive_level,
        managed_by=managed_by,
        specialist_route=specialist_route,
        validation_schema_json=validation_schema_json,
        min_value=min_value,
        max_value=max_value,
        allowed_values=allowed_values,
        admin_unit=admin_unit,
    )


RUNTIME_SETTING_DEFINITIONS: tuple[RuntimeSettingDefinition, ...] = (
    # ---- runtime ----
    _def(
        key="app_name",
        category="runtime",
        label="App name",
        description="Display name used in API metadata and emails.",
        value_type="string",
        env_var="APP_NAME",
        default="Pàdéyá API",
        sensitive_level="public",
    ),
    _def(
        key="support_email",
        category="runtime",
        label="Support email",
        description="Public support contact address.",
        value_type="string",
        env_var="SUPPORT_EMAIL",
        default="support@padeya.com",
        sensitive_level="public",
    ),
    _def(
        key="app_base_url",
        category="runtime",
        label="App base URL",
        description="Public site origin for email links (falls back to FRONTEND_URL).",
        value_type="string",
        env_var="APP_BASE_URL",
        default="",
        sensitive_level="public",
    ),
    _def(
        key="media_public_base_url",
        category="runtime",
        label="Media public base URL",
        description="Optional public origin prefix for /media URLs.",
        value_type="string",
        env_var="MEDIA_PUBLIC_BASE_URL",
        default="",
        sensitive_level="public",
    ),
    # ---- email (Class B tunables; SMTP secrets via specialist) ----
    _def(
        key="email_queue_enabled",
        category="email",
        label="Email queue enabled",
        description="Drain email_events via worker / in-process sweeper.",
        value_type="boolean",
        env_var="EMAIL_QUEUE_ENABLED",
        default=True,
        required_for_feature="email_queue",
    ),
    _def(
        key="email_worker_poll_seconds",
        category="email",
        label="Email worker poll seconds",
        description="Sleep between outbox batches in --loop mode.",
        value_type="number",
        env_var="EMAIL_WORKER_POLL_SECONDS",
        default=20,
        min_value=5,
        max_value=3600,
    ),
    _def(
        key="email_worker_batch_size",
        category="email",
        label="Email worker batch size",
        description="Max email_events per drain batch.",
        value_type="number",
        env_var="EMAIL_WORKER_BATCH_SIZE",
        default=50,
        min_value=1,
        max_value=500,
    ),
    _def(
        key="email_rate_limit_per_user_per_hour",
        category="email",
        label="Email rate limit / user / hour",
        description="Soft cap on queued emails per user per hour.",
        value_type="number",
        env_var="EMAIL_RATE_LIMIT_PER_USER_PER_HOUR",
        default=20,
        min_value=0,
        max_value=10_000,
    ),
    _def(
        key="email_log_body_in_dev",
        category="email",
        label="Log email bodies in dev",
        description="When true, log providers may include body text (dev only).",
        value_type="boolean",
        env_var="EMAIL_LOG_BODY_IN_DEV",
        default=False,
    ),
    # Specialist-managed (no runtime_settings secret column)
    _def(
        key="smtp_port",
        category="email",
        label="SMTP port",
        description="Managed by Email settings. Not stored in runtime_settings.",
        value_type="number",
        env_var="",
        default=587,
        editable=True,
        managed_by="email_provider_settings",
        specialist_route="/admin/email/settings",
        required_for_feature="email_sending",
        min_value=1,
        max_value=65535,
    ),
    _def(
        key="smtp_password",
        category="email",
        label="SMTP password",
        description="Managed by Email settings (encrypted). Not stored in runtime_settings.",
        value_type="secret",
        env_var="",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="email_provider_settings",
        specialist_route="/admin/email/settings",
        required_for_feature="email_sending",
    ),
    _def(
        key="smtp_username",
        category="email",
        label="SMTP username",
        description="Managed by Email settings (encrypted). Not stored in runtime_settings.",
        value_type="secret",
        env_var="",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="email_provider_settings",
        specialist_route="/admin/email/settings",
        required_for_feature="email_sending",
    ),
    # ---- push ----
    _def(
        key="push_queue_enabled",
        category="push",
        label="Push queue enabled",
        description="Drain push_events via worker / in-process sweeper.",
        value_type="boolean",
        env_var="PUSH_QUEUE_ENABLED",
        default=True,
        required_for_feature="push_queue",
    ),
    _def(
        key="push_worker_poll_seconds",
        category="push",
        label="Push worker poll seconds",
        description="Sleep between push outbox batches in --loop mode.",
        value_type="number",
        env_var="PUSH_WORKER_POLL_SECONDS",
        default=20,
        min_value=5,
        max_value=3600,
    ),
    _def(
        key="push_worker_batch_size",
        category="push",
        label="Push worker batch size",
        description="Max push_events per drain batch.",
        value_type="number",
        env_var="PUSH_WORKER_BATCH_SIZE",
        default=50,
        min_value=1,
        max_value=500,
    ),
    _def(
        key="push_message_rate_limit_per_hour",
        category="push",
        label="Message push rate limit / hour",
        description="Soft cap on message-category pushes per user per hour.",
        value_type="number",
        env_var="PUSH_MESSAGE_RATE_LIMIT_PER_HOUR",
        default=12,
        min_value=0,
        max_value=10_000,
    ),
    _def(
        key="vapid_private_key",
        category="push",
        label="VAPID private key",
        description="Managed by Push settings (encrypted). Not stored in runtime_settings.",
        value_type="secret",
        env_var="VAPID_PRIVATE_KEY",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="push_provider_settings",
        specialist_route="/admin/push/settings",
        required_for_feature="push_delivery",
    ),
    # ---- ai (non-secret knobs; AI_API_KEY status-only) ----
    _def(
        key="ai_enabled",
        category="ai",
        label="AI enabled",
        description="Master switch for AI Copilot features.",
        value_type="boolean",
        env_var="AI_ENABLED",
        default=False,
        required_for_feature="ai",
    ),
    _def(
        key="ai_provider",
        category="ai",
        label="AI provider",
        description="template | openai | anthropic | gemini | grok | none",
        value_type="string",
        env_var="AI_PROVIDER",
        default="template",
        allowed_values=frozenset(
            {
                "template",
                "openai",
                "anthropic",
                "gemini",
                "grok",
                "none",
                "off",
                "disabled",
            }
        ),
        required_for_feature="ai",
    ),
    _def(
        key="ai_model",
        category="ai",
        label="AI model",
        description="Model id for OpenAI-compatible providers.",
        value_type="string",
        env_var="AI_MODEL",
        default="gpt-4o-mini",
    ),
    _def(
        key="ai_base_url",
        category="ai",
        label="AI base URL",
        description="OpenAI-compatible API base URL.",
        value_type="string",
        env_var="AI_BASE_URL",
        default="https://api.openai.com/v1",
    ),
    _def(
        key="ai_max_tokens",
        category="ai",
        label="AI max tokens",
        description="Max completion tokens.",
        value_type="number",
        env_var="AI_MAX_TOKENS",
        default=800,
        min_value=1,
        max_value=128_000,
    ),
    _def(
        key="ai_timeout_seconds",
        category="ai",
        label="AI timeout seconds",
        description="HTTP timeout for AI provider calls.",
        value_type="number",
        env_var="AI_TIMEOUT_SECONDS",
        default=30,
        min_value=1,
        max_value=300,
    ),
    _def(
        key="ai_rate_limit_per_hour",
        category="ai",
        label="AI rate limit / hour",
        description="Soft per-user AI request cap.",
        value_type="number",
        env_var="AI_RATE_LIMIT_PER_HOUR",
        default=60,
        min_value=0,
        max_value=100_000,
    ),
    _def(
        key="ai_api_key",
        category="ai",
        label="AI API key",
        description="Env-only secret. Status shows configured/last4 — never editable here.",
        value_type="secret",
        env_var="AI_API_KEY",
        default="",
        is_secret=True,
        editable=False,
        sensitive_level="boot_critical",
        managed_by="env_only",
        required_for_feature="ai",
    ),
    # ---- payments (Paystack — admin-only; secrets Fernet-encrypted; no env vars) ----
    _def(
        key="paystack_mode",
        category="payments",
        label="Paystack mode",
        description=(
            "Test uses sk_test_/pk_test_ keys (no real money). Live uses sk_live_/pk_live_ "
            "for production. Same Paystack API URL for both — see Paystack authentication docs."
        ),
        value_type="string",
        env_var="",
        default="test",
        allowed_values=frozenset({"test", "live"}),
        sensitive_level="internal",
        required_for_feature="payments",
    ),
    _def(
        key="paystack_base_url",
        category="payments",
        label="Paystack base URL",
        description="Paystack API origin (non-secret). Official default: https://api.paystack.co",
        value_type="string",
        env_var="",
        default="https://api.paystack.co",
        sensitive_level="public",
    ),
    _def(
        key="paystack_secret_key",
        category="payments",
        label="Paystack test secret key",
        description="Test secret (sk_test_…). Used when mode is Test. Stored encrypted.",
        value_type="secret",
        env_var="",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="runtime_settings",
        required_for_feature="payments",
    ),
    _def(
        key="paystack_webhook_secret",
        category="payments",
        label="Paystack test webhook secret",
        description="Test webhook HMAC secret. Falls back to test secret key when empty. Stored encrypted.",
        value_type="secret",
        env_var="",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="runtime_settings",
        required_for_feature="payments",
    ),
    _def(
        key="paystack_public_key",
        category="payments",
        label="Paystack test public key",
        description="Test public key (pk_test_…) for checkout when mode is Test.",
        value_type="string",
        env_var="",
        default="",
        editable=True,
        sensitive_level="internal",
        managed_by="runtime_settings",
        required_for_feature="payments",
    ),
    _def(
        key="paystack_live_secret_key",
        category="payments",
        label="Paystack live secret key",
        description="Live secret (sk_live_…). Used when mode is Live. Stored encrypted.",
        value_type="secret",
        env_var="",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="runtime_settings",
        required_for_feature="payments",
    ),
    _def(
        key="paystack_live_webhook_secret",
        category="payments",
        label="Paystack live webhook secret",
        description="Live webhook HMAC secret. Falls back to live secret key when empty. Stored encrypted.",
        value_type="secret",
        env_var="",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="runtime_settings",
        required_for_feature="payments",
    ),
    _def(
        key="paystack_live_public_key",
        category="payments",
        label="Paystack live public key",
        description="Live public key (pk_live_…) for checkout when mode is Live.",
        value_type="string",
        env_var="",
        default="",
        editable=True,
        sensitive_level="internal",
        managed_by="runtime_settings",
        required_for_feature="payments",
    ),
    # ---- notifications (merch cart recovery) ----
    _def(
        key="merch_cart_abandon_after_hours",
        category="notifications",
        label="Cart abandon after (hours)",
        description="Hours before an inactive cart is treated as abandoned.",
        value_type="number",
        env_var="MERCH_CART_ABANDON_AFTER",
        default=24,
        min_value=1,
        max_value=720,
        required_for_feature="merch_cart_recovery",
    ),
    _def(
        key="merch_cart_expire_after_days",
        category="notifications",
        label="Cart expire after (days)",
        description="Days before abandoned carts expire.",
        value_type="number",
        env_var="MERCH_CART_EXPIRE_AFTER_DAYS",
        default=14,
        min_value=1,
        max_value=365,
    ),
    _def(
        key="merch_cart_recovery_min_gap_hours",
        category="notifications",
        label="Cart recovery min gap (hours)",
        description="Minimum hours between recovery reminder emails.",
        value_type="number",
        env_var="MERCH_CART_RECOVERY_MIN_GAP_HOURS",
        default=72,
        min_value=1,
        max_value=720,
    ),
    # ---- storage (limits only; mount paths are Class A) ----
    # Admin UI uses MB; persisted value + env remain bytes.
    _def(
        key="messaging_attachment_max_image_bytes",
        category="storage",
        label="Max image attachment (MB)",
        description="Per-image size limit for chat attachments. Enter megabytes.",
        value_type="number",
        env_var="MESSAGING_ATTACHMENT_MAX_IMAGE_BYTES",
        default=5 * 1024 * 1024,
        min_value=1024,
        max_value=50 * 1024 * 1024,
        admin_unit="mb",
    ),
    _def(
        key="messaging_attachment_max_doc_bytes",
        category="storage",
        label="Max document attachment (MB)",
        description="Per-document size limit for chat attachments. Enter megabytes.",
        value_type="number",
        env_var="MESSAGING_ATTACHMENT_MAX_DOC_BYTES",
        default=10 * 1024 * 1024,
        min_value=1024,
        max_value=50 * 1024 * 1024,
        admin_unit="mb",
    ),
    _def(
        key="messaging_attachment_max_total_bytes",
        category="storage",
        label="Max total attachments / message (MB)",
        description="Combined attachment budget per message. Enter megabytes.",
        value_type="number",
        env_var="MESSAGING_ATTACHMENT_MAX_TOTAL_BYTES",
        default=15 * 1024 * 1024,
        min_value=1024,
        max_value=100 * 1024 * 1024,
        admin_unit="mb",
    ),
    _def(
        key="messaging_attachment_max_count",
        category="storage",
        label="Max attachments / message",
        description="Max number of files per chat message.",
        value_type="number",
        env_var="MESSAGING_ATTACHMENT_MAX_COUNT",
        default=4,
        min_value=1,
        max_value=20,
    ),
    _def(
        key="messaging_attachment_orphan_hours",
        category="storage",
        label="Orphan attachment expiry (hours)",
        description="Unbound staged uploads expire after this many hours.",
        value_type="number",
        env_var="MESSAGING_ATTACHMENT_ORPHAN_HOURS",
        default=24,
        min_value=1,
        max_value=168,
    ),
    _def(
        key="messaging_attachment_cleanup_interval_seconds",
        category="storage",
        label="Attachment cleanup interval (seconds)",
        description="In-process orphan sweeper interval (0 disables). Restart may be needed.",
        value_type="number",
        env_var="MESSAGING_ATTACHMENT_CLEANUP_INTERVAL_SECONDS",
        default=3600,
        min_value=0,
        max_value=86_400,
        restart_required=True,
    ),
    _def(
        key="messaging_attachment_download_ttl_seconds",
        category="storage",
        label="Attachment download TTL (seconds)",
        description="Signed download token lifetime.",
        value_type="number",
        env_var="MESSAGING_ATTACHMENT_DOWNLOAD_TTL_SECONDS",
        default=900,
        min_value=60,
        max_value=3600,
    ),
    _def(
        key="messaging_attachment_strip_image_metadata",
        category="storage",
        label="Strip image metadata",
        description="Strip EXIF when Pillow can re-encode uploads.",
        value_type="boolean",
        env_var="MESSAGING_ATTACHMENT_STRIP_IMAGE_METADATA",
        default=True,
    ),
    _def(
        key="messaging_attachment_scanner",
        category="storage",
        label="Attachment scanner",
        description="noop (default) | clamav (reserved).",
        value_type="string",
        env_var="MESSAGING_ATTACHMENT_SCANNER",
        default="noop",
        allowed_values=frozenset({"noop", "clamav"}),
    ),
    # ---- integrations (Google Geocoding — admin-only; never NEXT_PUBLIC_*) ----
    _def(
        key="google_places_api_key",
        category="integrations",
        label="Google Places / Geocoding API key",
        description=(
            "Server-only key for admin event re-geocode. Restrict by IP in Google Cloud "
            "Console. Never expose to the browser or NEXT_PUBLIC_*."
        ),
        value_type="secret",
        env_var="",
        default="",
        is_secret=True,
        editable=True,
        sensitive_level="secret",
        managed_by="runtime_settings",
        required_for_feature="maps",
    ),
    # ---- integrations (analytics) ----
    _def(
        key="analytics_impression_dedupe_seconds",
        category="integrations",
        label="Impression dedupe window (seconds)",
        value_type="number",
        env_var="ANALYTICS_IMPRESSION_DEDUPE_SECONDS",
        default=300,
        description="Dedupe window for impression events.",
        min_value=0,
        max_value=86_400,
    ),
    _def(
        key="analytics_detail_view_dedupe_seconds",
        category="integrations",
        label="Detail view dedupe window (seconds)",
        value_type="number",
        env_var="ANALYTICS_DETAIL_VIEW_DEDUPE_SECONDS",
        default=1800,
        description="Dedupe window for detail-view events.",
        min_value=0,
        max_value=86_400,
    ),
    _def(
        key="analytics_checkout_start_dedupe_seconds",
        category="integrations",
        label="Checkout start dedupe window (seconds)",
        value_type="number",
        env_var="ANALYTICS_CHECKOUT_START_DEDUPE_SECONDS",
        default=3600,
        description="Dedupe window for checkout-start events.",
        min_value=0,
        max_value=86_400,
    ),
    _def(
        key="analytics_unique_click_dedupe_seconds",
        category="integrations",
        label="Unique click dedupe window (seconds)",
        value_type="number",
        env_var="ANALYTICS_UNIQUE_CLICK_DEDUPE_SECONDS",
        default=86_400,
        description="Dedupe window for unique click events.",
        min_value=0,
        max_value=604_800,
    ),
    _def(
        key="analytics_track_rate_limit_per_minute",
        category="integrations",
        label="Analytics track rate limit / minute",
        value_type="number",
        env_var="ANALYTICS_TRACK_RATE_LIMIT_PER_MINUTE",
        default=120,
        description="Per-IP rate limit for public analytics track.",
        min_value=1,
        max_value=10_000,
    ),
    _def(
        key="analytics_track_batch_max_items",
        category="integrations",
        label="Analytics track batch max items",
        value_type="number",
        env_var="ANALYTICS_TRACK_BATCH_MAX_ITEMS",
        default=50,
        description="Max events per track batch request.",
        min_value=1,
        max_value=500,
    ),
    _def(
        key="analytics_metadata_max_keys",
        category="integrations",
        label="Analytics metadata max keys",
        value_type="number",
        env_var="ANALYTICS_METADATA_MAX_KEYS",
        default=40,
        description="Max metadata keys on a track event.",
        min_value=1,
        max_value=200,
    ),
    _def(
        key="analytics_metadata_max_bytes",
        category="integrations",
        label="Analytics metadata max bytes",
        value_type="number",
        env_var="ANALYTICS_METADATA_MAX_BYTES",
        default=8192,
        description="Max serialized metadata size.",
        min_value=256,
        max_value=65_536,
    ),
    # ---- security-runtime (ambassador fraud / rate) ----
    _def(
        key="ambassador_track_rate_limit_per_minute",
        category="security-runtime",
        label="Ambassador track rate limit / minute",
        value_type="number",
        env_var="AMBASSADOR_TRACK_RATE_LIMIT_PER_MINUTE",
        default=60,
        description="Per-IP rate limit for ambassador click tracking.",
        min_value=1,
        max_value=10_000,
    ),
    _def(
        key="ambassador_click_spike_window_seconds",
        category="security-runtime",
        label="Click spike window (seconds)",
        value_type="number",
        env_var="AMBASSADOR_CLICK_SPIKE_WINDOW_SECONDS",
        default=300,
        description="Window for click-spike fraud detection.",
        min_value=1,
        max_value=86_400,
    ),
    _def(
        key="ambassador_click_spike_threshold",
        category="security-runtime",
        label="Click spike threshold",
        value_type="number",
        env_var="AMBASSADOR_CLICK_SPIKE_THRESHOLD",
        default=40,
        description="Clicks in window that trigger a fraud flag (0 disables).",
        min_value=0,
        max_value=100_000,
    ),
    _def(
        key="ambassador_high_value_reward_ngn",
        category="security-runtime",
        label="High-value reward alert (NGN)",
        value_type="number",
        env_var="AMBASSADOR_HIGH_VALUE_REWARD_NGN",
        default=50_000,
        description="Admin alert when a paid reward meets/exceeds this (0 = off).",
        min_value=0,
        max_value=1_000_000_000,
    ),
    _def(
        key="fan_connect_decline_cooldown_days",
        category="fan_connect",
        label="Default decline cooldown (days)",
        value_type="number",
        env_var="FAN_CONNECT_DECLINE_COOLDOWN_DAYS",
        default=30,
        description=(
            "When a user declines a connect request, the requester cannot send "
            "another request to that same person until this cooldown ends. "
            "The person who declined can still send a request back at any time."
        ),
        min_value=0,
        max_value=365,
    ),
    # ---- host recommendations (discovery) ----
    _def(
        key="host_recommendations_enabled",
        category="host-recommendations",
        label="Host recommendations enabled",
        value_type="boolean",
        env_var="HOST_RECOMMENDATIONS_ENABLED",
        default=True,
        description="When off, personalized host recommendations return empty lists.",
    ),
    _def(
        key="host_recommendations_min_score",
        category="host-recommendations",
        label="Minimum score to show",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_MIN_SCORE",
        default=35,
        description="Hosts below this score are hidden from personalized surfaces only.",
        min_value=0,
        max_value=100,
    ),
    _def(
        key="host_recommendations_dismiss_days",
        category="host-recommendations",
        label="Dismissal cooldown (days)",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_DISMISS_DAYS",
        default=60,
        description="How long a dismiss/not-interested hides a host from recommendations.",
        min_value=1,
        max_value=365,
    ),
    _def(
        key="host_recommendations_pool_size",
        category="host-recommendations",
        label="Candidate pool size",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_POOL_SIZE",
        default=120,
        description="Max discoverable hosts scored per fan request.",
        min_value=20,
        max_value=200,
    ),
    _def(
        key="host_recommendations_weight_interest",
        category="host-recommendations",
        label="Interest signal weight",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_WEIGHT_INTEREST",
        default=1.0,
        description="Multiplier for attendance, tickets, categories, and similar-followed signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="host_recommendations_weight_location",
        category="host-recommendations",
        label="Location signal weight",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_WEIGHT_LOCATION",
        default=1.0,
        description="Multiplier for city match and nearby geo signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="host_recommendations_weight_social",
        category="host-recommendations",
        label="Social graph weight",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_WEIGHT_SOCIAL",
        default=1.0,
        description="Multiplier for Fan Connect peers following a host.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="host_recommendations_weight_trust",
        category="host-recommendations",
        label="Trust / activity weight",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_WEIGHT_TRUST",
        default=1.0,
        description="Multiplier for verified hosts, upcoming events, check-ins, and ratings.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="host_recommendations_weight_freshness",
        category="host-recommendations",
        label="Freshness weight",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_WEIGHT_FRESHNESS",
        default=1.0,
        description="Multiplier for upcoming-soon and cold-start baseline signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="host_recommendations_max_per_category",
        category="host-recommendations",
        label="Max hosts per category",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_MAX_PER_CATEGORY",
        default=3,
        description="Diversity cap per primary category in one response.",
        min_value=1,
        max_value=20,
    ),
    _def(
        key="host_recommendations_max_per_city",
        category="host-recommendations",
        label="Max hosts per city/area",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_MAX_PER_CITY",
        default=4,
        description="Diversity cap per city label in one response.",
        min_value=1,
        max_value=30,
    ),
    _def(
        key="host_recommendations_cold_start_mode",
        category="host-recommendations",
        label="Cold-start mode",
        value_type="string",
        env_var="HOST_RECOMMENDATIONS_COLD_START_MODE",
        default="baseline",
        description="baseline adds upcoming-only hosts; off disables cold-start reasons.",
    ),
    _def(
        key="host_recommendations_category_hide_days",
        category="host-recommendations",
        label="Category hide duration (days)",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_CATEGORY_HIDE_DAYS",
        default=90,
        description="How long a hidden category stays excluded from recommendations.",
        min_value=1,
        max_value=365,
    ),
    _def(
        key="host_recommendations_impression_penalty_threshold",
        category="host-recommendations",
        label="Impression penalty threshold",
        value_type="number",
        env_var="HOST_RECOMMENDATIONS_IMPRESSION_PENALTY_THRESHOLD",
        default=3,
        description="After this many impressions with no click/follow, rank penalty applies.",
        min_value=1,
        max_value=20,
    ),
    # ---- event recommendations (discovery) ----
    _def(
        key="event_recommendations_enabled",
        category="event-recommendations",
        label="Event recommendations enabled",
        value_type="boolean",
        env_var="EVENT_RECOMMENDATIONS_ENABLED",
        default=True,
        description="When off, personalized event recommendations return empty lists.",
    ),
    _def(
        key="event_recommendations_min_score",
        category="event-recommendations",
        label="Minimum score to show",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_MIN_SCORE",
        default=35,
        description="Events below this score are hidden from personalized surfaces only.",
        min_value=0,
        max_value=100,
    ),
    _def(
        key="event_recommendations_dismiss_days",
        category="event-recommendations",
        label="Dismissal cooldown (days)",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_DISMISS_DAYS",
        default=60,
        description="How long dismiss/not-interested hides an event from recommendations.",
        min_value=1,
        max_value=365,
    ),
    _def(
        key="event_recommendations_pool_size",
        category="event-recommendations",
        label="Candidate pool size",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_POOL_SIZE",
        default=200,
        description="Max published events scored per fan request.",
        min_value=20,
        max_value=400,
    ),
    _def(
        key="event_recommendations_weight_interest",
        category="event-recommendations",
        label="Interest signal weight",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_WEIGHT_INTEREST",
        default=1.0,
        description="Multiplier for category and attendance affinity signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="event_recommendations_weight_host",
        category="event-recommendations",
        label="Host affinity weight",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_WEIGHT_HOST",
        default=1.0,
        description="Multiplier for followed/attended host signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="event_recommendations_weight_location",
        category="event-recommendations",
        label="Location signal weight",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_WEIGHT_LOCATION",
        default=1.0,
        description="Multiplier for city/area match signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="event_recommendations_weight_social",
        category="event-recommendations",
        label="Social graph weight",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_WEIGHT_SOCIAL",
        default=1.0,
        description="Multiplier for Fan Connect peer signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="event_recommendations_weight_trust",
        category="event-recommendations",
        label="Trust / activity weight",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_WEIGHT_TRUST",
        default=1.0,
        description="Multiplier for verified hosts, featured, and Pàdéyá Picks.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="event_recommendations_weight_freshness",
        category="event-recommendations",
        label="Freshness weight",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_WEIGHT_FRESHNESS",
        default=1.0,
        description="Multiplier for upcoming-soon and cold-start signals.",
        min_value=0.0,
        max_value=3.0,
    ),
    _def(
        key="event_recommendations_max_per_host",
        category="event-recommendations",
        label="Max events per host",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_MAX_PER_HOST",
        default=3,
        description="Diversity cap per host in one response.",
        min_value=1,
        max_value=20,
    ),
    _def(
        key="event_recommendations_max_per_category",
        category="event-recommendations",
        label="Max events per category",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_MAX_PER_CATEGORY",
        default=4,
        description="Diversity cap per category in one response.",
        min_value=1,
        max_value=30,
    ),
    _def(
        key="event_recommendations_max_per_city",
        category="event-recommendations",
        label="Max events per city",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_MAX_PER_CITY",
        default=5,
        description="Diversity cap per city in one response.",
        min_value=1,
        max_value=40,
    ),
    _def(
        key="event_recommendations_cold_start_mode",
        category="event-recommendations",
        label="Cold-start mode",
        value_type="string",
        env_var="EVENT_RECOMMENDATIONS_COLD_START_MODE",
        default="baseline",
        description="baseline enables city/pick cold-start reasons; off disables them.",
    ),
    _def(
        key="event_recommendations_category_hide_days",
        category="event-recommendations",
        label="Category hide duration (days)",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_CATEGORY_HIDE_DAYS",
        default=90,
        description="How long a hidden category stays excluded.",
        min_value=1,
        max_value=365,
    ),
    _def(
        key="event_recommendations_host_hide_days",
        category="event-recommendations",
        label="Host hide duration (days)",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_HOST_HIDE_DAYS",
        default=90,
        description="How long hide-host suppresses that host's events.",
        min_value=1,
        max_value=365,
    ),
    _def(
        key="event_recommendations_impression_penalty_threshold",
        category="event-recommendations",
        label="Impression penalty threshold",
        value_type="number",
        env_var="EVENT_RECOMMENDATIONS_IMPRESSION_PENALTY_THRESHOLD",
        default=3,
        description="After this many impressions with no click/save, rank penalty applies.",
        min_value=1,
        max_value=20,
    ),
)

FINGERPRINT_DISPLAY_PLAIN_KEYS: frozenset[str] = frozenset(
    {
        "paystack_public_key",
        "paystack_live_public_key",
    }
)


def setting_shows_fingerprint(defn: RuntimeSettingDefinition | None) -> bool:
    if defn is None:
        return False
    return defn.is_secret or defn.key in FINGERPRINT_DISPLAY_PLAIN_KEYS


DEFINITIONS_BY_KEY: dict[str, RuntimeSettingDefinition] = {
    d.key: d for d in RUNTIME_SETTING_DEFINITIONS
}

DEFINITIONS_BY_CATEGORY: dict[str, list[RuntimeSettingDefinition]] = {}
for _d in RUNTIME_SETTING_DEFINITIONS:
    DEFINITIONS_BY_CATEGORY.setdefault(_d.category, []).append(_d)


def get_definition(key: str) -> RuntimeSettingDefinition | None:
    return DEFINITIONS_BY_KEY.get(key)


def is_class_a_key(key: str) -> bool:
    k = (key or "").strip().lower()
    if k in CLASS_A_BLOCKLIST:
        return True
    env = (key or "").strip().upper()
    return env in CLASS_A_ENV_VARS


def is_patch_allowlisted(key: str) -> bool:
    """Writable via runtime_settings DB or specialist delegation."""
    if is_class_a_key(key):
        return False
    d = get_definition(key)
    if d is None:
        return False
    if d.sensitive_level == "boot_critical":
        return False
    return bool(d.editable)


def validate_value(defn: RuntimeSettingDefinition, raw: Any) -> Any:
    """Coerce + validate a non-secret (or secret plaintext input) value.

    When ``admin_unit == "mb"``, ``raw`` is treated as megabytes from the admin
    API and converted to bytes before min/max checks (storage stays bytes).
    """
    if defn.value_type == "boolean":
        return _bool(raw)
    if defn.value_type == "number":
        if defn.admin_unit == "mb":
            try:
                raw = admin_mb_to_bytes(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("Must be a number of megabytes") from exc
        min_v = int(defn.min_value) if defn.min_value is not None else None
        max_v = int(defn.max_value) if defn.max_value is not None else None
        return _int(raw, min_v=min_v, max_v=max_v)
    if defn.value_type in {"string", "secret"}:
        if defn.key in _URL_KEYS or defn.key.endswith("_url"):
            return _url(raw, allow_empty=defn.key in {"app_base_url", "media_public_base_url"})
        text = _str(raw, max_len=4000 if defn.is_secret else 2000)
        if defn.allowed_values is not None and text.lower() not in {
            a.lower() for a in defn.allowed_values
        }:
            raise ValueError(
                f"Must be one of: {', '.join(sorted(defn.allowed_values))}"
            )
        if defn.key == "paystack_mode":
            return text.lower()
        if text and defn.key in {
            "paystack_secret_key",
            "paystack_live_secret_key",
        }:
            if defn.key == "paystack_secret_key" and not text.startswith("sk_test_"):
                raise ValueError("Test secret key must start with sk_test_")
            if defn.key == "paystack_live_secret_key" and not text.startswith(
                "sk_live_"
            ):
                raise ValueError("Live secret key must start with sk_live_")
        if text and defn.key in {
            "paystack_public_key",
            "paystack_live_public_key",
        }:
            if defn.key == "paystack_public_key" and not text.startswith("pk_test_"):
                raise ValueError("Test public key must start with pk_test_")
            if defn.key == "paystack_live_public_key" and not text.startswith(
                "pk_live_"
            ):
                raise ValueError("Live public key must start with pk_live_")
        if text and defn.key == "google_places_api_key" and not text.startswith("AIza"):
            raise ValueError("Google API key must start with AIza")
        return text
    if defn.value_type == "json":
        if not isinstance(raw, (dict, list)):
            raise ValueError("Expected JSON object or array")
        return raw
    raise ValueError(f"Unsupported value type: {defn.value_type}")


def registry_public_meta(defn: RuntimeSettingDefinition) -> dict[str, Any]:
    # Map registry types → FE value_type aliases (int/bool/secret).
    fe_type = {
        "number": "int",
        "boolean": "bool",
        "string": "string",
        "json": "json",
        "secret": "secret",
    }.get(defn.value_type, defn.value_type)
    if defn.admin_unit == "mb":
        # Admin forms edit floats/ints in MB; allow one decimal.
        fe_type = "float"
    schema = defn.validation_schema_json
    if schema is None and (
        defn.min_value is not None
        or defn.max_value is not None
        or defn.allowed_values
    ):
        if defn.admin_unit == "mb":
            schema = {
                "min": bytes_to_admin_mb(defn.min_value)
                if defn.min_value is not None
                else None,
                "max": bytes_to_admin_mb(defn.max_value)
                if defn.max_value is not None
                else None,
                "unit": "mb",
                "allowed": list(defn.allowed_values) if defn.allowed_values else None,
            }
        else:
            schema = {
                "min": defn.min_value,
                "max": defn.max_value,
                "allowed": list(defn.allowed_values) if defn.allowed_values else None,
            }
    return {
        "key": defn.key,
        "category": defn.category,
        "label": defn.label,
        "description": defn.description,
        "type": defn.value_type,
        "value_type": fe_type,
        "is_secret": defn.is_secret,
        "editable": defn.editable and defn.sensitive_level != "boot_critical",
        "env_var": defn.env_var,
        "default": (
            None
            if defn.is_secret
            else (
                bytes_to_admin_mb(defn.default)
                if defn.admin_unit == "mb"
                else defn.default
            )
        ),
        "required_for_feature": defn.required_for_feature,
        "restart_required": defn.restart_required,
        "sensitive_level": defn.sensitive_level,
        "managed_by": defn.managed_by,
        "specialist_route": defn.specialist_route,
        "admin_unit": defn.admin_unit,
        "validation_schema_json": schema,
        "fingerprint_display": setting_shows_fingerprint(defn),
    }
