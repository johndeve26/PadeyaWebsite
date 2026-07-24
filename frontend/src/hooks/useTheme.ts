"use client";

import { useCallback, useContext, useMemo, useSyncExternalStore } from "react";

import { ThemeContext } from "@/components/theme/theme-context";
import {
  getServerThemeHydratedSnapshot,
  getServerThemeSnapshot,
  getThemeHydratedSnapshot,
  getThemeSnapshot,
  setThemePreference,
  subscribeTheme,
  THEME_OPTIONS,
  type ThemePreference,
  type ThemeState,
} from "@/lib/theme";

function useThemeStore(): ThemeState {
  return useSyncExternalStore(
    subscribeTheme,
    getThemeSnapshot,
    getServerThemeSnapshot,
  );
}

function useThemeHydrated(): boolean {
  return useSyncExternalStore(
    subscribeTheme,
    getThemeHydratedSnapshot,
    getServerThemeHydratedSnapshot,
  );
}

/**
 * Theme preference + resolved light/dark value.
 * Must be used under ThemeProvider (provider hydrates the store + OS listener).
 */
export function useTheme() {
  const inProvider = useContext(ThemeContext);
  if (!inProvider) {
    throw new Error("useTheme must be used within ThemeProvider");
  }

  const snapshot = useThemeStore();
  const mounted = useThemeHydrated();

  const setTheme = useCallback((next: ThemePreference) => {
    setThemePreference(next);
  }, []);

  const cycleTheme = useCallback(() => {
    const idx = THEME_OPTIONS.indexOf(snapshot.preference);
    const next = THEME_OPTIONS[(idx + 1) % THEME_OPTIONS.length]!;
    setThemePreference(next);
  }, [snapshot.preference]);

  return useMemo(
    () => ({
      theme: snapshot.preference,
      resolvedTheme: snapshot.resolved,
      setTheme,
      cycleTheme,
      mounted,
    }),
    [
      snapshot.preference,
      snapshot.resolved,
      setTheme,
      cycleTheme,
      mounted,
    ],
  );
}
