/**
 * Same-origin push deep-link validation (mirrors public/sw.js safeActionUrl).
 * Never allow external / javascript: destinations from push payloads.
 */

export const DEFAULT_PUSH_ACTION = "/dashboard/notifications";

export function safePushActionUrl(
  value: unknown,
  origin = "https://padeya.com",
  defaultPath = DEFAULT_PUSH_ACTION,
): string {
  try {
    const raw = String(value || defaultPath).trim();
    if (!raw || raw.startsWith("javascript:") || raw.startsWith("data:")) {
      return defaultPath;
    }
    const url = new URL(raw, origin);
    if (url.origin !== new URL(origin).origin) return defaultPath;
    if (/\/(vault|checkout)(\/|$)/i.test(url.pathname)) return defaultPath;
    const path = `${url.pathname}${url.search}${url.hash}`;
    return path || defaultPath;
  } catch {
    return defaultPath;
  }
}
