"""Progress logging for demo seed scripts."""

from __future__ import annotations


def log_seed_phase(message: str, *, script: str = "demo") -> None:
    print(f"[{script} seed] {message}", flush=True)
