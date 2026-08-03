"""Pàdéyá FastAPI application entrypoint."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from sqlalchemy import text

from app.admin.events_buyers_router import router as admin_events_buyers_router
from app.admin.impersonation_middleware import ImpersonationAuditMiddleware
from app.admin import impersonation_models as admin_impersonation_models  # noqa: F401
from app.admin.router import router as admin_router
from app.admin.users_router import router as admin_users_router
from app.maintenance.middleware import MaintenanceMiddleware
from app.maintenance.router import router as maintenance_router
from app.maintenance import models as maintenance_models  # noqa: F401
from app.platform.router import router as platform_readiness_router
from app.appeals.middleware import SuspendedAccountMiddleware
from app.appeals import models as appeals_models  # noqa: F401
from app.appeals.router import router as appeals_router
from app.auth.session_middleware import AuthSessionMiddleware
from app.ai.router import router as ai_router
from app.ai.seed import seed_ai_prompt_templates
from app.analytics.admin_event_router import router as admin_event_analytics_router
from app.analytics.host_event_router import router as host_event_analytics_router
from app.analytics.router import router as analytics_router
from app.sponsor_profiles.router import admin_router as sponsor_admin_router
from app.sponsor_profiles.router import router as sponsor_profiles_router
from app.sponsor_profiles.saved_router import router as sponsor_saved_router
from app.sponsor_profiles.campaign_router import router as sponsor_campaign_router
from app.sponsor_profiles.campaign_admin_router import (
    router as sponsor_campaign_admin_router,
)
from app.sponsor_profiles.deals_router import router as sponsor_deals_router
from app.sponsor_profiles.report_router import router as sponsor_report_router
from app.sponsorships.deals_admin_router import deals_router as sponsorship_deals_admin_router
from app.sponsorships.deals_admin_router import invoices_router as sponsorship_invoices_admin_router
from app.sponsorships.host_deals_router import router as host_sponsorship_deals_router
from app.sponsor_profiles.team_router import invite_router as sponsor_team_invite_router
from app.sponsor_profiles.team_router import router as sponsor_team_router
from app.sponsorships.router import router as sponsorships_router
from app.auth.router import router as auth_router
from app.checkins.router import router as checkins_router
from app.cms.router import router as cms_router
from app.blog.router import router as blog_router
from app.blog import models as blog_models  # noqa: F401
from app.knowledge_base.router import router as knowledge_base_router
from app.knowledge_base import models as knowledge_base_models  # noqa: F401
from app.knowledge_base.seed import seed_knowledge_base
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exception_handlers import unhandled_exception_handler
from app.core.http_errors import http_exception_handler
from app.core.cache_headers import CacheControlMiddleware
from app.core.redis import redis_health
from app.core.timing_middleware import RequestTimingMiddleware
from app.crm.router import router as crm_router
from app.email.router import router as email_router
from app.email.admin_templates_router import router as admin_email_templates_router
from app.notifications.router import router as notifications_router
from app.push.router import router as push_router
from app.push.admin_router import router as push_admin_router
from app.notifications import models as notifications_models  # noqa: F401
from app.admin_notifications.router import router as admin_notifications_router
from app.admin_notifications import models as admin_notifications_models  # noqa: F401
from app.admin_notifications.settings_service import ensure_default_settings
from app.admin_team.router import router as admin_team_router
from app.admin_team.invite_router import router as admin_team_invite_router
from app.admin_team import models as admin_team_models  # noqa: F401
from app.admin_team.service import ensure_system_admin_roles
from app.runtime_settings.router import router as runtime_settings_router
from app.runtime_settings import models as runtime_settings_models  # noqa: F401
from app.events.router import router as events_router
from app.finance.router import router as finance_router
from app.finance.fees.router import router as finance_fees_router
from app.pricing.router import router as pricing_router
from app.finance.fees import models as finance_fee_models  # noqa: F401
from app.hosts.router import router as hosts_router
from app.hosts.recommendations.admin_router import (
    router as host_recommendations_admin_router,
)
from app.events.recommendations.admin_router import (
    router as event_recommendations_admin_router,
)
from app.teams.admin_router import router as teams_admin_router
from app.teams.host_router import router as host_team_router
from app.teams.invite_router import router as team_invites_router
from app.teams.me_router import router as me_workspaces_router
from app.legacy.host_router import router as legacy_host_router
from app.legacy.router import public_u_router as legacy_public_u_router
from app.legacy.router import router as legacy_router
from app.memories.router import router as memories_router
from app.merch.alias_router import router as merch_alias_router
from app.merch.commerce_router import router as merch_commerce_router
from app.merch.marketplace_router import router as merch_marketplace_router
from app.merch.router import router as merch_router
from app.fan_connect.admin_router import router as fan_connect_admin_router
from app.fan_connect.router import router as fan_connect_router
from app.messaging.router import router as messaging_router
from app.messaging.ws import router as messaging_ws_router
from app.messaging.ws_bus import messaging_bus
from app.messaging.ws_hub import set_main_loop, start_messaging_bus, stop_messaging_bus
from app.passport.router import router as passport_router
from app.payments.router import router as payments_router

from app.ambassadors.admin_router import router as ambassadors_admin_router
from app.ambassadors.event_router import router as ambassadors_event_router
from app.ambassadors.host_router import router as ambassadors_host_router
from app.ambassadors.router import router as ambassadors_router
from app.promos.admin_router import router as promos_admin_router
from app.promos.router import router as promos_router
from app.promos.referrals_router import router as referrals_router
from app.reviews.router import router as reviews_router
from app.support.router import router as support_router
from app.placements.router import router as placements_router
from app.taxonomy.router import router as taxonomy_router
from app.tickets.router import router as tickets_router
from app.users.router import router as users_router
from app.events.seed import seed_event_categories
from app.legacy.seed import seed_legacy_tiers
from app.passport.seed import seed_fan_badges
from app.users.seed import seed_roles_and_permissions
from app.vault.router import router as vault_router

settings = get_settings()
MEDIA_ROOT = Path(settings.media_root)
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


class SafeMediaStaticFiles(StaticFiles):
    """Serve local public uploads inline with authoritative image MIME + nosniff."""

    _IMAGE_TYPES = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
    }

    async def get_response(self, path: str, scope) -> Response:  # type: ignore[override]
        response = await super().get_response(path, scope)
        response.headers["X-Content-Type-Options"] = "nosniff"
        lower = (path or "").lower()
        for ext, mime in self._IMAGE_TYPES.items():
            if lower.endswith(ext):
                response.headers["Content-Type"] = mime
                response.headers["Content-Disposition"] = "inline"
                break
        return response


def _run_orphan_attachment_cleanup() -> None:
    from app.messaging.service import cleanup_orphan_attachments

    db = SessionLocal()
    try:
        cleanup_orphan_attachments(db)
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_email_outbox_drain() -> None:
    from app.email.queue import process_pending_emails

    db = SessionLocal()
    try:
        process_pending_emails(db, limit=40)
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_push_outbox_drain() -> None:
    from app.push.worker import process_pending_push

    db = SessionLocal()
    try:
        process_pending_push(db, limit=40)
    except Exception:
        db.rollback()
    finally:
        db.close()


async def _orphan_attachment_sweeper() -> None:
    """Periodically expire unbound staged chat attachments."""
    interval = int(settings.messaging_attachment_cleanup_interval_seconds or 0)
    if interval <= 0:
        return
    while True:
        await asyncio.sleep(interval)
        # Sync SQLAlchemy must not run on the event loop (freezes all requests).
        await asyncio.to_thread(_run_orphan_attachment_cleanup)


async def _email_outbox_sweeper() -> None:
    """Drain pending email_events when the queue worker is not running separately."""
    while True:
        await asyncio.sleep(20)
        await asyncio.to_thread(_run_email_outbox_drain)


async def _push_outbox_sweeper() -> None:
    """Drain pending push_events when the queue worker is not running separately."""
    while True:
        await asyncio.sleep(20)
        await asyncio.to_thread(_run_push_outbox_drain)

@asynccontextmanager
async def lifespan(_: FastAPI):
    set_main_loop(asyncio.get_running_loop())
    start_messaging_bus()
    sweeper: asyncio.Task | None = None
    email_sweeper: asyncio.Task | None = None
    push_sweeper: asyncio.Task | None = None
    if settings.app_env != "test":
        from app.core.media import (
            get_public_media_storage,
            log_media_storage_status,
            media_storage_provider,
            validate_media_storage_config,
        )
        from app.core.media_private import get_private_media_storage

        validate_media_storage_config()
        if media_storage_provider() == "r2":
            get_public_media_storage()
            get_private_media_storage()
        log_media_storage_status()
        db = SessionLocal()
        try:
            seed_roles_and_permissions(db)
            seed_event_categories(db)
            seed_legacy_tiers(db)
            seed_fan_badges(db)
            seed_ai_prompt_templates(db)
            ensure_default_settings(db)
            ensure_system_admin_roles(db)
            if settings.app_env.strip().lower() in {"development", "dev", "local"}:
                from sqlalchemy import func, select

                from app.taxonomy.models import Location
                from app.taxonomy.service import seed_taxonomy_vocab

                country_count = int(
                    db.scalar(
                        select(func.count())
                        .select_from(Location)
                        .where(Location.kind == "country")
                    )
                    or 0
                )
                if country_count == 0:
                    seed_taxonomy_vocab(db)
            db.commit()
            try:
                seed_knowledge_base(db)
            except Exception:
                db.rollback()
        except Exception:
            # DB may be unavailable at boot; seed via scripts after migrate.
            db.rollback()
        finally:
            db.close()
        if int(settings.messaging_attachment_cleanup_interval_seconds or 0) > 0:
            sweeper = asyncio.create_task(_orphan_attachment_sweeper())
        if settings.email_enabled and settings.email_queue_enabled:
            email_sweeper = asyncio.create_task(_email_outbox_sweeper())
        if settings.push_queue_enabled:
            push_sweeper = asyncio.create_task(_push_outbox_sweeper())
    try:
        yield
    finally:
        for task in (sweeper, email_sweeper, push_sweeper):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        stop_messaging_bus()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version or "0.17.0",
    description="Pàdéyá platform API — commerce, advanced ticketing, Legacy, analytics, AI, and sponsorships.",
    lifespan=lifespan,
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Server-Timing"],
)
# Outer → inner (last added = outermost after CORS):
# RequestTiming → CacheControl → AuthSession → Impersonation → Suspended → Maintenance → app
app.add_middleware(MaintenanceMiddleware)
app.add_middleware(SuspendedAccountMiddleware)
app.add_middleware(ImpersonationAuditMiddleware)
app.add_middleware(AuthSessionMiddleware)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(RequestTimingMiddleware)

api = settings.api_prefix

app.include_router(maintenance_router, prefix=api)
app.include_router(platform_readiness_router, prefix=api)
app.include_router(auth_router, prefix=api)
# Register template/notification routes before `/admin/emails/{email_id}` catch-all.
app.include_router(admin_email_templates_router, prefix=api)
app.include_router(email_router, prefix=api)
app.include_router(notifications_router, prefix=api)
app.include_router(push_router, prefix=api)
app.include_router(push_admin_router, prefix=api)
app.include_router(admin_notifications_router, prefix=api)
app.include_router(admin_team_router, prefix=api)
app.include_router(admin_team_invite_router, prefix=api)
app.include_router(users_router, prefix=api)
app.include_router(appeals_router, prefix=api)
app.include_router(me_workspaces_router, prefix=api)
app.include_router(host_team_router, prefix=api)
app.include_router(team_invites_router, prefix=api)
app.include_router(hosts_router, prefix=api)
app.include_router(host_recommendations_admin_router, prefix=api)
app.include_router(event_recommendations_admin_router, prefix=api)
app.include_router(teams_admin_router, prefix=api)
app.include_router(events_router, prefix=api)
app.include_router(tickets_router, prefix=api)
app.include_router(payments_router, prefix=api)
app.include_router(merch_router, prefix=api)
# Commerce static paths (e.g. /dashboard/merchandise/post-event-drops) must
# register before alias dynamic /dashboard/merchandise/{item_id}.
app.include_router(merch_commerce_router, prefix=api)
app.include_router(merch_alias_router, prefix=api)
# Marketplace discovery — register after merch static paths so /merch/{slug}
# does not shadow /merch/health, /merch/mine, /merch/host/*, etc.
app.include_router(merch_marketplace_router, prefix=api)
app.include_router(promos_router, prefix=api)
app.include_router(promos_admin_router, prefix=api)
app.include_router(referrals_router, prefix=api)
app.include_router(ambassadors_router, prefix=api)
app.include_router(ambassadors_event_router, prefix=api)
app.include_router(ambassadors_host_router, prefix=api)
app.include_router(ambassadors_admin_router, prefix=api)

app.include_router(checkins_router, prefix=api)
app.include_router(legacy_host_router, prefix=api)
app.include_router(legacy_public_u_router, prefix=api)
app.include_router(legacy_router, prefix=api)
app.include_router(reviews_router, prefix=api)
app.include_router(vault_router, prefix=api)
app.include_router(passport_router, prefix=api)
app.include_router(fan_connect_router, prefix=api)
app.include_router(fan_connect_admin_router, prefix=api)
app.include_router(messaging_router, prefix=api)
app.include_router(messaging_ws_router, prefix=api)
app.include_router(memories_router, prefix=api)
app.include_router(crm_router, prefix=api)
app.include_router(support_router, prefix=api)
app.include_router(admin_router, prefix=api)
app.include_router(admin_users_router, prefix=api)
app.include_router(admin_events_buyers_router, prefix=api)
app.include_router(admin_event_analytics_router, prefix=api)
app.include_router(runtime_settings_router, prefix=api)
app.include_router(cms_router, prefix=api)
app.include_router(blog_router, prefix=api)
app.include_router(knowledge_base_router, prefix=api)
app.include_router(taxonomy_router, prefix=api)
app.include_router(placements_router, prefix=api)
app.include_router(analytics_router, prefix=api)
app.include_router(host_event_analytics_router, prefix=api)
app.include_router(ai_router, prefix=api)
app.include_router(sponsor_profiles_router, prefix=api)
app.include_router(sponsor_team_router, prefix=api)
app.include_router(sponsor_saved_router, prefix=api)
app.include_router(sponsor_campaign_router, prefix=api)
app.include_router(sponsor_campaign_admin_router, prefix=api)
app.include_router(sponsor_report_router, prefix=api)
app.include_router(sponsor_deals_router, prefix=api)
app.include_router(host_sponsorship_deals_router, prefix=api)
app.include_router(sponsorship_deals_admin_router, prefix=api)
app.include_router(sponsorship_invoices_admin_router, prefix=api)
app.include_router(sponsor_team_invite_router, prefix=api)
app.include_router(sponsor_admin_router, prefix=api)
app.include_router(sponsorships_router, prefix=api)
app.include_router(finance_router, prefix=api)
app.include_router(finance_fees_router, prefix=api)
app.include_router(pricing_router, prefix=api)

app.mount("/media", SafeMediaStaticFiles(directory=str(MEDIA_ROOT)), name="media")


@app.get("/health")
async def health() -> dict[str, object]:
    """Liveness — process is up. No DB query (keep cheap for probes)."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        **redis_health(),
        "messaging_ws_fanout": messaging_bus.mode,
    }


@app.get(f"{api}/health")
async def api_v1_health() -> dict[str, object]:
    """Same payload as ``/health`` — used by frontends on ``/api/v1/health``."""
    return await health()


def _readiness_payload() -> tuple[dict[str, object], int]:
    """Trivial readiness checks — no secrets/hostnames/connection strings."""
    db_status = "error"
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_status = "ok"
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        db_status = "error"

    redis_status = redis_health().get("redis", "unavailable")
    # Redis is fail-open for cache — readiness stays ready when Redis is down.
    ready = db_status == "ok"
    body: dict[str, object] = {
        "status": "ready" if ready else "not_ready",
        "database": db_status,
        "redis": redis_status,
    }
    return body, (200 if ready else 503)


@app.get("/ready")
async def ready():
    """Readiness — app initialized and PostgreSQL reachable (SELECT 1)."""
    from fastapi.responses import JSONResponse

    body, code = _readiness_payload()
    return JSONResponse(status_code=code, content=body)


@app.get(f"{api}/ready")
async def api_v1_ready():
    """Same as ``/ready`` for frontends probing ``/api/v1/ready``."""
    return await ready()


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Pàdéyá API foundation",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }
