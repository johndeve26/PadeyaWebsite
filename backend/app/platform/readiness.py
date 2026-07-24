"""Production readiness preflight — read-only checks for go-live safety."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.redis import redis_health
from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_EVENT_SLUG_PREFIX, HOST_SLUGS
from app.email.config import email_runtime, production_email_ready, provider_mode_label
from app.events.models import Event
from app.hosts.models import Host
from app.payments.config import paystack_runtime
from app.users.models import User

CheckStatus = Literal["pass", "fail", "warn", "skip"]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_WEAK_SECRETS = {
    "",
    "change-me-in-production",
    "changeme",
    "secret",
    "secret_key",
    "test-secret-key-not-for-production",
}


class ReadinessVerdict(str, Enum):
    READY_FOR_PRODUCTION = "READY_FOR_PRODUCTION"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ReadinessCheck:
    id: str
    category: str
    name: str
    status: CheckStatus
    message: str
    fix: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadinessReport:
    checks: tuple[ReadinessCheck, ...]
    verdict: ReadinessVerdict
    summary: str
    ai_readiness: Any | None = None  # AIReadinessSummary when AI checks ran

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "verdict": self.verdict.value,
            "summary": self.summary,
            "checks": [
                {
                    "id": c.id,
                    "category": c.category,
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "fix": c.fix,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }
        if self.ai_readiness is not None:
            out["ai_readiness"] = self.ai_readiness.to_dict()
        return out


def _mask_url(url: str) -> str:
    """Hide credentials in database/redis URLs."""
    if not url:
        return "(empty)"
    # postgresql+psycopg2://user:pass@host:5432/db
    return re.sub(
        r"(://[^:/@]+):([^@]+)@",
        r"\1:***@",
        url.strip(),
    )


def _secret_strength(key: str, *, min_len: int = 32) -> tuple[bool, str]:
    raw = (key or "").strip()
    if raw.lower() in _WEAK_SECRETS:
        return False, "uses a known weak placeholder"
    if len(raw) < min_len:
        return False, f"must be at least {min_len} characters"
    return True, "ok"


def _check(
    *,
    id: str,
    category: str,
    name: str,
    ok: bool,
    message: str,
    fix: str | None = None,
    warn: bool = False,
    details: dict[str, Any] | None = None,
) -> ReadinessCheck:
    if ok:
        status: CheckStatus = "pass"
    elif warn:
        status = "warn"
    else:
        status = "fail"
    return ReadinessCheck(
        id=id,
        category=category,
        name=name,
        status=status,
        message=message,
        fix=fix,
        details=details or {},
    )


def _alembic_script_and_current(db: Session | None) -> tuple[Any | None, str | None]:
    if db is None:
        return None, None
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        ini = _BACKEND_ROOT / "alembic.ini"
        if not ini.is_file():
            return None, None
        cfg = Config(str(ini))
        script = ScriptDirectory.from_config(cfg)
        conn = db.connection()
        context = MigrationContext.configure(conn)
        return script, context.get_current_revision()
    except Exception:  # noqa: BLE001
        return None, None


def _migration_status(db: Session | None) -> ReadinessCheck:
    script, current = _alembic_script_and_current(db)
    if db is None:
        return _check(
            id="migrations_head",
            category="database",
            name="Migrations at head",
            ok=False,
            warn=True,
            message="Database session unavailable — could not verify Alembic revision.",
            fix="Run from backend/: PYTHONPATH=. python scripts/prod_preflight.py with DATABASE_URL set.",
        )
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        ini = _BACKEND_ROOT / "alembic.ini"
        if not ini.is_file():
            return _check(
                id="migrations_head",
                category="database",
                name="Migrations at head",
                ok=False,
                message="alembic.ini not found in backend/",
                fix="Run preflight from a complete checkout with backend/alembic.ini present.",
            )
        if script is None:
            cfg = Config(str(ini))
            script = ScriptDirectory.from_config(cfg)
        if current is None:
            conn = db.connection()
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()
        heads = set(script.get_heads())
        head_label = ", ".join(sorted(heads)) if heads else "(none)"
        if not current:
            return _check(
                id="migrations_head",
                category="database",
                name="Migrations at head",
                ok=False,
                message="Database has no Alembic revision (alembic_version empty).",
                fix="Run: alembic upgrade head (or ./scripts/prod-migrate.sh on the server).",
                details={"head": head_label},
            )
        if current not in heads:
            return _check(
                id="migrations_head",
                category="database",
                name="Migrations at head",
                ok=False,
                message=f"Database revision {current} is not at head ({head_label}).",
                fix="Run: alembic upgrade head before go-live.",
                details={"current": current, "head": head_label},
            )
        return _check(
            id="migrations_head",
            category="database",
            name="Migrations at head",
            ok=True,
            message=f"Database at revision {current} (head).",
            details={"current": current},
        )
    except Exception as exc:  # noqa: BLE001
        return _check(
            id="migrations_head",
            category="database",
            name="Migrations at head",
            ok=False,
            warn=True,
            message=f"Could not verify migrations: {exc.__class__.__name__}.",
            fix="Ensure DATABASE_URL is correct and run alembic upgrade head manually.",
        )


def _demo_data_checks(db: Session | None) -> list[ReadinessCheck]:
    if db is None:
        return [
            _check(
                id="demo_users",
                category="demo_data",
                name="No demo users",
                ok=False,
                warn=True,
                message="Skipped — no database connection.",
                fix="Set DATABASE_URL and re-run preflight.",
            ),
        ]
    checks: list[ReadinessCheck] = []
    demo_user_count = db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.email.ilike(f"%@{DEMO_EMAIL_DOMAIN}")
            | User.email.ilike("%.demo.padeye.test")
        )
    ) or 0
    checks.append(
        _check(
            id="demo_users",
            category="demo_data",
            name="No demo users",
            ok=demo_user_count == 0,
            message=(
                f"No demo-domain users ({demo_user_count} found)."
                if demo_user_count
                else "No users with @demo.padeye.test (or *.demo.padeye.test) emails."
            ),
            fix=(
                "Do not copy a local demo database to production. Use a fresh Postgres "
                "or remove demo users on a non-production clone with scripts.reset_demo_data "
                "(never run reset/seed with APP_ENV=production)."
            ),
            details={"count": demo_user_count},
        )
    )

    demo_event_count = db.scalar(
        select(func.count())
        .select_from(Event)
        .where(Event.slug.like(f"{DEMO_EVENT_SLUG_PREFIX}%"))
    ) or 0
    checks.append(
        _check(
            id="demo_events",
            category="demo_data",
            name="No demo-prefixed events",
            ok=demo_event_count == 0,
            message=(
                f"{demo_event_count} event(s) with slug prefix '{DEMO_EVENT_SLUG_PREFIX}'."
                if demo_event_count
                else f"No events with slug prefix '{DEMO_EVENT_SLUG_PREFIX}'."
            ),
            fix=(
                "Use a fresh production database or run demo reset only on staging/local "
                "(APP_ENV must not be production)."
            ),
            details={"count": demo_event_count},
        )
    )

    if HOST_SLUGS:
        demo_host_count = db.scalar(
            select(func.count())
            .select_from(Host)
            .where(Host.slug.in_(HOST_SLUGS))
        ) or 0
        checks.append(
            _check(
                id="demo_hosts",
                category="demo_data",
                name="No seeded demo host slugs",
                ok=demo_host_count == 0,
                message=(
                    f"{demo_host_count} host(s) match known demo seed slugs."
                    if demo_host_count
                    else "No hosts with known demo seed slugs."
                ),
                fix=(
                    "Demo host slugs (e.g. djmaze) should not exist in production. "
                    "Start from an empty DB or staging-cleaned dump."
                ),
                details={"count": demo_host_count, "slugs_checked": len(HOST_SLUGS)},
            )
        )

    marker_count = 0
    try:
        marker_count = db.scalar(
            text("SELECT COUNT(*) FROM demo_entity_markers")
        ) or 0
    except Exception:  # noqa: BLE001
        marker_count = -1
    if marker_count >= 0:
        checks.append(
            _check(
                id="demo_markers",
                category="demo_data",
                name="No demo entity markers",
                ok=marker_count == 0,
                message=(
                    f"{marker_count} row(s) in demo_entity_markers."
                    if marker_count
                    else "demo_entity_markers table is empty."
                ),
                fix="Demo seed markers indicate seeded demo content — use a fresh production database.",
                details={"count": marker_count},
            )
        )
    return checks


def run_production_readiness(
    *,
    db: Session | None = None,
    settings: Settings | None = None,
) -> ReadinessReport:
    """Run all preflight checks (read-only). Safe on production."""
    s = settings or get_settings()
    checks: list[ReadinessCheck] = []
    env = (s.app_env or "").strip().lower()
    is_prod = env == "production"

    checks.append(
        _check(
            id="app_env",
            category="environment",
            name="APP_ENV=production",
            ok=is_prod,
            message=f"APP_ENV is '{s.app_env or '(unset)'}'.",
            fix="Set APP_ENV=production in backend/.env.production before go-live.",
        )
    )
    checks.append(
        _check(
            id="demo_mode",
            category="environment",
            name="DEMO_MODE disabled",
            ok=not s.demo_mode,
            message=f"DEMO_MODE={s.demo_mode}.",
            fix="Set DEMO_MODE=false. Never enable demo mode in production.",
        )
    )
    checks.append(
        _check(
            id="debug",
            category="environment",
            name="DEBUG disabled",
            ok=not s.debug,
            message=f"DEBUG={s.debug}.",
            fix="Set DEBUG=false when APP_ENV=production.",
        )
    )

    sk_ok, sk_reason = _secret_strength(s.secret_key)
    checks.append(
        _check(
            id="secret_key",
            category="environment",
            name="SECRET_KEY strength",
            ok=sk_ok,
            message="SECRET_KEY is set and strong." if sk_ok else f"SECRET_KEY {sk_reason}.",
            fix="Generate: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\" "
            "and set SECRET_KEY in backend env (32+ chars, not a placeholder).",
        )
    )

    qr = s.effective_qr_secret
    qr_ok, qr_reason = _secret_strength(qr)
    checks.append(
        _check(
            id="qr_signing",
            category="environment",
            name="QR signing secret",
            ok=qr_ok,
            message=(
                "QR_SIGNING_SECRET (or SECRET_KEY fallback) is strong."
                if qr_ok
                else f"QR signing secret {qr_reason}."
            ),
            fix="Set QR_SIGNING_SECRET to a unique 32+ character value in production.",
        )
    )

    db_url = (s.database_url or "").strip()
    checks.append(
        _check(
            id="database_url",
            category="database",
            name="DATABASE_URL configured",
            ok=bool(db_url),
            message=f"DATABASE_URL {_mask_url(db_url)}.",
            fix="Set DATABASE_URL to your production Postgres connection string.",
            details={"masked": _mask_url(db_url)},
        )
    )

    redis_url = (s.redis_url or "").strip()
    redis_ok = bool(redis_url)
    checks.append(
        _check(
            id="redis_url",
            category="infrastructure",
            name="Redis URL configured",
            ok=redis_ok,
            message=f"REDIS_URL {_mask_url(redis_url)}.",
            fix="Set REDIS_URL (e.g. redis://redis:6379/0 in compose).",
            details={"masked": _mask_url(redis_url)},
        )
    )
    if is_prod and redis_ok:
        ping_ok = redis_health().get("redis") == "ok"
        checks.append(
            _check(
                id="redis_ping",
                category="infrastructure",
                name="Redis reachable",
                ok=ping_ok,
                message=(
                    "Redis ping succeeded."
                    if ping_ok
                    else f"Redis not reachable ({redis_health().get('redis', 'unknown')})."
                ),
                fix="Start Redis and verify REDIS_URL from the API container/host.",
            )
        )

    frontend = (s.frontend_url or "").strip()
    fe_https = frontend.lower().startswith("https://")
    checks.append(
        _check(
            id="frontend_url",
            category="environment",
            name="FRONTEND_URL is HTTPS",
            ok=fe_https if is_prod else bool(frontend),
            message=f"FRONTEND_URL={frontend or '(unset)'}.",
            fix="Set FRONTEND_URL=https://your-domain.com (public HTTPS, no localhost).",
        )
    )

    origins = s.cors_origin_list
    has_local = any("localhost" in o or "127.0.0.1" in o for o in origins)
    checks.append(
        _check(
            id="cors_origins",
            category="environment",
            name="CORS without localhost",
            ok=not has_local and bool(origins),
            message=(
                f"CORS_ORIGINS: {', '.join(origins) if origins else '(empty)'}."
            ),
            fix="Set CORS_ORIGINS to your public HTTPS site origins only (comma-separated).",
        )
    )

    public_demo = (os.environ.get("NEXT_PUBLIC_DEMO_MODE") or "").strip().lower()
    if public_demo in {"", "false", "0", "no", "off"}:
        ndm_ok = public_demo != "true" and public_demo not in {"1", "yes", "on"}
        ndm_msg = (
            "NEXT_PUBLIC_DEMO_MODE=false (or unset in this process)."
            if not public_demo
            else "NEXT_PUBLIC_DEMO_MODE=false."
        )
        checks.append(
            _check(
                id="next_public_demo",
                category="environment",
                name="Frontend demo flag",
                ok=ndm_ok,
                warn=not public_demo,
                message=ndm_msg,
                fix=(
                    "Rebuild frontend with NEXT_PUBLIC_DEMO_MODE=false in frontend/.env.production. "
                    "/demo must 404 in production builds."
                ),
            )
        )
    else:
        checks.append(
            _check(
                id="next_public_demo",
                category="environment",
                name="Frontend demo flag",
                ok=False,
                message=f"NEXT_PUBLIC_DEMO_MODE={public_demo}.",
                fix="Set NEXT_PUBLIC_DEMO_MODE=false and rebuild the Next.js production image.",
            )
        )

    checks.append(
        _check(
            id="demo_route",
            category="environment",
            name="/demo hub disabled",
            ok=not s.demo_mode,
            message=(
                "Backend DEMO_MODE is off (required for /demo to stay disabled with frontend flag)."
                if not s.demo_mode
                else "DEMO_MODE is on — demo hub must not run in production."
            ),
            fix="DEMO_MODE=false and NEXT_PUBLIC_DEMO_MODE=false.",
        )
    )

    # Paystack (DB runtime settings)
    if db is not None:
        pay = paystack_runtime(db)
        pay_live_ok = (
            pay.is_live_mode
            and pay.secret_configured
            and pay.public_configured
            and bool(pay.effective_webhook_secret.strip())
        )
        checks.append(
            _check(
                id="paystack_live",
                category="integrations",
                name="Paystack live + webhook",
                ok=pay_live_ok if is_prod else pay.secret_configured,
                message=(
                    f"Paystack mode={pay.mode}; "
                    f"secret={'yes' if pay.secret_configured else 'no'}; "
                    f"public={'yes' if pay.public_configured else 'no'}; "
                    f"webhook_secret={'yes' if bool(pay.webhook_secret.strip()) else 'fallback/secret'}."
                ),
                fix=(
                    "Admin → Payment integration: set mode Live, sk_live/pk_live keys, "
                    "and live webhook secret. Register webhook URL in Paystack dashboard."
                ),
                details={"mode": pay.mode},
            )
        )
    else:
        checks.append(
            _check(
                id="paystack_live",
                category="integrations",
                name="Paystack live + webhook",
                ok=False,
                warn=True,
                message="Skipped — no database (runtime settings live in DB).",
                fix="Re-run with DATABASE_URL to verify Paystack keys in Admin → Payment integration.",
            )
        )

    # Email
    cfg = email_runtime(s, db=db)
    email_ok, email_err = production_email_ready(s, db=db)
    log_mode = cfg.provider in {"log", "console"} or cfg.dev_mode
    prod_email_ok = email_ok and not log_mode and cfg.enabled
    if not cfg.enabled:
        prod_email_ok = True  # disabled is acceptable if intentional
        email_msg = "Email sending disabled in config."
    elif log_mode:
        email_msg = f"Email in log/dev mode ({provider_mode_label(s, db=db)})."
    elif email_ok:
        email_msg = f"Email provider={cfg.provider}; queue={'on' if cfg.queue_enabled else 'off'}."
    else:
        email_msg = email_err or "Email not production-ready."

    checks.append(
        _check(
            id="email_smtp",
            category="integrations",
            name="Email SMTP (not log mode)",
            ok=prod_email_ok if is_prod and cfg.enabled else email_ok or not cfg.enabled,
            message=email_msg,
            fix=(
                "Admin → Email settings: provider=smtp, dev/log mode off, SMTP host/credentials set. "
                "Set EMAIL_SETTINGS_ENCRYPTION_KEY on the host for encrypted SMTP secrets."
            ),
            details={
                "provider": cfg.provider,
                "dev_mode": cfg.dev_mode,
                "enabled": cfg.enabled,
            },
        )
    )

    enc_key = (s.email_settings_encryption_key or "").strip()
    if is_prod and cfg.enabled and cfg.provider == "smtp" and db is not None:
        checks.append(
            _check(
                id="email_encryption_key",
                category="integrations",
                name="EMAIL_SETTINGS_ENCRYPTION_KEY",
                ok=bool(enc_key) and enc_key.lower() not in _WEAK_SECRETS,
                message=(
                    "Host encryption key set for admin SMTP secrets."
                    if enc_key
                    else "EMAIL_SETTINGS_ENCRYPTION_KEY is missing."
                ),
                fix="Set EMAIL_SETTINGS_ENCRYPTION_KEY in backend env (Fernet key) before storing SMTP in admin.",
            )
        )

    checks.append(
        _check(
            id="email_worker",
            category="integrations",
            name="Email outbox worker expected",
            ok=cfg.queue_enabled if (is_prod and cfg.enabled) else True,
            warn=not cfg.queue_enabled and cfg.enabled,
            message=(
                f"email_queue_enabled={cfg.queue_enabled}. "
                "Ensure email_worker container or cron runs scripts/process_email_outbox.py."
            ),
            fix=(
                "Enable queue in runtime settings and run the email_worker service "
                "(see docker-compose.prod.yml and docs/OPERATIONS.md)."
            ),
        )
    )

    compose_prod = _REPO_ROOT / "docker-compose.prod.yml"
    worker_in_compose = False
    if compose_prod.is_file():
        body = compose_prod.read_text(encoding="utf-8", errors="replace")
        worker_in_compose = "email_worker" in body
    checks.append(
        _check(
            id="email_worker_compose",
            category="integrations",
            name="email_worker in prod compose",
            ok=worker_in_compose,
            warn=not worker_in_compose,
            message=(
                "docker-compose.prod.yml defines email_worker."
                if worker_in_compose
                else "Could not find email_worker in docker-compose.prod.yml."
            ),
            fix="Deploy with docker-compose.prod.yml and keep email_worker running.",
        )
    )

    backup_script = _REPO_ROOT / "scripts" / "prod-backup-db.sh"
    checks.append(
        _check(
            id="backup_script",
            category="operations",
            name="Database backup script",
            ok=backup_script.is_file(),
            message=(
                "scripts/prod-backup-db.sh present."
                if backup_script.is_file()
                else "Backup script missing."
            ),
            fix="Schedule ./scripts/prod-backup-db.sh and store dumps off-box before go-live.",
        )
    )

    checks.extend(_demo_data_checks(db))
    alembic_script, alembic_current = _alembic_script_and_current(db)
    checks.append(_migration_status(db))

    from app.platform.ai_readiness import run_ai_readiness_checks

    ai_checks, ai_summary = run_ai_readiness_checks(
        db,
        alembic_script=alembic_script,
        current_revision=alembic_current,
    )
    checks.extend(ai_checks)

    failures = [c for c in checks if c.status == "fail"]
    verdict = (
        ReadinessVerdict.READY_FOR_PRODUCTION
        if not failures
        else ReadinessVerdict.BLOCKED
    )
    if not failures:
        summary = "All required checks passed. Review any warnings before traffic."
    else:
        summary = f"{len(failures)} blocking check(s) failed — resolve before go-live."

    return ReadinessReport(
        checks=tuple(checks),
        verdict=verdict,
        summary=summary,
        ai_readiness=ai_summary,
    )


def format_report_cli(report: ReadinessReport) -> str:
    lines = [
        "Pàdéyá production preflight",
        "=" * 28,
        "",
    ]
    if report.ai_readiness is not None:
        lines.append(f"AI_READY: {report.ai_readiness.status}")
        lines.append(f"      {report.ai_readiness.message}")
        lines.append("")
    for check in report.checks:
        tag = check.status.upper()
        lines.append(f"[{tag}] {check.name}")
        lines.append(f"      {check.message}")
        if check.fix and check.status in {"fail", "warn"}:
            lines.append(f"      Fix: {check.fix}")
        lines.append("")
    lines.append("=" * 28)
    lines.append(f"STATUS: {report.verdict.value}")
    lines.append(report.summary)
    return "\n".join(lines)
