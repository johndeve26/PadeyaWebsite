import { describe, expect, it } from "vitest";

import { hasEventsFacetQuery } from "./facet-policy";
import {
  isIntentionallyNoIndexPath,
  isPublicIndexablePath,
  isRobotsBlocked,
  responseHasNoindex,
} from "./indexability";
import { buildPageMetadata } from "./site";
import { shouldIndexEnvironment } from "./env-policy";

const prodEnv = {
  appEnv: "production",
  vercelEnv: "production",
  nodeEnv: "production",
};

describe("indexability path helpers", () => {
  it("marks public hubs/entities indexable", () => {
    for (const p of [
      "/",
      "/events",
      "/events/demo-night",
      "/events/c/tech",
      "/events/city/lagos",
      "/hosts",
      "/u/djmaze",
      "/fans",
      "/f/toluwave",
      "/sponsorships",
      "/sponsors/korawave-pay",
      "/merch",
      "/merch/legacy-tee",
      "/blog",
      "/blog/a-post",
      "/help",
      "/help/articles/how-to-buy-tickets",
      "/about",
      "/ambassadors",
    ]) {
      expect(isPublicIndexablePath(p)).toBe(true);
      expect(isIntentionallyNoIndexPath(p)).toBe(false);
    }
  });

  it("marks intentional noindex surfaces", () => {
    for (const p of [
      "/login",
      "/register",
      "/dashboard",
      "/host",
      "/sponsor",
      "/events/search",
      "/events/demo-night/checkout",
      "/merch/hosts/djmaze/checkout",
      "/checkout/success",
      "/tickets/claim",
      "/connect",
      "/messages",
      "/admin",
    ]) {
      expect(isIntentionallyNoIndexPath(p)).toBe(true);
      expect(isPublicIndexablePath(p)).toBe(false);
    }
  });
});

describe("response / robots matching", () => {
  it("detects noindex signals", () => {
    expect(
      responseHasNoindex({ robotsMeta: "index, follow" }),
    ).toBe(false);
    expect(
      responseHasNoindex({ robotsMeta: "noindex, follow" }),
    ).toBe(true);
    expect(
      responseHasNoindex({ googlebotMeta: "noindex" }),
    ).toBe(true);
    expect(
      responseHasNoindex({ xRobotsTag: "noindex, nofollow" }),
    ).toBe(true);
  });

  it("does not let checkout wildcards block public event/merch paths", () => {
    const robots = `User-Agent: *
Allow: /
Disallow: /events/*/checkout
Disallow: /merch/hosts/*/checkout
Disallow: /dashboard/
`;
    expect(isRobotsBlocked(robots, "/events")).toBe(false);
    expect(isRobotsBlocked(robots, "/events/demo-night")).toBe(false);
    expect(isRobotsBlocked(robots, "/events/city/lagos")).toBe(false);
    expect(isRobotsBlocked(robots, "/merch")).toBe(false);
    expect(isRobotsBlocked(robots, "/merch/legacy-tee")).toBe(false);
    expect(isRobotsBlocked(robots, "/merch/hosts/djmaze")).toBe(false);
    expect(isRobotsBlocked(robots, "/events/demo-night/checkout")).toBe(true);
    expect(isRobotsBlocked(robots, "/merch/hosts/djmaze/checkout")).toBe(true);
    expect(isRobotsBlocked(robots, "/dashboard")).toBe(true);
  });
});

describe("production public metadata regression", () => {
  it("emits indexable robots for core public routes", () => {
    for (const path of [
      "/",
      "/events",
      "/hosts",
      "/fans",
      "/sponsorships",
      "/merch",
      "/blog",
      "/help",
      "/events/city/lagos",
      "/events/c/tech",
    ]) {
      const meta = buildPageMetadata({
        title: "t",
        description: "d",
        path,
        env: prodEnv,
      });
      expect(meta.robots).toMatchObject({ index: true, follow: true });
      expect(String(meta.alternates?.canonical)).toContain("https://padeya.com");
    }
  });

  it("keeps faceted /events noindex while tracking-only stays indexable", () => {
    expect(hasEventsFacetQuery({ q: "lagos" })).toBe(true);
    expect(hasEventsFacetQuery({ utm_source: "x", ref: "y" })).toBe(false);
    const faceted = buildPageMetadata({
      title: "Events",
      description: "d",
      path: "/events",
      noIndex: true,
      noIndexFollow: true,
      env: prodEnv,
    });
    expect(faceted.robots).toMatchObject({ index: false, follow: true });
  });
});

describe("environment indexability", () => {
  it("indexes Vercel production; protects staging/preview/dev/test", () => {
    expect(
      shouldIndexEnvironment({
        appEnv: "production",
        vercelEnv: "production",
        nodeEnv: "production",
      }),
    ).toBe(true);
    expect(
      shouldIndexEnvironment({
        appEnv: "staging",
        vercelEnv: null,
        nodeEnv: "production",
      }),
    ).toBe(false);
    expect(
      shouldIndexEnvironment({
        appEnv: "production",
        vercelEnv: "preview",
        nodeEnv: "production",
      }),
    ).toBe(false);
    expect(
      shouldIndexEnvironment({
        appEnv: "development",
        nodeEnv: "development",
      }),
    ).toBe(false);
    expect(
      shouldIndexEnvironment({
        appEnv: "test",
        nodeEnv: "test",
      }),
    ).toBe(false);
  });
});
