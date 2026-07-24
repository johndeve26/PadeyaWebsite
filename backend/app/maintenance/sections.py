"""Canonical platform section keys for maintenance controls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionDefinition:
    key: str
    label: str
    description: str
    # API path prefixes (matched with startswith)
    api_prefixes: tuple[str, ...]
    # Frontend path prefixes (for docs / FE banners)
    fe_prefixes: tuple[str, ...] = ()


SECTION_DEFINITIONS: tuple[SectionDefinition, ...] = (
    SectionDefinition(
        "public_discovery",
        "Public event discovery",
        "Public event listing and search",
        ("/api/v1/events",),
        ("/events", "/explore", "/"),
    ),
    SectionDefinition(
        "checkout",
        "Checkout / payments",
        "Orders, payment init, checkout",
        ("/api/v1/orders", "/api/v1/payments"),
        ("/checkout", "/dashboard/orders"),
    ),
    SectionDefinition(
        "ticketing",
        "Ticketing",
        "Tickets and ticket types",
        ("/api/v1/tickets",),
        ("/dashboard/tickets",),
    ),
    SectionDefinition(
        "checkin",
        "QR check-in / scanner",
        "Check-in and scanner APIs",
        ("/api/v1/checkins",),
        ("/host/check-in", "/scan"),
    ),
    SectionDefinition(
        "host_workspace",
        "Host workspace",
        "Host studio and host APIs",
        ("/api/v1/hosts", "/api/v1/host"),
        ("/host",),
    ),
    SectionDefinition(
        "fan_dashboard",
        "Fan dashboard",
        "Buyer dashboard APIs",
        ("/api/v1/users/me",),
        ("/dashboard",),
    ),
    SectionDefinition(
        "messaging",
        "Messaging",
        "Chat send and threads",
        ("/api/v1/messages", "/api/v1/host/messages"),
        ("/messages", "/dashboard/messages", "/host/messages"),
    ),
    SectionDefinition(
        "fan_connect",
        "Fan Connect",
        "Fan Connect requests and graph",
        ("/api/v1/fan-connect",),
        ("/connect",),
    ),
    SectionDefinition(
        "fan_passport",
        "Fan Passport",
        "Passport profile APIs",
        ("/api/v1/fans", "/api/v1/passport"),
        ("/dashboard/passport", "/f/"),
    ),
    SectionDefinition(
        "vault",
        "Vault",
        "Vault unlock and content",
        ("/api/v1/vault",),
        ("/dashboard/vault", "/host/vault"),
    ),
    SectionDefinition(
        "merch",
        "Merch",
        "Merchandise commerce",
        ("/api/v1/merch", "/api/v1/merchandise"),
        ("/merch", "/dashboard/merch"),
    ),
    SectionDefinition(
        "ambassadors",
        "Ambassadors",
        "Ambassador program",
        ("/api/v1/ambassadors", "/api/v1/promos"),
        ("/dashboard/ambassadors", "/host/ambassadors"),
    ),
    SectionDefinition(
        "sponsorships",
        "Sponsorships",
        "Sponsorship marketplace",
        ("/api/v1/sponsorships",),
        ("/sponsorships", "/host/sponsorships"),
    ),
    SectionDefinition(
        "reviews",
        "Reviews",
        "Event reviews",
        ("/api/v1/reviews",),
        ("/reviews",),
    ),
    SectionDefinition(
        "notifications",
        "Notifications",
        "In-app notification list/mark",
        ("/api/v1/notifications",),
        ("/dashboard/notifications",),
    ),
    SectionDefinition(
        "admin_users",
        "Admin user management",
        "Admin user CRUD (still bypassable)",
        ("/api/v1/admin/users",),
        ("/admin/users",),
    ),
    SectionDefinition(
        "webhooks",
        "API / webhooks",
        "Inbound payment webhooks (use carefully)",
        ("/api/v1/payments/webhook", "/api/v1/webhooks"),
        (),
    ),
)

SECTION_BY_KEY = {s.key: s for s in SECTION_DEFINITIONS}

# Safe methods always allowed in read-only (unless full-site hard block).
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Paths never blocked by maintenance (health, auth, public status, docs).
ALWAYS_ALLOW_EXACT = frozenset(
    {
        "/health",
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/maintenance/status",
        "/api/v1/maintenance/public",
    }
)
ALWAYS_ALLOW_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/admin/platform/maintenance",  # manage + bypass endpoints
    # Keep payment webhooks receivable so completed checkouts can settle.
    "/api/v1/payments/webhook",
)
