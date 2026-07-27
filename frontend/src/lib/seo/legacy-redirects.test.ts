import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

import { LIVE_SITE_ORIGIN } from "./env-policy";
import {
  buildAppRedirects,
  CANONICAL_AUTH_PATHS,
  LEGACY_NO_REDIRECT_PATHS,
  PRODUCT_PATH_REDIRECTS,
  WORDPRESS_LEGACY_REDIRECTS,
  wordpressLegacyExactSources,
  WWW_HOST,
  wwwToApexRedirects,
} from "./legacy-redirects";

const root = path.join(__dirname, "../../..");

describe("legacy + domain redirects", () => {
  it("www→apex destinations use LIVE_SITE_ORIGIN and preserve :path*", () => {
    const rules = wwwToApexRedirects();
    expect(rules.length).toBeGreaterThanOrEqual(2);
    for (const rule of rules) {
      expect(rule.has?.[0]?.value).toBe(WWW_HOST);
      expect(rule.destination.startsWith(LIVE_SITE_ORIGIN)).toBe(true);
      expect(rule.permanent).toBe(true);
      expect(rule.destination).not.toContain("www.padeya.com");
      expect(rule.destination).not.toContain("smartlancedesigns");
    }
    expect(rules.some((r) => r.source === "/:path*")).toBe(true);
    expect(rules.some((r) => r.source === "/")).toBe(true);
  });

  it("maps WordPress membership URLs to current auth routes", () => {
    const bySource = Object.fromEntries(
      WORDPRESS_LEGACY_REDIRECTS.map((r) => [r.source, r]),
    );
    expect(bySource["/member-register"]?.destination).toBe("/register");
    expect(bySource["/member-login"]?.destination).toBe("/login");
    for (const r of WORDPRESS_LEGACY_REDIRECTS) {
      expect(r.permanent).toBe(true);
      expect(r.destination).not.toBe("/");
    }
  });

  it("does not redirect known removed WP paths to homepage", () => {
    const destBySource = new Map(
      [...WORDPRESS_LEGACY_REDIRECTS, ...PRODUCT_PATH_REDIRECTS].map((r) => [
        r.source,
        r.destination,
      ]),
    );
    for (const p of LEGACY_NO_REDIRECT_PATHS) {
      expect(destBySource.has(p)).toBe(false);
    }
  });

  it("buildAppRedirects includes www, product, and WordPress maps once", () => {
    const all = buildAppRedirects();
    const sources = all.map((r) => r.source);
    expect(sources).toContain("/member-register");
    expect(sources).toContain("/member-login");
    expect(sources).toContain("/sponsors");
    expect(sources.filter((s) => s === "/member-register").length).toBe(1);
    expect(all.every((r) => r.permanent === true)).toBe(true);
  });

  it("next.config uses buildAppRedirects (single authoritative map)", () => {
    const cfg = fs.readFileSync(path.join(root, "next.config.ts"), "utf8");
    expect(cfg).toMatch(/buildAppRedirects/);
    expect(cfg).toMatch(/legacy-redirects/);
    expect(cfg).toMatch(/Do NOT add a catch-all 404/);
    // No catch-all homepage redirect rule (destination "/" with wildcard source)
    expect(cfg).not.toMatch(
      /source:\s*["']\/:path\*["'][\s\S]{0,80}destination:\s*["']\/["']/,
    );
  });

  it("legacy auth sources are not sitemap/canonical auth destinations", () => {
    const exact = wordpressLegacyExactSources();
    expect(exact).toContain("/member-register");
    expect(exact).toContain("/member-login");
    for (const auth of CANONICAL_AUTH_PATHS) {
      expect(exact).not.toContain(auth);
    }

    const sitemap = fs.readFileSync(path.join(root, "src/app/sitemap.ts"), "utf8");
    expect(sitemap).not.toMatch(/member-register|member-login/);
    // /register and /login are auth — must not be static sitemap entries
    expect(sitemap).not.toMatch(/path:\s*["']\/register["']/);
    expect(sitemap).not.toMatch(/path:\s*["']\/login["']/);
  });

  it("not-found stays HTTP 404 (no homepage redirect)", () => {
    const page = fs.readFileSync(path.join(root, "src/app/not-found.tsx"), "utf8");
    expect(page).toMatch(/index:\s*false/);
    expect(page).not.toMatch(/redirect\(|permanentRedirect\(/);
    expect(page).not.toMatch(/alternates:\s*\{\s*canonical/);
  });
});
