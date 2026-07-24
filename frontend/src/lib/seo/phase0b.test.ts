import { describe, expect, it } from "vitest";

import {
  buildFanMetadata,
  fanPassportJsonLd,
  isFanPassportIndexable,
} from "./fan-metadata";
import {
  buildHostMetadata,
  buildHostMetadataFromPage,
  hostLegacyCanonicalPath,
  hostLegacyJsonLd,
} from "./host-metadata";
import { pickEntityOgImage, resolvePublicAssetUrl } from "./public-asset";
import {
  buildSponsorMetadata,
  sponsorProfileJsonLd,
  sponsorshipsIndexMetadata,
} from "./sponsor-metadata";
import type { SeoEnvInput } from "./env-policy";
import type { LegacyPage } from "@/lib/types/legacy";
import type { FanPassportPublicPage } from "@/lib/types/passport";
import type { SponsorPublicProfile } from "@/lib/sponsor-profiles-api";

const prodEnv: SeoEnvInput = {
  appEnv: "production",
  vercelEnv: "production",
  nodeEnv: "production",
  nextPublicSiteUrl: "https://padeya.com",
};

describe("public assets", () => {
  it("resolves relative media to padeya.com", () => {
    expect(resolvePublicAssetUrl("/media/x.png")).toBe(
      "https://padeya.com/media/x.png",
    );
    expect(resolvePublicAssetUrl("https://cdn.example/a.jpg")).toBe(
      "https://cdn.example/a.jpg",
    );
  });

  it("picks cover over avatar over logo", () => {
    expect(
      pickEntityOgImage({
        cover: "/c.jpg",
        avatar: "/a.jpg",
        logo: "/l.jpg",
      }),
    ).toBe("https://padeya.com/c.jpg");
  });
});

describe("host Legacy SEO", () => {
  const page = {
    host_id: "h1",
    display_name: "DJ Maze",
    username: "djmaze",
    status: "active",
    verified: true,
    legacy_status: "active",
    profile: {
      bio: "Lagos nightlife curator",
      website: "https://example.com/maze",
      city: "Lagos",
      state: "Lagos",
      country: "NG",
      avatar_url: "/media/avatar.jpg",
      cover_url: "/media/cover.jpg",
      social_links: { instagram: "https://instagram.com/djmaze" },
    },
    stats: {
      events_hosted: 1,
      tickets_sold: 1,
      verified_checkins: 1,
      average_verified_rating: null,
      review_count: 0,
      followers: 0,
      repeat_buyers_rate: null,
      refund_dispute_rate: null,
      legacy_status: "active",
    },
    about: null,
    upcoming_events: [],
    past_events: [],
    reviews: [],
    follow_enabled: true,
    share_path: "/@djmaze",
    tagline: "Nights that move the city",
    settings: { sponsorship_available: false, primary_category_slug: "nightlife" },
    social_links: [
      {
        platform: "x",
        url: "https://x.com/djmaze",
        sort_order: 0,
        is_visible: true,
      },
    ],
    contact: {
      preference: "email",
      public_email: "secret@example.com",
      show_contact_form: true,
    },
  } as LegacyPage;

  it("uses /u/{username} canonical", () => {
    expect(hostLegacyCanonicalPath("djmaze")).toBe("/u/djmaze");
    const meta = buildHostMetadataFromPage(page);
    // Force prod via buildHostMetadata path check
    const direct = buildHostMetadata({
      displayName: "DJ Maze",
      bio: "bio",
      slug: "djmaze",
      image: "/media/x.jpg",
    });
    expect(String(direct.alternates?.canonical)).toContain("/u/djmaze");
    expect(String(meta.alternates?.canonical)).toContain("/u/djmaze");
  });

  it("emits ProfilePage Organization without private email", () => {
    const ld = hostLegacyJsonLd(page);
    expect(ld["@type"]).toBe("ProfilePage");
    const org = ld.mainEntity as Record<string, unknown>;
    expect(org["@type"]).toBe("Organization");
    expect(org.name).toBe("DJ Maze");
    const blob = JSON.stringify(ld);
    expect(blob).not.toContain("secret@example.com");
    expect(blob).toContain("https://instagram.com/djmaze");
  });
});

describe("sponsor profile SEO", () => {
  const profile = {
    id: "s1",
    display_name: "Peak Brands",
    slug: "peak-brands",
    sponsor_type: "brand",
    logo_url: "/media/logo.png",
    cover_image_url: null,
    use_cover_fallback: true,
    short_bio: "Consumer brand partnerships",
    description: null,
    website_url: "https://peak.example",
    industry: "beverages",
    categories: ["nightlife"],
    target_locations: ["lagos"],
    campaign_goals: [],
    verification_status: "verified",
    verified: true,
    show_contact_cta: true,
    accepting_inquiries: true,
    partnership_blurb: null,
    summary_cards: [],
    public_campaigns: [],
    sponsored_events: [],
    partnered_hosts: [],
    related_sponsors: [],
  } as SponsorPublicProfile;

  it("builds canonical sponsor metadata", () => {
    const meta = buildSponsorMetadata(profile);
    expect(String(meta.alternates?.canonical)).toBe(
      "https://padeya.com/sponsors/peak-brands",
    );
    expect(String(meta.title)).toContain("Peak Brands");
  });

  it("emits Organization ProfilePage without budgets/contacts", () => {
    const ld = sponsorProfileJsonLd(profile);
    const blob = JSON.stringify(ld);
    expect(ld["@type"]).toBe("ProfilePage");
    expect(blob).toContain("Peak Brands");
    expect(blob).not.toContain("budget");
    expect(blob).not.toContain("contact_email");
  });

  it("sponsorships index has metadata helper", () => {
    const meta = sponsorshipsIndexMetadata();
    expect(String(meta.alternates?.canonical)).toBe(
      "https://padeya.com/sponsorships",
    );
  });
});

describe("fan passport SEO", () => {
  const publicFan = {
    username: "ada",
    user_id: "u1",
    display_name: "Ada",
    avatar_url: "/media/ada.jpg",
    tagline: "City nights",
    bio: null,
    visibility: "public",
    is_superfan: false,
    events_attended: 3,
    hosts_followed: 1,
    badges_earned_count: 1,
    reviews_written: 0,
    cities_explored: 1,
    categories_explored: 1,
    connections_count: 0,
    favorite_categories: [],
    favorite_cities: [],
    badges: [],
    attended_events: [],
    followed_hosts: [],
    reviews: [],
    vault_unlocks: [],
  } as unknown as FanPassportPublicPage;

  it("indexes public passports with Person schema", () => {
    expect(isFanPassportIndexable(publicFan)).toBe(true);
    const meta = buildFanMetadata(publicFan);
    expect(String(meta.alternates?.canonical)).toBe(
      "https://padeya.com/f/ada",
    );
    const ld = fanPassportJsonLd(publicFan);
    expect(ld?.["@type"]).toBe("ProfilePage");
    expect((ld?.mainEntity as { "@type": string })["@type"]).toBe("Person");
  });

  it("noindexes unlisted and skips Person JSON-LD", () => {
    const unlisted = { ...publicFan, visibility: "unlisted" as const };
    expect(isFanPassportIndexable(unlisted)).toBe(false);
    const meta = buildFanMetadata(unlisted);
    expect(meta.robots).toMatchObject({ index: false, follow: false });
    expect(fanPassportJsonLd(unlisted)).toBeNull();
  });
});

// silence unused in case tree-shaking of prodEnv in future
void prodEnv;
