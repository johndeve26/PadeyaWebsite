#!/usr/bin/env python3
"""Run Pàdéyá production preflight from the repo root.

Delegates to backend/scripts/prod_preflight.py (read-only checks).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SCRIPT = BACKEND / "scripts" / "prod_preflight.py"


def main() -> int:
    if not SCRIPT.is_file():
        print(f"Missing {SCRIPT}", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", ".")
    return subprocess.call(
        [sys.executable, str(SCRIPT)],
        cwd=str(BACKEND),
        env=env,
    )


if __name__ == "__main__":
    sys.exit(main())
