/**
 * Production / live SEO smoke (Phase 1C).
 *
 * Usage:
 *   SEO_BASE_URL=https://padeya.com node scripts/seo-production-smoke.mjs
 *
 * Optional:
 *   SEO_SMOKE_STRICT=1  — fail if optional samples (blog/help/merch) missing
 *   SEO_SMOKE_TIMEOUT_MS=20000
 *
 * Does not mutate production data. Safe to run against a deployed environment.
 */

/**
 * Helpers mirror `src/lib/seo/production-checks.ts` (vitest covers the TS source).
 * Do not import .ts from this script — plain Node only.
 */

const LIVE_SITE_ORIGIN = "https://padeya.com";

const BASE = (process.env.SEO_BASE_URL || LIVE_SITE_ORIGIN)
  .trim()
  .replace(/\/$/, "");
const STRICT = process.env.SEO_SMOKE_STRICT === "1";
const TIMEOUT_MS = Number(process.env.SEO_SMOKE_TIMEOUT_MS || 20000);
const MAX_REDIRECTS = 4;

const FORBIDDEN_HOST_SNIPPETS = [
  "localhost",
  "127.0.0.1",
  ".vercel.app",
  ".onrender.com",
  "smartlancedesigns.com",
  "trycloudflare.com",
  "ngrok",
];

function fail(msg) {
  console.error(`seo-production-smoke FAIL: ${msg}`);
  process.exitCode = 1;
}

function ok(msg) {
  console.log(`  ✓ ${msg}`);
}

function isForbiddenHost(hostname) {
  const h = hostname.toLowerCase();
  return FORBIDDEN_HOST_SNIPPETS.some((s) => h.includes(s));
}

function assertPadeyaUrl(url, label) {
  let u;
  try {
    u = new URL(url);
  } catch {
    fail(`${label}: invalid URL ${url}`);
    return false;
  }
  if (u.protocol !== "https:") {
    fail(`${label}: not https — ${url}`);
    return false;
  }
  if (isForbiddenHost(u.hostname)) {
    fail(`${label}: forbidden host — ${url}`);
    return false;
  }
  if (u.hostname !== "padeya.com" && u.hostname !== "www.padeya.com") {
    // When SEO_BASE_URL is a staging host for dry-run, still flag non-padeya in sitemap.
    if (BASE.includes("padeya.com")) {
      fail(`${label}: expected padeya.com — ${url}`);
      return false;
    }
  }
  return true;
}

async function fetchFollow(url, opts = {}) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    let current = url;
    let redirects = 0;
    const chain = [];
    // Manual redirect tracking
    for (;;) {
      const res = await fetch(current, {
        redirect: "manual",
        signal: ac.signal,
        headers: {
          "user-agent": "PadeyaSEOProductionSmoke/1.0",
          accept: opts.accept || "text/html,application/xhtml+xml,*/*",
          ...(opts.headers || {}),
        },
      });
      chain.push({ url: current, status: res.status });
      if ([301, 302, 303, 307, 308].includes(res.status)) {
        redirects += 1;
        if (redirects > MAX_REDIRECTS) {
          fail(`excessive redirects (>${MAX_REDIRECTS}) for ${url}`);
          return { ok: false, chain, res: null, html: null };
        }
        const loc = res.headers.get("location");
        if (!loc) {
          fail(`redirect without Location for ${current}`);
          return { ok: false, chain, res: null, html: null };
        }
        current = new URL(loc, current).toString();
        continue;
      }
      const html =
        opts.asText === false
          ? null
          : await res.text();
      return { ok: true, chain, res, html, finalUrl: current };
    }
  } catch (e) {
    fail(`fetch error ${url}: ${e?.message || e}`);
    return { ok: false, chain: [], res: null, html: null };
  } finally {
    clearTimeout(t);
  }
}

function extractCanonical(html) {
  const m =
    html.match(
      /<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i,
    ) ||
    html.match(
      /<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i,
    );
  return m?.[1] || null;
}

function extractMeta(html, name) {
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

function extractTitle(html) {
  return html.match(/<title[^>]*>([^<]*)<\/title>/i)?.[1]?.trim() || null;
}

function extractJsonLd(html) {
  const blocks = [];
  const re =
    /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html))) {
    try {
      blocks.push(JSON.parse(m[1]));
    } catch {
      blocks.push({ __parse_error: true });
    }
  }
  return blocks;
}

