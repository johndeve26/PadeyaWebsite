/**
 * Shared helpers for public media sizing / next/image eligibility.
 * Keep presets aligned with real layout widths — do not invent "priority" here.
 */

export const MEDIA_SIZES = {
  /** Full-bleed heroes (event cover, host banner, sponsor cover). */
  hero: "100vw",
  /** Marketplace event cards (≈1 / 2 / 3 columns). */
  eventCard:
    "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw",
  /** Merch product hero (≈ half viewport on desktop). */
  merchHero: "(max-width: 1024px) 100vw, 50vw",
  merchCard: "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw",
  merchThumb: "64px",
  avatarLg: "160px",
  avatarMd: "112px",
  avatarSm: "48px",
  sponsorLogo: "112px",
  logo: "160px",
} as const;

export type MediaSizesPreset = keyof typeof MEDIA_SIZES;

/** Hosts Next/Image is allowed to optimize (no open wildcard). */
export const OPTIMIZABLE_MEDIA_HOSTS = [
  "padeya.com",
  "www.padeya.com",
  "padeyawebsite.onrender.com",
  "localhost",
  "127.0.0.1",
] as const;

export function isSvgMediaSrc(src: string): boolean {
  const path = src.split("?")[0]?.toLowerCase() ?? "";
  return path.endsWith(".svg") || path.includes("image/svg");
}

export function isOptimizableMediaSrc(src: string): boolean {
  if (!src || isSvgMediaSrc(src)) return false;
  if (src.startsWith("/")) {
    return (
      src.startsWith("/media/") ||
      src.startsWith("/brand/") ||
      src.startsWith("/demo/") ||
      src.startsWith("/icons/") ||
      src.startsWith("/images/")
    );
  }
  try {
    const url = new URL(src);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    return (OPTIMIZABLE_MEDIA_HOSTS as readonly string[]).includes(url.hostname);
  } catch {
    return false;
  }
}

export function resolveMediaSizes(
  sizes?: string | MediaSizesPreset,
): string | undefined {
  if (!sizes) return undefined;
  if (sizes in MEDIA_SIZES) {
    return MEDIA_SIZES[sizes as MediaSizesPreset];
  }
  return sizes;
}
