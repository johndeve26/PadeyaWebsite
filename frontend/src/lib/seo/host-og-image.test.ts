import { describe, expect, it } from "vitest";

import { buildHostLegacyOgImage } from "./host-og-image";
import type { LegacyPage } from "@/lib/types/legacy";

function page(overrides: Partial<LegacyPage> = {}): LegacyPage {
  return {
    host_id: "h1",
    display_name: "DJ Maze",
    username: "djmaze",
    status: "active",
    verified: true,
    legacy_status: "Rising",
    profile: {
      bio: "Lagos nightlife curator",
      website: null,
      city: "Lagos",
      state: "Lagos",
      country: "Nigeria",
      avatar_url: null,
      cover_url: null,
      social_links: null,
    },
    stats: {
      events_hosted: 21,
      tickets_sold: 2200,
      verified_checkins: 1800,
      average_verified_rating: 4.7,
      review_count: 40,
      followers: 900,
      repeat_buyers_rate: null,
      refund_dispute_rate: null,
      legacy_status: "Rising",
    },
    about: null,
    upcoming_events: [],
    past_events: [],
    reviews: [],
    follow_enabled: true,
    share_path: "/@djmaze",
    tagline: "Premium Afrobeats and nightlife experiences across Lagos",
    legacy_trust: {
      score: 92,
      display_score: 92,
      tier: { key: "rising", name: "Rising", description: "", rank: 2 },
      legacy_status: "Rising",
      is_provisional: false,
      provisional_reasons: [],
      headline: "",
      evidence: [],
      factor_bands: [],
    },
    ...overrides,
  } as LegacyPage;
}

describe("buildHostLegacyOgImage", () => {
  it("returns a PNG ImageResponse for a full host", async () => {
    const res = await buildHostLegacyOgImage(page());
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toContain("image/png");
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.byteLength).toBeGreaterThan(5_000);
    // PNG signature
    expect(buf.subarray(0, 8)).toEqual(
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    );
  }, 30_000);

  it("returns a PNG for missing host fallback", async () => {
    const res = await buildHostLegacyOgImage(null);
    expect(res.status).toBe(200);
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.byteLength).toBeGreaterThan(2_000);
  }, 30_000);

  it("handles unverified host without cover/avatar", async () => {
    const res = await buildHostLegacyOgImage(
      page({
        verified: false,
        legacy_trust: null,
        profile: {
          bio: null,
          website: null,
          city: null,
          state: null,
          country: null,
          avatar_url: null,
          cover_url: null,
          social_links: null,
        },
        stats: {
          events_hosted: 0,
          tickets_sold: 0,
          verified_checkins: 0,
          average_verified_rating: null,
          review_count: 0,
          followers: 0,
          repeat_buyers_rate: null,
          refund_dispute_rate: null,
          legacy_status: "Starter",
        },
        tagline: null,
      }),
    );
    expect(res.status).toBe(200);
  }, 30_000);

  it("truncates long name without crashing", async () => {
    const res = await buildHostLegacyOgImage(
      page({ display_name: "X".repeat(80), tagline: "Y".repeat(300) }),
    );
    expect(res.status).toBe(200);
  }, 30_000);
});
