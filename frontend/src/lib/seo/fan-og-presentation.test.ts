import { describe, expect, it } from "vitest";

import {
  fanOgBio,
  fanOgDescription,
  fanOgDisplayName,
  fanOgLocation,
  fanOgScenes,
  fanOgShareHandle,
  fanOgShowVerified,
  fanOgStampChips,
  fanOgStats,
  fanOgTitle,
  fanOgUsername,
  pickFanAvatarUrl,
} from "./fan-og-presentation";
import type { FanPassportPublicPage } from "@/lib/types/passport";

function basePage(
  overrides: Partial<FanPassportPublicPage> = {},
): FanPassportPublicPage {
  return {
    username: "toluwave",
    user_id: "u1",
    display_name: "Tolu Nightlife Explorer",
    avatar_url: "/media/avatar.jpg",
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
        description: "x",
        criteria_key: "first_ticket",
        awarded_at: "2026-01-01",
        earned: true,
      },
      {
        id: "b2",
        slug: "checked-in-attendee",
        name: "Checked-in Attendee",
        description: "x",
        criteria_key: "checked_in_attendee",
        awarded_at: "2026-01-02",
        earned: true,
      },
      {
        id: "b3",
        slug: "nightlife-explorer",
        name: "Nightlife Explorer",
        description: "x",
        criteria_key: "nightlife_explorer",
        awarded_at: "2026-01-03",
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

describe("fan OG presentation", () => {
  it("builds verified title and share handle from share_path", () => {
    expect(fanOgTitle(basePage())).toBe(
      "Tolu Nightlife Explorer — Verified Fan Passport | Pàdéyá",
    );
    expect(fanOgShareHandle(basePage())).toBe("padeya.com/f/toluwave");
  });

  it("uses neutral title when no verified activity", () => {
    expect(
      fanOgTitle(
        basePage({
          events_attended: 0,
          hosts_followed: 0,
          badges_earned_count: 0,
          badges: [],
          is_superfan: false,
        }),
      ),
    ).toBe("Tolu Nightlife Explorer's Fan Passport | Pàdéyá");
    expect(
      fanOgShowVerified(
        basePage({
          events_attended: 0,
          badges_earned_count: 0,
          badges: [],
          is_superfan: false,
        }),
      ),
    ).toBe(false);
  });

  it("formats identity fields with truncation", () => {
    expect(fanOgDisplayName(basePage())).toBe("Tolu Nightlife Explorer");
    expect(fanOgUsername(basePage())).toBe("@toluwave");
    expect(fanOgLocation(basePage())).toBe("Lagos");
    expect(fanOgBio(basePage())).toContain("afterparties");
    expect(fanOgScenes(basePage())).toBe("Nightlife · Music");
    expect(
      fanOgDisplayName(basePage({ display_name: "A".repeat(60) })).length,
    ).toBeLessThanOrEqual(35);
  });

  it("hides empty location and scenes", () => {
    expect(fanOgLocation(basePage({ favorite_cities: [] }))).toBeNull();
    expect(fanOgScenes(basePage({ favorite_categories: [] }))).toBeNull();
  });

  it("formats stats and stamp chips from public badges only", () => {
    const stats = fanOgStats(basePage());
    expect(stats.map((s) => `${s.value} ${s.label}`)).toEqual([
      "1 EVENT ATTENDED",
      "3 HOSTS FOLLOWED",
      "8 STAMPS EARNED",
    ]);
    expect(fanOgStampChips(basePage()).map((c) => c.label)).toEqual([
      "First Ticket",
      "Checked-in Attendee",
      "Nightlife Explorer",
    ]);
  });

  it("uses discover fallback description when bio is short", () => {
    expect(
      fanOgDescription(basePage({ tagline: "Hi", bio: null })),
    ).toContain("See Tolu Nightlife Explorer");
  });

  it("prefers avatar media og_url", () => {
    expect(
      pickFanAvatarUrl(
        basePage({
          avatar_media: {
            og_url: "/og.webp",
            display_url: "/d.jpg",
            url: "/u.jpg",
          },
        }),
      ),
    ).toBe("/og.webp");
  });
});
