"""Repair public R2 image objects so browsers preview instead of downloading.

Older uploads (and media migrations) often lack ``Content-Disposition: inline``
or were stored as ``application/octet-stream``. This rewrites metadata in place
for every object key with a known image extension in the public bucket.

Usage (from backend/, with R2 env configured):

  python -m scripts.repair_public_media_inline_headers --dry-run
  python -m scripts.repair_public_media_inline_headers
  python -m scripts.repair_public_media_inline_headers --prefix taxonomy/
"""

from __future__ import annotations

import argparse
import sys

from app.core.r2_client import (
    IMMUTABLE_PUBLIC_CACHE_CONTROL,
    R2BucketClient,
    guess_image_content_type,
    public_r2_config,
)


def _iter_keys(client: R2BucketClient, *, prefix: str) -> list[str]:
    keys: list[str] = []
    continuation: str | None = None
    while True:
        kwargs: dict = {
            "Bucket": client.bucket,
            "MaxKeys": 1000,
        }
        if prefix:
            kwargs["Prefix"] = prefix
        if continuation:
            kwargs["ContinuationToken"] = continuation
        page = client._client.list_objects_v2(**kwargs)
        for item in page.get("Contents") or []:
            key = item.get("Key") or ""
            if key and guess_image_content_type(key):
                keys.append(key)
        if not page.get("IsTruncated"):
            break
        continuation = page.get("NextContinuationToken")
        if not continuation:
            break
    return keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite public R2 image headers for inline browser preview."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matching keys without rewriting metadata.",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional key prefix filter (e.g. events/ or taxonomy/).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max objects to rewrite (0 = all).",
    )
    args = parser.parse_args(argv)

    r2 = R2BucketClient(public_r2_config())
    keys = _iter_keys(r2, prefix=(args.prefix or "").lstrip("/"))
    if args.limit > 0:
        keys = keys[: args.limit]

    print(f"public_bucket={r2.bucket} image_objects={len(keys)} dry_run={args.dry_run}")
    ok = 0
    fail = 0
    for key in keys:
        if args.dry_run:
            print(f"would_repair {key}")
            ok += 1
            continue
        if r2.rewrite_public_image_headers(
            key, cache_control=IMMUTABLE_PUBLIC_CACHE_CONTROL
        ):
            print(f"repaired {key}")
            ok += 1
        else:
            print(f"failed {key}", file=sys.stderr)
            fail += 1

    print(f"done ok={ok} fail={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
