/**
 * Frontend presentation helpers for public sponsorship slots.
 * Enriches slots with host city/category/audience for marketplace filters.
 */

import {
  enrichSponsorHost,
  type SponsorHostPresentation,
} from "@/lib/sponsor-host-presentation";
import type { SponsorHost, SponsorshipSlot } from "@/lib/types/sponsorships";

export type SponsorSlotSort =
  | "recommended"
  | "campaign_recommended"
  | "newest"
  | "price_asc"
  | "audience"
  | "closing";

export type SponsorBudgetRange = "all" | "under_50k" | "50k_200k" | "over_200k";
export type SponsorAudienceBucket = "all" | "growing" | "high_reach";

export type EnrichedSponsorshipSlot = SponsorshipSlot & {
  city: string | null;
  category: string | null;
  audienceReach: number;
  hostTier: string | null;
};

export const SLOT_TYPE_OPTIONS = [
  { value: "logo_event_page", label: "Logo on event page" },
  { value: "logo_ticket_email", label: "Logo on ticket email" },
  { value: "banner_legacy_page", label: "Banner on Legacy Page" },
  { value: "sponsored_memory_page", label: "Sponsored Event Memory page" },
  { value: "sponsored_vault_content", label: "Sponsored Vault drop" },
  { value: "booth_at_event", label: "Booth at event" },
  { value: "host_shoutout", label: "Host shoutout" },
  { value: "custom_package", label: "Custom package" },
] as const;

export function enrichSponsorshipSlots(
  slots: SponsorshipSlot[],
  hosts: SponsorHost[] | SponsorHostPresentation[],
): EnrichedSponsorshipSlot[] {
  const byUsername = new Map<string, SponsorHostPresentation>();
  const byId = new Map<string, SponsorHostPresentation>();

  for (const host of hosts) {
    const enriched =
      "verifiedCheckins" in host ? host : enrichSponsorHost(host as SponsorHost);
    byUsername.set(enriched.username.replace(/^@/, "").toLowerCase(), enriched);
    byId.set(enriched.host_id, enriched);
  }

  return slots.map((slot) => {
    const key = (slot.host_username || "").replace(/^@/, "").toLowerCase();
    const host = (key && byUsername.get(key)) || byId.get(slot.host_id) || null;
    return {
      ...slot,
      city: host?.city ?? null,
      category: host?.category ?? null,
      audienceReach: host?.verifiedCheckins ?? host?.followers ?? 0,
      hostTier: host?.tier ?? null,
    };
  });
}

function slotPrice(slot: SponsorshipSlot): number {
  const n = typeof slot.price === "number" ? slot.price : Number(slot.price);
  return Number.isFinite(n) ? n : 0;
}

function matchesBudget(price: number, range: SponsorBudgetRange): boolean {
  if (range === "all") return true;
  if (range === "under_50k") return price < 50_000;
  if (range === "50k_200k") return price >= 50_000 && price <= 200_000;
  return price > 200_000;
}

function matchesAudience(
  reach: number,
  bucket: SponsorAudienceBucket,
): boolean {
  if (bucket === "all") return true;
  if (bucket === "high_reach") return reach >= 5_000;
  return reach < 5_000;
}

export function uniqueSlotCities(slots: EnrichedSponsorshipSlot[]): string[] {
  return Array.from(
    new Set(
      slots.map((s) => s.city?.trim()).filter((c): c is string => Boolean(c)),
    ),
  ).sort((a, b) => a.localeCompare(b));
}

export function uniqueSlotCategories(slots: EnrichedSponsorshipSlot[]): string[] {
  return Array.from(
    new Set(
      slots
        .map((s) => s.category?.trim())
        .filter((c): c is string => Boolean(c)),
    ),
  ).sort((a, b) => a.localeCompare(b));
}

export function uniqueSlotTypes(slots: EnrichedSponsorshipSlot[]): {
  value: string;
  label: string;
}[] {
  const seen = new Map<string, string>();
  for (const slot of slots) {
    if (!seen.has(slot.slot_type)) {
      seen.set(slot.slot_type, slot.slot_type_label || slot.slot_type);
    }
  }
  return Array.from(seen.entries())
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export function filterAndSortSponsorshipSlots(
  slots: EnrichedSponsorshipSlot[],
  opts: {
    search?: string;
    city?: string;
    category?: string;
    slotType?: string;
    budget?: SponsorBudgetRange;
    audience?: SponsorAudienceBucket;
    sort?: SponsorSlotSort;
    hostUsername?: string;
    campaignScores?: Record<string, number>;
  },
): EnrichedSponsorshipSlot[] {
  const q = (opts.search || "").trim().toLowerCase();
  const hostFilter = (opts.hostUsername || "").replace(/^@/, "").toLowerCase();

  let rows = slots.filter((slot) => {
    if (hostFilter) {
      const u = (slot.host_username || "").replace(/^@/, "").toLowerCase();
      if (u !== hostFilter) return false;
    }
    if (opts.city && opts.city !== "all" && slot.city !== opts.city) return false;
    if (opts.category && opts.category !== "all" && slot.category !== opts.category) {
      return false;
    }
    if (opts.slotType && opts.slotType !== "all" && slot.slot_type !== opts.slotType) {
      return false;
    }
    if (!matchesBudget(slotPrice(slot), opts.budget || "all")) return false;
    if (!matchesAudience(slot.audienceReach, opts.audience || "all")) return false;
    if (!q) return true;
    const hay = [
      slot.title,
      slot.description,
      slot.host_display_name,
      slot.host_username,
      slot.event_title,
      slot.slot_type_label,
      slot.city,
      slot.category,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });

  const sort = opts.sort || "recommended";
  rows = [...rows].sort((a, b) => {
    if (sort === "newest") {
      const at = Date.parse(a.published_at || a.created_at);
      const bt = Date.parse(b.published_at || b.created_at);
      return bt - at;
    }
    if (sort === "price_asc") {
      return slotPrice(a) - slotPrice(b);
    }
    if (sort === "audience") {
      return b.audienceReach - a.audienceReach;
    }
    if (sort === "closing") {
      const at = Date.parse(a.published_at || a.created_at);
      const bt = Date.parse(b.published_at || b.created_at);
      return at - bt;
    }
    if (sort === "campaign_recommended" && opts.campaignScores) {
      const sa = opts.campaignScores[a.id] ?? 0;
      const sb = opts.campaignScores[b.id] ?? 0;
      return sb - sa;
    }
    // recommended: verified + higher audience + mid price balance
    const score = (s: EnrichedSponsorshipSlot) =>
      (s.host_verified ? 1000 : 0) +
      Math.min(s.audienceReach / 100, 500) -
      slotPrice(s) / 10_000;
    return score(b) - score(a);
  });

  return rows;
}
