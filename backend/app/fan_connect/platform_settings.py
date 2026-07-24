"""Platform-wide Fan Connect settings (runtime_settings-backed)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.runtime_settings.service import get_runtime_setting

DECLINE_COOLDOWN_DAYS_KEY = "fan_connect_decline_cooldown_days"
DECLINE_COOLDOWN_MIN_DAYS = 0
DECLINE_COOLDOWN_MAX_DAYS = 365
DECLINE_COOLDOWN_DEFAULT_DAYS = 30

# User-selectable decline durations (days). 365 = “Never” in UI copy.
DECLINE_COOLDOWN_USER_OPTIONS: frozenset[int] = frozenset({7, 30, 90, 365})


def get_default_decline_cooldown_days(db: Session | None = None) -> int:
    raw = get_runtime_setting(DECLINE_COOLDOWN_DAYS_KEY, db=db)
    try:
        days = int(raw if raw is not None else DECLINE_COOLDOWN_DEFAULT_DAYS)
    except (TypeError, ValueError):
        days = DECLINE_COOLDOWN_DEFAULT_DAYS
    return max(DECLINE_COOLDOWN_MIN_DAYS, min(DECLINE_COOLDOWN_MAX_DAYS, days))


def validate_decline_cooldown_days(days: int) -> int:
    if days < DECLINE_COOLDOWN_MIN_DAYS or days > DECLINE_COOLDOWN_MAX_DAYS:
        raise ValueError(
            f"cooldown_days must be between {DECLINE_COOLDOWN_MIN_DAYS} and "
            f"{DECLINE_COOLDOWN_MAX_DAYS}"
        )
    return days
