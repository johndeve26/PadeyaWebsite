"""Current-page help blurbs for known route keys."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageHelpEntry:
    route_key: str
    summary: str
    tips: tuple[str, ...] = ()
    related_actions: tuple[str, ...] = ()


PAGE_HELP: dict[str, PageHelpEntry] = {
    "home": PageHelpEntry(
        route_key="home",
        summary="You're on the Pàdéyá home page — a starting point to discover events and culture.",
        tips=("Browse Events to find what's on.", "Hosts have Legacy Pages with history."),
        related_actions=("navigate_to_route:events", "search_public_events"),
    ),
    "events": PageHelpEntry(
        route_key="events",
        summary="Browse public events. Filters and search find listed upcoming events.",
        tips=("Use city or category filters when available.", "Open an event for tickets and details."),
        related_actions=("search_public_events",),
    ),
    "hosts": PageHelpEntry(
        route_key="hosts",
        summary="Discover hosts on the marketplace and open their Legacy Pages.",
        related_actions=("search_public_hosts",),
    ),
    "help": PageHelpEntry(
        route_key="help",
        summary="Help Center articles for common product questions.",
        tips=("Search help topics, or contact Support if you're stuck."),
        related_actions=("search_help", "navigate_to_route:support"),
    ),
    "support": PageHelpEntry(
        route_key="support",
        summary="Open a support ticket for account, payment, or product issues.",
        related_actions=("create_support_ticket_draft",),
    ),
    "host_events": PageHelpEntry(
        route_key="host_events",
        summary="Host Studio event list — create drafts, edit, and publish from the product UI.",
        tips=("The assistant can help draft descriptions but will not publish for you."),
        related_actions=("list_my_events", "navigate_to_route:host_events_create"),
    ),
    "host_events_create": PageHelpEntry(
        route_key="host_events_create",
        summary="Create a new event draft. Publishing requires ticket types and your confirmation in the UI.",
        tips=("Add at least one ticket type before publishing."),
        related_actions=("create_event_draft", "draft_event_description"),
    ),
    "fan_tickets": PageHelpEntry(
        route_key="fan_tickets",
        summary="Your ticket wallet — upcoming and past tickets for events you purchased.",
        related_actions=("list_my_upcoming_tickets",),
    ),
    "shop": PageHelpEntry(
        route_key="shop",
        summary="Merch marketplace — browse public products from hosts.",
        related_actions=("search_public_products",),
    ),
}


def get_page_help(route_key: str | None) -> PageHelpEntry | None:
    if not route_key:
        return None
    return PAGE_HELP.get(route_key.strip().lower())
