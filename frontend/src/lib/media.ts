import { getApiBaseUrl } from "@/lib/api-base";
import { LIVE_SITE_ORIGIN } from "@/lib/seo/env-policy";

const LOCALHOST_MEDIA_URL =
  /^https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?(\/(?:media|api\/v1\/messages\/attachments)\/.+)$/i;

function extractMediaPath(src: string): string | null {
  if (
    src.startsWith("/media/") ||
    src.startsWith("/api/v1/messages/attachments/")
  ) {
    return src;
  }
  const match = LOCALHOST_MEDIA_URL.exec(src);
  return match?.[1] ?? null;
}

/**
 * Force static demo assets onto the live brand origin.
 * DB/API may still contain padeya.smartlancedesigns.com/demo/... leftovers.
 */
export function enforcePadeyaDemoAssetUrl(src: string): string {
  const raw = src.trim();
  if (!raw) return raw;

  let candidate = raw;
  if (candidate.startsWith("//")) candidate = `https:${candidate}`;

  if (candidate.startsWith("/demo/")) {
    return `${LIVE_SITE_ORIGIN}${candidate}`;
  }

  if (!/^https?:\/\//i.test(candidate)) {
    return raw;
  }

  try {
    const url = new URL(candidate);
    const host = url.hostname.toLowerCase();
    const isSmartlance = host === "smartlancedesigns.com" || host.endsWith(".smartlancedesigns.com");
    const isPadeyaDemo =
      url.pathname.startsWith("/demo/") &&
      (host === "padeya.com" || host === "www.padeya.com" || isSmartlance);

    if (isSmartlance || isPadeyaDemo) {
      return `${LIVE_SITE_ORIGIN}${url.pathname}${url.search}`;
    }
  } catch {
    return raw;
  }

  return raw;
}

/**
 * Resolve API-hosted media paths for <img>/links in the Next app.
 * Supports public `/media/` and private attachment API paths (signed query OK).
 * Empty API base → same-origin (ngrok + Next rewrites).
 * Never leaves padeya.smartlancedesigns.com in the resolved URL.
 */
export function resolveMediaUrl(src?: string | null): string {
  if (!src) return "";
  const enforced = enforcePadeyaDemoAssetUrl(src);
  const path = extractMediaPath(enforced);
  if (path) {
    const base = getApiBaseUrl().replace(/\/$/, "");
    return `${base}${path}`;
  }
  return enforced;
}
