const DEVICE_ID_KEY = "padeya.auth.device_id";
const LAST_LOGIN_KEY = "padeya.auth.last_login_at";
const LAST_REFRESH_KEY = "padeya.auth.last_refreshed_at";

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `d${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

export function getOrCreateDeviceId(): string {
  const store = storage();
  if (!store) return randomId();
  const existing = store.getItem(DEVICE_ID_KEY);
  if (existing) return existing;
  const id = randomId();
  store.setItem(DEVICE_ID_KEY, id);
  return id;
}

export function recordLoginTimestamp(): void {
  const store = storage();
  if (!store) return;
  store.setItem(LAST_LOGIN_KEY, new Date().toISOString());
}

export function recordRefreshTimestamp(): void {
  const store = storage();
  if (!store) return;
  store.setItem(LAST_REFRESH_KEY, new Date().toISOString());
}

export function readAuthSessionMeta(): {
  deviceId: string | null;
  lastLoginAt: string | null;
  lastRefreshedAt: string | null;
} {
  const store = storage();
  if (!store) {
    return { deviceId: null, lastLoginAt: null, lastRefreshedAt: null };
  }
  return {
    deviceId: store.getItem(DEVICE_ID_KEY),
    lastLoginAt: store.getItem(LAST_LOGIN_KEY),
    lastRefreshedAt: store.getItem(LAST_REFRESH_KEY),
  };
}

export function clearAuthSessionMeta(): void {
  const store = storage();
  if (!store) return;
  store.removeItem(LAST_LOGIN_KEY);
  store.removeItem(LAST_REFRESH_KEY);
}
