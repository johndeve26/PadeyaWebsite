import { describe, expect, it } from "vitest";

import {
  buildEntitySitemapPaths,
  collectNonEmptyBlogHubSlugs,
  filterFansForSitemap,
  filterHostsForSitemap,
  filterListedEventsForSitemap,
  filterMerchForSitemap,
  filterSponsorsForSitemap,
  isExcludedFromSitemap,
  isForbiddenSitemapPath,
  isSitemapEligibleEvent,
  isSitemapEligibleFan,
  isSitemapEligibleHost,
  isSitemapEligibleMerch,
  isSitemapEligibleSponsor,
  sitemapLastModified,
} from "./sitemap-filter";

describe("sitemap event privacy", () => {
  it("includes only listed events", () => {
    const listed = filterListedEventsForSitemap([
      { slug: "ok", visibility: "listed" },
      { slug: "default" },
      { slug: "unlisted", visibility: "unlisted" },
      { slug: "pw", visibility: "password_protected" },
      { slug: "approval", visibility: "approval_required" },
      { slug: "draft", visibility: "private" },
      { slug: "" },
    ]);
    expect(listed.map((e) => e.slug)).toEqual(["ok", "default"]);
  });

  it("rejects private event visibilities", () => {
    expect(isSitemapEligibleEvent({ slug: "a", visibility: "unlisted" })).toBe(
      false,
    );
    expect(
      isSitemapEligibleEvent({ slug: "a", visibility: "password_protected" }),
    ).toBe(false);
    expect(
      isSitemapEligibleEvent({ slug: "a", visibility: "approval_required" }),
    ).toBe(false);
    expect(isExcludedFromSitemap("unlisted")).toBe(true);
  });
});

describe("sitemap host / fan / sponsor privacy", () => {
  it("never admits hosts without username", () => {
    expect(isSitemapEligibleHost({ username: "dj-ade" })).toBe(true);
    expect(isSitemapEligibleHost({ username: "  " })).toBe(false);
    expect(isSitemapEligibleHost({})).toBe(false);
    expect(
      filterHostsForSitemap([
        { username: "a" },
        { username: null },
        { username: "" },
      ]),
    ).toHaveLength(1);
  });

  it("never invents private/unlisted fans — directory cards only", () => {
    expect(isSitemapEligibleFan({ username: "kunle" })).toBe(true);
    expect(isSitemapEligibleFan({ username: null })).toBe(false);
    expect(
      filterFansForSitemap([{ username: "a" }, { username: "" }]),
    ).toHaveLength(1);
  });

  it("rejects unverified or slugless sponsors", () => {
    expect(
      isSitemapEligibleSponsor({ slug: "acme", verified: true }),
    ).toBe(true);
    expect(
      isSitemapEligibleSponsor({ slug: "pending", verified: false }),
    ).toBe(false);
    expect(isSitemapEligibleSponsor({ slug: "", verified: true })).toBe(false);
    expect(
      filterSponsorsForSitemap([
        { slug: "ok", verified: true },
        { slug: "nope", verified: false },
        { slug: null, verified: true },
      ]),
    ).toEqual([{ slug: "ok", verified: true }]);
  });
});

describe("sitemap merch + blog hubs", () => {
  it("excludes non-indexable merch", () => {
    expect(isSitemapEligibleMerch({ slug: "tee", indexable: true })).toBe(true);
    expect(isSitemapEligibleMerch({ slug: "tee", indexable: false })).toBe(
      false,
    );
    expect(
      filterMerchForSitemap([
        { slug: "a", indexable: true },
        { slug: "b", indexable: false },
        { slug: "c" },
      ]).map((m) => m.slug),
    ).toEqual(["a", "c"]);
  });

  it("only marks hubs with published posts as non-empty", () => {
    const hubs = collectNonEmptyBlogHubSlugs([
      {
        status: "published",
        category: { slug: "guides" },
        author: { slug: "team" },
        tags: [{ slug: "seo" }, { slug: "hosts" }],
      },
      {
        status: "draft",
        category: { slug: "secret" },
        author: { slug: "ghost" },
        tags: [{ slug: "draft-only" }],
      },
    ]);
    expect([...hubs.categories]).toEqual(["guides"]);
    expect([...hubs.authors]).toEqual(["team"]);
    expect([...hubs.tags].sort()).toEqual(["hosts", "seo"]);
  });
});

describe("sitemap lastModified", () => {
  it("uses real entity timestamps and never invents now", () => {
    const d = sitemapLastModified("2026-01-15T12:00:00.000Z", null);
    expect(d?.toISOString()).toBe("2026-01-15T12:00:00.000Z");
    expect(sitemapLastModified(null, undefined, "")).toBeUndefined();
    expect(sitemapLastModified("not-a-date")).toBeUndefined();
  });
});

describe("forbidden sitemap paths", () => {
  it("blocks auth, workspace, checkout, search, and token URLs", () => {
    const blocked = [
      "/events/search",
      "/login",
      "/register",
      "/host/events",
      "/dashboard",
      "/admin/users",
      "/sponsor/settings",
      "/checkout/abc",
      "/events/foo/checkout",
      "/ambassador/links",
      "/team/invite/xyz",
      "/tickets/claim/tok",
      "https://padeya.com/events/search",
      "/f/user?token=abc",
    ];
    for (const p of blocked) {
      expect(isForbiddenSitemapPath(p), p).toBe(true);
    }
  });

  it("allows public entity paths", () => {
    for (const p of [
      "/u/dj-ade",
      "/f/kunle",
      "/sponsors/acme",
      "/fans",
      "/ambassadors",
      "/blog/category/guides",
      "/events/lagos-night",
    ]) {
      expect(isForbiddenSitemapPath(p), p).toBe(false);
    }
  });
});

describe("buildEntitySitemapPaths privacy assembly", () => {
  it("never emits private hosts/fans/sponsors and omits empty hubs", () => {
    const paths = buildEntitySitemapPaths({
      includeFansDirectory: true,
      ambassadors: true,
      hosts: [{ username: "public-host" }, { username: "" }, {}],
      fans: [{ username: "public-fan" }, { username: null }],
      sponsors: [
        { slug: "verified-co", verified: true },
        { slug: "pending-co", verified: false },
        { slug: "directory-co" },
      ],
      blogHubs: {
        categories: ["guides", "empty-cat"],
        tags: ["seo", "empty-tag"],
        authors: ["team", "empty-author"],
        nonEmpty: {
          categories: new Set(["guides"]),
          tags: new Set(["seo"]),
          authors: new Set(["team"]),
        },
      },
    });

    expect(paths).toContain("/fans");
    expect(paths).toContain("/ambassadors");
    expect(paths).toContain("/ambassadors/events");
    expect(paths).toContain("/ambassadors/how-it-works");
    expect(paths).toContain("/u/public-host");
    expect(paths).toContain("/f/public-fan");
    expect(paths).toContain("/sponsors/verified-co");
    expect(paths).toContain("/sponsors/directory-co");
    expect(paths).toContain("/blog/category/guides");
    expect(paths).toContain("/blog/tag/seo");
    expect(paths).toContain("/blog/author/team");

    expect(paths).not.toContain("/u/");
    expect(paths.some((p) => p.includes("pending-co"))).toBe(false);
    expect(paths).not.toContain("/blog/category/empty-cat");
    expect(paths).not.toContain("/blog/tag/empty-tag");
    expect(paths).not.toContain("/blog/author/empty-author");
    expect(paths.every((p) => !isForbiddenSitemapPath(p))).toBe(true);
  });
});
