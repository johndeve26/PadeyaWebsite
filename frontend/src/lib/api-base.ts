/**
 * Resolve the API origin for browser vs server.
 *
 * When NEXT_PUBLIC_API_URL is empty, the browser uses same-origin paths
 * (so one ngrok frontend tunnel can reach the API via Next rewrites).
 * On the live padeya.com site, same-origin rewrites are not reliable in
 * production — fall back to the public API origin instead.
 * Server/RSC still talks to the local backend directly.
 */
import { LIVE_SITE_HOST } from "@/lib/seo/env-policy";

/** Public API origin for the live site when build-time env is missing. */
export const LIVE_API_ORIGIN = (
  process.env.NEXT_PUBLIC_LIVE_API_URL?.trim() ||
  "https://padeyawebsite.onrender.com"
).replace(/\/$/, "");

function productionBrowserApiOrigin(): string | null {
  if (typeof window === "undefined") return null;
  const host = window.location.hostname.toLowerCase();
  if (host === LIVE_SITE_HOST || host === `www.${LIVE_SITE_HOST}`) {
    return LIVE_API_ORIGIN;
  }
  return null;
}

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") {
    return productionBrowserApiOrigin() ?? "";
  }
  return (process.env.API_PROXY_TARGET || "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function getApiPrefix(): string {
  return process.env.NEXT_PUBLIC_API_PREFIX ?? "/api/v1";
}

/** WebSocket origin (browser only). */
export function getApiWsBaseUrl(): string {
  const http = getApiBaseUrl() || (typeof window !== "undefined" ? window.location.origin : "");
  return http.replace(/^http/i, "ws");
}
