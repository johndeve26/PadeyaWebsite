import type { FanBadge } from "@/lib/types/passport";

export type PassportStampSource =
  | "Ticket"
  | "Check-in"
  | "Review"
  | "Merch"
  | "Vault"
  | "Host support";

const MERCH_KEYS = new Set([
  "first_merch_buy",
  "merch_collector",
  "vip_pack_owner",
  "event_drop_supporter",
  "vault_merch_member",
  "sponsor_drop_supporter",
  "founder_mode_gear",
]);

const REVIEW_KEYS = new Set(["reviewer", "review_writer"]);
const VAULT_KEYS = new Set(["vault_member", "vault_merch_member"]);
const HOST_KEYS = new Set(["day_one_fan", "superfan"]);
const TICKET_KEYS = new Set([
  "first_ticket",
  "vip_regular",
  "early_bird",
  "table_buyer",
]);
const CHECKIN_KEYS = new Set([
  "verified_attendee",
  "checked_in_attendee",
  "nightlife_explorer",
  "concert_lover",
  "comedy_fan",
  "tech_regular",
  "campus_explorer",
  "event_hopper",
  "lagos_explorer",
]);

/** Map badge criteria to a public stamp source label. */
export function stampSourceForBadge(badge: FanBadge): PassportStampSource {
  const key = (badge.criteria_key || "").toLowerCase();
  const slug = (badge.slug || "").toLowerCase();
  const name = (badge.name || "").toLowerCase();

  if (
    MERCH_KEYS.has(key) ||
    slug.includes("merch") ||
    name.includes("merch") ||
    name.includes("founder mode")
  ) {
    return "Merch";
  }
  if (REVIEW_KEYS.has(key) || slug.includes("review") || name.includes("review")) {
    return "Review";
  }
  if (VAULT_KEYS.has(key) || slug.includes("vault") || name.includes("vault")) {
    return "Vault";
  }
  if (HOST_KEYS.has(key) || name.includes("superfan") || name.includes("day one")) {
    return "Host support";
  }
  if (TICKET_KEYS.has(key) || name.includes("ticket") || name.includes("vip")) {
    return "Ticket";
  }
  if (CHECKIN_KEYS.has(key) || name.includes("check") || name.includes("attendee")) {
    return "Check-in";
  }
  return "Check-in";
}

export function stampInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "PS";
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}
