/**
 * Theme / dark-mode smoke checks — no browser / React test runner required.
 * Mirrors project pattern of pwa-smoke / discovery-smoke.
 * Run: npm run test:theme
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

const THEME_STORAGE_KEY = "padeya-theme";
const THEME_OPTIONS = ["light", "dark", "system"];
const THEME_COLOR = { light: "#ffffff", dark: "#0a0a0a" };

/** Mirror of resolveTheme + getSystemTheme contract from lib/theme.ts */
function resolveTheme(preference, systemTheme) {
  return preference === "system" ? systemTheme : preference;
}

function cycleTheme(preference) {
  const idx = THEME_OPTIONS.indexOf(preference);
  return THEME_OPTIONS[(idx + 1) % THEME_OPTIONS.length];
}

function isThemePreference(value) {
  return value === "light" || value === "dark" || value === "system";
}

// --- Files exist ---
for (const rel of [
  "src/lib/theme.ts",
  "src/hooks/useTheme.ts",
  "src/components/theme/ThemeProvider.tsx",
  "src/components/theme/ThemeToggle.tsx",
  "src/components/theme/ThemeScript.tsx",
  "src/components/theme/ThemeAppearanceCard.tsx",
  "src/components/theme/theme-context.tsx",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const themeLib = read("src/lib/theme.ts");
const provider = read("src/components/theme/ThemeProvider.tsx");
const toggle = read("src/components/theme/ThemeToggle.tsx");
const script = read("src/components/theme/ThemeScript.tsx");
const appearance = read("src/components/theme/ThemeAppearanceCard.tsx");
const useTheme = read("src/hooks/useTheme.ts");
const layout = read("src/app/layout.tsx");
const globals = read("src/styles/globals.css");
const tailwindTheme = read("src/styles/tailwind-theme.css");

// --- ThemeProvider wired + renders children ---
assert.match(provider, /export function ThemeProvider/);
assert.match(provider, /ThemeContext\.Provider/);
assert.match(provider, /\{children\}/);
assert.match(provider, /hydrateThemeStore/);
assert.match(provider, /syncSystemPreference/);
assert.match(provider, /THEME_STORAGE_KEY/);
assert.match(layout, /ThemeProvider/);
assert.match(layout, /ThemeScript/);
assert.match(layout, /suppressHydrationWarning/);

// --- ThemeToggle changes theme ---
assert.match(toggle, /export function ThemeToggle/);
assert.match(toggle, /cycleTheme|setTheme/);
assert.match(toggle, /variant === "segmented"/);
assert.match(useTheme, /setThemePreference/);
assert.match(useTheme, /THEME_OPTIONS/);
assert.match(useTheme, /useSyncExternalStore/);
assert.match(useTheme, /getServerThemeSnapshot/);

// --- Persistence contract in source ---
assert.match(themeLib, /THEME_STORAGE_KEY = "padeya-theme"/);
assert.match(themeLib, /localStorage\.setItem\(THEME_STORAGE_KEY/);
assert.match(themeLib, /localStorage\.getItem\(THEME_STORAGE_KEY\)/);
assert.match(themeLib, /export function setThemePreference/);
assert.match(themeLib, /export function readStoredPreference/);

// --- System mode does not crash (handlers present) ---
assert.match(themeLib, /prefers-color-scheme: dark/);
assert.match(themeLib, /export function syncSystemPreference/);
assert.match(themeLib, /preference !== "system"/);
assert.match(provider, /matchMedia\("\(prefers-color-scheme: dark\)"\)/);
assert.match(provider, /addEventListener\("change"/);
assert.match(themeLib, /preference === "system"/);

// --- Hydration safety ---
assert.match(themeLib, /getServerThemeSnapshot/);
assert.match(themeLib, /themeInitScript/);
assert.match(script, /themeInitScript/);
assert.match(script, /dangerouslySetInnerHTML|beforeInteractive|id="padeya-theme-script"/);
assert.match(useTheme, /getServerThemeHydratedSnapshot/);
assert.match(useTheme, /mounted/);

// --- Token / class architecture ---
assert.match(globals, /\.dark\s*\{/);
assert.match(globals, /--background:/);
assert.match(tailwindTheme, /@custom-variant dark/);
assert.match(themeLib, /classList\.toggle\("dark"/);
assert.match(themeLib, /THEME_COLOR/);
assert.equal(THEME_COLOR.light, "#ffffff");
assert.equal(THEME_COLOR.dark, "#0a0a0a");
assert.match(themeLib, /#ffffff/);
assert.match(themeLib, /#0a0a0a/);

// --- No light-on-lime anti-pattern (bg-accent + text-foreground) ---
function walkTsx(dir, files = []) {
  for (const ent of fs.readdirSync(path.join(root, dir), { withFileTypes: true })) {
    const rel = path.join(dir, ent.name);
    if (ent.isDirectory()) walkTsx(rel, files);
    else if (/\.tsx?$/.test(ent.name)) files.push(rel);
  }
  return files;
}
const limeOnLight = [];
for (const rel of walkTsx("src")) {
  const t = read(rel);
  // Solid lime fill + theme foreground (light in dark mode). Allow washes (bg-accent/15)
  // and muted defaults (text-foreground/40) when hover uses text-primary-foreground.
  const hits = t.match(
    /[^\n]*\bbg-accent(?!\/)[^\n]{0,120}\btext-foreground(?!\/)[^\n]*|[^\n]*\btext-foreground(?!\/)[^\n]{0,120}\bbg-accent(?!\/)[^\n]*/g,
  );
  if (hits) {
    for (const h of hits) {
      if (/\btext-primary-foreground\b/.test(h) || /\btext-ink\b/.test(h)) continue;
      limeOnLight.push(`${rel}: ${h.trim().slice(0, 120)}`);
    }
  }
}
assert.equal(
  limeOnLight.length,
  0,
  `bg-accent + text-foreground is unreadable in dark mode (use text-primary-foreground):\n${limeOnLight.join("\n")}`,
);

// --- Settings Appearance surfaces ---
assert.match(appearance, /ThemeToggle/);
assert.match(appearance, /variant="segmented"/);
assert.ok(exists("src/app/dashboard/settings/page.tsx"));
assert.ok(exists("src/app/host/settings/page.tsx"));
assert.match(read("src/app/dashboard/settings/page.tsx"), /ThemeAppearanceCard/);
assert.match(read("src/app/host/settings/page.tsx"), /ThemeAppearanceCard/);

// --- Pure logic: resolve + cycle (ThemeToggle path) ---
assert.equal(resolveTheme("light", "dark"), "light");
assert.equal(resolveTheme("dark", "light"), "dark");
assert.equal(resolveTheme("system", "dark"), "dark");
assert.equal(resolveTheme("system", "light"), "light");
assert.equal(cycleTheme("light"), "dark");
assert.equal(cycleTheme("dark"), "system");
assert.equal(cycleTheme("system"), "light");
assert.ok(isThemePreference("system"));
assert.equal(isThemePreference("neon"), false);

// --- Runtime: preference persists to localStorage (mock DOM) ---
const store = new Map();
const classList = new Set();
const metas = [];

const fakeWindow = {
  matchMedia(query) {
    const dark = query.includes("prefers-color-scheme: dark");
    return {
      matches: dark ? false : false, // system = light in this fixture
      addEventListener() {},
      removeEventListener() {},
    };
  },
  localStorage: {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(key, String(value));
    },
  },
};

const fakeDocument = {
  documentElement: {
    classList: {
      contains(name) {
        return classList.has(name);
      },
      toggle(name, force) {
        if (force) classList.add(name);
        else classList.delete(name);
      },
    },
    style: { colorScheme: "light" },
  },
  head: {
    appendChild(node) {
      metas.push(node);
    },
  },
  querySelectorAll(sel) {
    if (sel === 'meta[name="theme-color"]') return metas;
    return [];
  },
  createElement(tag) {
    return {
      tagName: tag,
      setAttribute(k, v) {
        this[k] = v;
      },
    };
  },
};

/** Minimal mirror of setThemePreference + applyThemeToDocument */
function setThemePreferenceMock(preference) {
  const system = fakeWindow.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
  const resolved = resolveTheme(preference, system);
  fakeWindow.localStorage.setItem(THEME_STORAGE_KEY, preference);
  fakeDocument.documentElement.classList.toggle("dark", resolved === "dark");
  fakeDocument.documentElement.style.colorScheme = resolved;
  return { preference, resolved };
}

let next = setThemePreferenceMock("dark");
assert.equal(next.preference, "dark");
assert.equal(next.resolved, "dark");
assert.equal(store.get(THEME_STORAGE_KEY), "dark");
assert.ok(classList.has("dark"));

next = setThemePreferenceMock("light");
assert.equal(store.get(THEME_STORAGE_KEY), "light");
assert.ok(!classList.has("dark"));

next = setThemePreferenceMock("system");
assert.equal(store.get(THEME_STORAGE_KEY), "system");
assert.equal(next.resolved, "light");
assert.ok(!classList.has("dark"));

// --- Runtime: FOUC init script (same contract as themeInitScript) ---
assert.match(themeLib, /export const themeInitScript/);
assert.match(themeLib, /localStorage\.getItem\(k\)/);
assert.match(themeLib, /prefers-color-scheme: dark/);
assert.match(themeLib, /classList\.toggle\("dark"/);
assert.match(themeLib, /meta\[name="theme-color"\]/);

/** Rebuilt to match lib/theme.ts themeInitScript interpolation. */
const themeInitScript = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var t=localStorage.getItem(k);var d=window.matchMedia("(prefers-color-scheme: dark)").matches;var dark=t==="dark"||(t!=="light"&&d);var r=document.documentElement;r.classList.toggle("dark",dark);r.style.colorScheme=dark?"dark":"light";var c=dark?${JSON.stringify(THEME_COLOR.dark)}:${JSON.stringify(THEME_COLOR.light)};var ms=document.querySelectorAll('meta[name="theme-color"]');if(ms.length){for(var i=0;i<ms.length;i++)ms[i].setAttribute("content",c);}else{var m=document.createElement("meta");m.setAttribute("name","theme-color");m.setAttribute("content",c);document.head.appendChild(m);}}catch(e){}})();`;

function runInitScript(stored, systemDark) {
  store.clear();
  classList.clear();
  metas.length = 0;
  if (stored != null) store.set(THEME_STORAGE_KEY, stored);

  const localStorage = fakeWindow.localStorage;
  const windowObj = {
    matchMedia(query) {
      return {
        matches: query.includes("prefers-color-scheme: dark")
          ? systemDark
          : !systemDark,
      };
    },
    localStorage,
  };

  assert.doesNotThrow(() => {
    vm.runInNewContext(themeInitScript, {
      window: windowObj,
      document: fakeDocument,
      localStorage,
    });
  }, `themeInitScript threw (stored=${stored}, systemDark=${systemDark})`);
}

runInitScript(null, true);
assert.ok(classList.has("dark"), "system dark should set .dark");

runInitScript("light", true);
assert.ok(!classList.has("dark"), "explicit light overrides system dark");

runInitScript("dark", false);
assert.ok(classList.has("dark"), "explicit dark overrides system light");

runInitScript("system", false);
assert.ok(!classList.has("dark"), "system + light OS stays light");

console.log("Theme smoke checks passed:");
console.log("  ✓ ThemeProvider / ThemeToggle / ThemeScript present + wired");
console.log("  ✓ preference persists to padeya-theme localStorage (mock)");
console.log("  ✓ ThemeToggle cycle light → dark → system");
console.log("  ✓ system mode resolve + init script do not crash");
console.log("  ✓ hydration-safe SSR snapshot + suppressHydrationWarning");
console.log("  ✓ Appearance on dashboard + host settings");
