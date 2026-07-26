"""Internal public + private media storage connectivity check.

Usage (from backend/):
  PYTHONPATH=. python scripts/check_media_storage.py

Reports only: configured / reachable / bucket accessible.
Never prints credentials, Authorization headers, or presigned URLs.
Not a public HTTP endpoint.
"""

from __future__ import annotations

import json
import sys

from app.core.config import get_settings
from app.core.media import (
    MediaStorageError,
    get_public_media_storage,
    media_storage_provider,
    reset_media_storage,
    validate_media_storage_config,
)
from app.core.media_private import get_private_media_storage
from app.core.r2_client import r2_public_domain


def main() -> int:
    settings = get_settings()
    provider = media_storage_provider()
    report: dict[str, object] = {
        "provider": provider,
        "public": {
            "configured": False,
            "reachable": False,
            "bucket_accessible": False,
        },
        "private": {
            "configured": False,
            "reachable": False,
            "bucket_accessible": False,
        },
    }

    try:
        validate_media_storage_config()
    except MediaStorageError as exc:
        report["error"] = str(exc)
        print(json.dumps(report, indent=2))
        return 1

    reset_media_storage()
    public = get_public_media_storage()
    private = get_private_media_storage()

    if provider == "r2":
        report["public"] = {
            "configured": True,
            "reachable": False,
            "bucket_accessible": False,
            "bucket": (settings.r2_bucket_name or "").strip(),
            "public_domain": r2_public_domain(settings),
        }
        report["private"] = {
            "configured": True,
            "reachable": False,
            "bucket_accessible": False,
            "bucket": (settings.r2_private_bucket_name or "").strip(),
        }
        pub_probe = getattr(public, "check_connectivity", None)
        priv_probe = getattr(private, "check_connectivity", None)
        if callable(pub_probe):
            result = pub_probe()
            report["public"]["reachable"] = bool(result.get("reachable"))
            report["public"]["bucket_accessible"] = bool(
                result.get("bucket_accessible")
            )
        if callable(priv_probe):
            result = priv_probe()
            report["private"]["reachable"] = bool(result.get("reachable"))
            report["private"]["bucket_accessible"] = bool(
                result.get("bucket_accessible")
            )
    else:
        for label, storage in (("public", public), ("private", private)):
            probe = getattr(storage, "check_connectivity", None)
            if callable(probe):
                result = probe()
                report[label] = {
                    "configured": True,
                    "reachable": bool(result.get("reachable")),
                    "bucket_accessible": bool(result.get("bucket_accessible")),
                    "provider": "local",
                }
            else:
                try:
                    stored = storage.store_validated_bytes(
                        data=b"padeya-media-probe",
                        filename="probe.bin",
                        content_type="application/octet-stream",
                        folder="_health",
                        extension=".bin",
                        max_bytes=64,
                    )
                    ok = storage.exists(stored.key)
                    storage.delete(stored.key)
                    report[label] = {
                        "configured": True,
                        "reachable": ok,
                        "bucket_accessible": ok,
                        "provider": "local",
                    }
                except Exception as exc:
                    report[label] = {
                        "configured": True,
                        "reachable": False,
                        "bucket_accessible": False,
                        "error": type(exc).__name__,
                    }

    print(json.dumps(report, indent=2))
    pub = report["public"]
    priv = report["private"]
    ok = all(
        bool(section.get("configured"))
        and bool(section.get("reachable"))
        and bool(section.get("bucket_accessible"))
        for section in (pub, priv)
        if isinstance(section, dict)
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
