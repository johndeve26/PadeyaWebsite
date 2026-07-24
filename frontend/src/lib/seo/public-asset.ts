/** Resolve public media URLs for metadata / JSON-LD (never broken relative hosts). */

import { absoluteUrl } from "@/lib/seo/site";

const RETIRED_MEDIA_HOST =
  /^(?:https?:)?\/\/(?:[\w.-]+\.)?smartlancedesigns\.com/i;

/**
 * Prefer absolute https URLs. Relative app/media paths become padeya.com absolute
 * (production serves `/media` via same-origin rewrite).
 * Retired demo hosts are rewritten to the same path on padeya.com.
 */
export function resolvePublicAssetUrl(
  url: string | null | undefined,
): string | null {
  const raw = (url || "").trim();
  if (!raw) return null;

  let candidate = raw;
  if (candidate.startsWith("//")) candidate = `https:${candidate}`;

  if (RETIRED_MEDIA_HOST.test(candidate)) {
    try {
      const path = new URL(candidate).pathname || "/";
      return absoluteUrl(path);
    } catch {
      return null;
    }
  }

  if (/^https?:\/\//i.test(candidate)) return candidate;
  const path = candidate.startsWith("/") ? candidate : `/${candidate}`;
  return absoluteUrl(path);
}

/**
 * WhatsApp / iMessage / Facebook link previews reject SVG (and most vector)
 * OG images. Prefer raster formats only for social cards.
 */
export function isSocialPreviewSafeImage(url: string): boolean {
  try {
    const pathname = new URL(url, "https://padeya.com").pathname.toLowerCase();
    if (pathname.endsWith(".svg") || pathname.includes(".svg/")) return false;
    if (/\.(jpe?g|png|gif|webp|avif)(\?|$)/i.test(pathname)) return true;
    // Extensionless CDN /media paths are allowed; scrapers negotiate content-type.
    return !pathname.endsWith(".svg");
  } catch {
    return false;
  }
}

/** Resolve + social-preview safety. Returns null when missing or SVG/unsafe. */
export function resolveOgImageUrl(
  url: string | null | undefined,
): string | null {
  const resolved = resolvePublicAssetUrl(url);
  if (!resolved) return null;
  if (!isSocialPreviewSafeImage(resolved)) return null;
  return resolved;
}

/** Cover → avatar/logo → null (caller falls back to default OG). */
export function pickEntityOgImage(opts: {
  cover?: string | null;
  avatar?: string | null;
  logo?: string | null;
}): string | null {
  for (const candidate of [opts.cover, opts.avatar, opts.logo]) {
    const resolved = resolveOgImageUrl(candidate);
    if (resolved) return resolved;
  }
  return null;
}
