"""Internal media storage connectivity check.

Usage (from backend/):
  PYTHONPATH=. python scripts/check_media_storage.py

Reports only: configured / reachable / bucket accessible.
Never prints credentials or signed authorization headers.
Not a public HTTP endpoint.
"""

from __future__ import annotations

import json
import sys

from app.core.config import get_settings
from app.core.media import (
    MediaStorageError,
    get_media_storage,
    media_storage_provider,
    reset_media_storage,
    validate_media_storage_config,
)


def main() -> int:
    settings = get_settings()
    provider = media_storage_provider()
    report: dict[str, object] = {
        "provider": provider,
        "configured": False,
        "reachable": False,
        "bucket_accessible": False,
    }

    try:
        validate_media_storage_config()
    except MediaStorageError as exc:
        report["error"] = str(exc)
        print(json.dumps(report, indent=2))
        return 1

    if provider == "r2":
        report["bucket"] = (settings.r2_bucket_name or "").strip()
        from app.core.media_r2 import r2_public_domain

        report["public_domain"] = r2_public_domain(settings)
        report["configured"] = True
        reset_media_storage()
        storage = get_media_storage()
        probe = getattr(storage, "check_connectivity", None)
        if callable(probe):
            result = probe()
            report["reachable"] = bool(result.get("reachable"))
            report["bucket_accessible"] = bool(result.get("bucket_accessible"))
        else:
            report["error"] = "Connectivity probe unavailable"
            print(json.dumps(report, indent=2))
            return 1
    else:
        report["configured"] = True
        storage = get_media_storage()
        # Local: write+delete a tiny probe under a reserved prefix.
        try:
            stored = storage.store_validated_bytes(
                data=b"padeya-media-probe",
                filename="probe.bin",
                content_type="application/octet-stream",
                folder="_health",
                extension=".bin",
                max_bytes=64,
            )
            report["reachable"] = storage.exists(stored.key)
            report["bucket_accessible"] = report["reachable"]
            storage.delete(stored.key)
        except Exception as exc:
            report["error"] = type(exc).__name__
            print(json.dumps(report, indent=2))
            return 1

    print(json.dumps(report, indent=2))
    ok = bool(report["configured"] and report["reachable"] and report["bucket_accessible"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
