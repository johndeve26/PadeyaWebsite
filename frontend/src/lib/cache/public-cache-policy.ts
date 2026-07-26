/**
 * Public cache safety matrix for Pàdéyá Phase 2 (SSR / CDN).
 *
 * Security/privacy correctness beats cache speed.
 */

export type PublicCacheClass =
  | "PUBLIC_CACHEABLE"
  | "PUBLIC_SHORT_TTL"
  | "PUBLIC_REALTIME"
  | "PRIVATE_NEVER_CACHE";

export const PUBLIC_CACHE_POLICY = {
  /** Published event detail, public host Legacy, public sponsor, blog/help, taxonomy. */
  PUBLIC_CACHEABLE: [
    "published_event_detail",
    "public_host_legacy",
    "public_sponsor_profile",
    "public_merch_product_seo",
    "published_blog_help",
    "public_taxonomy",
    "public_discovery_hubs",
  ],
  /** Ticket/availability-ish, follower counts, fan directory, near start/cancel. */
  PUBLIC_SHORT_TTL: [
    "event_list_shell",
    "ticket_availability_summary",
    "fan_directory",
    "sponsorship_marketplace_shell",
  ],
  PUBLIC_REALTIME: ["checkout_inventory", "live_capacity_gates"],
  PRIVATE_NEVER_CACHE: [
    "authenticated_user",
    "account_profile",
    "tickets_orders_payments",
    "checkout_state",
    "private_fan_passport",
    "fan_passport_html",
    "private_sponsor_data",
    "crm_messages_notifications",
    "admin_host_sponsor_workspace",
    "vault_private",
    "private_analytics",
  ],
} as const;

/**
 * Fan Passport HTML cache rules (privacy-first).
 *
 * `/f/{username}` is force-dynamic / no-store. API 404 + TTL is **not** used
 * as the privacy control for PUBLIC→PRIVATE. Directory (`/fans`) uses short ISR
 * and is purged via authenticated `/api/revalidate/fan`.
 */
export const FAN_PASSPORT_CACHE = {
  public: {
    class: "PRIVATE_NEVER_CACHE" as const,
    html: "force-dynamic / no-store",
    indexable: true,
    note: "Request-scoped React cache() only; never CDN-cache HTML",
  },
  unlisted: {
    class: "PRIVATE_NEVER_CACHE" as const,
    html: "force-dynamic / no-store",
    indexable: false,
    note: "Direct link only; noindex; not directory/sitemap eligible",
  },
  private: {
    class: "PRIVATE_NEVER_CACHE" as const,
    behavior: "API 404 — never render; no stale CDN HTML possible (no-store)",
  },
  directory: {
    class: "PUBLIC_SHORT_TTL" as const,
    revalidateSeconds: 180,
    purge: "POST /api/revalidate/fan (Bearer REVALIDATE_SECRET)",
  },
} as const;

export function isPrivateNeverCachePath(pathname: string): boolean {
  const prefixes = [
    "/admin",
    "/dashboard",
    "/host",
    "/sponsor",
    "/connect",
    "/messages",
    "/checkout",
    "/account",
  ];
  if (prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return true;
  }
  // Public Fan Passport HTML is never CDN-cached (privacy).
  if (pathname === "/f" || pathname.startsWith("/f/")) return true;
  return false;
}