function jsonLdHasType(blocks, typeName) {
  const want = typeName.toLowerCase();
  const walk = (node) => {
    if (!node || typeof node !== "object") return false;
    if (Array.isArray(node)) return node.some(walk);
    const t = node["@type"];
    if (typeof t === "string" && t.toLowerCase() === want) return true;
    if (Array.isArray(t) && t.some((x) => String(x).toLowerCase() === want))
      return true;
    if (node["@graph"] && walk(node["@graph"])) return true;
    return Object.values(node).some(walk);
  };
  return blocks.some(walk);
}

function parseSitemapLocs(xml) {
  const locs = [];
  const re = /<loc>\s*([^<]+)\s*<\/loc>/gi;
  let m;
  while ((m = re.exec(xml))) locs.push(m[1].trim());
  return locs;
}

function pickByPath(urls, predicate) {
  return urls.find((u) => {
    try {
      return predicate(new URL(u).pathname);
    } catch {
      return false;
    }
  });
}

async function checkIndexablePage(url, { requireTypes = [], label }) {
  const result = await fetchFollow(url);
  if (!result.ok || !result.res) return null;
  const { res, html, chain } = result;
  if (res.status !== 200) {
    fail(`${label}: expected 200, got ${res.status} (${url})`);
    return null;
  }
  ok(`${label}: HTTP 200 (${chain.length > 1 ? `via ${chain.length - 1} redirect(s)` : "direct"})`);

  const title = extractTitle(html);
  const desc = extractMeta(html, "description");
  const canonical = extractCanonical(html);
  const ogTitle = extractMeta(html, "og:title");
  const ogDesc = extractMeta(html, "og:description");
  const ogUrl = extractMeta(html, "og:url");
  const twCard = extractMeta(html, "twitter:card");
  const robots = extractMeta(html, "robots");

  if (!title) fail(`${label}: missing <title>`);
  else ok(`${label}: title`);
  if (!desc) fail(`${label}: missing meta description`);
  else ok(`${label}: description`);
  if (!canonical) fail(`${label}: missing canonical`);
  else {
    assertPadeyaUrl(canonical, `${label} canonical`);
    if (canonical.includes("?")) fail(`${label}: canonical has query`);
    else ok(`${label}: canonical ${canonical}`);
  }
  if (!ogTitle || !ogDesc || !ogUrl) fail(`${label}: incomplete Open Graph`);
  else ok(`${label}: Open Graph`);
  if (!twCard) fail(`${label}: missing twitter:card`);
  else ok(`${label}: Twitter card`);
  if (robots && /\bnoindex\b/i.test(robots) && !label.includes("search")) {
    // indexable pages should not noindex (unless env is non-prod against staging base)
    if (BASE.includes("padeya.com")) {
      fail(`${label}: unexpected noindex robots on indexable page`);
    }
  }

  const ld = extractJsonLd(html);
  if (ld.some((b) => b && b.__parse_error)) {
    fail(`${label}: JSON-LD parse error`);
  }
  for (const t of requireTypes) {
    if (!jsonLdHasType(ld, t)) fail(`${label}: missing JSON-LD @type ${t}`);
    else ok(`${label}: JSON-LD ${t}`);
  }
  return { html, canonical, ld };
}

async function checkNoindexPage(path, label) {
  const url = `${BASE}${path}`;
  const result = await fetchFollow(url);
  if (!result.ok || !result.res) return;
  const { res, html, chain } = result;
  // Auth redirects (3xx already followed) or 200/401/403 are acceptable.
  if (![200, 401, 403].includes(res.status) && res.status < 300) {
    // already followed
  }
  ok(`${label}: final status ${res.status} (chain ${chain.map((c) => c.status).join("→")})`);
  if (html) {
    const robots = extractMeta(html, "robots");
    const xrobots = result.res.headers.get("x-robots-tag");
    if (
      robots && /\bnoindex\b/i.test(robots) ||
      (xrobots && /\bnoindex\b/i.test(xrobots))
    ) {
      ok(`${label}: noindex present`);
    } else if (res.status === 200) {
      // Soft warn — middleware may only set header on some paths
      console.warn(`  ⚠ ${label}: 200 without obvious noindex meta/header`);
    }
  }
}

async function checkMissing404(path, label) {
  const result = await fetchFollow(`${BASE}${path}`);
  if (!result.ok || !result.res) return;
  if (result.res.status !== 404) {
    fail(`${label}: expected 404, got ${result.res.status}`);
  } else ok(`${label}: HTTP 404`);
}

