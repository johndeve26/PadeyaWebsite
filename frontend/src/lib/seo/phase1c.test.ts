import { describe, expect, it } from "vitest";

import {
  isGa4Configured,
  normalizeAnalyticsConsent,
  shouldLoadGa4,
} from "@/lib/analytics-consent";

import {
  assertPadeyaAbsoluteUrl,
  decideMerchProductSample,
  extractCanonicalHref,
  extractJsonLdBlocks,
  extractMetaContent,
  extractTitle,
  isForbiddenLiveHost,
  isMerchHubPath,
  isMerchProductPath,
  isNoindexRobotsContent,
  jsonLdContainsType,
  normalizeSeoBaseUrl,
  parseSitemapLocs,
  pickMerchProductUrl,
  robotsAdvertisesPadeyaSitemap,
  robotsDisallowsPrivateTrees,
  sitemapUrlsLookSafe,
} from "./production-checks";
import { buildSiteVerificationMetadata } from "./verification";
import {
  isClientProductionSeoEnvironment,
  shouldIndexEnvironment,
} from "./env-policy";
import { RESERVED_MERCH_PATH_SEGMENTS } from "./merch-paths";

describe("Search Console / Bing verification metadata", () => {
  it("omits verification when env tokens are empty", () => {
    expect(
      buildSiteVerificationMetadata({
        googleSiteVerification: null,
        bingSiteVerification: null,
      }),
    ).toBeUndefined();
    expect(
      buildSiteVerificationMetadata({
        googleSiteVerification: "  ",
        bingSiteVerification: "",
      }),
    ).toBeUndefined();
  });

  it("emits google verification only when configured", () => {
    expect(
      buildSiteVerificationMetadata({
        googleSiteVerification: "abc123TOKEN",
        bingSiteVerification: null,
      }),
    ).toEqual({ google: "abc123TOKEN" });
  });

  it("emits Bing msvalidate.01 when configured", () => {
    expect(
      buildSiteVerificationMetadata({
        googleSiteVerification: null,
        bingSiteVerification: "BINGTOKEN99",
      }),
    ).toEqual({ other: { "msvalidate.01": "BINGTOKEN99" } });
  });

  it("rejects pasted meta tags / whitespace tokens", () => {
    expect(
      buildSiteVerificationMetadata({
        googleSiteVerification: '<meta name="google-site-verification" content="x">',
        bingSiteVerification: "has space",
      }),
    ).toBeUndefined();
  });
});

describe("GA4 env + consent gating", () => {
  it("accepts G- measurement IDs only", () => {
    expect(isGa4Configured("G-ABCDEF12")).toBe(true);
    expect(isGa4Configured("UA-123")).toBe(false);
    expect(isGa4Configured("")).toBe(false);
    expect(isGa4Configured(null)).toBe(false);
  });

  it("normalizes consent states", () => {
    expect(normalizeAnalyticsConsent("granted")).toBe("granted");
    expect(normalizeAnalyticsConsent("DENIED")).toBe("denied");
    expect(normalizeAnalyticsConsent(null)).toBe("unset");
    expect(normalizeAnalyticsConsent("maybe")).toBe("unset");
  });

  it("loads GA4 only in production SEO with ID + granted consent", () => {
    expect(
      shouldLoadGa4({
        measurementId: "G-ABCDEF12",
        isProductionSeo: true,
        consent: "granted",
      }),
    ).toBe(true);

    expect(
      shouldLoadGa4({
        measurementId: "G-ABCDEF12",
        isProductionSeo: true,
        consent: "denied",
      }),
    ).toBe(false);

    expect(
      shouldLoadGa4({
        measurementId: "G-ABCDEF12",
        isProductionSeo: true,
        consent: "unset",
      }),
    ).toBe(false);

    expect(
      shouldLoadGa4({
        measurementId: "G-ABCDEF12",
        isProductionSeo: false,
        consent: "granted",
      }),
    ).toBe(false);

    expect(
      shouldLoadGa4({
        measurementId: null,
        isProductionSeo: true,
        consent: "granted",
      }),
    ).toBe(false);
  });
});

