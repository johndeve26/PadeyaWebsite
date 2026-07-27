/**
 * Frontend-only presentation helpers for Legacy Page visuals.
 * No API contract changes.
 */

import { resolveMediaUrl } from "@/lib/media";

const EVENT_COVERS = [
  "/demo/events/detty-friday-live.svg",
  "/demo/events/afrobeats-night-live.svg",
  "/demo/events/mainland-vibes-summer.svg",
  "/demo/events/mainland-vibes-2025.svg",
  "/demo/events/pending-neon-nights.svg",
  "/demo/events/cancelled-beach-bash.svg",
  "/demo/events/draft-secret-session.svg",
  "/demo/events/rejected-stadium-show.svg",
  "/demo/events/lagos-comedy-jam.svg",
  "/demo/events/island-comedy-night.svg",
  "/demo/events/founders-mixer-lagos.svg",
  "/demo/events/product-builders-meetup.svg",
  "/demo/events/startup-demo-evening.svg",
  "/demo/events/worship-under-stars.svg",
  "/demo/events/praise-experience-live.svg",
  "/demo/events/food-and-flow.svg",
  "/demo/events/rooftop-games-night.svg",
  "/demo/events/sports-sunday.svg",
  "/demo/events/campus-fest-2026.svg",
  "/demo/events/art-walk-lagos.svg",
] as const;

/** Category → preferred demo covers (keeps fallbacks on-brand and less repetitive). */
const EVENT_COVERS_BY_CATEGORY: Record<string, readonly string[]> = {
  Music: [
    "/demo/events/afrobeats-night-live.svg",
    "/demo/events/detty-friday-live.svg",
    "/demo/events/mainland-vibes-summer.svg",
  ],
  Comedy: [
    "/demo/events/lagos-comedy-jam.svg",
    "/demo/events/island-comedy-night.svg",
  ],
  Tech: [
    "/demo/events/founders-mixer-lagos.svg",
    "/demo/events/product-builders-meetup.svg",
    "/demo/events/startup-demo-evening.svg",
  ],
  Faith: [
    "/demo/events/worship-under-stars.svg",
    "/demo/events/praise-experience-live.svg",
  ],
  Food: ["/demo/events/food-and-flow.svg"],
  Sports: [
    "/demo/events/sports-sunday.svg",
    "/demo/events/rooftop-games-night.svg",
  ],
  Arts: ["/demo/events/art-walk-lagos.svg"],
  Campus: ["/demo/events/campus-fest-2026.svg"],
  Events: EVENT_COVERS,
};

const HOST_COVERS: Record<string, { cover: string; avatar: string }> = {
  djmaze: {
    cover: "/demo/hosts/djmaze-cover.svg",
    avatar: "/demo/hosts/djmaze-avatar.svg",
  },
  lagoscomedyhub: {
    cover: "/demo/hosts/lagoscomedyhub-cover.svg",
    avatar: "/demo/hosts/lagoscomedyhub-avatar.svg",
  },
  mainlandvibes: {
    cover: "/demo/hosts/mainlandvibes-cover.svg",
    avatar: "/demo/hosts/mainlandvibes-avatar.svg",
  },
  techconnectafrica: {
    cover: "/demo/hosts/techconnectafrica-cover.svg",
    avatar: "/demo/hosts/techconnectafrica-avatar.svg",
  },
  praiseexperience: {
    cover: "/demo/hosts/praiseexperience-cover.svg",
    avatar: "/demo/hosts/praiseexperience-avatar.svg",
  },
};

function hash(input: string): number {
  let h = 0;
  for (let i = 0; i < input.length; i += 1) {
    h = (h * 31 + input.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function resolveHostMedia(
  username: string,
  coverUrl?: string | null,
  avatarUrl?: string | null,
) {
  const key = username.replace(/^@/, "").toLowerCase();
  const demo = HOST_COVERS[key];
  return {
    coverUrl: coverUrl || demo?.cover || null,
    avatarUrl: avatarUrl || demo?.avatar || null,
  };
}

export function resolveEventImage(
  slug: string,
  title: string,
  bannerUrl?: string | null,
  categoryHint?: string | null,
): string {
  if (bannerUrl) {
    // Enforce padeya.com for demo assets (never smartlancedesigns.com).
    return resolveMediaUrl(bannerUrl) || bannerUrl;
  }
  const normalized = slug.replace(/^demo-/, "").replace(/-gallery$/, "");
  const bySlug = EVENT_COVERS.find(
    (p) => p.endsWith(`/${normalized}.svg`) || p.includes(`/${normalized}`),
  );
  if (bySlug) return resolveMediaUrl(bySlug);
  const category = mapCategoryHint(categoryHint) || inferEventCategory(title, slug);
  const pool = EVENT_COVERS_BY_CATEGORY[category] ?? EVENT_COVERS;
  return resolveMediaUrl(pool[hash(`${slug}:${title}:${category}`) % pool.length]);
}

function mapCategoryHint(hint?: string | null): string | null {
  if (!hint) return null;
  const t = hint.toLowerCase();
  if (t.includes("comedy")) return "Comedy";
  if (t.includes("gospel") || t.includes("faith") || t.includes("worship"))
    return "Faith";
  if (t.includes("tech") || t.includes("business")) return "Tech";
  if (t.includes("food")) return "Food";
  if (t.includes("sport")) return "Sports";
  if (t.includes("art") || t.includes("culture")) return "Arts";
  if (t.includes("campus")) return "Campus";
  if (
    t.includes("music") ||
    t.includes("nightlife") ||
    t.includes("lifestyle")
  )
    return "Music";
  return null;
}

export function inferEventCategory(title: string, slug: string): string {
  const t = `${title} ${slug}`.toLowerCase();
  if (/comedy|open.?mic|laugh/.test(t)) return "Comedy";
  if (/worship|praise|gospel|faith/.test(t)) return "Faith";
  if (/tech|founder|startup|product|builder|meetup/.test(t)) return "Tech";
  if (/food|taste|culinary/.test(t)) return "Food";
  if (/sport|game|football/.test(t)) return "Sports";
  if (/art|gallery|walk/.test(t)) return "Arts";
  if (/campus|student/.test(t)) return "Campus";
  if (/afrobeats|dj|music|detty|night|vibes|concert/.test(t)) return "Music";
  return "Events";
}

export function formatLegacyDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function formatCompact(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}K`;
  return String(n);
}

export function reviewerInitials(name?: string | null): string {
  if (!name?.trim()) return "A";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

/** Normalize social platform keys for icon/label mapping (existing profile fields only). */
export function normalizeSocialPlatform(platform: string): string {
  const key = platform.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
  if (key === "twitter" || key === "xcom" || key === "xtwitter") return "x";
  if (key === "www" || key === "site" || key === "web") return "website";
  if (key === "yt" || key === "youtubemusic") return "youtube";
  if (key === "ig") return "instagram";
  if (key === "tt") return "tiktok";
  return key;
}

export function socialPlatformLabel(platform: string): string {
  const key = normalizeSocialPlatform(platform);
  const labels: Record<string, string> = {
    website: "Website",
    instagram: "Instagram",
    tiktok: "TikTok",
    x: "X",
    youtube: "YouTube",
    spotify: "Spotify",
    mixcloud: "Mixcloud",
    facebook: "Facebook",
    linkedin: "LinkedIn",
  };
  return labels[key] || platform;
}
