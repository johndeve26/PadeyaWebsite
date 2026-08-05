import { describe, expect, it } from "vitest";

import {
  fitEventTitle,
  getCharacterWeight,
  wrapTitleLines,
} from "./event-og-title";
import {
  classifyImageAspect,
  eventOgDateBlock,
  eventOgHostLine,
  eventOgImagePath,
  eventOgLocation,
  eventOgPageTitle,
  eventOgPriceLabel,
  eventOgPrivacyNote,
  eventOgStatusBadge,
  pickEventOgMedia,
} from "./event-og-presentation";
import type { EventItem } from "@/lib/types/events";

function baseEvent(overrides: Partial<EventItem> = {}): EventItem {
  return {
    id: "e1",
    title: "Mainland After Dark",
    slug: "mainland-after-dark",
    description: "A Lagos night.",
    short_tagline: "Late nights. Local vibes. Verified tickets.",
    start_datetime: "2026-08-15T02:33:00.000Z",
    end_datetime: "2026-08-15T06:00:00.000Z",
    timezone: "Africa/Lagos",
    status: "published",
    visibility: "listed",
    featured: false,
    venue_name: null,
    address: "12 Hidden Street",
    city: "Lagos",
    state: "Lagos",
    country: "NG",
    location_visibility: "hidden_until_payment",
    location_address_revealed: false,
    public_location_label: "Victoria Island, Lagos",
    location_privacy_message: "Exact venue revealed after purchase",
    banner_url: "/media/banner.jpg",
    social_share_image_url: null,
    host_display_name: "DJ Maze",
    host_slug: "djmaze",
    category: { id: "c1", name: "Nightlife", slug: "nightlife" },
    ticket_types: [
      {
        id: "t1",
        name: "General",
        price: 3500,
        type: "paid",
        visibility: "public",
        status: "active",
        quantity: 100,
        quantity_sold: 10,
      },
    ],
    ...overrides,
  } as EventItem;
}

describe("event OG title fit", () => {
  it("weights wide characters higher", () => {
    expect(getCharacterWeight("M")).toBeGreaterThan(getCharacterWeight("i"));
  });

  it("fits short titles at large size", () => {
    const fit = fitEventTitle("Afrobeats Night", 640, 220);
    expect(fit.fontSize).toBeGreaterThanOrEqual(72);
    expect(fit.lines.length).toBeLessThanOrEqual(2);
    expect(fit.density).toBe("short");
  });

  it("balances long titles across lines", () => {
    const { lines } = wrapTitleLines(
      "Unforgettable Night of Sharp Vibes and Connections",
      52,
      640,
      3,
    );
    expect(lines.length).toBeGreaterThanOrEqual(2);
    expect(lines[0]!.split(/\s+/).length).toBeGreaterThan(1);
  });

  it("truncates extremely long titles at minimum size", () => {
    const fit = fitEventTitle("X".repeat(140), 520, 200, {
      hasTagline: false,
    });
    expect(fit.fontSize).toBeLessThanOrEqual(48);
    expect(fit.truncated || fit.lines.join("").includes("…")).toBe(true);
  });
});

describe("event OG presentation", () => {
  it("builds canonical OG path and page title", () => {
    expect(eventOgImagePath("mainland-after-dark")).toBe(
      "/events/mainland-after-dark/opengraph-image",
    );
    expect(eventOgPageTitle(baseEvent())).toContain("Mainland After Dark");
    expect(eventOgPageTitle(baseEvent())).toContain("Tickets on Pàdéyá");
  });

  it("protects private venues and shows privacy note", () => {
    expect(eventOgLocation(baseEvent())).toBe("Victoria Island, Lagos");
    expect(eventOgPrivacyNote(baseEvent())).toContain("Exact venue");
    expect(eventOgLocation(baseEvent())).not.toContain("Hidden Street");
  });

  it("formats price and host line", () => {
    expect(eventOgPriceLabel(baseEvent())).toBe("From NGN 3,500");
    expect(eventOgHostLine(baseEvent())).toBe("Hosted by DJ Maze");
    expect(eventOgPriceLabel(baseEvent({ ticket_types: [] }))).toBeNull();
  });

  it("shows cancelled status", () => {
    expect(eventOgStatusBadge(baseEvent({ status: "cancelled" }))).toBe(
      "CANCELLED",
    );
  });

  it("picks media in priority order", () => {
    expect(pickEventOgMedia(baseEvent())?.source).toBe("banner");
    expect(
      pickEventOgMedia(
        baseEvent({ social_share_image_url: "/media/social.jpg" }),
      )?.source,
    ).toBe("social");
  });

  it("builds date block from timezone", () => {
    const block = eventOgDateBlock(baseEvent());
    expect(block?.month).toBeTruthy();
    expect(block?.day).toBeTruthy();
    expect(block?.weekday).toBeTruthy();
  });

  it("classifies flyer aspects", () => {
    expect(classifyImageAspect(1200, 630)).toBe("landscape");
    expect(classifyImageAspect(800, 1200)).toBe("portrait");
    expect(classifyImageAspect(1000, 1000)).toBe("square");
  });
});
