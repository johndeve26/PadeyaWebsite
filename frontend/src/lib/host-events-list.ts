import type { EventItem, EventStatus } from "@/lib/types/events";

/**
 * Tab → event filter mapping (HOST_AREA_AUDIT §7.2).
 *
 * | Tab        | Rule |
 * |------------|------|
 * | Upcoming   | end_datetime >= now AND status ∈ published, paused, draft, pending_review |
 * | Drafts     | status ∈ draft, rejected |
 * | Published  | status === published |
 * | Completed  | status === completed (auto when end_datetime passes; also manual Mark completed) |
 * | Cancelled  | status === cancelled |
 * | All        | no tab filter |
 */

export type EventListTab =
  | "upcoming"
  | "drafts"
  | "published"
  | "completed"
  | "cancelled"
  | "all";

export type EventViewMode = "table" | "list" | "grid";

export type EventSortKey =
  | "start_asc"
  | "start_desc"
  | "created_desc"
  | "sales_desc"
  | "revenue_desc"
  | "title_asc";

export type EventListMetrics = {
  tickets_sold?: number;
  revenue?: number;
  check_in_count?: number;
  merch_product_count?: number;
  merch_pending_pickup?: number;
  merch_sales_status?: string;
};

export const EVENT_VISIBILITY_OPTIONS = [
  { value: "listed", label: "Listed" },
  { value: "unlisted", label: "Unlisted" },
  { value: "password_protected", label: "Password protected" },
  { value: "approval_required", label: "Approval required" },
] as const;

export const EVENT_LIST_TABS: { value: EventListTab; label: string }[] = [
  { value: "upcoming", label: "Upcoming" },
  { value: "drafts", label: "Drafts" },
  { value: "published", label: "Published" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "all", label: "All" },
];

const UPCOMING_STATUSES = new Set<EventStatus>([
  "published",
  "paused",
  "draft",
  "pending_review",
]);

export function parseEventListTab(value: string | null): EventListTab {
  // Legacy URL alias: ?tab=past → Completed
  if (value === "past") return "completed";
  if (
    value === "upcoming" ||
    value === "drafts" ||
    value === "published" ||
    value === "completed" ||
    value === "cancelled" ||
    value === "all"
  ) {
    return value;
  }
  return "upcoming";
}

export function eventEndMs(event: EventItem): number {
  return new Date(event.end_datetime || event.start_datetime).getTime();
}

export function eventMatchesTab(event: EventItem, tab: EventListTab, nowMs: number): boolean {
  const endMs = eventEndMs(event);
  switch (tab) {
    case "upcoming":
      return endMs >= nowMs && UPCOMING_STATUSES.has(event.status);
    case "drafts":
      return event.status === "draft" || event.status === "rejected";
    case "published":
      return event.status === "published";
    case "completed":
      return event.status === "completed";
    case "cancelled":
      return event.status === "cancelled";
    case "all":
      return true;
    default:
      return true;
  }
}

export function formatEventVisibility(value: string | null | undefined): string {
  switch (value) {
    case "listed":
      return "Listed";
    case "unlisted":
      return "Unlisted";
    case "password_protected":
      return "Password";
    case "approval_required":
      return "Approval";
    default:
      return value?.trim() ? value : "—";
  }
}

export function formatLocationPrivacy(
  value: string | null | undefined,
): string {
  switch (value) {
    case "full_public":
      return "Public";
    case "area_only":
      return "Area only";
    case "hidden_until_payment":
      return "After payment";
    case "hidden_until_24h_before":
      return "24h before";
    case "hidden_until_manual_approval":
      return "Manual reveal";
    case "online_only":
      return "Online";
    default:
      return "—";
  }
}

/** Single-line label for dense tables (avoids Listed + subtype stack). */
export function formatEventVisibilityBrief(
  visibility: string | null | undefined,
  locationVisibility: string | null | undefined,
): string {
  switch (visibility) {
    case "unlisted":
      return "Unlisted";
    case "password_protected":
      return "Password";
    case "approval_required":
      return "Approval";
    case "listed":
    case null:
    case undefined:
    case "": {
      const place = formatLocationPrivacy(locationVisibility);
      return place === "—" ? "Public" : place;
    }
    default:
      return formatEventVisibility(visibility);
  }
}

