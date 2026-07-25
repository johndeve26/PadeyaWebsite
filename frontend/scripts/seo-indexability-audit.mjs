/**
 * Safe production indexability matrix audit.
 *
 * Usage:
 *   SEO_BASE_URL=https://padeya.com npm run seo:indexability-audit
 *
 * GET only. Samples hubs + sitemap categories. Does not crawl thousands of URLs.
 */

const LIVE_SITE_ORIGIN = "https://padeya.com";
const BASE = (process.env.SEO_BASE_URL || LIVE_SITE_ORIGIN).trim().replace(/\/$/, "");
const TIMEOUT_MS = Number(process.env.SEO_SMOKE_TIMEOUT_MS || 20000);
const MAX_REDIRECTS = 4;

const STATIC_PUBLIC = [
  "/",
  "/events",
  "/events/today",
  "/events/this-weekend",
  "/events/free",
  "/events/vip",
  "/events/online",
  "/events/in-person",
  "/events/hybrid",
  "/hosts",
  "/fans",
  "/sponsorships",
  "/sponsorships/hosts",
  "/merch",
  "/merch/drops",
  "/merch-guide",
  "/blog",
  "/help",
  "/about",
  "/contact",
  "/pricing",
  "/for-fans",
  "/for-hosts",
  "/faq",
  "/ambassadors",
  "/ambassadors/events",
  "/ambassadors/how-it-works",
  "/support",
  "/privacy",
  "/terms",
  "/cookies",
  "/refund-policy",
  "/ticket-policy",
  "/community-guidelines",
  "/safety",
  "/accessibility",
  "/report",
];

const INTENTIONAL_NOINDEX = [
  "/events/search",
  "/login",
  "/register",
  "/dashboard",
  "/host",
  "/sponsor",
];

function fail(msg) {
  console.error(`seo-indexability-audit FAIL: ${msg}`);
  process.exitCode = 1;
}

async function fetchFollow(url) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    let current = url;
    let redirects = 0;
    for (;;) {
      const res = await fetch(current, {
        redirect: "manual",
        signal: ac.signal,
        headers: {
          "user-agent": "PadeyaSEOIndexabilityAudit/1.0",
          accept: "text/html,application/xhtml+xml,*/*",
        },
      });
      if ([301, 302, 303, 307, 308].includes(res.status)) {
        redirects += 1;
        if (redirects > MAX_REDIRECTS) {
          return { ok: false, status: res.status, html: null, headers: res.headers, finalUrl: current };
        }
        const loc = res.headers.get("location");
        if (!loc) {
          return { ok: false, status: res.status, html: null, headers: res.headers, finalUrl: current };
        }
        current = new URL(loc, current).toString();
        continue;
      }
      const html = await res.text();
      return { ok: true, status: res.status, html, headers: res.headers, finalUrl: current };
    }
  } catch (e) {
    return { ok: false, status: 0, html: null, headers: new Headers(), finalUrl: url, error: e?.message || String(e) };
  } finally {
    clearTimeout(t);
  }
}

function extractMeta(html, name) {
  if (!html) return null;
  const esc = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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

function extractCanonical(html) {
  if (!html) return null;
  const m =
    html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i) ||
    html.match(/<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i);
  return m?.[1] || null;
}

function hasNoindex(robots, googlebot, xrobots) {
  return [robots, googlebot, xrobots].some((v) => v && /\b(noindex|none)\b/i.test(v));
}

