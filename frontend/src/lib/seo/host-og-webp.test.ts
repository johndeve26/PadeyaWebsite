import { describe, expect, it } from "vitest";
import { buildHostLegacyOgImage } from "./host-og-image";
import type { LegacyPage } from "@/lib/types/legacy";

const page = {
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
    avatar_url:
      "https://media.padeya.com/public-media/user/6e0d10ad-b715-49a3-95b8-4760e93b49c8/2c57846e-1fd3-4c01-8a92-f5a4cd8252da/8036d6c4-c1d1-453e-b81c-b10a85116426.webp",
    cover_url:
      "https://media.padeya.com/public-media/host/aeac24d2-5c88-4975-923a-2669c3bbd85a/a587c270-6bca-4e1e-9e79-5b6b922b7282/b1059bd9-65ca-4155-8e67-9ae468b1396d.webp",
    cover_media: {
      og_url:
        "https://media.padeya.com/public-media/host/aeac24d2-5c88-4975-923a-2669c3bbd85a/a587c270-6bca-4e1e-9e79-5b6b922b7282/b1059bd9-65ca-4155-8e67-9ae468b1396d.webp",
      display_url:
        "https://media.padeya.com/public-media/host/aeac24d2-5c88-4975-923a-2669c3bbd85a/a587c270-6bca-4e1e-9e79-5b6b922b7282/b1059bd9-65ca-4155-8e67-9ae468b1396d.webp",
    },
    avatar_media: {
      display_url:
        "https://media.padeya.com/public-media/user/6e0d10ad-b715-49a3-95b8-4760e93b49c8/2c57846e-1fd3-4c01-8a92-f5a4cd8252da/8036d6c4-c1d1-453e-b81c-b10a85116426.webp",
    },
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
} as LegacyPage;

describe("real media host og", () => {
  it("renders with live webp cover+avatar", async () => {
    const res = await buildHostLegacyOgImage(page);
    expect(res.status).toBe(200);
    const buf = Buffer.from(await res.arrayBuffer());
    expect(buf.subarray(0, 4)).toEqual(Buffer.from([0x89, 0x50, 0x4e, 0x47]));
    console.log("bytes", buf.byteLength);
  }, 60_000);
});
