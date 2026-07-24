/**
 * Helpers for the branded 404 / recovery experience.
 * Never log query strings, tokens, or payment references.
 */

import { userHasPermission, userHasRole } from "@/lib/auth/permissions";
import type { User } from "@/lib/auth/types";
import { SPONSORSHIP_MARKETPLACE_PATH } from "@/lib/sponsor-marketplace-paths";

export type NotFoundPathKind =
  | "event"
  | "host"
  | "legacy"
  | "fan"
  | "ticket"
  | "payment"
  | "generic";

export type NotFoundCta = {
  href: string;
  label: string;
  variant?: "primary" | "secondary" | "ghost";
};

const ADMIN_ROLES = [
  "super_admin",
  "admin",
  "admin_staff",
  "finance_admin",
  "support_agent",
  "moderation",
  "operations",
  "marketing",
] as const;

/** Classify a path for contextual recovery CTAs (no query string). */
export function classifyNotFoundPath(path: string): NotFoundPathKind {
  const p = (path.split("?")[0] || "/").toLowerCase();
  if (
    p.startsWith("/events/") ||
    p.startsWith("/e/") ||
    /^\/events\/[^/]+/.test(p)
  ) {
    return "event";
  }
  if (
    p.startsWith("/u/") ||
    p.startsWith("/@") ||
    p.startsWith("/hosts/") ||
    p.startsWith("/legacy/")
  ) {
    return "host";
  }
  if (p.startsWith("/f/")) return "fan";
  if (
    p.includes("/ticket") ||
    p.startsWith("/dashboard/tickets") ||
    p.startsWith("/t/")
  ) {
    return "ticket";
  }
  if (p.includes("/checkout") || p.includes("/payment") || p.includes("/orders/")) {
    return "payment";
  }
  return "generic";
}

/** Strip secrets from a path before analytics — drop query + hash. */
export function sanitizeNotFoundPath(path: string): string {
  const bare = (path || "/").split("?")[0].split("#")[0].trim() || "/";
  return bare.slice(0, 200);
}

/** Truncate UA; never store full fingerprint dumps. */
export function sanitizeUserAgent(ua: string | null | undefined): string | null {
  if (!ua) return null;
  const trimmed = ua.trim().slice(0, 180);
  return trimmed || null;
}

export function roleAwarePrimaryCta(user: User | null): NotFoundCta | null {
  if (!user) return null;
  if (
    userHasPermission(user, "admin.full_access") ||
    userHasRole(user, ...ADMIN_ROLES)
  ) {
    return { href: "/admin", label: "Admin dashboard", variant: "primary" };
  }
  if (userHasRole(user, "host", "host_staff")) {
    return { href: "/host", label: "Host workspace", variant: "primary" };
  }
  return { href: "/dashboard", label: "Personal dashboard", variant: "primary" };
}

export function buildNotFoundCtas(
  user: User | null,
  pathKind: NotFoundPathKind,
): NotFoundCta[] {
  const ctas: NotFoundCta[] = [];
  const roleCta = roleAwarePrimaryCta(user);

  if (pathKind === "event" || pathKind === "generic") {
    ctas.push({
      href: "/events",
      label: "Explore events",
      variant: roleCta ? "secondary" : "primary",
    });
  }
  if (pathKind === "host" || pathKind === "legacy") {
    ctas.push({
      href: "/hosts",
      label: "Explore hosts",
      variant: roleCta ? "secondary" : "primary",
    });
  }
  if (pathKind === "fan") {
    ctas.push({
      href: "/fans",
      label: "Explore fans",
      variant: roleCta ? "secondary" : "primary",
    });
  }

  if (roleCta) {
    ctas.unshift(roleCta);
  } else {
    ctas.push({
      href: "/dashboard",
      label: "Go to dashboard",
      variant: "secondary",
    });
  }

  ctas.push({ href: "/", label: "Go home", variant: "secondary" });

  // Dedupe by href, keep first label (Contact support lives in NOT_FOUND_HELP_LINKS below).
  const seen = new Set<string>();
  return ctas.filter((c) => {
    if (seen.has(c.href)) return false;
    seen.add(c.href);
    return true;
  });
}

export const NOT_FOUND_HELP_LINKS: { href: string; label: string }[] = [
  { href: "/events", label: "Events" },
  { href: "/hosts", label: "Hosts" },
  { href: "/fans", label: "Fans" },
  { href: SPONSORSHIP_MARKETPLACE_PATH, label: "Sponsors" },
  { href: "/support", label: "Contact support" },
];
