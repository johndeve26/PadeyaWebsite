/**
 * Pure helpers for Fan Passport Open Graph copy + card fields.
 */

import { stampInitials } from "@/components/passport/badge-source";
import { formatCompact } from "@/lib/legacy-presentation";
import { truncateEllipsis } from "@/lib/seo/host-og-presentation";
import type { FanBadge, FanPassportPublicPage } from "@/lib/types/passport";

export const FAN_OG_GOLD = "#D4AF37";
export const FAN_OG_MUTED = "rgba(255,255,255,0.72)";
export const FAN_OG_DIM = "rgba(255,255,255,0.55)";

export type FanOgStat = {
  key: "events" | "hosts" | "stamps";
  value: string;
  label: string;
  /** Non-zero values use brand green; zeros stay muted. */
  active: boolean;
};

export type FanOgStampChip = {
  key: string;
  label: string;
  initials: string;
  color: string;
};

const STAMP_COLORS = [
  "#8EF012",
  "#E8C547",
  "#B794F6",
  "#F6AD55",
  "#63B3ED",
] as const;

/**
 * Use an explicit public verification flag only.
 * Never infer verification from activity, stamps, superfans, or demo status.
 * Current FanPassportPublicPage has no verified field — seal stays PUBLIC.
 */
export function fanOgShowVerified(
  page: FanPassportPublicPage | null,
): boolean {
  if (!page) return false;
  const flagged = page as FanPassportPublicPage & {
    is_verified?: boolean | null;
    verified?: boolean | null;
  };
  return flagged.is_verified === true || flagged.verified === true;
}

export function fanOgDisplayNameFontSize(name: string): number {
  const len = name.trim().length;
  if (len <= 20) return 60;
  if (len <= 30) return 54;
  if (len <= 42) return 46;
  return 40;
}

export function fanOgDisplayName(
  page: Pick<FanPassportPublicPage, "display_name">,
): string {
  return truncateEllipsis(page.display_name, 48) || "Fan";
}

export function fanOgUsername(
  page: Pick<FanPassportPublicPage, "username">,
): string {
  const slug = (page.username || "").replace(/^@/, "").trim();
  return truncateEllipsis(slug ? `@${slug}` : "", 28);
}

export function fanOgLocation(
  page: Pick<FanPassportPublicPage, "favorite_cities">,
): string | null {
  const city = page.favorite_cities?.find((c) => c?.trim())?.trim() || "";
  return truncateEllipsis(city, 28) || null;
}

export function fanOgBio(page: FanPassportPublicPage): string {
  const bio =
    page.tagline?.trim() ||
    page.bio?.trim() ||
    "Building a Fan Passport on Pàdéyá.";
  return truncateEllipsis(bio, 105);
}

export function fanOgScenes(
  page: Pick<FanPassportPublicPage, "favorite_categories">,
): string | null {
  const scenes = (page.favorite_categories || [])
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 3);
  if (!scenes.length) return null;
  return truncateEllipsis(scenes.join(" · "), 42);
}

/** Status line under username — never duplicates the FAN PASSPORT heading. */
export function fanOgStatusLine(page: FanPassportPublicPage): string {
  if (fanOgShowVerified(page)) return "Verified Passport";
  if (page.visibility === "unlisted") return "Unlisted Passport";
  return "Public Passport";
}

export function fanOgHasActivity(page: FanPassportPublicPage): boolean {
  return (page.events_attended ?? 0) > 0 || (page.badges_earned_count ?? 0) > 0;
}

export function fanOgSupportCopy(page: FanPassportPublicPage): string {
  if (fanOgHasActivity(page)) {
    return "Verified nights, stamps and scenes on Pàdéyá.";
  }
  return "Build your nightlife story on Pàdéyá.";
}

export function fanOgEmptyStampCopy(page: FanPassportPublicPage): string | null {
  if ((page.badges_earned_count ?? 0) > 0) return null;
  if ((page.badges || []).some((b) => b.earned !== false)) return null;
  return "Your first verified check-in unlocks a passport stamp.";
}

export function fanOgStats(page: FanPassportPublicPage): FanOgStat[] {
  const events = page.events_attended ?? 0;
  const hosts = page.hosts_followed ?? 0;
  const stamps = page.badges_earned_count ?? 0;
  return [
    {
      key: "events",
      value: formatCompact(events),
      label: events === 1 ? "EVENT ATTENDED" : "EVENTS ATTENDED",
      active: events > 0,
    },
    {
      key: "hosts",
      value: formatCompact(hosts),
      label: hosts === 1 ? "HOST FOLLOWED" : "HOSTS FOLLOWED",
      active: hosts > 0,
    },
    {
      key: "stamps",
      value: formatCompact(stamps),
      label: stamps === 1 ? "STAMP EARNED" : "STAMPS EARNED",
      active: stamps > 0,
    },
  ];
}

export function fanOgStampChips(
  page: Pick<FanPassportPublicPage, "badges" | "badges_earned_count">,
): { chips: FanOgStampChip[]; extra: number; summary: string | null } {
  const earned = (page.badges || []).filter((b) => b.earned !== false);
  const total = Math.max(page.badges_earned_count ?? 0, earned.length);
  if (total <= 0) return { chips: [], extra: 0, summary: null };
  const chips = earned.slice(0, 4).map((badge, i) => fanOgStampChip(badge, i));
  const extra = Math.max(0, total - chips.length);
  const summary =
    total === 1 ? "1 passport stamp earned" : `${total} passport stamps earned`;
  return { chips, extra, summary };
}

function fanOgStampChip(badge: FanBadge, index: number): FanOgStampChip {
  const name = truncateEllipsis(badge.name || "Stamp", 18) || "Stamp";
  return {
    key: badge.id || badge.slug || `stamp-${index}`,
    label: name,
    initials: stampInitials(badge.name || "PS"),
    color: STAMP_COLORS[index % STAMP_COLORS.length]!,
  };
}

export function fanOgShareHandle(
  page: Pick<FanPassportPublicPage, "username" | "share_path">,
): string {
  const fromShare = (page.share_path || "").replace(/^\//, "").trim();
  if (fromShare) {
    return truncateEllipsis(`padeya.com/${fromShare}`, 40);
  }
  const slug = (page.username || "").replace(/^@/, "").trim();
  return slug ? `padeya.com/f/${slug}` : "padeya.com";
}

export function fanOgTitle(page: FanPassportPublicPage): string {
  const name = page.display_name.trim() || "Fan";
  if (fanOgShowVerified(page)) {
    return `${name} — Verified Fan Passport | Pàdéyá`;
  }
  return `${name}'s Fan Passport | Pàdéyá`;
}

export function fanOgDescription(page: FanPassportPublicPage): string {
  const name = page.display_name.trim() || "this fan";
  const bio = page.tagline?.trim() || page.bio?.trim() || "";
  if (bio.length >= 24) {
    return truncateEllipsis(bio, 160);
  }
  return truncateEllipsis(
    `View ${name}'s public Fan Passport, hosts followed, event activity and stamps on Pàdéyá.`,
    160,
  );
}

export function pickFanAvatarUrl(
  page: Pick<FanPassportPublicPage, "avatar_url" | "avatar_media">,
): string | null {
  const media = page.avatar_media;
  return (
    media?.og_url ||
    media?.display_url ||
    media?.url ||
    media?.full_url ||
    page.avatar_url ||
    null
  );
}
