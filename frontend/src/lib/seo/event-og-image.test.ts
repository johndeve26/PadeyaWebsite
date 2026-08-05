import { describe, expect, it } from "vitest";

import { buildEventOgImage } from "./event-og-image";
import type { EventItem } from "@/lib/types/events";

function event(overrides: Partial<EventItem> = {}): EventItem {
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
    featured: true,
    venue_name: null,
    address: null,
    city: "Lagos",
    state: "Lagos",
    location_visibility: "area_only",
    location_address_revealed: false,
    public_location_label: "Victoria Island, Lagos",
    location_privacy_message: "Exact venue revealed after purchase",
    banner_url: null,
    social_share_image_url: null,
    host_display_name: "DJ Maze",
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

describe("buildEventOgImage", () => {
  it("returns a PNG for a full public event", async () => {
    const res = await buildEventOgImage(event());
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toContain("image/png");
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.subarray(0, 8)).toEqual(
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    );
    expect(buf.byteLength).toBeGreaterThan(5_000);
  }, 30_000);

  it("returns a PNG for missing event fallback", async () => {
    const res = await buildEventOgImage(null);
    expect(res.status).toBe(200);
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.byteLength).toBeGreaterThan(2_000);
  }, 30_000);

  it("handles long titles without crashing", async () => {
    const res = await buildEventOgImage(
      event({
        title:
          "Unforgettable Night of Sharp Vibes and Connections Across Lagos Mainland",
        short_tagline: null,
      }),
    );
    expect(res.status).toBe(200);
  }, 30_000);

  it("handles cancelled events", async () => {
    const res = await buildEventOgImage(event({ status: "cancelled" }));
    expect(res.status).toBe(200);
  }, 30_000);
});
