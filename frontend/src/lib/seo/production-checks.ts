/**
 * Pure helpers for production SEO smoke checks (Phase 1C).
 * Used by vitest and mirrored by scripts/seo-production-smoke.mjs.
 */

import { LIVE_SITE_HOST, LIVE_SITE_ORIGIN } from "@/lib/seo/env-policy";

const FORBIDDEN_HOST_SNIPPETS = [
  "localhost",
  "127.0.0.1",
  ".vercel.app",
  ".onrender.com",
  "smartlancedesigns.com",
  "trycloudflare.com",
  "ngrok",
];

export function isForbiddenLiveHost(hostname: string): boolean {
  const h = hostname.trim().toLowerCase();
  if (!h) return true;
  if (h === LIVE_SITE_HOST || h === `www.${LIVE_SITE_HOST}`) return false;
  return FORBIDDEN_HOST_SNIPPETS.some((s) => h.includes(s));
}

export function assertPadeyaAbsoluteUrl(url: string): {
  ok: boolean;
  reason?: string;
} {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return { ok: false, reason: "invalid_url" };
  }
  if (parsed.protocol !== "https:") {
    return { ok: false, reason: "not_https" };
  }
  if (isForbiddenLiveHost(parsed.hostname)) {
    return { ok: false, reason: "forbidden_host" };
  }
  if (
    parsed.hostname !== LIVE_SITE_HOST &&
    parsed.hostname !== `www.${LIVE_SITE_HOST}`
  ) {
    // Allow only padeya.com for sitemap/canonical production checks.
    return { ok: false, reason: "not_padeya_com" };
  }
  if (parsed.search && !isAllowedCanonicalQuery(parsed.pathname, parsed.search)) {
    return { ok: false, reason: "query_on_canonical" };
  }
  return { ok: true };
}

/** Canonicals should be path-only except rare intentional cases (none today). */
function isAllowedCanonicalQuery(_pathname: string, search: string): boolean {
  return !search || search === "";
}

export function extractCanonicalHref(html: string): string | null {
  const m =
    html.match(
      /<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i,
    ) ||
    html.match(
      /<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i,
    );
  return m?.[1] || null;
}

export function extractMetaContent(
  html: string,
  nameOrProperty: string,
): string | null {
  const esc = nameOrProperty.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(
    `<meta[^>]+(?:name|property)=["']${esc}["'][^>]+content=["']([^"']*)["']`,
    "i",
  );
  const re2 = new RegExp(
    `<meta[^>]+content=["']([^"']*)["'][^>]+(?:name|property)=["']${esc}["']`,
    "i",
  );
  return html.match(re)?.[1] ?? html.match(re2)?.[1] ?? null;
}

export function extractTitle(html: string): string | null {
  const m = html.match(/<title[^>]*>([^<]*)<\/title>/i);
  return m?.[1]?.trim() || null;
}

export function extractJsonLdBlocks(html: string): unknown[] {
  const blocks: unknown[] = [];
  const re =
    /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(html))) {
    const raw = match[1]?.trim();
    if (!raw) continue;
    try {
      blocks.push(JSON.parse(raw));
    } catch {
      blocks.push({ __parse_error: true, raw: raw.slice(0, 80) });
    }
  }
  return blocks;
}

export function jsonLdContainsType(
  blocks: unknown[],
  typeName: string,
): boolean {
  const want = typeName.toLowerCase();
  const walk = (node: unknown): boolean => {
    if (!node || typeof node !== "object") return false;
    if (Array.isArray(node)) return node.some(walk);
    const obj = node as Record<string, unknown>;
    const t = obj["@type"];
    if (typeof t === "string" && t.toLowerCase() === want) return true;
    if (Array.isArray(t) && t.some((x) => String(x).toLowerCase() === want)) {
      return true;
    }
    if (obj["@graph"] && walk(obj["@graph"])) return true;
    return Object.values(obj).some(walk);
  };
  return blocks.some(walk);
}

export function isNoindexRobotsContent(content: string | null): boolean {
  if (!content) return false;
  return /\bnoindex\b/i.test(content);
}

export function sitemapUrlsLookSafe(urls: string[]): {
  ok: boolean;
  bad: string[];
} {
  const bad: string[] = [];
  for (const u of urls) {
    const check = assertPadeyaAbsoluteUrl(u.split("#")[0] || u);
    if (!check.ok) bad.push(u);
    try {
      const path = new URL(u).pathname.toLowerCase();
      if (
        path.startsWith("/admin") ||
        path.startsWith("/dashboard") ||
        path.startsWith("/host/") ||
        path.startsWith("/sponsor/") ||
        path.startsWith("/connect") ||
        path.startsWith("/messages") ||
        path.includes("/checkout") ||
        path === "/events/search" ||
        path.startsWith("/login") ||
        path.startsWith("/register")
      ) {
        bad.push(u);
      }
      if (u.includes("?")) bad.push(u);
    } catch {
      bad.push(u);
    }
  }
  return { ok: bad.length === 0, bad: [...new Set(bad)].slice(0, 20) };
}

export function parseSitemapLocs(xml: string): string[] {
  const locs: string[] = [];
  const re = /<loc>\s*([^<]+)\s*<\/loc>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml))) {
    const u = m[1]?.trim();
    if (u) locs.push(u);
  }
  return locs;
}

export function robotsAdvertisesPadeyaSitemap(robotsTxt: string): boolean {
  return /sitemap:\s*https:\/\/padeya\.com\/sitemap\.xml/i.test(robotsTxt);
}

export function robotsDisallowsPrivateTrees(robotsTxt: string): boolean {
  const need = ["/admin/", "/dashboard/", "/host/", "/sponsor/", "/login"];
  return need.every((p) => robotsTxt.includes(`Disallow: ${p}`) || robotsTxt.includes(`Disallow: ${p.replace(/\/$/, "")}`));
}

export function normalizeSeoBaseUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/$/, "");
  if (!trimmed) return LIVE_SITE_ORIGIN;
  try {
    const u = new URL(trimmed.includes("://") ? trimmed : `https://${trimmed}`);
    return `${u.protocol}//${u.host}`;
  } catch {
    return LIVE_SITE_ORIGIN;
  }
}

export { LIVE_SITE_ORIGIN, LIVE_SITE_HOST };
