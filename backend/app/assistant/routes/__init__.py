"""Route registries for assistant navigation and page help."""

from app.assistant.routes.auth_registry import (
    AUTH_ROUTE_REGISTRY,
    AuthRouteEntry,
    get_auth_route_by_key,
    resolve_auth_route,
)
from app.assistant.routes.public_registry import (
    PUBLIC_ROUTE_REGISTRY,
    PublicRouteEntry,
    get_public_route_by_key,
    get_route_by_key,
    resolve_public_route,
)

__all__ = [
    "AUTH_ROUTE_REGISTRY",
    "PUBLIC_ROUTE_REGISTRY",
    "AuthRouteEntry",
    "PublicRouteEntry",
    "get_auth_route_by_key",
    "get_public_route_by_key",
    "get_route_by_key",
    "resolve_auth_route",
    "resolve_public_route",
]