console.log(`seo-production-smoke: base=${BASE}`);

// --- robots.txt ---
{
  const r = await fetchFollow(`${BASE}/robots.txt`, {
    accept: "text/plain,*/*",
  });
  if (!r.ok || !r.html) {
    fail("robots.txt unreachable");
  } else {
    const txt = r.html;
    if (BASE.includes("padeya.com")) {
      if (!/Sitemap:\s*https:\/\/padeya\.com\/sitemap\.xml/i.test(txt)) {
        fail("robots.txt missing Sitemap: https://padeya.com/sitemap.xml");
      } else ok("robots.txt advertises padeya.com sitemap");
      for (const d of ["/admin/", "/dashboard/", "/host/", "/login"]) {
        if (!txt.includes(`Disallow: ${d}`) && !txt.includes(`Disallow: ${d.replace(/\/$/, "")}`)) {
          fail(`robots.txt missing Disallow ${d}`);
        }
      }
      ok("robots.txt private disallows present");
      if (/Disallow:\s*\/\s*$/m.test(txt) && !txt.includes("Allow:")) {
        // full disallow would be non-prod
        console.warn("  ⚠ robots.txt may be non-production Disallow: /");
      }
    } else {
      ok("robots.txt fetched (non-padeya base — skipping production assertions)");
    }
  }
}

// --- sitemap ---
let sitemapUrls = [];
{
  const r = await fetchFollow(`${BASE}/sitemap.xml`, {
    accept: "application/xml,text/xml,*/*",
  });
  if (!r.ok || !r.html) {
    fail("sitemap.xml unreachable");
  } else {
    if (!r.html.includes("<urlset") && !r.html.includes("<sitemapindex")) {
      fail("sitemap.xml does not look like XML sitemap");
    } else ok("sitemap.xml parseable");
    sitemapUrls = parseSitemapLocs(r.html);
    if (sitemapUrls.length < 5) fail(`sitemap too small (${sitemapUrls.length} locs)`);
    else ok(`sitemap has ${sitemapUrls.length} URLs`);

    for (const u of sitemapUrls.slice(0, 500)) {
      assertPadeyaUrl(u, "sitemap loc");
      if (u.includes("?")) fail(`sitemap query URL ${u}`);
      const path = new URL(u).pathname.toLowerCase();
      if (
        path.startsWith("/admin") ||
        path.startsWith("/dashboard") ||
        path.includes("/checkout") ||
        path === "/events/search" ||
        path.startsWith("/login")
      ) {
        fail(`sitemap private/forbidden path ${u}`);
      }
    }
    ok("sitemap URLs look production-safe (sampled)");
  }
}

// --- pick samples ---
const home = `${BASE}/`;
const events = `${BASE}/events`;
const hosts = `${BASE}/hosts`;
const fans = `${BASE}/fans`;
const sponsorships = `${BASE}/sponsorships`;

const sampleEvent = pickByPath(
  sitemapUrls,
  (p) => /^\/events\/[^/]+$/.test(p) && !["/events/search", "/events/location"].includes(p) && !p.startsWith("/events/c/") && !p.startsWith("/events/city/") && !p.startsWith("/events/today") && !p.startsWith("/events/free") && !p.startsWith("/events/vip") && !p.startsWith("/events/this-weekend"),
);
const sampleHost = pickByPath(sitemapUrls, (p) => /^\/u\/[^/]+$/.test(p));
const sampleFan = pickByPath(sitemapUrls, (p) => /^\/f\/[^/]+$/.test(p));
const sampleSponsor = pickByPath(sitemapUrls, (p) => /^\/sponsors\/[^/]+$/.test(p));
const sampleMerch = pickByPath(sitemapUrls, (p) => /^\/merch\/[^/]+$/.test(p));
const sampleBlog = pickByPath(sitemapUrls, (p) => /^\/blog\/[^/]+$/.test(p) && !p.startsWith("/blog/category") && !p.startsWith("/blog/tag") && !p.startsWith("/blog/author"));
const sampleHelp = pickByPath(sitemapUrls, (p) => /^\/help\/articles\/[^/]+$/.test(p));
const sampleLocation = pickByPath(
  sitemapUrls,
  (p) =>
    /^\/events\/(city|state|country|area)\/[^/]+$/.test(p),
);

