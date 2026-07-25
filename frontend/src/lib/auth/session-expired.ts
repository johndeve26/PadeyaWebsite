const SESSION_EXPIRED_KEY = "padeya.auth.session_expired_message";

/** Dispatched when refresh fails and local tokens are cleared — AuthProvider must drop `user`. */
export const SESSION_EXPIRED_EVENT = "padeya:session-expired";

export const DEFAULT_SESSION_EXPIRED_MESSAGE =
  "Your session has expired. Please log in again.";

export function markSessionExpired(
  message: string = DEFAULT_SESSION_EXPIRED_MESSAGE,
): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(SESSION_EXPIRED_KEY, message);
  } catch {
    /* ignore */
  }
  try {
    window.dispatchEvent(
      new CustomEvent(SESSION_EXPIRED_EVENT, { detail: { message } }),
    );
  } catch {
    /* ignore */
  }
}

export function consumeSessionExpiredMessage(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_EXPIRED_KEY);
    sessionStorage.removeItem(SESSION_EXPIRED_KEY);
    return raw?.trim() || null;
  } catch {
    return null;
  }
}

export function peekSessionExpiredMessage(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_EXPIRED_KEY);
    return raw?.trim() || null;
  } catch {
    return null;
  }
}
