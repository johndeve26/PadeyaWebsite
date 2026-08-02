import type { HostDeskEvent } from "@/lib/types/host-workspace";

/** Desk list filters — default “ready” keeps door/merch focused. */
export type DeskEventFilter =
  | "ready"
  | "completed"
  | "other"
  | "all";

export const DESK_EVENT_FILTERS: {
  value: DeskEventFilter;
  label: string;
}[] = [
  { value: "ready", label: "Published" },
  { value: "completed", label: "Completed" },
  { value: "other", label: "Other" },
  { value: "all", label: "All" },
];

const READY_STATUSES = new Set(["published", "paused"]);
const OTHER_STATUSES = new Set([
  "draft",
  "rejected",
  "cancelled",
]);

export function deskEventMatchesFilter(
  event: HostDeskEvent,
  filter: DeskEventFilter,
): boolean {
  const status = (event.status || "").toLowerCase();
  switch (filter) {
    case "ready":
      return READY_STATUSES.has(status);
    case "completed":
      return status === "completed";
    case "other":
      // Drafts / rejected / cancelled — not door-ready, not completed.
      return (
        OTHER_STATUSES.has(status) ||
        (!READY_STATUSES.has(status) && status !== "completed")
      );
    case "all":
      return true;
    default:
      return true;
  }
}

export function countDeskEventsByFilter(
  events: HostDeskEvent[],
): Record<DeskEventFilter, number> {
  const counts: Record<DeskEventFilter, number> = {
    ready: 0,
    completed: 0,
    other: 0,
    all: events.length,
  };
  for (const event of events) {
    if (deskEventMatchesFilter(event, "ready")) counts.ready += 1;
    if (deskEventMatchesFilter(event, "completed")) counts.completed += 1;
    if (deskEventMatchesFilter(event, "other")) counts.other += 1;
  }
  return counts;
}

export function filterDeskEvents(
  events: HostDeskEvent[],
  filter: DeskEventFilter,
): HostDeskEvent[] {
  const filtered = events.filter((event) =>
    deskEventMatchesFilter(event, filter),
  );
  const byStart = (a: HostDeskEvent, b: HostDeskEvent) =>
    new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime();

  if (filter === "completed") {
    return [...filtered].sort((a, b) => -byStart(a, b));
  }
  return [...filtered].sort(byStart);
}

export function emptyCopyForDeskFilter(filter: DeskEventFilter): {
  title: string;
  description: string;
} {
  switch (filter) {
    case "ready":
      return {
        title: "No published events",
        description:
          "Publish an event to scan tickets or run merch pickup from the desk.",
      };
    case "completed":
      return {
        title: "No completed events",
        description: "Finished nights show here for late pickup and follow-up.",
      };
    case "other":
      return {
        title: "Nothing in other statuses",
        description: "Drafts, pending review, rejected, and cancelled appear here.",
      };
    default:
      return {
        title: "No assigned events yet",
        description:
          "Ask the host owner to add you on an event’s staff list, or grant host-wide desk access.",
      };
  }
}
