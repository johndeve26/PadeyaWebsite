import { describe, expect, it } from "vitest";

import {
  emptyStateForTab,
  eventMatchesTab,
  parseEventListTab,
} from "@/lib/host-events-list";
import type { EventItem } from "@/lib/types/events";

function event(partial: Partial<EventItem> & Pick<EventItem, "status">): EventItem {
  return {
    id: "e1",
    title: "Test Night",
    slug: "test-night",
    start_datetime: "2026-01-01T18:00:00Z",
    end_datetime: "2026-01-01T22:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    city: "Lagos",
    venue_name: "The Yard",
    visibility: "listed",
    ...partial,
  } as EventItem;
}

describe("host-events-list completed tab", () => {
  const nowMs = Date.parse("2026-07-26T12:00:00Z");

  it("parses completed and legacy past alias", () => {
    expect(parseEventListTab("completed")).toBe("completed");
    expect(parseEventListTab("past")).toBe("completed");
    expect(parseEventListTab("upcoming")).toBe("upcoming");
  });

  it("matches completed by status only", () => {
    expect(
      eventMatchesTab(
        event({ status: "completed", end_datetime: "2026-01-01T22:00:00Z" }),
        "completed",
        nowMs,
      ),
    ).toBe(true);
    expect(
      eventMatchesTab(
        event({ status: "published", end_datetime: "2026-01-01T22:00:00Z" }),
        "completed",
        nowMs,
      ),
    ).toBe(false);
  });

  it("keeps past-dated published out of upcoming", () => {
    expect(
      eventMatchesTab(
        event({ status: "published", end_datetime: "2026-01-01T22:00:00Z" }),
        "upcoming",
        nowMs,
      ),
    ).toBe(false);
  });

  it("empty state names completed", () => {
    expect(emptyStateForTab("completed").title).toMatch(/completed/i);
  });
});