function isRobotsBlocked(robotsTxt, pathname) {
  const lines = robotsTxt.split(/\r?\n/);
  let inStar = false;
  const disallows = [];
  const allows = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const ua = line.match(/^user-agent:\s*(.+)$/i);
    if (ua) {
      inStar = ua[1].trim() === "*";
      continue;
    }
    if (!inStar) continue;
    const d = line.match(/^disallow:\s*(.*)$/i);
    if (d) {
      disallows.push(d[1].trim());
      continue;
    }
    const a = line.match(/^allow:\s*(.*)$/i);
    if (a) allows.push(a[1].trim());
  }
  const matches = (pattern) => {
    if (!pattern) return false;
    if (pattern.includes("*")) {
      const escaped = pattern
        .replace(/[.+?^${}()|[\]\\]/g, "\\$&")
        .replace(/\*/g, "[^/]+");
      return new RegExp(`^${escaped}`).test(pathname);
    }
    if (pathname === pattern) return true;
    if (pathname.startsWith(pattern)) return true;
    if (pattern.endsWith("/") && pathname === pattern.slice(0, -1)) return true;
    return false;
  };
  let blocked = false;
  let best = -1;
  for (const d of disallows) {
    if (matches(d) && d.length >= best) {
      blocked = true;
      best = d.length;
    }
  }
  for (const a of allows) {
    if (matches(a) && a.length >= best) {
      blocked = false;
      best = a.length;
    }
  }
  return blocked;
}

function parseSitemapLocs(xml) {
  const locs = [];
  const re = /<loc>\s*([^<]+)\s*<\/loc>/gi;
  let m;
  while ((m = re.exec(xml))) locs.push(m[1].trim());
  return locs;
}

