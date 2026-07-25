import { describe, expect, it } from "vitest";

import {
  EVENTS_FACET_CANONICAL_PATH,
  eventsSearchPageMetadataPolicy,
  hasEventsFacetQuery,
} from "./facet-policy";
import {
  buildHubInventoryFromEvents,
  evaluateCityCategoryHubEligibility,
  evaluateLocationHubEligibility,
  HUB_ELIGIBILITY,
  isCityCategoryInSitemap,
  isLocationInSitemap,
  locationHubFallbackCopy,
} from "./hub-eligibility";
import {
  DECORATIVE_ALT,
  eventCoverAlt,
  merchImageAlt,
  sponsorLogoAlt,
} from "./image-alt";
import { hubPageMetadata } from "./hub-page";

describe("faceted /events policy", () => {
  it("canonicalizes filter/query variants to /events and marks facets noindex", () => {
    expect(EVENTS_FACET_CANONICAL_PATH).toBe("/events");
    expect(hasEventsFacetQuery({ sort: "popular" })).toBe(true);
    expect(hasEventsFacetQuery({ q: "afrobeats" })).toBe(true);
    expect(hasEventsFacetQuery({ category: "music" })).toBe(true);
    expect(hasEventsFacetQuery({ utm_source: "x" })).toBe(false);
    expect(hasEventsFacetQuery({ ref: "abc" })).toBe(false);
    expect(hasEventsFacetQuery({})).toBe(false);

    const meta = hubPageMetadata({
      title: "Events",
      description: "Discover events",
      path: "/events",
      noIndex: hasEventsFacetQuery({ sort: "popular" }),
      noIndexFollow: true,
      env: {
        appEnv: "production",
        vercelEnv: "production",
        nodeEnv: "production",
      },
    });
    expect(meta.alternates?.canonical).toBe("https://padeya.com/events");
    expect(meta.robots).toMatchObject({
      index: false,
      follow: true,
    });
  });

  it("/events/search is never indexable and canonicalizes to /events", () => {
    const policy = eventsSearchPageMetadataPolicy();
    expect(policy.noIndex).toBe(true);
    expect(policy.canonicalPath).toBe("/events");
    const meta = hubPageMetadata({
      title: "Search",
      description: "Search",
      path: policy.path,
      canonicalPath: policy.canonicalPath,
      noIndex: policy.noIndex,
    });
    expect(meta.alternates?.canonical).toBe("https://padeya.com/events");
    expect(String(meta.alternates?.canonical)).not.toContain("search");
    // Page overrides to follow:true; helper still marks noindex.
    expect(meta.robots).toBeTruthy();
  });
});

describe("location / city×category thin hubs", () => {
  it("indexes valid locations at or above threshold", () => {
    const ok = evaluateLocationHubEligibility({
      exists: true,
      isActive: true,
      kind: "city",
      eventCount: HUB_ELIGIBILITY.locationMinEvents,
      seoIndexMode: "auto",
    });
    expect(ok.indexable).toBe(true);
    expect(ok.reason).toBe("ok");
  });

  it("noindexes below threshold unless force_index", () => {
    const thin = evaluateLocationHubEligibility({
      exists: true,
      isActive: true,
      kind: "city",
      eventCount: 0,
      seoIndexMode: "auto",
    });
    expect(thin.indexable).toBe(false);
    expect(thin.reason).toBe("below_threshold");

    const forced = evaluateLocationHubEligibility({
      exists: true,
      isActive: true,
      kind: "city",
      eventCount: 0,
      seoIndexMode: "force_index",
    });
    expect(forced.indexable).toBe(true);
    expect(forced.reason).toBe("force_index");
  });

  it("honors force_noindex even with inventory", () => {
    const r = evaluateLocationHubEligibility({
      exists: true,
      isActive: true,
      kind: "city",
      eventCount: 50,
      seoIndexMode: "force_noindex",
    });
    expect(r.indexable).toBe(false);
    expect(r.reason).toBe("force_noindex");
  });

  it("keeps empty valid locations usable but noindex (not missing)", () => {
    const r = evaluateLocationHubEligibility({
      exists: true,
      isActive: true,
      kind: "city",
      eventCount: 0,
    });
    expect(r.indexable).toBe(false);
    expect(r.reason).not.toBe("missing");
  });

  it("city×category uses stricter threshold", () => {
    const below = evaluateCityCategoryHubEligibility({
      cityExists: true,
      categoryExists: true,
      eventCount: HUB_ELIGIBILITY.cityCategoryMinEvents - 1,
    });
    expect(below.indexable).toBe(false);

    const ok = evaluateCityCategoryHubEligibility({
      cityExists: true,
      categoryExists: true,
      eventCount: HUB_ELIGIBILITY.cityCategoryMinEvents,
    });
    expect(ok.indexable).toBe(true);
  });

  it("sitemap helpers respect the same eligibility rules", () => {
    const { locationCounts, cityCategoryCounts } = buildHubInventoryFromEvents([
      {
        city: "Lagos",
        category: { slug: "music" },
        location: { kind: "city", slug: "lagos" },
      },
      {
        city: "Lagos",
        category: { slug: "music" },
        location: { kind: "city", slug: "lagos" },
      },
      {
        city: "Ibadan",
        category: { slug: "tech" },
        location: { kind: "city", slug: "ibadan" },
      },
    ]);

    expect(
      isLocationInSitemap(
        { kind: "city", slug: "lagos", is_active: true },
        locationCounts,
      ),
    ).toBe(true);
    expect(
      isLocationInSitemap(
        { kind: "city", slug: "ibadan", is_active: true },
        locationCounts,
      ),
    ).toBe(false);
    expect(
      isCityCategoryInSitemap("lagos", "music", cityCategoryCounts),
    ).toBe(true);
    expect(
      isCityCategoryInSitemap("ibadan", "tech", cityCategoryCounts),
    ).toBe(false);
  });

  it("builds natural fallback copy without keyword stuffing", () => {
    const copy = locationHubFallbackCopy({
      locationName: "Lagos",
      kind: "city",
    });
    expect(copy.title).toBe("Events in Lagos");
    expect(copy.description.toLowerCase()).not.toContain("best cheap");
    expect(copy.description).toContain("Pàdéyá");
  });
});

describe("image alt helpers", () => {
  it("builds meaningful alts and keeps decorative empty", () => {
    expect(eventCoverAlt("Lagos Night")).toBe("Lagos Night event cover");
    expect(merchImageAlt("Legacy Tee")).toBe("Legacy Tee");
    expect(sponsorLogoAlt("Acme")).toBe("Acme logo");
    expect(DECORATIVE_ALT).toBe("");
  });
});
