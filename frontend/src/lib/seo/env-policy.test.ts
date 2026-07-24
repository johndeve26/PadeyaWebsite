import { describe, expect, it } from "vitest";

import {
  getCanonicalSiteOrigin,
  isForbiddenCanonicalHost,
  isProductionSeoEnvironment,
  isValidProductionCanonicalOrigin,
  LIVE_SITE_ORIGIN,
  robotsMetaForEnvironment,
  shouldIndexEnvironment,
  type SeoEnvInput,
} from "./env-policy";
import {
  buildEventMetadata,
  eventJsonLd,
  isEventSeoIndexable,
  isPasswordProtectedEvent,
} from "./event-metadata";
import { canonicalPathOnly, stripTrackingSearchParams } from "./canonical-path";
import { buildPageMetadata, rootSeoMetadataFields, siteOrigin } from "./site";
import { filterListedEventsForSitemap } from "./sitemap-filter";
import type { EventItem } from "@/lib/types/events";

const prodEnv: SeoEnvInput = {
  appEnv: "production",
  vercelEnv: "production",
  nodeEnv: "production",
  nextPublicSiteUrl: "https://padeya.com",
};

function eventFixture(over: Partial<EventItem> = {}): EventItem {
  return {
    id: "e1",
    slug: "lagos-night",
    title: "Lagos Night",
    description: "Meet at 12 Admiralty Way, Lekki for doors.",
    short_tagline: "A night in Lekki",
    status: "published",
    visibility: "listed",
    category_id: null,
    host_id: "h1",
    start_datetime: "2026-08-01T18:00:00Z",
    end_datetime: "2026-08-01T23:00:00Z",
    event_type: "public",
    venue_name: null,
    city: "Lagos",
    state: "Lagos",
    country: "NG",
    location_visibility: "area_only",
    location_address_revealed: false,
    address: "12 Admiralty Way, Lekki",
    ticket_types: [],
    ...over,
  } as EventItem;
}

describe("isProductionSeoEnvironment / shouldIndexEnvironment", () => {
  it("allows production when APP_ENV=production", () => {
    expect(isProductionSeoEnvironment(prodEnv)).toBe(true);
    expect(shouldIndexEnvironment(prodEnv)).toBe(true);
  });

  it("allows production Node build when APP_ENV is missing", () => {
    const env: SeoEnvInput = {
      appEnv: null,
      vercelEnv: null,
      nodeEnv: "production",
    };
    expect(isProductionSeoEnvironment(env)).toBe(true);
    expect(shouldIndexEnvironment(env)).toBe(true);
  });

  it("allows VERCEL_ENV=production", () => {
    expect(
      shouldIndexEnvironment({
        appEnv: null,
        vercelEnv: "production",
        nodeEnv: "production",
      }),
    ).toBe(true);
  });

  it("blocks development", () => {
    expect(
      shouldIndexEnvironment({
        appEnv: "development",
        nodeEnv: "development",
      }),
    ).toBe(false);
  });

  it("blocks staging", () => {
    expect(
      shouldIndexEnvironment({
        appEnv: "staging",
        nodeEnv: "production",
        vercelEnv: "production",
      }),
    ).toBe(false);
  });

  it("blocks Vercel preview even if APP_ENV=production", () => {
    expect(
      shouldIndexEnvironment({
        appEnv: "production",
        vercelEnv: "preview",
        nodeEnv: "production",
      }),
    ).toBe(false);
  });

  it("blocks test env", () => {
    expect(
      shouldIndexEnvironment({
        appEnv: "test",
        nodeEnv: "test",
      }),
    ).toBe(false);
  });
});

describe("getCanonicalSiteOrigin", () => {
  it("returns https://padeya.com in production", () => {
    expect(getCanonicalSiteOrigin(prodEnv)).toBe(LIVE_SITE_ORIGIN);
    expect(siteOrigin(prodEnv)).toBe("https://padeya.com");
  });

  it("rejects localhost / preview / tunnel as canonical", () => {
    expect(isForbiddenCanonicalHost("localhost")).toBe(true);
    expect(isForbiddenCanonicalHost("127.0.0.1")).toBe(true);
    expect(isForbiddenCanonicalHost("padeya-git-main.vercel.app")).toBe(true);
    expect(isForbiddenCanonicalHost("padeya.onrender.com")).toBe(true);
    expect(isForbiddenCanonicalHost("foo.trycloudflare.com")).toBe(true);
    expect(isForbiddenCanonicalHost("padeya.smartlancedesigns.com")).toBe(true);

    expect(
      getCanonicalSiteOrigin({
        ...prodEnv,
        nextPublicSiteUrl: "http://localhost:3000",
      }),
    ).toBe(LIVE_SITE_ORIGIN);

    expect(
      getCanonicalSiteOrigin({
        ...prodEnv,
        nextPublicSiteUrl: "https://padeya-git-x.vercel.app",
      }),
    ).toBe(LIVE_SITE_ORIGIN);
  });

  it("normalizes www.padeya.com to apex", () => {
    expect(
      getCanonicalSiteOrigin({
        ...prodEnv,
        nextPublicSiteUrl: "https://www.padeya.com/",
      }),
    ).toBe("https://padeya.com");
    expect(isValidProductionCanonicalOrigin("https://www.padeya.com")).toBe(true);
    expect(isValidProductionCanonicalOrigin("http://padeya.com")).toBe(false);
  });

  it("uses live origin in non-production (pages are noindex)", () => {
    expect(
      getCanonicalSiteOrigin({
        appEnv: "staging",
        nodeEnv: "production",
        nextPublicSiteUrl: "https://staging.example.com",
      }),
    ).toBe(LIVE_SITE_ORIGIN);
  });
});

