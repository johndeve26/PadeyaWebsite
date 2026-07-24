import { getApiBaseUrl } from "@/lib/api-base";

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
 * Resolve API-hosted media paths for <img>/links in the Next app.
 * Supports public `/media/` and private attachment API paths (signed query OK).
 * Empty API base → same-origin (ngrok + Next rewrites).
 */
export function resolveMediaUrl(src?: string | null): string {
  if (!src) return "";
  const path = extractMediaPath(src);
  if (path) {
    const base = getApiBaseUrl().replace(/\/$/, "");
    return `${base}${path}`;
  }
  return src;
}