describe("client production SEO signal for GA4", () => {
  it("treats NEXT_PUBLIC_APP_ENV=staging as non-production", () => {
    expect(
      isClientProductionSeoEnvironment({
        NEXT_PUBLIC_APP_ENV: "staging",
        NODE_ENV: "production",
        VERCEL_ENV: null,
      }),
    ).toBe(false);
    expect(
      isClientProductionSeoEnvironment({
        NEXT_PUBLIC_APP_ENV: "production",
        NODE_ENV: "production",
        VERCEL_ENV: "production",
      }),
    ).toBe(true);
  });
});

describe("production URL / HTML check helpers", () => {
  it("rejects forbidden hosts and non-padeya canonicals", () => {
    expect(isForbiddenLiveHost("localhost")).toBe(true);
    expect(isForbiddenLiveHost("foo.vercel.app")).toBe(true);
    expect(isForbiddenLiveHost("padeya.onrender.com")).toBe(true);
    expect(isForbiddenLiveHost("padeya.smartlancedesigns.com")).toBe(true);
    expect(isForbiddenLiveHost("padeya.com")).toBe(false);

    expect(assertPadeyaAbsoluteUrl("https://padeya.com/events").ok).toBe(true);
    expect(assertPadeyaAbsoluteUrl("http://padeya.com/events").ok).toBe(false);
    expect(assertPadeyaAbsoluteUrl("https://localhost:3000/").ok).toBe(false);
    expect(
      assertPadeyaAbsoluteUrl("https://padeya.com/events?sort=popular").ok,
    ).toBe(false);
  });

  it("parses canonical, title, meta, and JSON-LD from HTML", () => {
    const html = `
      <html><head>
        <title>Night Market · Pàdéyá</title>
        <meta name="description" content="A public event" />
        <link rel="canonical" href="https://padeya.com/events/night-market" />
        <meta property="og:title" content="Night Market" />
        <meta name="robots" content="index,follow" />
        <script type="application/ld+json">
          {"@context":"https://schema.org","@graph":[
            {"@type":"Organization","name":"Pàdéyá"},
            {"@type":"WebSite","name":"Pàdéyá","potentialAction":{"@type":"SearchAction"}}
          ]}
        </script>
        <script type="application/ld+json">
          {"@type":"Event","name":"Night Market"}
        </script>
      </head></html>
    `;
    expect(extractTitle(html)).toBe("Night Market · Pàdéyá");
    expect(extractMetaContent(html, "description")).toBe("A public event");
    expect(extractCanonicalHref(html)).toBe(
      "https://padeya.com/events/night-market",
    );
    expect(isNoindexRobotsContent(extractMetaContent(html, "robots"))).toBe(
      false,
    );
    const blocks = extractJsonLdBlocks(html);
    expect(jsonLdContainsType(blocks, "Organization")).toBe(true);
    expect(jsonLdContainsType(blocks, "WebSite")).toBe(true);
    expect(jsonLdContainsType(blocks, "SearchAction")).toBe(true);
    expect(jsonLdContainsType(blocks, "Event")).toBe(true);
  });

  it("flags noindex robots content", () => {
    expect(isNoindexRobotsContent("noindex, follow")).toBe(true);
    expect(isNoindexRobotsContent("index,follow")).toBe(false);
  });

  it("validates sitemap locs and robots production signals", () => {
    const xml = `<?xml version="1.0"?>
      <urlset>
        <url><loc>https://padeya.com/</loc></url>
        <url><loc>https://padeya.com/events/ok</loc></url>
        <url><loc>https://padeya.com/u/host1</loc></url>
      </urlset>`;
    const urls = parseSitemapLocs(xml);
    expect(urls).toHaveLength(3);
    expect(sitemapUrlsLookSafe(urls).ok).toBe(true);
    expect(
      sitemapUrlsLookSafe([
        "https://padeya.com/events/search",
        "https://localhost/events",
        "https://padeya.com/events?q=1",
      ]).ok,
    ).toBe(false);

    const robots = `User-Agent: *
Allow: /
Disallow: /admin/
Disallow: /dashboard/
Disallow: /host/
Disallow: /sponsor/
Disallow: /login
Sitemap: https://padeya.com/sitemap.xml
`;
    expect(robotsAdvertisesPadeyaSitemap(robots)).toBe(true);
    expect(robotsDisallowsPrivateTrees(robots)).toBe(true);
  });

  it("normalizes SEO_BASE_URL", () => {
    expect(normalizeSeoBaseUrl("https://padeya.com/")).toBe(
      "https://padeya.com",
    );
    expect(normalizeSeoBaseUrl("padeya.com")).toBe("https://padeya.com");
  });
});

