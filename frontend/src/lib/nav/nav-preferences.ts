export type WorkspaceNavScope = "buyer" | "host" | "admin" | "support";

export type NavFavoritesState = {
  favorites: string[];
  pinned: string[];
};

export type NavCollapseState = Record<string, boolean>;

const COLLAPSE_PREFIX = "padeya:nav:collapse:";
const FAVORITES_PREFIX = "padeya:nav:favorites:";

const EMPTY_FAVORITES: NavFavoritesState = { favorites: [], pinned: [] };

export function workspaceNavScope(title: string): WorkspaceNavScope {
  const key = title.trim().toLowerCase();
  if (key === "host" || key.startsWith("host:")) return "host";
  if (key === "admin") return "admin";
  if (key === "support") return "support";
  // "Personal", "Buyer", and other personal-shell titles share buyer prefs.
  return "buyer";
}

export function navCollapseStorageKey(scope: WorkspaceNavScope): string {
  return `${COLLAPSE_PREFIX}${scope}`;
}

export function navFavoritesStorageKey(scope: WorkspaceNavScope): string {
  return `${FAVORITES_PREFIX}${scope}`;
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

function readJson<T>(key: string, fallback: T): T {
  if (!canUseStorage()) return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  if (!canUseStorage()) return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore quota / private mode
  }
}

export function readNavCollapseState(scope: WorkspaceNavScope): NavCollapseState {
  return readJson(navCollapseStorageKey(scope), {});
}

export function writeNavCollapseState(
  scope: WorkspaceNavScope,
  state: NavCollapseState,
): void {
  writeJson(navCollapseStorageKey(scope), state);
}

export function readNavFavoritesState(scope: WorkspaceNavScope): NavFavoritesState {
  const raw = readJson<Partial<NavFavoritesState>>(
    navFavoritesStorageKey(scope),
    EMPTY_FAVORITES,
  );
  return {
    favorites: Array.isArray(raw.favorites) ? raw.favorites : [],
    pinned: Array.isArray(raw.pinned) ? raw.pinned : [],
  };
}

export function writeNavFavoritesState(
  scope: WorkspaceNavScope,
  state: NavFavoritesState,
): void {
  writeJson(navFavoritesStorageKey(scope), state);
}
