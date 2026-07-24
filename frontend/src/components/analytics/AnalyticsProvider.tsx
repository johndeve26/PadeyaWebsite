"use client";

import { useEffect, type ReactNode } from "react";

import { useUTMAttribution } from "@/hooks/useUTMAttribution";
import { flushAnalytics, initAnalytics } from "@/lib/analytics";

/** Bootstraps visitor IDs, UTM capture, and queue flush on hide. */
export function AnalyticsProvider({ children }: { children: ReactNode }) {
  useUTMAttribution();

  useEffect(() => {
    initAnalytics();
    return () => {
      flushAnalytics();
    };
  }, []);

  return <>{children}</>;
}
