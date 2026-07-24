"""Admin Runtime Settings — typed allowlist overrides for Class B tunables.

Boot-critical Class A config stays on ``Settings`` / ``.env`` only.
Optional secrets (if ever allowlisted) use ``value_encrypted`` + ``last_four``;
admin APIs never return plaintext secrets.

Deferred / not in Settings (do not invent): S3/Cloudinary/Slack/reCAPTCHA keys,
``PAYSTACK_ENABLED``, ``MAINTENANCE_MODE``, maps provider keys.
Email SMTP / Push VAPID secrets stay on specialist admin modules.
"""

from app.runtime_settings.service import (
    RuntimeSettingsService,
    get_runtime_secret,
    get_runtime_setting,
    invalidate_runtime_settings_cache,
    runtime_settings_service,
)

__all__ = [
    "RuntimeSettingsService",
    "get_runtime_secret",
    "get_runtime_setting",
    "invalidate_runtime_settings_cache",
    "runtime_settings_service",
]