describe("environment indexing policy (regression)", () => {
  it("production signals index; preview/staging do not", () => {
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
        vercelEnv: "preview",
        nodeEnv: "production",
      }),
    ).toBe(false);
  });
});

describe("merch product vs hub path classification", () => {
  it("does not treat hubs as Product detail paths", () => {
    expect(isMerchProductPath("/merch")).toBe(false);
    expect(isMerchProductPath("/merch/drops")).toBe(false);
    expect(isMerchProductPath("/merch/vault")).toBe(false);
    expect(isMerchProductPath("/merch/hosts")).toBe(false);
    expect(isMerchProductPath("/merch/hosts/dj-ade")).toBe(false);
    expect(isMerchProductPath("/merch-guide")).toBe(false);
    expect(isMerchHubPath("/merch/drops")).toBe(true);
    expect(isMerchHubPath("/merch")).toBe(true);
    for (const seg of RESERVED_MERCH_PATH_SEGMENTS) {
      expect(isMerchProductPath(`/merch/${seg}`)).toBe(false);
    }
  });

  it("classifies real product slugs correctly", () => {
    expect(isMerchProductPath("/merch/legacy-tee")).toBe(true);
    expect(isMerchProductPath("/merch/night-market-hoodie")).toBe(true);
    expect(isMerchProductPath("https://padeya.com/merch/legacy-tee")).toBe(
      true,
    );
  });

  it("picks product URLs from sitemap and skips hubs", () => {
    const urls = [
      "https://padeya.com/merch",
      "https://padeya.com/merch/drops",
      "https://padeya.com/merch/vault",
      "https://padeya.com/merch/legacy-tee",
    ];
    expect(pickMerchProductUrl(urls)).toBe(
      "https://padeya.com/merch/legacy-tee",
    );
    expect(pickMerchProductUrl(urls.slice(0, 3))).toBeNull();
  });

  it("non-strict skips cleanly when no product inventory; strict fails clearly", () => {
    const skip = decideMerchProductSample(null, false);
    expect(skip.action).toBe("skip");
    expect(skip.message).toMatch(/No public indexable merch product available/);

    const fail = decideMerchProductSample(null, true);
    expect(fail.action).toBe("fail");
    expect(fail.message).toBe("No public indexable merch Product URL found");
    expect(fail.message).not.toMatch(/drops/);

    const check = decideMerchProductSample(
      "https://padeya.com/merch/legacy-tee",
      true,
    );
    expect(check).toEqual({
      action: "check",
      url: "https://padeya.com/merch/legacy-tee",
    });
  });

  it("requires Product JSON-LD on a real product HTML sample", () => {
    const html = `
      <script type="application/ld+json">
        {"@type":"Product","name":"Legacy Tee","offers":{"@type":"Offer"}}
      </script>`;
    const blocks = extractJsonLdBlocks(html);
    expect(jsonLdContainsType(blocks, "Product")).toBe(true);
    expect(jsonLdContainsType(blocks, "Offer")).toBe(true);
  });
});
