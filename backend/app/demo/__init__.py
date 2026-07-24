"""Pàdéyá local demo content package — never auto-run in production."""

from app.demo.guards import DemoEnvironmentError, assert_demo_ops_allowed, demo_mode_enabled
from app.demo.reset import reset_demo_data
from app.demo.seed import seed_demo_data

__all__ = [
    "DemoEnvironmentError",
    "assert_demo_ops_allowed",
    "demo_mode_enabled",
    "reset_demo_data",
    "seed_demo_data",
]
