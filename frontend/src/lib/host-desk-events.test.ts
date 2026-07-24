import { describe, expect, it } from "vitest";

import {
  countDeskEventsByFilter,
  deskEventMatchesFilter,
  filterDeskEvents,
} from "@/lib/host-desk-events";
import type { HostDeskEvent } from "@/lib/types/host-workspace";

function event(
  partial: Pick<HostDeskEvent, "id" | "title" | "status" | "start_datetime">,
): HostDeskEvent {
  return {
    slug: partial.id,
    staff_check_in_path: `/check-in/${partial.id}`,
    host_check_in_path: `/host/events/${partial.id}/check-in`,
    ...partial,
  };
}

const sample: HostDeskEvent[] = [
  event({
    id: "1",
    title: "Live",
    status: "published",
    start_datetime: "2026-07-25T20:00:00Z",
  }),
  event({
    id: "2",
    title: "Draft",
    status: "draft",
    start_datetime: "2026-08-01T20:00:00Z",
  }),
  event({
    id: "3",
    title: "Done",
    status: "completed",
    start_datetime: "2026-06-24T20:00:00Z",
  }),
  event({
    id: "4",
    title: "Review",
    status: "pending_review",
    start_datetime: "2026-08-30T20:00:00Z",
  }),
];

describe("host desk event filters", () => {
  it("defaults ready to published/paused only", () => {
    expect(deskEventMatchesFilter(sample[0], "ready")).toBe(true);
    expect(deskEventMatchesFilter(sample[1], "ready")).toBe(false);
    expect(filterDeskEvents(sample, "ready").map((e) => e.id)).toEqual(["1"]);
  });

  it("keeps completed out of other", () => {
    expect(deskEventMatchesFilter(sample[2], "other")).toBe(false);
    expect(deskEventMatchesFilter(sample[1], "other")).toBe(true);
    const counts = countDeskEventsByFilter(sample);
    expect(counts.ready).toBe(1);
    expect(counts.completed).toBe(1);
    expect(counts.other).toBe(2);
    expect(counts.all).toBe(4);
  });
});
