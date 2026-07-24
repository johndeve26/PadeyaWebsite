/** Resolve public media URLs for metadata / JSON-LD (never broken relative hosts). */

import { absoluteUrl } from "@/lib/seo/site";

/**
 * Prefer absolute https URLs. Relative app/media paths become padeya.com absolute
 * (production serves `/media` via same-origin rewrite).
 */
export function resolvePublicAssetUrl(
  url: string | null | undefined,
): string | null {
  const raw = (url || "").trim();
  if (!raw) return null;
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith("//")) return `https:${raw}`;
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  return absoluteUrl(path);
}

/** Cover → avatar/logo → default OG. */
export function pickEntityOgImage(opts: {
  cover?: string | null;
  avatar?: string | null;
  logo?: string | null;
}): string | null {
  return (
    resolvePublicAssetUrl(opts.cover) ||
    resolvePublicAssetUrl(opts.avatar) ||
    resolvePublicAssetUrl(opts.logo)
  );
}
