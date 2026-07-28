"""Refuse Phase 4.5 concurrency runs against production / Neon hosts.

Never logs passwords. Call ``assert_safe_postgres_url`` before connecting.
"""

from __future__ import annotations

from urllib.parse import urlparse, unquote

# Host/path patterns that must never receive Phase 4.5 mutation tests.
_BLOCKED_HOST_FRAGMENTS = (
    "neon.tech",
    "neon.database",
    "aws.neon",
    "azure.neon",
    "render.com",  # managed prod-like
)

_BLOCKED_DB_NAMES = (
    # explicit production-ish names if pointed at shared hosts
)

_REQUIRED_TEST_DB_HINTS = (
    "phase45",
    "phase4_5",
    "test",
    "_test",
)


class UnsafeDatabaseError(RuntimeError):
    """Raised when the configured URL looks like production."""


def redact_database_url(url: str) -> str:
    """Return scheme://user@host:port/db without password."""
    raw = (url or "").strip()
    if not raw:
        return ""
    # SQLAlchemy dialect prefix
    display = raw.replace("postgresql+psycopg2://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    try:
        parsed = urlparse(display)
    except Exception:
        return "<unparseable>"
    user = unquote(parsed.username or "")
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or ""
    auth = f"{user}@" if user else ""
    return f"{parsed.scheme}://{auth}{host}{port}{path}"


def assert_safe_postgres_url(
    url: str,
    *,
    app_env: str | None = None,
    allow_non_hint_local: bool = False,
) -> dict:
    """Validate URL is isolated local/test Postgres. Returns metadata (no secrets)."""
    env = (app_env or "").strip().lower()
    if env == "production":
        raise UnsafeDatabaseError("APP_ENV=production — Phase 4.5 refused")

    if not url or "sqlite" in url.lower():
        raise UnsafeDatabaseError("Phase 4.5 requires PostgreSQL TEST_DATABASE_URL")

    normalized = url.replace("postgresql+psycopg2://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    db_name = (parsed.path or "").lstrip("/").split("?")[0].lower()

    for frag in _BLOCKED_HOST_FRAGMENTS:
        if frag in host:
            raise UnsafeDatabaseError(
                f"Blocked host pattern '{frag}' — not an isolated Phase 4.5 DB"
            )

    if host not in {"127.0.0.1", "localhost", "::1"} and not host.endswith(".local"):
        # Allow docker compose service name only when DB name is clearly a test DB
        if not any(h in db_name for h in _REQUIRED_TEST_DB_HINTS):
            raise UnsafeDatabaseError(
                f"Non-loopback host '{host}' without test DB name hint — refused"
            )

    if db_name in {"neondb", "production", "prod"}:
        raise UnsafeDatabaseError(f"Database name '{db_name}' is not allowed")

    if not allow_non_hint_local and host in {"127.0.0.1", "localhost", "::1"}:
        if not any(h in db_name for h in _REQUIRED_TEST_DB_HINTS):
            raise UnsafeDatabaseError(
                f"Local DB '{db_name}' must include a test/phase45 hint "
                "(refusing to mutate shared 'padeya' or similar)"
            )

    return {
        "safe": True,
        "redacted_url": redact_database_url(url),
        "host": host,
        "database": db_name,
        "app_env": env or None,
        "is_loopback": host in {"127.0.0.1", "localhost", "::1"},
    }
