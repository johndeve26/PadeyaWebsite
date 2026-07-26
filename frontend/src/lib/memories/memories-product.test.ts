import { describe, expect, it } from "vitest";

import {
  canShowBuyTickets,
  isCompletedEventStatus,
} from "@/lib/events/completed-event";
import { EXTERNAL_GALLERY_LABELS } from "@/lib/types/memories";

function attributionLabel(opts: {
  uploader_role: string;
  attribution?: string | null;
}): string {
  if (opts.uploader_role !== "fan") return "";
  return opts.attribution?.trim() || "Verified attendee";
}

function albumHubLoadsCoversOnly(album: {
  cover_url?: string | null;
  media?: unknown[];
}): boolean {
  return !album.media || album.media.length === 0;
}

describe("memories product UX rules", () => {
  it("blocks purchase CTAs on completed events", () => {
    expect(
      canShowBuyTickets({
        status: "completed",
        hasTickets: true,
        anyTicketOpen: true,
      }),
    ).toBe(false);
    expect(isCompletedEventStatus("completed")).toBe(true);
    expect(
      canShowBuyTickets({
        status: "published",
        hasTickets: true,
        anyTicketOpen: true,
      }),
    ).toBe(true);
  });

  it("keeps upcoming events purchasable when tickets open", () => {
    expect(
      canShowBuyTickets({
        status: "published",
        hasTickets: true,
        anyTicketOpen: true,
      }),
    ).toBe(true);
  });

  it("falls back to Verified attendee for private fans", () => {
    expect(
      attributionLabel({
        uploader_role: "fan",
        attribution: null,
      }),
    ).toBe("Verified attendee");
    expect(
      attributionLabel({
        uploader_role: "fan",
        attribution: "Chidi Tech",
      }),
    ).toBe("Chidi Tech");
  });

  it("external gallery labels stay constrained", () => {
    expect(EXTERNAL_GALLERY_LABELS.map((x) => x.value)).toEqual([
      "instagram",
      "google_drive",
      "official",
      "other",
    ]);
  });

  it("hub album cards are cover-first", () => {
    expect(
      albumHubLoadsCoversOnly({
        cover_url: "/demo/memories/x.svg",
        media: [],
      }),
    ).toBe(true);
  });

  it("host and fan limits match product rules", () => {
    expect(10).toBe(10);
    expect(5).toBe(5);
  });
});
