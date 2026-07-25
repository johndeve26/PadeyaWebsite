import { getAccessToken } from "@/lib/auth/storage";

/**
 * Unread chrome polls must not run without a bearer token.
 * Prevents 401 storms after session expiry clears tokens but React user lags.
 */
export function canPollAuthenticatedChrome(): boolean {
  return Boolean(getAccessToken());
}
