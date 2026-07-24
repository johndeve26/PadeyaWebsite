"""Guards for rich sponsor demo seed — never run in production."""

from __future__ import annotations

import os

from app.core.config import get_settings
from app.demo.guards import DemoEnvironmentError, assert_demo_ops_allowed, demo_mode_enabled


class SponsorDemoSeedError(RuntimeError):
    """Rich sponsor demo seed is disabled or not allowed."""


def sponsor_demo_seed_enabled() -> bool:
    flag = (os.environ.get("SPONSOR_DEMO_SEED_ENABLED") or "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    return demo_mode_enabled()


def assert_sponsor_demo_seed_allowed(*, operation: str = "sponsor demo seed") -> None:
    assert_demo_ops_allowed(operation=operation)
    if not sponsor_demo_seed_enabled():
        raise SponsorDemoSeedError(
            f"Refusing to {operation}: set DEMO_MODE=true or SPONSOR_DEMO_SEED_ENABLED=true."
        )
