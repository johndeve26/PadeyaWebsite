"use client";

import { useEffect, useSyncExternalStore } from "react";

import {
  getGa4MeasurementId,
  readAnalyticsConsent,
  shouldLoadGa4,
  type AnalyticsConsentState,
} from "@/lib/analytics-consent";
import { isClientProductionSeoEnvironment } from "@/lib/seo/env-policy";

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

function subscribeConsent(onChange: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === "padeya_analytics_consent" || e.key === null) onChange();
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener("padeya-analytics-consent", onChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener("padeya-analytics-consent", onChange);
  };
}

function getConsentSnapshot(): AnalyticsConsentState {
  return readAnalyticsConsent();
}

function getServerConsentSnapshot(): AnalyticsConsentState {
  return "unset";
}

/**
 * Optional GA4 loader — only when measurement ID + production SEO + consent granted.
 * First-party AnalyticsProvider is independent.
 */
export function Ga4Script() {
  const consent = useSyncExternalStore(
    subscribeConsent,
    getConsentSnapshot,
    getServerConsentSnapshot,
  );
  const measurementId = getGa4MeasurementId();
  const isProductionSeo = isClientProductionSeoEnvironment();

  useEffect(() => {
    if (
      !shouldLoadGa4({
        measurementId,
        isProductionSeo,
        consent,
      })
    ) {
      return;
    }

    const id = measurementId!;
    if (document.getElementById("padeya-ga4")) return;

    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag(...args: unknown[]) {
      window.dataLayer?.push(args);
    };
    window.gtag("js", new Date());
    window.gtag("config", id, { anonymize_ip: true });

    const script = document.createElement("script");
    script.id = "padeya-ga4";
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    document.head.appendChild(script);
  }, [consent, measurementId, isProductionSeo]);

  return null;
}