describe("rootSeoMetadataFields / buildPageMetadata", () => {
  it("sets metadataBase to padeya.com in production", () => {
    const fields = rootSeoMetadataFields(prodEnv);
    const base = fields.metadataBase;
    expect(base).toBeInstanceOf(URL);
    expect((base as URL).origin).toBe("https://padeya.com");
    expect(fields.robots).toEqual({ index: true, follow: true });
  });

  it("noindexes non-production via robotsMetaForEnvironment", () => {
    expect(
      robotsMetaForEnvironment({ appEnv: "staging", nodeEnv: "production" }),
    ).toEqual({ index: false, follow: false });
  });

  it("forces noindex on public builder when env is non-production", () => {
    const meta = buildPageMetadata({
      title: "Events",
      description: "Discover events",
      path: "/events?utm_source=x&ref=amb",
      env: { appEnv: "preview", vercelEnv: "preview", nodeEnv: "production" },
    });
    expect(meta.alternates?.canonical).toBe("https://padeya.com/events");
    expect(meta.robots).toMatchObject({ index: false, follow: false });
  });

  it("keeps production public pages indexable without noIndex flag", () => {
    const meta = buildPageMetadata({
      title: "Events",
      description: "Discover events",
      path: "/events",
      env: prodEnv,
    });
    expect(meta.alternates?.canonical).toBe("https://padeya.com/events");
    expect(meta.robots).toBeUndefined();
  });

  it("never puts tracking params in canonical", () => {
    expect(canonicalPathOnly("/events?utm_source=ig&ref=abc")).toBe("/events");
    expect(stripTrackingSearchParams("/events?utm_campaign=x&ref=1")).toBe(
      "/events",
    );
    const meta = buildPageMetadata({
      title: "Events",
      description: "x",
      path: "/events?utm_source=ig&ref=host",
      env: prodEnv,
    });
    expect(meta.alternates?.canonical).toBe("https://padeya.com/events");
  });
});

describe("event visibility SEO", () => {
  it("indexes listed events in production", () => {
    const event = eventFixture({ visibility: "listed" });
    expect(isEventSeoIndexable(event)).toBe(true);
    const meta = buildEventMetadata(event, prodEnv);
    expect(meta.alternates?.canonical).toBe(
      "https://padeya.com/events/lagos-night",
    );
    expect(meta.robots).toBeUndefined();
  });

  it("noindexes unlisted events", () => {
    const event = eventFixture({ visibility: "unlisted" });
    expect(isEventSeoIndexable(event)).toBe(false);
    const meta = buildEventMetadata(event, prodEnv);
    expect(meta.robots).toMatchObject({ index: false, follow: false });
  });

  it("noindexes password events and hides body description", () => {
    const event = eventFixture({
      visibility: "password_protected",
      description: "SECRET VENUE 12 Admiralty Way",
      seo_description: "Do not leak this",
    });
    expect(isPasswordProtectedEvent(event)).toBe(true);
    const meta = buildEventMetadata(event, prodEnv);
    expect(meta.robots).toMatchObject({ index: false, follow: false });
    expect(String(meta.description)).not.toContain("SECRET");
    expect(String(meta.description)).toContain("Password-protected");
    expect(eventJsonLd(event)).toBeNull();
  });

  it("excludes unlisted and password from sitemap filter", () => {
    const listed = filterListedEventsForSitemap([
      { slug: "a", visibility: "listed" },
      { slug: "b", visibility: "unlisted" },
      { slug: "c", visibility: "password_protected" },
      { slug: "d", visibility: "approval_required" },
    ]);
    expect(listed.map((e) => e.slug)).toEqual(["a"]);
  });
});
