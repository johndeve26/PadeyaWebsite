"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_SECRETS = {
    "",
    "change-me-in-production",
    "changeme",
    "secret",
    "secret_key",
    "test-secret-key-not-for-production",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Pàdéyá API"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    # Optional deploy labels for timing logs (never required for boot).
    app_version: str = "0.17.0"
    build_sha: str = ""

    # Local demo helper (/demo) + seed tooling. Never enable in production.
    demo_mode: bool = False

    # Host submit publishes immediately; admins review flagged listings later.
    events_auto_publish_on_submit: bool = True

    # PostgreSQL
    database_url: str = (
        "postgresql+psycopg2://padeya:padeya@localhost:5432/padeya"
    )

    # Redis — rate limits, and messaging WebSocket multi-worker pub/sub.
    # If Redis is down, messaging falls back to in-memory fan-out (single worker only).
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Secrets — never hardcode real values; set via environment
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 180
    # Impersonation
    impersonation_token_expire_minutes: int = 30

    # Super admins may restrict/ban other platform admins (default on).
    super_admin_may_restrict_platform_admins: bool = True

    # Frontend / callbacks
    frontend_url: str = "http://localhost:3000"

    # Local media uploads (swap storage backend later without changing routes)
    media_root: str = "media_uploads"
    # Public origin prefix for /media/... URLs in API responses (optional).
    # Leave empty to use relative paths (/media/...) — best with Next.js /media rewrites.
    media_public_base_url: str = ""

    # Paystack — Admin → Payment integration only (runtime_settings); not in .env

    # QR signing (falls back to secret_key when empty)
    qr_signing_secret: str = ""

    # Email — Admin → Email settings + runtime settings (not .env); see docs/EMAILS.md.
    email_provider: str = "log"
    email_enabled: bool = True
    email_dev_mode: bool = True
    email_queue_enabled: bool = True
    email_log_body_in_dev: bool = False
    email_from: str = "noreply@padeya.com"
    smtp_from_email: str = "noreply@padeya.com"
    smtp_from_name: str = "Pàdéyá"
    support_email: str = "support@padeya.com"
    email_reply_to: str = "support@padeya.com"
    app_base_url: str = ""  # falls back to frontend_url
    email_rate_limit_per_user_per_hour: int = 20
    # Stable Fernet key for admin SMTP secrets (see app/core/encryption.py)
    email_settings_encryption_key: str = ""
    # Legacy Settings fields (tests / internal defaults); configure SMTP in admin only.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_from: str = ""  # legacy alias → smtp_from_email
    # Outbox worker poll interval (seconds) when running --loop
    email_worker_poll_seconds: int = 20
    email_worker_batch_size: int = 50

    # Browser push outbox (see docs/NOTIFICATIONS.md + app/push/)
    push_queue_enabled: bool = True
    push_worker_poll_seconds: int = 20
    push_worker_batch_size: int = 50
    # Soft cap on message-category push per user (enqueue skips when exceeded)
    push_message_rate_limit_per_hour: int = 12

    # AI Copilot (optional — never required for core flows)
    ai_enabled: bool = False
    ai_provider: str = "template"  # template | openai | anthropic | gemini | grok | none
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_max_tokens: int = 800
    ai_timeout_seconds: int = 30
    ai_rate_limit_per_hour: int = 60  # placeholder soft rate limit

    # Merch cart recovery TTLs (MERCH_CART_ABANDON_AFTER aliases hours)
    merch_cart_abandon_after_hours: int = Field(
        default=24,
        validation_alias=AliasChoices(
            "MERCH_CART_ABANDON_AFTER",
            "MERCH_CART_ABANDON_AFTER_HOURS",
            "merch_cart_abandon_after_hours",
        ),
    )
    merch_cart_expire_after_days: int = 14
    merch_cart_recovery_min_gap_hours: int = 72

    # Messaging chat attachments (safe v1 allowlist — see messaging/attachments.py)
    messaging_attachment_max_image_bytes: int = 5 * 1024 * 1024  # 5 MB
    messaging_attachment_max_doc_bytes: int = 10 * 1024 * 1024  # 10 MB
    messaging_attachment_max_total_bytes: int = 15 * 1024 * 1024  # 15 MB / message
    messaging_attachment_max_count: int = 4
    # Unbound staged uploads (message_id null) expire after this many hours.
    messaging_attachment_orphan_hours: int = 24
    # How often the in-process orphan sweeper runs (0 disables).
    messaging_attachment_cleanup_interval_seconds: int = 3600
    # Private attachment storage: local | s3 | r2 (s3/r2 adapters reserved)
    messaging_attachment_storage_provider: str = "local"
    messaging_attachment_storage_root: str = "storage/message_attachments"
    # Short-lived signed download query tokens for <img src> (seconds)
    messaging_attachment_download_ttl_seconds: int = 900
    # Strip EXIF/metadata from images when Pillow can re-encode (recommended)
    messaging_attachment_strip_image_metadata: bool = True
    # AV hook: noop (default) | clamav (reserved — not wired yet)
    messaging_attachment_scanner: str = "noop"

    # Analytics dedupe windows (seconds)
    analytics_impression_dedupe_seconds: int = 300  # 5 minutes
    analytics_detail_view_dedupe_seconds: int = 1800  # 30 minutes
    analytics_checkout_start_dedupe_seconds: int = 3600  # 1 hour
    analytics_unique_click_dedupe_seconds: int = 86400  # 24 hours for unique_clicks
    analytics_track_rate_limit_per_minute: int = 120
    analytics_track_batch_max_items: int = 50
    analytics_metadata_max_keys: int = 40
    analytics_metadata_max_bytes: int = 8192
    # Ambassadors fraud / tracking (phase 14)
    ambassador_track_rate_limit_per_minute: int = 60
    events_nearby_rate_limit_per_minute: int = 60
    ambassador_click_spike_window_seconds: int = 300
    ambassador_click_spike_threshold: int = 40
    # Admin alert when a reward marked paid meets/exceeds this commission (NGN). 0 = off.
    ambassador_high_value_reward_ngn: int = 50000

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_qr_secret(self) -> str:
        return self.qr_signing_secret or self.secret_key

    @property
    def is_production(self) -> bool:
        return (self.app_env or "").strip().lower() == "production"

    @model_validator(mode="after")
    def enforce_production_safety(self) -> "Settings":
        env = (self.app_env or "").strip().lower()
        if env in {"development", "dev", "test", "local"}:
            return self

        if self.secret_key.strip().lower() in _WEAK_SECRETS:
            raise ValueError(
                "SECRET_KEY must be set to a strong unique value when "
                f"APP_ENV={self.app_env}. Refusing to start with a weak default."
            )
        if len(self.secret_key.strip()) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters in non-development environments."
            )

        if env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false when APP_ENV=production.")
            if self.demo_mode:
                raise ValueError(
                    "DEMO_MODE must be false when APP_ENV=production. "
                    "Demo seed/hub is local-only."
                )
            # Email provider/SMTP/dev mode: Admin → Email settings (DB).
            # production_email_ready() + email_worker validate merged config.
            origins = self.cors_origin_list
            if not origins:
                raise ValueError(
                    "CORS_ORIGINS must be an explicit comma-separated allowlist "
                    "when APP_ENV=production."
                )
            if any("localhost" in o or "127.0.0.1" in o for o in origins):
                raise ValueError(
                    "CORS_ORIGINS must not include localhost/127.0.0.1 "
                    "when APP_ENV=production."
                )
            frontend = (self.frontend_url or "").strip().lower()
            if not frontend or "localhost" in frontend or "127.0.0.1" in frontend:
                raise ValueError(
                    "FRONTEND_URL must be a public HTTPS origin when APP_ENV=production."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
