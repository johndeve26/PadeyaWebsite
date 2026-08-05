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
  /** Stamps row is visually emphasized. */
  emphasize?: boolean;
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

export function fanOgDisplayName(
  page: Pick<FanPassportPublicPage, "display_name">,
): string {
  return truncateEllipsis(page.display_name, 35) || "Fan Passport";
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
  return truncateEllipsis(city, 25) || null;
}

export function fanOgBio(page: FanPassportPublicPage): string {
  const bio =
    page.tagline?.trim() ||
    page.bio?.trim() ||
    "Building their Fan Passport on Pàdéyá";
  return truncateEllipsis(bio, 100);
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

/**
 * Public Fan Passports present verified nightlife history in product UI.
 * Empty brand-new passports keep a neutral seal instead.
 */
export function fanOgShowVerified(page: FanPassportPublicPage): boolean {
  return (
    page.events_attended > 0 ||
    page.badges_earned_count > 0 ||
    page.is_superfan ||
    (page.badges?.length ?? 0) > 0
  );
}

export function fanOgStats(page: FanPassportPublicPage): FanOgStat[] {
  const stamps = page.badges_earned_count ?? 0;
  return [
    {
      key: "events",
      value: formatCompact(page.events_attended ?? 0),
      label:
        (page.events_attended ?? 0) === 1
          ? "EVENT ATTENDED"
          : "EVENTS ATTENDED",
    },
    {
      key: "hosts",
      value: formatCompact(page.hosts_followed ?? 0),
      label:
        (page.hosts_followed ?? 0) === 1
          ? "HOST FOLLOWED"
          : "HOSTS FOLLOWED",
    },
    {
      key: "stamps",
      value: formatCompact(stamps),
      label: stamps === 1 ? "STAMP EARNED" : "STAMPS EARNED",
      emphasize: true,
    },
  ];
}

export function fanOgStampChips(
  page: Pick<FanPassportPublicPage, "badges">,
): FanOgStampChip[] {
  const earned = (page.badges || []).filter((b) => b.earned !== false);
  return earned.slice(0, 5).map((badge, i) => fanOgStampChip(badge, i));
}

function fanOgStampChip(badge: FanBadge, index: number): FanOgStampChip {
  const name = truncateEllipsis(badge.name || "Stamp", 22) || "Stamp";
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
    `See ${name}'s verified nights, stamps, favourite scenes and Fan Passport on Pàdéyá.`,
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
