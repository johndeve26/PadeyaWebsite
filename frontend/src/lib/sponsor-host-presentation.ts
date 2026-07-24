/**
 * Frontend-only presentation enrichment for sponsorship host cards.
 * Does not change API contracts — fills visual gaps (cover, tier, category, stats)
 * for known demo hosts and sensible fallbacks for everyone else.
 */

import type { SponsorHost } from "@/lib/types/sponsorships";

export type SponsorHostPresentation = SponsorHost & {
  coverUrl: string | null;
  avatarUrl: string | null;
  tier: string | null;
  category: string | null;
  eventsHosted: number | null;
  verifiedCheckins: number | null;
  averageRating: number | null;
  followers: number | null;
  featured: boolean;
};

type Enrichment = {
  coverUrl?: string;
  avatarUrl?: string;
  tier?: string;
  category?: string;
  eventsHosted?: number;
  verifiedCheckins?: number;
  averageRating?: number;
  followers?: number;
  featured?: boolean;
};

const COVER_POOL = [
  "/demo/hosts/djmaze-cover.svg",
  "/demo/hosts/lagoscomedyhub-cover.svg",
  "/demo/hosts/mainlandvibes-cover.svg",
  "/demo/hosts/techconnectafrica-cover.svg",
  "/demo/hosts/praiseexperience-cover.svg",
] as const;

const BY_USERNAME: Record<string, Enrichment> = {
  djmaze: {
    coverUrl: "/demo/hosts/djmaze-cover.svg",
    avatarUrl: "/demo/hosts/djmaze-avatar.svg",
    tier: "Certified",
    category: "Music",
    eventsHosted: 48,
    verifiedCheckins: 18240,
    averageRating: 4.9,
    followers: 12600,
    featured: true,
  },
  lagoscomedyhub: {
    coverUrl: "/demo/hosts/lagoscomedyhub-cover.svg",
    avatarUrl: "/demo/hosts/lagoscomedyhub-avatar.svg",
    tier: "Established",
    category: "Comedy",
    eventsHosted: 32,
    verifiedCheckins: 9100,
    averageRating: 4.7,
    followers: 5400,
  },
  mainlandvibes: {
    coverUrl: "/demo/hosts/mainlandvibes-cover.svg",
    avatarUrl: "/demo/hosts/mainlandvibes-avatar.svg",
    tier: "Rising",
    category: "Music",
    eventsHosted: 18,
    verifiedCheckins: 6200,
    averageRating: 4.6,
    followers: 3100,
  },
  techconnectafrica: {
    coverUrl: "/demo/hosts/techconnectafrica-cover.svg",
    avatarUrl: "/demo/hosts/techconnectafrica-avatar.svg",
    tier: "Established",
    category: "Tech",
    eventsHosted: 26,
    verifiedCheckins: 4800,
    averageRating: 4.8,
    followers: 7200,
  },
  praiseexperience: {
    coverUrl: "/demo/hosts/praiseexperience-cover.svg",
    avatarUrl: "/demo/hosts/praiseexperience-avatar.svg",
    tier: "Rising",
    category: "Faith",
    eventsHosted: 14,
    verifiedCheckins: 8700,
    averageRating: 4.9,
    followers: 4100,
  },
};

function hashUsername(username: string): number {
  let h = 0;
  for (let i = 0; i < username.length; i += 1) {
    h = (h * 31 + username.charCodeAt(i)) >>> 0;
  }
  return h;
}

const TIER_RANK: Record<string, number> = {
  legend: 6,
  icon: 5,
  certified: 4,
  established: 3,
  rising: 2,
  new_host: 1,
  "new host": 1,
};

export function enrichSponsorHost(host: SponsorHost): SponsorHostPresentation {
  const key = host.username.replace(/^@/, "").toLowerCase();
  const extra = BY_USERNAME[key] ?? {};
  const idx = hashUsername(key) % COVER_POOL.length;
  const slots = host.open_slots || 0;
  return {
    ...host,
    coverUrl: extra.coverUrl ?? COVER_POOL[idx],
    avatarUrl: extra.avatarUrl ?? null,
    tier: extra.tier ?? (slots >= 5 ? "Established" : slots >= 2 ? "Rising" : "New Host"),
    category: extra.category ?? null,
    eventsHosted: extra.eventsHosted ?? Math.max(slots * 3, 1),
    verifiedCheckins: extra.verifiedCheckins ?? Math.max(slots * 400, 50),
    averageRating: extra.averageRating ?? 4.6,
    followers: extra.followers ?? Math.max(slots * 200, 40),
    featured: Boolean(extra.featured) || slots >= 5,
  };
}

export function enrichSponsorHosts(hosts: SponsorHost[]): SponsorHostPresentation[] {
  return hosts.map(enrichSponsorHost);
}

export function tierRank(tier: string | null | undefined): number {
  if (!tier) return 0;
  return TIER_RANK[tier.toLowerCase()] ?? 0;
}

export function summarizeSponsorHosts(hosts: SponsorHostPresentation[]) {
  const cities = new Set(
    hosts.map((h) => h.city?.trim()).filter((c): c is string => Boolean(c)),
  );
  const openSlots = hosts.reduce((sum, h) => sum + (h.open_slots || 0), 0);
  const attendees = hosts.reduce(
    (sum, h) => sum + (h.verifiedCheckins || 0),
    0,
  );
  return {
    verifiedHosts: hosts.length,
    openSlots,
    verifiedAttendees: attendees,
    cities: cities.size,
  };
}

export function uniqueHostCities(hosts: SponsorHostPresentation[]): string[] {
  return Array.from(
    new Set(
      hosts.map((h) => h.city?.trim()).filter((c): c is string => Boolean(c)),
    ),
  ).sort((a, b) => a.localeCompare(b));
}

export function uniqueHostCategories(hosts: SponsorHostPresentation[]): string[] {
  return Array.from(
    new Set(
      hosts
        .map((h) => h.category?.trim())
        .filter((c): c is string => Boolean(c)),
    ),
  ).sort((a, b) => a.localeCompare(b));
}

export type SponsorHostSort = "slots" | "audience" | "tier" | "name";

export function filterAndSortSponsorHosts(
  hosts: SponsorHostPresentation[],
  opts: {
    search?: string;
    city?: string;
    category?: string;
    verifiedOnly?: boolean;
    sort?: SponsorHostSort;
  },
): SponsorHostPresentation[] {
  const q = (opts.search || "").trim().toLowerCase();
  let rows = hosts.filter((h) => {
    if (opts.verifiedOnly && !h.verified) return false;
    if (opts.city && opts.city !== "all" && h.city !== opts.city) return false;
    if (opts.category && opts.category !== "all" && h.category !== opts.category) {
      return false;
    }
    if (!q) return true;
    const hay = `${h.display_name} ${h.username} ${h.city || ""} ${h.category || ""} ${h.bio || ""} ${h.pitch || ""}`.toLowerCase();
    return hay.includes(q);
  });

  const sort = opts.sort || "slots";
  rows = [...rows].sort((a, b) => {
    if (a.featured !== b.featured) return a.featured ? -1 : 1;
    if (sort === "audience") {
      return (b.verifiedCheckins || 0) - (a.verifiedCheckins || 0);
    }
    if (sort === "tier") {
      return tierRank(b.tier) - tierRank(a.tier);
    }
    if (sort === "name") {
      return a.display_name.localeCompare(b.display_name);
    }
    return (b.open_slots || 0) - (a.open_slots || 0);
  });

  return rows;
}

export function formatCompactNumber(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}K`;
  return String(n);
}
