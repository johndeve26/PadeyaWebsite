/**
 * Production indexability path helpers (shared by smoke/audit scripts + tests).
 * Policy stays in env-policy / facet-policy / noindex — this is path classification.
 */

/** Exact paths that are intentionally noindex (auth, thin utility). */
const EXACT_NOINDEX = new Set([
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/demo",
  "/offline",
  "/unauthorized",
  "/events/search",
  "/tickets/claim",
]);

/** Prefix trees that are private / checkout / token surfaces. */
const NOINDEX_PREFIXES = [
  "/admin",
  "/dashboard",
  "/host",
  "/sponsor",
  "/connect",
  "/messages",
  "/staff",
  "/ambassador",
  "/checkout",
  "/team/invite",
  "/support/tickets",
  "/support/desk",
  "/support/cases",
  "/support/refunds",
  "/account/appeal",
  "/account/suspended",
] as const;

export function normalizePathname(pathOrUrl: string): string {
  try {
    if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
      return new URL(pathOrUrl).pathname || "/";
    }
  } catch {
    /* fall through */
  }
  const raw = (pathOrUrl.split("?")[0] || "/").split("#")[0] || "/";
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  if (path.length > 1 && path.endsWith("/")) return path.slice(0, -1);
  return path || "/";
}

/** True when the path itself is an intentional noindex surface (ignores query facets). */
export function isIntentionallyNoIndexPath(pathOrUrl: string): boolean {
  const pathname = normalizePathname(pathOrUrl);
  if (EXACT_NOINDEX.has(pathname)) return true;
  if (
    NOINDEX_PREFIXES.some(
      (p) => pathname === p || pathname.startsWith(`${p}/`),
    )
  ) {
    return true;
  }
  if (/^\/events\/[^/]+\/checkout(\/|$)/.test(pathname)) return true;
  if (/^\/merch\/hosts\/[^/]+\/checkout(\/|$)/.test(pathname)) return true;
  return false;
}

/**
 * Conservative public-hub allowlist used by production smoke labels.
 * Entity pages (/events/{slug}, /u/*, …) are also public-indexable when listed.
 */
export function isPublicIndexablePath(pathOrUrl: string): boolean {
  if (isIntentionallyNoIndexPath(pathOrUrl)) return false;
  const pathname = normalizePathname(pathOrUrl);
  if (pathname === "/") return true;

  const publicExact = new Set([
    "/events",
    "/hosts",
    "/fans",
    "/sponsorships",
    "/sponsorships/hosts",
    "/merch",
    "/merch/drops",
    "/merch/vault",
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
    "/events/today",
    "/events/this-weekend",
    "/events/free",
    "/events/vip",
    "/events/online",
    "/events/in-person",
    "/events/hybrid",
    "/events/location",
  ]);
  if (publicExact.has(pathname)) return true;

  if (/^\/events\/c\/[^/]+$/.test(pathname)) return true;
  if (/^\/events\/(city|state|country|area)\/[^/]+$/.test(pathname)) return true;
  if (/^\/events\/city\/[^/]+\/[^/]+$/.test(pathname)) return true;
  if (/^\/events\/state\/[^/]+\/[^/]+$/.test(pathname)) return true;
  if (/^\/events\/under\/[^/]+$/.test(pathname)) return true;
  if (
    /^\/events\/[^/]+$/.test(pathname) &&
    !pathname.startsWith("/events/c/") &&
    pathname !== "/events/search"
  ) {
    return true;
  }
  if (/^\/u\/[^/]+$/.test(pathname)) return true;
  if (/^\/f\/[^/]+$/.test(pathname)) return true;
  if (/^\/sponsors\/[^/]+$/.test(pathname)) return true;
  if (/^\/blog\/[^/]+$/.test(pathname)) return true;
  if (/^\/blog\/(category|tag|author)\/[^/]+$/.test(pathname)) return true;
  if (/^\/help\/[^/]+$/.test(pathname)) return true;
  if (/^\/help\/articles\/[^/]+$/.test(pathname)) return true;
  if (/^\/merch\/hosts\/[^/]+$/.test(pathname)) return true;
  if (
    /^\/merch\/[^/]+$/.test(pathname) &&
    !["drops", "vault", "hosts"].includes(pathname.split("/")[2] || "")
  ) {
    return true;
  }
  return false;
}

export function responseHasNoindex(opts: {
  robotsMeta?: string | null;
  googlebotMeta?: string | null;
  xRobotsTag?: string | null;
}): boolean {
  const parts = [opts.robotsMeta, opts.googlebotMeta, opts.xRobotsTag];
  return parts.some((v) => Boolean(v && /\b(noindex|none)\b/i.test(v)));
}

/**
 * Minimal robots.txt allow check for path-only rules (no wildcards beyond *).
 * Mirrors Google's common prefix + single-* segment semantics used in our disallows.
 */
export function isRobotsBlocked(
  robotsTxt: string,
  pathOrUrl: string,
): boolean {
  const pathname = normalizePathname(pathOrUrl);
  const lines = robotsTxt.split(/\r?\n/);
  let inStarGroup = false;
  const disallows: string[] = [];
  const allows: string[] = [];

  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const ua = line.match(/^user-agent:\s*(.+)$/i);
    if (ua) {
      const agent = ua[1].trim();
      inStarGroup = agent === "*";
      continue;
    }
    if (!inStarGroup) continue;
    const dis = line.match(/^disallow:\s*(.*)$/i);
    if (dis) {
      disallows.push(dis[1].trim());
      continue;
    }
    const allow = line.match(/^allow:\s*(.*)$/i);
    if (allow) {
      allows.push(allow[1].trim());
    }
  }

  const matches = (pattern: string): boolean => {
    if (!pattern) return false;
    // "/events/*/checkout" style
    if (pattern.includes("*")) {
      const escaped = pattern
        .replace(/[.+?^${}()|[\]\\]/g, "\\$&")
        .replace(/\*/g, "[^/]+");
      return new RegExp(`^${escaped}`).test(pathname);
    }
    if (pathname === pattern) return true;
    if (pathname.startsWith(pattern)) return true;
    // Disallow: /dashboard/ also matches /dashboard
    if (pattern.endsWith("/") && pathname === pattern.slice(0, -1)) return true;
    return false;
  };

  let blocked = false;
  let bestDisallow = -1;
  for (const d of disallows) {
    if (matches(d) && d.length >= bestDisallow) {
      blocked = true;
      bestDisallow = d.length;
    }
  }
  for (const a of allows) {
    if (matches(a) && a.length >= bestDisallow) {
      blocked = false;
      bestDisallow = a.length;
    }
  }
  return blocked;
}
