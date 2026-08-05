import { describe, expect, it } from "vitest";

import {
  fanOgBio,
  fanOgDescription,
  fanOgDisplayName,
  fanOgDisplayNameFontSize,
  fanOgEmptyStampCopy,
  fanOgLocation,
  fanOgScenes,
  fanOgShareHandle,
  fanOgShowVerified,
  fanOgStampChips,
  fanOgStats,
  fanOgStatusLine,
  fanOgSupportCopy,
  fanOgTitle,
  fanOgUsername,
  pickFanAvatarUrl,
} from "./fan-og-presentation";
import type { FanPassportPublicPage } from "@/lib/types/passport";

function basePage(
  overrides: Partial<FanPassportPublicPage> = {},
): FanPassportPublicPage {
  return {
    username: "abiodun",
    user_id: "u1",
    display_name: "Abiodun",
    avatar_url: "/media/avatar.jpg",
    tagline: "Let's get the party started",
    bio: null,
    visibility: "public",
    is_superfan: false,
    events_attended: 0,
    hosts_followed: 5,
    badges_earned_count: 0,
    reviews_written: 0,
    cities_explored: 0,
    categories_explored: 0,
    connections_count: 0,
    favorite_categories: [],
    favorite_cities: ["Lagos"],
    badges: [],
    attended_events: [],
    followed_hosts: [],
    reviews: [],
    vault_unlocks: [],
    share_path: "/f/abiodun",
    ...overrides,
  };
}

describe("fan OG presentation (improved card)", () => {
  it("never infers verification from activity", () => {
    expect(fanOgShowVerified(basePage({ events_attended: 5, badges_earned_count: 3 }))).toBe(
      false,
    );
    expect(fanOgTitle(basePage())).toBe("Abiodun's Fan Passport | Pàdéyá");
    expect(fanOgStatusLine(basePage())).toBe("Public Passport");
  });

  it("honors an explicit verified flag when present", () => {
    const verified = {
      ...basePage(),
      is_verified: true,
    } as FanPassportPublicPage & { is_verified: boolean };
    expect(fanOgShowVerified(verified)).toBe(true);
    expect(fanOgTitle(verified)).toBe("Abiodun — Verified Fan Passport | Pàdéyá");
    expect(fanOgStatusLine(verified)).toBe("Verified Passport");
  });

  it("sizes display names and formats identity", () => {
    expect(fanOgDisplayNameFontSize("Abiodun")).toBe(60);
    expect(fanOgDisplayNameFontSize("A".repeat(45))).toBe(40);
    expect(fanOgUsername(basePage())).toBe("@abiodun");
    expect(fanOgLocation(basePage())).toBe("Lagos");
    expect(fanOgBio(basePage())).toContain("party");
  });

  it("shows progress copy for empty stamps and activity-aware support line", () => {
    expect(fanOgEmptyStampCopy(basePage())).toContain("unlocks a passport stamp");
    expect(fanOgSupportCopy(basePage())).toContain("Build your nightlife story");
    expect(
      fanOgSupportCopy(basePage({ events_attended: 2 })),
    ).toContain("Verified nights");
    expect(
      fanOgEmptyStampCopy(
        basePage({
          badges_earned_count: 2,
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
          ],
        }),
      ),
    ).toBeNull();
  });

  it("formats horizontal stats with active flags", () => {
    const stats = fanOgStats(basePage());
    expect(stats.map((s) => s.value)).toEqual(["0", "5", "0"]);
    expect(stats.find((s) => s.key === "hosts")?.active).toBe(true);
    expect(stats.find((s) => s.key === "events")?.active).toBe(false);
  });

  it("caps stamp chips and reports extras", () => {
    const badges = Array.from({ length: 6 }, (_, i) => ({
      id: `b${i}`,
      slug: `s${i}`,
      name: `Stamp ${i}`,
      description: "x",
      criteria_key: "first_ticket",
      awarded_at: "2026-01-01",
      earned: true,
    }));
    const pack = fanOgStampChips(
      basePage({ badges, badges_earned_count: 6 }),
    );
    expect(pack.chips).toHaveLength(4);
    expect(pack.extra).toBe(2);
    expect(pack.summary).toContain("6 passport stamps");
  });

  it("uses public-safe description fallback", () => {
    expect(fanOgDescription(basePage({ tagline: "Hi", bio: null }))).toContain(
      "public Fan Passport",
    );
    expect(fanOgShareHandle(basePage())).toBe("padeya.com/f/abiodun");
    expect(fanOgScenes(basePage())).toBeNull();
    expect(pickFanAvatarUrl(basePage())).toBe("/media/avatar.jpg");
    expect(fanOgDisplayName(basePage())).toBe("Abiodun");
  });
});
