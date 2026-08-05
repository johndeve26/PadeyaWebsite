/**
 * Pure helpers for Host Legacy Open Graph copy + card fields.
 * Keep ImageResponse layout free of business rules.
 */

import { formatCompact } from "@/lib/legacy-presentation";
import type { LegacyPage } from "@/lib/types/legacy";

export const HOST_OG_GOLD = "#D4AF37";
export const HOST_OG_MUTED = "rgba(255,255,255,0.72)";
export const HOST_OG_PANEL = "rgba(0,0,0,0.62)";

export type HostOgStat = {
  key: "events" | "tickets" | "rating";
  icon: "calendar" | "ticket" | "star";
  label: string;
};

export function truncateEllipsis(
  value: string | null | undefined,
  max: number,
): string {
  const raw = (value || "").trim().replace(/\s+/g, " ");
  if (!raw) return "";
  if (raw.length <= max) return raw;
  if (max <= 1) return "…";
  return `${raw.slice(0, Math.max(1, max - 1)).trimEnd()}…`;
}

export function hostOgDisplayName(page: Pick<LegacyPage, "display_name">): string {
  return truncateEllipsis(page.display_name, 40) || "Host";
}

/** First word(s) white, last word green — matches premium share mock. */
export function splitDisplayNameTone(name: string): {
  lead: string;
  accent: string;
} {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length < 2) return { lead: name, accent: "" };
  return {
    lead: parts.slice(0, -1).join(" "),
    accent: parts[parts.length - 1]!,
  };
}

export function hostOgUsername(page: Pick<LegacyPage, "username">): string {
  const slug = (page.username || "").replace(/^@/, "").trim();
  return truncateEllipsis(slug ? `@${slug}` : "", 32);
}

export function hostOgLocation(
  page: Pick<LegacyPage, "profile">,
): string | null {
  const parts = [
    page.profile?.city,
    page.profile?.state,
    page.profile?.country,
  ]
    .map((p) => (p || "").trim())
    .filter(Boolean);
  const deduped: string[] = [];
  for (const part of parts) {
    const prev = deduped[deduped.length - 1];
    if (prev && prev.toLowerCase() === part.toLowerCase()) continue;
    deduped.push(part);
  }
  return truncateEllipsis(deduped.join(", "), 48) || null;
}

export function hostOgBio(page: LegacyPage): string | null {
  const bio =
    page.tagline?.trim() ||
    page.settings?.tagline?.trim() ||
    page.about?.trim() ||
    page.profile?.bio?.trim() ||
    "";
  return truncateEllipsis(bio, 110) || null;
}

export function hostOgLegacyScore(page: LegacyPage): number | null {
  const fromTrust = page.legacy_trust?.display_score;
  if (typeof fromTrust === "number" && Number.isFinite(fromTrust)) {
    return Math.round(fromTrust);
  }
  const raw = page.composite_score ?? page.stats?.composite_score;
  if (raw == null || raw === "") return null;
  const n = typeof raw === "number" ? raw : Number(raw);
  if (!Number.isFinite(n)) return null;
  return Math.round(n);
}

export function hostOgShareHandle(page: Pick<LegacyPage, "username">): string {
  const slug = (page.username || "").replace(/^@/, "").trim();
  return slug ? `padeya.com/@${slug}` : "padeya.com";
}

function parseRating(value: string | number | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

export function hostOgStats(page: LegacyPage): HostOgStat[] {
  const stats = page.stats;
  const out: HostOgStat[] = [];

  if (stats && typeof stats.events_hosted === "number" && !Number.isNaN(stats.events_hosted)) {
    out.push({
      key: "events",
      icon: "calendar",
      label: `${formatCompact(stats.events_hosted)} Events Hosted`,
    });
  }

  if (stats && typeof stats.tickets_sold === "number" && !Number.isNaN(stats.tickets_sold)) {
    out.push({
      key: "tickets",
      icon: "ticket",
      label: `${formatCompact(stats.tickets_sold)} Tickets Sold`,
    });
  }

  const rating = parseRating(stats?.average_verified_rating);
  const reviews = stats?.review_count ?? 0;
  if (rating != null && reviews > 0) {
    out.push({
      key: "rating",
      icon: "star",
      label: `${rating.toFixed(1)} Avg Rating`,
    });
  }

  return out;
}

export function hostOgTitle(page: LegacyPage): string {
  const name = page.display_name.trim() || "Host";
  const score = hostOgLegacyScore(page);
  if (page.verified && score != null) {
    return `${name} — Verified Host & Legacy ${score} | Pàdéyá`;
  }
  if (page.verified) {
    return `${name} — Verified Host | Pàdéyá`;
  }
  if (score != null) {
    return `${name} — Legacy ${score} | Pàdéyá`;
  }
  return `${name} · Host Legacy | Pàdéyá`;
}

export function hostOgDescription(page: LegacyPage): string {
  const name = page.display_name.trim() || "this host";
  const bio = hostOgBio(page);
  if (bio && bio.length >= 24) {
    return truncateEllipsis(bio, 160);
  }
  return truncateEllipsis(
    `Discover ${name}'s verified events, ratings, memories and host legacy on Pàdéyá.`,
    160,
  );
}

export function pickHostMediaUrl(
  media:
    | {
        og_url?: string | null;
        display_url?: string | null;
        url?: string | null;
        full_url?: string | null;
      }
    | null
    | undefined,
  legacyUrl?: string | null,
): string | null {
  return (
    media?.og_url ||
    media?.display_url ||
    media?.url ||
    media?.full_url ||
    legacyUrl ||
    null
  );
}
