"""Email settings helpers — brand copy always uses Pàdéyá.

Resolution when ``db`` is provided:
1. Active ``email_provider_settings`` row (Admin → Email settings)
2. Code defaults + Admin runtime settings tunables (queue, log bodies, app URL)
3. LogEmailProvider when dev/log mode or provider is log
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings

BRAND_NAME = "Pàdéyá"
FORBIDDEN_BRAND_SPELLINGS = ("Padeya", "Padéyá", "Pàdéyé")


@dataclass(frozen=True)
class EmailRuntimeConfig:
    enabled: bool
    provider: str
    dev_mode: bool
    queue_enabled: bool
    log_body_in_dev: bool
    from_email: str
    from_name: str
    reply_to: str | None
    support_email: str
    app_base_url: str
    rate_limit_per_user_per_hour: int
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_use_ssl: bool = False


def _env_email_runtime(settings: Settings | None = None) -> EmailRuntimeConfig:
    s = settings or get_settings()
    from_email = (
        s.smtp_from_email or s.smtp_from or s.email_from or "noreply@padeya.com"
    ).strip()
    from_name = (s.smtp_from_name or BRAND_NAME).strip() or BRAND_NAME
    reply_to = (s.email_reply_to or s.support_email or "").strip() or None
    base = (s.app_base_url or s.frontend_url or "https://padeya.com").rstrip("/")
    use_ssl = bool(getattr(s, "smtp_use_ssl", False))
    use_tls = bool(s.smtp_use_tls) and not use_ssl
    return EmailRuntimeConfig(
        enabled=bool(s.email_enabled),
        provider=(s.email_provider or "log").strip().lower(),
        dev_mode=bool(s.email_dev_mode),
        queue_enabled=bool(s.email_queue_enabled),
        log_body_in_dev=bool(s.email_log_body_in_dev),
        from_email=from_email,
        from_name=from_name,
        reply_to=reply_to,
        support_email=(s.support_email or "support@padeya.com").strip(),
        app_base_url=base,
        rate_limit_per_user_per_hour=int(s.email_rate_limit_per_user_per_hour or 20),
        smtp_host=(s.smtp_host or "").strip(),
        smtp_port=int(s.smtp_port or (465 if use_ssl else 587)),
        smtp_username=(s.smtp_username or "").strip(),
        smtp_password=(s.smtp_password or "").strip(),
        smtp_use_tls=use_tls,
        smtp_use_ssl=use_ssl,
    )


def email_runtime(
    settings: Settings | None = None,
    *,
    db: Session | None = None,
) -> EmailRuntimeConfig:
    """Resolved email config. Pass ``db`` to apply active admin settings."""
    env_cfg = _env_email_runtime(settings)
    if db is not None:
        try:
            from app.runtime_settings import get_runtime_setting

            env_cfg = EmailRuntimeConfig(
                enabled=env_cfg.enabled,
                provider=env_cfg.provider,
                dev_mode=env_cfg.dev_mode,
                queue_enabled=bool(
                    get_runtime_setting("email_queue_enabled", db=db, settings=settings)
                ),
                log_body_in_dev=bool(
                    get_runtime_setting("email_log_body_in_dev", db=db, settings=settings)
                ),
                from_email=env_cfg.from_email,
                from_name=env_cfg.from_name,
                reply_to=env_cfg.reply_to,
                support_email=env_cfg.support_email,
                app_base_url=(
                    str(
                        get_runtime_setting("app_base_url", db=db, settings=settings)
                        or env_cfg.app_base_url
                    ).rstrip("/")
                    or env_cfg.app_base_url
                ),
                rate_limit_per_user_per_hour=int(
                    get_runtime_setting(
                        "email_rate_limit_per_user_per_hour", db=db, settings=settings
                    )
                    or 20
                ),
                smtp_host=env_cfg.smtp_host,
                smtp_port=env_cfg.smtp_port,
                smtp_username=env_cfg.smtp_username,
                smtp_password=env_cfg.smtp_password,
                smtp_use_tls=env_cfg.smtp_use_tls,
                smtp_use_ssl=env_cfg.smtp_use_ssl,
            )
        except Exception:  # noqa: BLE001
            pass
    if db is None:
        return env_cfg
    try:
        from app.email.settings_service import (
            apply_admin_override,
            get_active_provider_settings,
        )

        row = get_active_provider_settings(db)
        return apply_admin_override(env_cfg, row)
    except Exception:  # noqa: BLE001
        return env_cfg


def production_email_ready(
    settings: Settings | None = None,
    *,
    db: Session | None = None,
) -> tuple[bool, str | None]:
    s = settings or get_settings()
    cfg = email_runtime(s, db=db)
    if not cfg.enabled:
        return True, None
    if not s.is_production:
        return True, None
    if cfg.dev_mode:
        return (
            False,
            "Email dev_mode must be false in production when email sending is enabled "
            "(turn off Dev / log mode in Admin → Email settings)",
        )
    if cfg.provider == "smtp":
        if db is not None:
            try:
                from app.email.settings_service import (
                    get_active_provider_settings,
                    smtp_secret_decrypt_error,
                )

                decrypt_err = smtp_secret_decrypt_error(get_active_provider_settings(db))
                if decrypt_err:
                    return False, decrypt_err
            except Exception:  # noqa: BLE001
                pass
        if not cfg.smtp_host:
            return False, "SMTP host is required when provider=smtp in production"
        if not cfg.from_email:
            return False, "From email is required when provider=smtp in production"
        if not cfg.smtp_username:
            return False, "SMTP username is required when provider=smtp in production"
        if not cfg.smtp_password:
            return False, "SMTP password is required when provider=smtp in production"
        if cfg.smtp_use_tls and cfg.smtp_use_ssl:
            return False, "smtp_use_tls and smtp_use_ssl cannot both be true"
    if cfg.provider in {"postmark", "brevo", "resend", "sendgrid"}:
        return False, f"Provider {cfg.provider} is not implemented yet"
    return True, None


def assert_email_runtime_safe(
    settings: Settings | None = None,
    *,
    db: Session | None = None,
) -> None:
    ok, err = production_email_ready(settings, db=db)
    if not ok:
        raise RuntimeError(err or "Email configuration is invalid for production")


def provider_mode_label(
    settings: Settings | None = None,
    *,
    db: Session | None = None,
) -> str:
    cfg = email_runtime(settings, db=db)
    if not cfg.enabled:
        return "disabled"
    if cfg.dev_mode:
        return f"dev_log (configured_provider={cfg.provider})"
    return cfg.provider


def delivers_to_inbox(
    cfg: EmailRuntimeConfig,
    *,
    settings: Settings | None = None,
) -> bool:
    """True when configured provider will attempt real network delivery."""
    if not cfg.enabled:
        return False
    if cfg.dev_mode or cfg.provider in {"log", "console", "disabled"}:
        return False
    if cfg.provider == "smtp":
        return True
    return False


def assert_host_announcement_email_delivery(db: Session) -> EmailRuntimeConfig:
    """Raise 503 when host blast would not reach real inboxes."""
    from fastapi import HTTPException, status

    from app.core.config import get_settings

    cfg = email_runtime(db=db)
    if not cfg.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Email sending is disabled on this server. "
                "Enable it in Admin → Email settings (or EMAIL_ENABLED) then dispatch again."
            ),
        )
    if not delivers_to_inbox(cfg, settings=get_settings()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Email is in dev/log mode — announcements are not delivered to real inboxes. "
                "In Admin → Email: turn off dev/log mode, set provider to SMTP, and save host credentials."
            ),
        )
    settings = get_settings()
    if settings.is_production:
        ok, err = production_email_ready(settings, db=db)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err or "Email is not configured for production delivery.",
            )
    return cfg
