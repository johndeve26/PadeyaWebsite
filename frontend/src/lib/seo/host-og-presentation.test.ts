import { describe, expect, it } from "vitest";

import {
  hostOgBio,
  hostOgDescription,
  hostOgDisplayName,
  hostOgLegacyScore,
  hostOgLocation,
  hostOgShareHandle,
  hostOgStats,
  hostOgTitle,
  hostOgUsername,
  pickHostMediaUrl,
  splitDisplayNameTone,
  truncateEllipsis,
} from "./host-og-presentation";
import type { LegacyPage } from "@/lib/types/legacy";

function basePage(overrides: Partial<LegacyPage> = {}): LegacyPage {
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
      avatar_url: "/media/avatar.jpg",
      cover_url: "/media/cover.jpg",
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
      score: 92.4,
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

describe("host OG presentation", () => {
  it("truncates with ellipsis", () => {
    expect(truncateEllipsis("abcdefghij", 6)).toBe("abcde…");
    expect(truncateEllipsis("short", 10)).toBe("short");
  });

  it("splits display name tone", () => {
    expect(splitDisplayNameTone("DJ Maze")).toEqual({
      lead: "DJ",
      accent: "Maze",
    });
    expect(splitDisplayNameTone("Solo")).toEqual({
      lead: "Solo",
      accent: "",
    });
  });

  it("builds title for verified + score", () => {
    expect(hostOgTitle(basePage())).toBe(
      "DJ Maze — Verified Host & Legacy 92 | Pàdéyá",
    );
  });

  it("falls back title when unverified / no score", () => {
    expect(
      hostOgTitle(basePage({ verified: false, legacy_trust: null })),
    ).toBe("DJ Maze · Host Legacy | Pàdéyá");
    expect(
      hostOgTitle(
        basePage({
          verified: false,
          legacy_trust: {
            score: 48,
            display_score: 48,
            tier: { key: "starter", name: "Starter", description: "", rank: 1 },
            legacy_status: "Starter",
            is_provisional: true,
            provisional_reasons: [],
            headline: "",
            evidence: [],
            factor_bands: [],
          },
        }),
      ),
    ).toBe("DJ Maze — Legacy 48 | Pàdéyá");
  });

  it("prefers bio for description when long enough", () => {
    const desc = hostOgDescription(basePage());
    expect(desc).toContain("Premium Afrobeats");
  });

  it("uses discover fallback when bio is short", () => {
    const desc = hostOgDescription(
      basePage({ tagline: "Hi", about: null, profile: { ...basePage().profile!, bio: "x" } }),
    );
    expect(desc).toContain("Discover DJ Maze");
  });

  it("dedupes location parts", () => {
    expect(hostOgLocation(basePage())).toBe("Lagos, Nigeria");
  });

  it("formats username and share handle", () => {
    expect(hostOgUsername(basePage())).toBe("@djmaze");
    expect(hostOgShareHandle(basePage())).toBe("padeya.com/@djmaze");
  });

  it("formats stats and hides empty rating", () => {
    const stats = hostOgStats(basePage());
    expect(stats.map((s) => s.label)).toEqual([
      "21 Events Hosted",
      "2.2K Tickets Sold",
      "4.7 Avg Rating",
    ]);

    const noRating = hostOgStats(
      basePage({
        stats: {
          ...basePage().stats,
          average_verified_rating: null,
          review_count: 0,
        },
      }),
    );
    expect(noRating.some((s) => s.key === "rating")).toBe(false);
  });

  it("shows zero events when present", () => {
    const stats = hostOgStats(
      basePage({
        stats: {
          ...basePage().stats,
          events_hosted: 0,
          tickets_sold: 0,
          average_verified_rating: null,
          review_count: 0,
        },
      }),
    );
    expect(stats.map((s) => s.label)).toEqual([
      "0 Events Hosted",
      "0 Tickets Sold",
    ]);
  });

  it("reads legacy score from trust summary", () => {
    expect(hostOgLegacyScore(basePage())).toBe(92);
    expect(hostOgLegacyScore(basePage({ legacy_trust: null }))).toBeNull();
  });

  it("truncates long display name and bio", () => {
    const long = "A".repeat(60);
    expect(hostOgDisplayName(basePage({ display_name: long })).length).toBeLessThanOrEqual(40);
    expect(
      (hostOgBio(basePage({ tagline: "B".repeat(200) })) || "").length,
    ).toBeLessThanOrEqual(110);
  });

  it("picks media urls with og preference", () => {
    expect(
      pickHostMediaUrl(
        { og_url: "/og.jpg", display_url: "/d.jpg", url: "/u.jpg" },
        "/legacy.jpg",
      ),
    ).toBe("/og.jpg");
    expect(pickHostMediaUrl(null, "/legacy.jpg")).toBe("/legacy.jpg");
  });
});
