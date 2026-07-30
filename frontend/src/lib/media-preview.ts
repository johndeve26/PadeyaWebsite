/**
 * Allowlisted public media URLs safe to proxy for browser inline preview.
 */

import { OPTIMIZABLE_MEDIA_HOSTS } from "@/lib/media-image";

const IMAGE_EXT = /\.(jpe?g|png|webp|gif|svg)(?:$|\?)/i;

export function isAllowedInlinePreviewUrl(raw: string): boolean {
  const cleaned = raw.trim();
  if (!cleaned) return false;

  if (cleaned.startsWith("/media/")) {
    return IMAGE_EXT.test(cleaned);
  }

  try {
    const url = new URL(cleaned);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    if (!(OPTIMIZABLE_MEDIA_HOSTS as readonly string[]).includes(url.hostname)) {
      return false;
    }
    if (url.hostname === "localhost" || url.hostname === "127.0.0.1") {
      return url.pathname.startsWith("/media/") && IMAGE_EXT.test(url.pathname);
    }
    // CDN keys are under folders; require an image extension on the path.
    return IMAGE_EXT.test(url.pathname);
  } catch {
    return false;
  }
}

export function guessImageContentType(pathOrUrl: string): string {
  const path = pathOrUrl.split("?")[0]?.toLowerCase() ?? "";
  if (path.endsWith(".png")) return "image/png";
  if (path.endsWith(".webp")) return "image/webp";
  if (path.endsWith(".gif")) return "image/gif";
  if (path.endsWith(".svg")) return "image/svg+xml";
  return "image/jpeg";
}

/** Same-origin preview URL that forces Content-Disposition: inline. */
export function inlineMediaPreviewHref(src: string): string {
  return `/api/media-preview?url=${encodeURIComponent(src.trim())}`;
}

/**
 * Open a public image in a new tab via the inline preview proxy.
 * Falls back to the raw URL when the source is not allowlisted.
 */
export function openPublicMediaInNewTab(src: string): void {
  const cleaned = src.trim();
  if (!cleaned) return;
  const href = isAllowedInlinePreviewUrl(cleaned)
    ? inlineMediaPreviewHref(cleaned)
    : cleaned;
  window.open(href, "_blank", "noopener,noreferrer");
}
