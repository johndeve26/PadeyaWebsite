"use client";

import { useSyncExternalStore } from "react";

import {
  getGa4MeasurementId,
  readAnalyticsConsent,
  writeAnalyticsConsent,
  type AnalyticsConsentState,
} from "@/lib/analytics-consent";
import { Button } from "@/components/ui";

function notifyConsentChange() {
  window.dispatchEvent(new Event("padeya-analytics-consent"));
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
 * Optional GA4 preference control on /cookies.
 * Hidden when GA is not configured. Does not gate first-party analytics.
 */
export function OptionalAnalyticsConsentControls() {
  const configured = Boolean(getGa4MeasurementId());
  const consent = useSyncExternalStore(
    subscribeConsent,
    getConsentSnapshot,
    getServerConsentSnapshot,
  );

  if (!configured) return null;

  const set = (next: AnalyticsConsentState) => {
    writeAnalyticsConsent(next);
    notifyConsentChange();
  };

  return (
    <div className="mt-4 space-y-3 rounded-[var(--radius-lg)] border border-border bg-card p-4">
      <p className="text-sm font-semibold text-foreground">
        Optional Google Analytics (GA4)
      </p>
      <p className="text-sm text-muted-foreground">
        First-party Pàdéyá product analytics stay on to operate the marketplace.
        GA4 is optional and loads only after you allow it.
      </p>
      <p className="text-xs text-muted-foreground">
        Current choice:{" "}
        <strong className="text-foreground">
          {consent === "granted"
            ? "Allowed"
            : consent === "denied"
              ? "Denied"
              : "Not decided"}
        </strong>
      </p>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant={consent === "granted" ? "primary" : "secondary"}
          onClick={() => set("granted")}
        >
          Allow GA4
        </Button>
        <Button
          type="button"
          size="sm"
          variant={consent === "denied" ? "primary" : "secondary"}
          onClick={() => set("denied")}
        >
          Deny GA4
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => set("unset")}>
          Reset
        </Button>
      </div>
    </div>
  );
}
