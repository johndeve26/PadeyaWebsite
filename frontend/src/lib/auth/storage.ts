import type { AuthTokens } from "@/lib/auth/types";
import {
  clearAuthSessionMeta,
  recordLoginTimestamp,
  recordRefreshTimestamp,
} from "@/lib/auth/session-meta";

const ACCESS_KEY = "padeya.access_token";
const REFRESH_KEY = "padeya.refresh_token";
const ADMIN_ACCESS_KEY = "padeya.admin_access_token";
const ADMIN_REFRESH_KEY = "padeya.admin_refresh_token";
const IMPERSONATION_FLAG = "padeya.impersonating";

const AUTH_KEYS = [
  ACCESS_KEY,
  REFRESH_KEY,
  ADMIN_ACCESS_KEY,
  ADMIN_REFRESH_KEY,
  IMPERSONATION_FLAG,
] as const;

function canUseStorage(): boolean {
  return typeof window !== "undefined";
}

/** Prefer localStorage so login survives tab/browser restarts. */
function store(): Storage | null {
  if (!canUseStorage()) return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/**
 * One-time migrate sessionStorage → localStorage so an open tab keeps its
 * session after this change ships.
 */
function migrateFromSessionStorage(): void {
  if (!canUseStorage()) return;
  const local = store();
  if (!local) return;
  try {
    for (const key of AUTH_KEYS) {
      if (local.getItem(key)) continue;
      const legacy = window.sessionStorage.getItem(key);
      if (legacy != null) {
        local.setItem(key, legacy);
        window.sessionStorage.removeItem(key);
      }
    }
  } catch {
    // Private mode / blocked storage — ignore.
  }
}

let migrated = false;
function ensureMigrated(): Storage | null {
  if (!migrated) {
    migrateFromSessionStorage();
    migrated = true;
  }
  return store();
}

function removeFromBoth(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

export function getAccessToken(): string | null {
  return ensureMigrated()?.getItem(ACCESS_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  return ensureMigrated()?.getItem(REFRESH_KEY) ?? null;
}

function invalidateHostWorkspacesCacheLazy(): void {
  void import("@/lib/hosts-api")
    .then((m) => m.invalidateHostWorkspacesCache())
    .catch(() => {
      /* ignore */
    });
}

export function setTokens(tokens: AuthTokens): void {
  const s = ensureMigrated();
  if (!s) return;
  s.setItem(ACCESS_KEY, tokens.access_token);
  s.setItem(REFRESH_KEY, tokens.refresh_token);
  recordRefreshTimestamp();
  invalidateHostWorkspacesCacheLazy();
  // Drop any leftover sessionStorage copies.
  try {
    window.sessionStorage.removeItem(ACCESS_KEY);
    window.sessionStorage.removeItem(REFRESH_KEY);
  } catch {
    /* ignore */
  }
}

export function clearTokens(): void {
  if (!canUseStorage()) return;
  removeFromBoth(ACCESS_KEY);
  removeFromBoth(REFRESH_KEY);
  clearAuthSessionMeta();
  invalidateHostWorkspacesCacheLazy();
}

export function hasStoredSession(): boolean {
  return Boolean(getAccessToken() || getRefreshToken());
}

/** Stash the real admin session before swapping in an impersonation access token. */
export function stashAdminTokens(): void {
  const s = ensureMigrated();
  if (!s) return;
  const access = getAccessToken();
  const refresh = getRefreshToken();
  if (access) s.setItem(ADMIN_ACCESS_KEY, access);
  if (refresh) s.setItem(ADMIN_REFRESH_KEY, refresh);
  s.setItem(IMPERSONATION_FLAG, "1");
}

export function isImpersonationSession(): boolean {
  return ensureMigrated()?.getItem(IMPERSONATION_FLAG) === "1";
}

/** Restore the stashed admin session after ending impersonation. */
export function restoreAdminTokens(): AuthTokens | null {
  const s = ensureMigrated();
  if (!s) return null;
  const access = s.getItem(ADMIN_ACCESS_KEY);
  const refresh = s.getItem(ADMIN_REFRESH_KEY);
  removeFromBoth(ADMIN_ACCESS_KEY);
  removeFromBoth(ADMIN_REFRESH_KEY);
  removeFromBoth(IMPERSONATION_FLAG);
  if (!access || !refresh) {
    clearTokens();
    return null;
  }
  const tokens: AuthTokens = {
    access_token: access,
    refresh_token: refresh,
    token_type: "bearer",
  };
  setTokens(tokens);
  return tokens;
}

/** Set impersonation access token only (no refresh — not a real user login). */
export function setImpersonationAccessToken(accessToken: string): void {
  const s = ensureMigrated();
  if (!s) return;
  s.setItem(ACCESS_KEY, accessToken);
  removeFromBoth(REFRESH_KEY);
  s.setItem(IMPERSONATION_FLAG, "1");
}

export function recordAuthLogin(): void {
  recordLoginTimestamp();
  recordRefreshTimestamp();
}

export function clearImpersonationStash(): void {
  if (!canUseStorage()) return;
  removeFromBoth(ADMIN_ACCESS_KEY);
  removeFromBoth(ADMIN_REFRESH_KEY);
  removeFromBoth(IMPERSONATION_FLAG);
}
