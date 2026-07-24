export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "padeya-theme";

export const THEME_OPTIONS: readonly ThemePreference[] = [
  "light",
  "dark",
  "system",
] as const;

export const THEME_LABELS: Record<ThemePreference, string> = {
  light: "Light",
  dark: "Dark",
  system: "System",
};

/** Browser chrome / PWA status bar colors */
export const THEME_COLOR: Record<ResolvedTheme, string> = {
  light: "#ffffff",
  dark: "#0a0a0a",
};

export type ThemeState = {
  preference: ThemePreference;
  resolved: ResolvedTheme;
};

const DEFAULT_STATE: ThemeState = {
  preference: "system",
  resolved: "light",
};

let state: ThemeState = DEFAULT_STATE;
let hydrated = false;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

export function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  return preference === "system" ? getSystemTheme() : preference;
}

export function readStoredPreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

/** Sync browser / PWA chrome color with the resolved theme (all theme-color metas). */
export function applyThemeColor(resolved: ResolvedTheme) {
  if (typeof document === "undefined") return;
  const color = THEME_COLOR[resolved];
  const metas = document.querySelectorAll('meta[name="theme-color"]');
  if (metas.length === 0) {
    const meta = document.createElement("meta");
    meta.setAttribute("name", "theme-color");
    meta.setAttribute("content", color);
    document.head.appendChild(meta);
    return;
  }
  metas.forEach((meta) => {
    meta.setAttribute("content", color);
  });
}

export function applyThemeToDocument(resolved: ResolvedTheme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
  applyThemeColor(resolved);
}

export function subscribeTheme(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Client snapshot — stable default until hydrateThemeStore runs. */
export function getThemeSnapshot(): ThemeState {
  return state;
}

/** Server / SSR snapshot — must match the first client render. */
export function getServerThemeSnapshot(): ThemeState {
  return DEFAULT_STATE;
}

export function getThemeHydratedSnapshot(): boolean {
  return hydrated;
}

export function getServerThemeHydratedSnapshot(): boolean {
  return false;
}

function readThemeStateFromEnvironment(): ThemeState {
  const preference = readStoredPreference();
  const fromDom = document.documentElement.classList.contains("dark")
    ? "dark"
    : "light";
  const resolved =
    preference === "system" ? fromDom : resolveTheme(preference);
  return { preference, resolved };
}

/**
 * Sync React store from localStorage + DOM class set by ThemeScript.
 * Safe to call once after mount; use `rehydrateThemeStore` for cross-tab sync.
 */
export function hydrateThemeStore() {
  if (typeof window === "undefined" || hydrated) return;
  hydrated = true;
  state = readThemeStateFromEnvironment();
  applyThemeToDocument(state.resolved);
  emit();
}

/** Re-read preference (e.g. storage event from another tab). */
export function rehydrateThemeStore() {
  if (typeof window === "undefined") return;
  hydrated = true;
  state = readThemeStateFromEnvironment();
  applyThemeToDocument(state.resolved);
  emit();
}

export function setThemePreference(preference: ThemePreference) {
  const resolved = resolveTheme(preference);
  state = { preference, resolved };
  try {
    localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    /* private mode / blocked storage */
  }
  applyThemeToDocument(resolved);
  emit();
}

/** Keep system mode in sync when OS preference changes. */
export function syncSystemPreference() {
  if (state.preference !== "system") return;
  const resolved = getSystemTheme();
  if (resolved === state.resolved) return;
  state = { preference: "system", resolved };
  applyThemeToDocument(resolved);
  emit();
}

/**
 * Inline script — runs before paint so the first frame matches the
 * user's stored preference (or system). Keep in sync with ThemeScript.
 */
export const themeInitScript = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var t=localStorage.getItem(k);var d=window.matchMedia("(prefers-color-scheme: dark)").matches;var dark=t==="dark"||(t!=="light"&&d);var r=document.documentElement;r.classList.toggle("dark",dark);r.style.colorScheme=dark?"dark":"light";var c=dark?${JSON.stringify(THEME_COLOR.dark)}:${JSON.stringify(THEME_COLOR.light)};var ms=document.querySelectorAll('meta[name="theme-color"]');if(ms.length){for(var i=0;i<ms.length;i++)ms[i].setAttribute("content",c);}else{var m=document.createElement("meta");m.setAttribute("name","theme-color");m.setAttribute("content",c);document.head.appendChild(m);}}catch(e){}})();`;
