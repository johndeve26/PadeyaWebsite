"""Production safety validators for Settings."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _strong() -> str:
    return "unit-test-production-secret-key-32chars-min"


def test_production_rejects_weak_secret() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            app_env="production",
            debug=False,
            demo_mode=False,
            secret_key="change-me-in-production",
            email_enabled=False,
            email_dev_mode=False,
            cors_origins="https://padeya.com",
            frontend_url="https://padeya.com",
        )


def test_production_rejects_demo_mode() -> None:
    with pytest.raises(ValidationError, match="DEMO_MODE"):
        Settings(
            app_env="production",
            debug=False,
            demo_mode=True,
            secret_key=_strong(),
            email_enabled=False,
            email_dev_mode=False,
            cors_origins="https://padeya.com",
            frontend_url="https://padeya.com",
        )


def test_production_rejects_localhost_cors() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            app_env="production",
            debug=False,
            demo_mode=False,
            secret_key=_strong(),
            email_enabled=False,
            email_dev_mode=False,
            cors_origins="http://localhost:3000",
            frontend_url="https://padeya.com",
        )


def test_production_accepts_safe_config() -> None:
    settings = Settings(
        app_env="production",
        debug=False,
        demo_mode=False,
        secret_key=_strong(),
        email_enabled=False,
        email_dev_mode=False,
        cors_origins="https://padeya.com,https://www.padeya.com",
        frontend_url="https://padeya.com",
    )
    assert settings.is_production
    assert settings.demo_mode is False