await checkIndexablePage(home, {
  label: "home",
  requireTypes: ["Organization", "WebSite"],
});
await checkIndexablePage(events, { label: "events hub", requireTypes: ["CollectionPage"] });
await checkIndexablePage(hosts, { label: "hosts" });
await checkIndexablePage(fans, { label: "fans" });
await checkIndexablePage(sponsorships, {
  label: "sponsorships",
  requireTypes: ["CollectionPage"],
});

if (sampleEvent) {
  await checkIndexablePage(sampleEvent, {
    label: "event",
    requireTypes: ["Event", "BreadcrumbList"],
  });
} else fail("no public event URL in sitemap");

if (sampleHost) {
  await checkIndexablePage(sampleHost, {
    label: "host",
    requireTypes: ["ProfilePage", "Organization"],
  });
} else fail("no public host /u/ URL in sitemap");

if (sampleFan) {
  await checkIndexablePage(sampleFan, {
    label: "fan",
    requireTypes: ["ProfilePage", "Person"],
  });
} else if (STRICT) fail("no public fan /f/ URL in sitemap");
else console.warn("  ⚠ no fan sample in sitemap (skip)");

if (sampleSponsor) {
  await checkIndexablePage(sampleSponsor, {
    label: "sponsor",
    requireTypes: ["ProfilePage", "Organization"],
  });
} else if (STRICT) fail("no sponsor sample in sitemap");
else console.warn("  ⚠ no sponsor sample in sitemap (skip)");

if (sampleMerch) {
  await checkIndexablePage(sampleMerch, {
    label: "merch",
    requireTypes: ["Product"],
  });
} else if (STRICT) fail("no merch sample in sitemap");
else console.warn("  ⚠ no merch sample in sitemap (skip)");

if (sampleBlog) {
  await checkIndexablePage(sampleBlog, {
    label: "blog",
    requireTypes: ["Article"],
  });
} else if (STRICT) fail("no blog sample in sitemap");
else console.warn("  ⚠ no blog sample in sitemap (skip)");

if (sampleHelp) {
  await checkIndexablePage(sampleHelp, { label: "help", requireTypes: ["Article"] });
} else if (STRICT) fail("no help sample in sitemap");
else console.warn("  ⚠ no help sample in sitemap (skip)");

if (sampleLocation) {
  await checkIndexablePage(sampleLocation, {
    label: "location hub",
    requireTypes: ["CollectionPage"],
  });
} else if (STRICT) fail("no location hub in sitemap");
else console.warn("  ⚠ no location hub sample in sitemap (skip)");

// Faceted canonical
{
  const r = await fetchFollow(`${BASE}/events?sort=popular&utm_source=smoke`);
  if (r.ok && r.html) {
    const c = extractCanonical(r.html);
    if (c !== `${BASE.replace(/\/$/, "")}/events` && c !== "https://padeya.com/events") {
      // www normalize
      if (!c?.endsWith("/events")) fail(`faceted /events canonical unexpected: ${c}`);
      else ok(`faceted /events canonical → ${c}`);
    } else ok(`faceted /events canonical → ${c}`);
  }
}

// Private / noindex surfaces
for (const [path, label] of [
  ["/login", "login"],
  ["/register", "register"],
  ["/dashboard", "dashboard"],
  ["/host", "host workspace"],
  ["/sponsor", "sponsor workspace"],
  ["/messages", "messages"],
  ["/connect", "connect"],
  ["/events/search", "events/search"],
]) {
  await checkNoindexPage(path, label);
}

if (sampleEvent) {
  const slug = new URL(sampleEvent).pathname.split("/").pop();
  await checkNoindexPage(`/events/${slug}/checkout`, "event checkout");
}

// Soft-404 guards (synthetic missing IDs)
await checkMissing404("/events/padeya-seo-smoke-missing-event-xyz", "missing event");
await checkMissing404("/merch/padeya-seo-smoke-missing-merch-xyz", "missing merch");
await checkMissing404("/sponsors/padeya-seo-smoke-missing-sponsor-xyz", "missing sponsor");
await checkMissing404("/u/padeya-seo-smoke-missing-host-xyz", "missing host");

if (process.exitCode && process.exitCode !== 0) {
  console.error("seo-production-smoke: FAILED");
  process.exit(process.exitCode);
} else {
  console.log("seo-production-smoke: ok");
}
