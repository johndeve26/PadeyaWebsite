"use client";

import { useEffect, type ReactNode } from "react";

import { ThemeContext } from "@/components/theme/theme-context";
import {
  hydrateThemeStore,
  rehydrateThemeStore,
  syncSystemPreference,
  THEME_STORAGE_KEY,
} from "@/lib/theme";

/**
 * Hydrates the theme store after mount and listens for OS scheme changes
 * when preference is "system". Visual theme is already applied by ThemeScript.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    hydrateThemeStore();

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onSchemeChange = () => {
      syncSystemPreference();
    };
    mq.addEventListener("change", onSchemeChange);

    const onStorage = (event: StorageEvent) => {
      if (event.key === null || event.key === THEME_STORAGE_KEY) {
        rehydrateThemeStore();
      }
    };
    window.addEventListener("storage", onStorage);

    return () => {
      mq.removeEventListener("change", onSchemeChange);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  return <ThemeContext.Provider value={true}>{children}</ThemeContext.Provider>;
}

/** @deprecated Prefer `@/hooks/useTheme` */
export { useTheme } from "@/hooks/useTheme";
