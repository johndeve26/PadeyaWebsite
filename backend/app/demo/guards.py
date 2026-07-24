"""Safety guards for demo seed/reset commands."""

from __future__ import annotations

import os

from app.core.config import get_settings


class DemoEnvironmentError(RuntimeError):
    """Raised when demo operations are not allowed in the current environment."""


def assert_demo_ops_allowed(*, operation: str = "demo seed") -> None:
    """Refuse demo seed/reset in production. Never auto-seed in production.

    Hard blocks:
    - APP_ENV=production (env or settings)
    - NODE_ENV=production unless DEMO_SEED_ENABLED=true (explicit override for tooling)
    """
    env = (os.environ.get("APP_ENV") or "").strip().lower()
    if env == "production":
        raise DemoEnvironmentError(
            f"Refusing to {operation}: APP_ENV=production. "
            "Demo data is for local development only."
        )

    # Fall back to settings when APP_ENV is unset in the process env.
    if not env:
        settings = get_settings()
        env = (settings.app_env or "").strip().lower()
        if env == "production":
            raise DemoEnvironmentError(
                f"Refusing to {operation}: APP_ENV=production. "
                "Demo data is for local development only."
            )

    node_env = (os.environ.get("NODE_ENV") or "").strip().lower()
    demo_seed_enabled = (os.environ.get("DEMO_SEED_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if node_env == "production" and not demo_seed_enabled:
        raise DemoEnvironmentError(
            f"Refusing to {operation}: NODE_ENV=production without "
            "DEMO_SEED_ENABLED=true. Demo merch must never run in production "
            "unless explicitly enabled."
        )


def demo_mode_enabled() -> bool:
    settings = get_settings()
    return bool(getattr(settings, "demo_mode", False))


def demo_seed_explicitly_enabled() -> bool:
    """True when DEMO_SEED_ENABLED is set (optional explicit allow flag)."""
    return (os.environ.get("DEMO_SEED_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
