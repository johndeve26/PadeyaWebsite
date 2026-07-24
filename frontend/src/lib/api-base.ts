/**
 * Resolve the API origin for browser vs server.
 *
 * When NEXT_PUBLIC_API_URL is empty, the browser uses same-origin paths
 * (so one ngrok frontend tunnel can reach the API via Next rewrites).
 * Server/RSC still talks to the local backend directly.
 */
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") return "";
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
