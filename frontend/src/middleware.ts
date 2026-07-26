import { NextResponse, type NextRequest } from "next/server";

import { hasEventsFacetQuery } from "@/lib/seo/facet-policy";
import {
  shouldIndexEnvironment,
  X_ROBOTS_NOINDEX,
} from "@/lib/seo/env-policy";

/**
 * Paths that must never be indexed (private, auth, checkout, tokens).
 * Complements layout robots metadata — headers apply even when HTML is thin.
 */
function isNoIndexPath(pathname: string): boolean {
  const exact = new Set([
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/demo",
    "/offline",
    "/unauthorized",
  ]);
  if (exact.has(pathname)) return true;

  const prefixes = [
    "/admin",
    "/dashboard",
    "/host",
    "/sponsor",
    "/connect",
    "/messages",
    "/staff",
    "/ambassador",
    "/checkout",
    "/tickets/claim",
    "/team/invite",
    "/support/tickets",
    "/support/desk",
    "/support/cases",
    "/support/refunds",
    "/account/appeal",
    "/account/suspended",
  ];
  if (prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return true;
  }

  // /events/{slug}/checkout and nested checkout paths
  if (/^\/events\/[^/]+\/checkout(\/|$)/.test(pathname)) return true;
  if (/^\/merch\/hosts\/[^/]+\/checkout(\/|$)/.test(pathname)) return true;

  return false;
}

/** Faceted marketplace query strings — noindex without dynamizing the page. */
function isFacetNoIndexPath(request: NextRequest): boolean {
  const { pathname, searchParams } = request.nextUrl;
  if (pathname === "/events" || pathname === "/events/search") {
    return hasEventsFacetQuery(searchParams);
  }
  if (pathname === "/sponsorships") {
    return Boolean(
      searchParams.get("host") ||
        searchParams.get("sponsor") ||
        searchParams.get("q") ||
        searchParams.get("sort"),
    );
  }
  if (pathname === "/help") {
    return Boolean(searchParams.get("q") || searchParams.get("audience"));
  }
  return false;
}

const X_ROBOTS_NOINDEX_FOLLOW = "noindex, follow";

function withSeoHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const pathname = request.nextUrl.pathname;
  if (!shouldIndexEnvironment() || isNoIndexPath(pathname)) {
    response.headers.set("X-Robots-Tag", X_ROBOTS_NOINDEX);
  } else if (isFacetNoIndexPath(request)) {
    // Facets: noindex but keep follow (SEO Phase 1B) — without dynamizing RSC.
    response.headers.set("X-Robots-Tag", X_ROBOTS_NOINDEX_FOLLOW);
  }
  return response;
}

/**
 * Public host surfaces live at /@username[…].
 * App Router cannot use @ as a URL segment, so rewrite to /u/[username][…].
 * Also applies X-Robots-Tag for non-production + private/facet paths (Phase 0A + 2).
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/@")) {
    const remainder = pathname.slice(2); // username/...
    const slash = remainder.indexOf("/");
    const username = slash === -1 ? remainder : remainder.slice(0, slash);
    const rest = slash === -1 ? "" : remainder.slice(slash); // /vault|/merch|…
    if (!username) {
      return withSeoHeaders(NextResponse.next(), request);
    }

    const url = request.nextUrl.clone();
    url.pathname = `/u/${username}${rest}`;
    return withSeoHeaders(NextResponse.rewrite(url), request);
  }

  return withSeoHeaders(NextResponse.next(), request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
