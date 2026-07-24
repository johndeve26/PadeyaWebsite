/** Client-side JWT exp hint only — never trust for authorization. */

type JwtPayload = {
  exp?: number;
  iat?: number;
};

function decodeBase64Url(segment: string): string {
  const padded = segment.replace(/-/g, "+").replace(/_/g, "/");
  const pad = padded.length % 4 === 0 ? "" : "=".repeat(4 - (padded.length % 4));
  if (typeof atob === "undefined") return "";
  try {
    return atob(padded + pad);
  } catch {
    return "";
  }
}

export function readAccessTokenExpiry(accessToken: string | null): number | null {
  if (!accessToken) return null;
  const parts = accessToken.split(".");
  if (parts.length < 2) return null;
  try {
    const json = decodeBase64Url(parts[1]);
    if (!json) return null;
    const payload = JSON.parse(json) as JwtPayload;
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}

/** True when token is missing, unparsable, or past exp (with small clock skew). */
export function isAccessTokenExpired(
  accessToken: string | null,
  skewSeconds = 30,
): boolean {
  if (!accessToken) return true;
  const exp = readAccessTokenExpiry(accessToken);
  if (exp == null) return false;
  const now = Math.floor(Date.now() / 1000);
  return exp <= now + skewSeconds;
}

/** Refresh proactively before access token expires (default 2 minutes). */
export function shouldRefreshAccessToken(
  accessToken: string | null,
  withinSeconds = 120,
): boolean {
  if (!accessToken) return true;
  const exp = readAccessTokenExpiry(accessToken);
  if (exp == null) return false;
  const now = Math.floor(Date.now() / 1000);
  return exp - now <= withinSeconds;
}