function classifySitemap(url) {
  let p;
  try {
    p = new URL(url).pathname;
  } catch {
    return null;
  }
  if (/^\/events\/[^/]+$/.test(p) && !p.startsWith("/events/c/") && !["/events/search", "/events/location", "/events/today", "/events/free", "/events/vip", "/events/this-weekend", "/events/online", "/events/in-person", "/events/hybrid", "/events/near-me", "/events/map", "/events/calendar"].includes(p)) {
    return "events";
  }
  if (/^\/u\/[^/]+$/.test(p)) return "hosts";
  if (/^\/f\/[^/]+$/.test(p)) return "fans";
  if (/^\/sponsors\/[^/]+$/.test(p)) return "sponsors";
  if (/^\/merch\/[^/]+$/.test(p) && !["drops", "vault", "hosts"].includes(p.split("/")[2])) return "merch";
  if (/^\/blog\/[^/]+$/.test(p) && !p.startsWith("/blog/category")) return "blog";
  if (/^\/help\/articles\/[^/]+$/.test(p)) return "help";
  if (/^\/events\/(city|state|country|area|c)\//.test(p)) return "hubs";
  return null;
}

const rows = [];

function printRow(row) {
  rows.push(row);
  const result = row.result.padEnd(28);
  console.log(
    `${row.path.padEnd(42)} ${String(row.status).padEnd(4)} ${(row.canonical || "—").replace(BASE, "").slice(0, 36).padEnd(36)} ${(row.meta_robots || "—").padEnd(18)} ${(row.googlebot || "—").padEnd(12)} ${(row.x_robots_tag || "—").padEnd(18)} ${(row.robots_allowed ? "yes" : "no").padEnd(4)} ${(row.sitemap ? "yes" : "no").padEnd(4)} ${result}`,
  );
}

console.log(`seo-indexability-audit: base=${BASE}`);
console.log(
  `${"URL".padEnd(42)} ${"st".padEnd(4)} ${"canonical".padEnd(36)} ${"meta_robots".padEnd(18)} ${"googlebot".padEnd(12)} ${"x_robots_tag".padEnd(18)} ${"ok?".padEnd(4)} ${"sm".padEnd(4)} result`,
);

const robotsRes = await fetchFollow(`${BASE}/robots.txt`);
const robotsTxt = robotsRes.html || "";
const sitemapRes = await fetchFollow(`${BASE}/sitemap.xml`);
const sitemapUrls = sitemapRes.html ? parseSitemapLocs(sitemapRes.html) : [];
const sitemapSet = new Set(sitemapUrls.map((u) => {
  try {
    return new URL(u).pathname.replace(/\/$/, "") || "/";
  } catch {
    return u;
  }
}));

async function auditPath(path, { expectNoindex = false, inSitemap = null } = {}) {
  const url = `${BASE}${path}`;
  const r = await fetchFollow(url);
  const robots = extractMeta(r.html, "robots");
  const googlebot = extractMeta(r.html, "googlebot");
  const xrobots = r.headers?.get?.("x-robots-tag") || null;
  const canonical = extractCanonical(r.html);
  const blocked = isRobotsBlocked(robotsTxt, path);
  const noindex = hasNoindex(robots, googlebot, xrobots);
  const sm = sitemapSet.has(path === "/" ? "/" : path.replace(/\/$/, ""));
  let result = "PASS";
  if (!r.ok || r.status !== 200) {
    result = expectNoindex ? `PASS (status ${r.status})` : "FAIL status";
    if (!expectNoindex) fail(`${path}: status ${r.status}`);
  } else if (expectNoindex) {
    if (!noindex && r.status === 200) {
      result = "WARN missing noindex";
      console.warn(`  ⚠ ${path}: expected intentional noindex`);
    } else {
      result = "PASS (intentional noindex)";
    }
  } else if (noindex) {
    result = "FAIL accidental noindex";
    fail(`${path}: accidental noindex`);
  } else if (blocked) {
    result = "FAIL robots blocked";
    fail(`${path}: robots.txt blocked`);
  } else if (canonical && !canonical.includes("padeya.com")) {
    result = "FAIL bad canonical host";
    fail(`${path}: bad canonical ${canonical}`);
  } else if (canonical && /[?&](utm_|ref=|gclid|fbclid)/i.test(canonical)) {
    result = "FAIL tracking canonical";
    fail(`${path}: tracking params in canonical`);
  }

  printRow({
    path,
    status: r.status || 0,
    canonical: canonical || "—",
    meta_robots: robots || "—",
    googlebot: googlebot || "—",
    x_robots_tag: xrobots || "—",
    robots_allowed: !blocked,
    sitemap: inSitemap == null ? sm : inSitemap,
    result,
  });
}

for (const path of STATIC_PUBLIC) {
  await auditPath(path, { expectNoindex: false });
}
for (const path of INTENTIONAL_NOINDEX) {
  await auditPath(path, { expectNoindex: true, inSitemap: false });
}

// Facet sample
{
  const path = "/events?q=lagos";
  const r = await fetchFollow(`${BASE}${path}`);
  const robots = extractMeta(r.html, "robots");
  const noindex = hasNoindex(robots, extractMeta(r.html, "googlebot"), r.headers.get("x-robots-tag"));
  const canonical = extractCanonical(r.html);
  let result = "PASS (intentional noindex)";
  if (!noindex) {
    result = "FAIL expected facet noindex";
    fail("faceted /events?q= missing noindex");
  } else if (canonical !== `${BASE}/events` && canonical !== "https://padeya.com/events") {
    result = "FAIL facet canonical";
    fail(`facet canonical ${canonical}`);
  }
  printRow({
    path,
    status: r.status,
    canonical: canonical || "—",
    meta_robots: robots || "—",
    googlebot: extractMeta(r.html, "googlebot") || "—",
    x_robots_tag: r.headers.get("x-robots-tag") || "—",
    robots_allowed: true,
    sitemap: false,
    result,
  });
}

const caps = { events: 5, hosts: 5, fans: 5, sponsors: 5, merch: 5, blog: 5, help: 5, hubs: 10 };
const buckets = Object.fromEntries(Object.keys(caps).map((k) => [k, []]));
for (const u of sitemapUrls) {
  const c = classifySitemap(u);
  if (c && buckets[c].length < caps[c]) buckets[c].push(u);
}

for (const [cat, urls] of Object.entries(buckets)) {
  for (const u of urls) {
    const path = new URL(u).pathname;
    await auditPath(path, { expectNoindex: false, inSitemap: true });
  }
  if (!urls.length) {
    console.warn(`  ⚠ no sitemap samples for ${cat}`);
  }
}

if (process.exitCode && process.exitCode !== 0) {
  console.error("seo-indexability-audit: FAILED");
  process.exit(process.exitCode);
}
console.log(`seo-indexability-audit: ok (${rows.length} rows)`);