export function filterEventsForList(
  events: EventItem[],
  options: {
    tab: EventListTab;
    query: string;
    statusFilter: EventStatus | "all";
    cityFilter: string;
    visibilityFilter: string;
    dateFrom?: string;
    dateTo?: string;
    nowMs?: number;
  },
): EventItem[] {
  const nowMs = options.nowMs ?? Date.now();
  const q = options.query.trim().toLowerCase();
  const fromMs = options.dateFrom
    ? new Date(`${options.dateFrom}T00:00:00`).getTime()
    : null;
  const toMs = options.dateTo
    ? new Date(`${options.dateTo}T23:59:59.999`).getTime()
    : null;

  return events.filter((event) => {
    if (!eventMatchesTab(event, options.tab, nowMs)) return false;
    if (options.statusFilter !== "all" && event.status !== options.statusFilter) {
      return false;
    }
    if (options.cityFilter !== "all" && (event.city || "") !== options.cityFilter) {
      return false;
    }
    if (
      options.visibilityFilter !== "all" &&
      (event.visibility || "") !== options.visibilityFilter
    ) {
      return false;
    }
    const startMs = new Date(event.start_datetime).getTime();
    if (fromMs != null && Number.isFinite(startMs) && startMs < fromMs) {
      return false;
    }
    if (toMs != null && Number.isFinite(startMs) && startMs > toMs) {
      return false;
    }
    if (!q) return true;
    const haystack = [
      event.title,
      event.venue_name,
      event.city,
      event.slug,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });
}

function metricNumber(
  metrics: Record<string, EventListMetrics> | undefined,
  eventId: string,
  key: keyof EventListMetrics,
): number {
  const value = metrics?.[eventId]?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function sortEventsForList(
  events: EventItem[],
  sortKey: EventSortKey,
  metrics?: Record<string, EventListMetrics>,
): EventItem[] {
  const rows = [...events];
  rows.sort((a, b) => {
    switch (sortKey) {
      case "start_desc":
        return (
          new Date(b.start_datetime).getTime() -
          new Date(a.start_datetime).getTime()
        );
      case "created_desc":
        return (
          new Date(b.created_at).getTime() -
          new Date(a.created_at).getTime()
        );
      case "sales_desc":
        return (
          metricNumber(metrics, b.id, "tickets_sold") -
          metricNumber(metrics, a.id, "tickets_sold")
        );
      case "revenue_desc":
        return (
          metricNumber(metrics, b.id, "revenue") -
          metricNumber(metrics, a.id, "revenue")
        );
      case "title_asc":
        return a.title.localeCompare(b.title);
      case "start_asc":
      default:
        return (
          new Date(a.start_datetime).getTime() -
          new Date(b.start_datetime).getTime()
        );
    }
  });
  return rows;
}

export function uniqueEventCities(events: EventItem[]): string[] {
  const cities = new Set<string>();
  for (const event of events) {
    if (event.city?.trim()) cities.add(event.city.trim());
  }
  return [...cities].sort((a, b) => a.localeCompare(b));
}

export function upcomingEvents(events: EventItem[], limit = 3, nowMs = Date.now()): EventItem[] {
  return events
    .filter((event) => eventMatchesTab(event, "upcoming", nowMs))
    .sort(
      (a, b) =>
        new Date(a.start_datetime).getTime() -
        new Date(b.start_datetime).getTime(),
    )
    .slice(0, limit);
}

export function todaysOperations(events: EventItem[], nowMs = Date.now()): EventItem[] {
  const dayEnd = nowMs + 24 * 60 * 60 * 1000;
  return events
    .filter((event) => {
      const startMs = new Date(event.start_datetime).getTime();
      return (
        Number.isFinite(startMs) &&
        startMs >= nowMs &&
        startMs <= dayEnd &&
        UPCOMING_STATUSES.has(event.status)
      );
    })
    .sort(
      (a, b) =>
        new Date(a.start_datetime).getTime() -
        new Date(b.start_datetime).getTime(),
    );
}

export function viewHref(event: EventItem): string {
  if (event.status === "published" && event.slug) {
    return `/events/${event.slug}`;
  }
  return `/host/events/${event.id}/preview`;
}

export function emptyStateForTab(tab: EventListTab): {
  title: string;
  description: string;
} {
  switch (tab) {
    case "upcoming":
      return {
        title: "No upcoming events",
        description: "Create a night to start selling tickets.",
      };
    case "drafts":
      return { title: "No drafts", description: "Draft events appear here." };
    case "published":
      return {
        title: "Nothing live",
        description: "Publish an event to go live on Pàdéyá.",
      };
    case "completed":
      return {
        title: "No completed events yet",
        description: "Events move here when their end time passes.",
      };
    case "cancelled":
      return {
        title: "No cancelled events",
        description: "Cancelled events appear here.",
      };
    default:
      return {
        title: "No events yet",
        description: "Create your first event to get started.",
      };
  }
}
