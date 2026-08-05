import { describe, expect, it } from "vitest";

import { buildFanPassportOgImage } from "./fan-og-image";
import type { FanPassportPublicPage } from "@/lib/types/passport";

function page(
  overrides: Partial<FanPassportPublicPage> = {},
): FanPassportPublicPage {
  return {
    username: "toluwave",
    user_id: "u1",
    display_name: "Tolu Nightlife Explorer",
    avatar_url: null,
    tagline: "Chasing afterparties and verified Detty stamps.",
    bio: null,
    visibility: "public",
    is_superfan: false,
    events_attended: 1,
    hosts_followed: 3,
    badges_earned_count: 8,
    reviews_written: 0,
    cities_explored: 1,
    categories_explored: 2,
    connections_count: 0,
    favorite_categories: ["Nightlife", "Music"],
    favorite_cities: ["Lagos"],
    badges: [
      {
        id: "b1",
        slug: "first-ticket",
        name: "First Ticket",
        description: "private criteria text should not matter",
        criteria_key: "first_ticket",
        awarded_at: "2026-01-01",
        earned: true,
      },
      {
        id: "b2",
        slug: "early-bird",
        name: "Early Bird",
        description: "x",
        criteria_key: "early_bird",
        awarded_at: "2026-01-02",
        earned: true,
      },
    ],
    attended_events: [],
    followed_hosts: [],
    reviews: [],
    vault_unlocks: [],
    share_path: "/f/toluwave",
    ...overrides,
  };
}

describe("buildFanPassportOgImage", () => {
  it("returns a PNG for a verified fan", async () => {
    const res = await buildFanPassportOgImage(page());
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toContain("image/png");
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.subarray(0, 8)).toEqual(
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    );
    expect(buf.byteLength).toBeGreaterThan(5_000);

  }, 30_000);

  it("returns a PNG for missing / private fan fallback", async () => {
    const res = await buildFanPassportOgImage(null);
    expect(res.status).toBe(200);
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.byteLength).toBeGreaterThan(2_000);
  }, 30_000);

  it("handles unverified empty passport", async () => {
    const res = await buildFanPassportOgImage(
      page({
        events_attended: 0,
        hosts_followed: 0,
        badges_earned_count: 0,
        badges: [],
        favorite_categories: [],
        favorite_cities: [],
        tagline: null,
        bio: null,
      }),
    );
    expect(res.status).toBe(200);
  }, 30_000);

  it("truncates long name without crashing", async () => {
    const res = await buildFanPassportOgImage(
      page({
        display_name: "X".repeat(80),
        tagline: "Y".repeat(300),
      }),
    );
    expect(res.status).toBe(200);
  }, 30_000);
});
