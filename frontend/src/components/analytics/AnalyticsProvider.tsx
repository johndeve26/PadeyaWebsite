"use client";

import { useEffect, type ReactNode } from "react";

import { Ga4Script } from "@/components/analytics/Ga4Script";
import { useUTMAttribution } from "@/hooks/useUTMAttribution";
import { flushAnalytics, initAnalytics } from "@/lib/analytics";

/** Bootstraps visitor IDs, UTM capture, queue flush, and optional consent-gated GA4. */
export function AnalyticsProvider({ children }: { children: ReactNode }) {
  useUTMAttribution();

  useEffect(() => {
    initAnalytics();
    return () => {
      flushAnalytics();
    };
  }, []);

  return (
    <>
      <Ga4Script />
      {children}
    </>
  );
}
