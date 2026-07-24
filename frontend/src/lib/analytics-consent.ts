/**
 * Optional third-party analytics consent (GA4).
 *
 * First-party Pàdéyá analytics (AnalyticsProvider → /analytics/track*) are
 * product analytics and are not gated by this preference.
 *
 * GA4 loads only when:
 * - NEXT_PUBLIC_GA_MEASUREMENT_ID is set
 * - production SEO environment (shouldIndexEnvironment / production signals)
 * - consent is explicitly "granted"
 */

export type AnalyticsConsentState = "granted" | "denied" | "unset";

export const ANALYTICS_CONSENT_STORAGE_KEY = "padeya_analytics_consent";

export function normalizeAnalyticsConsent(
  value: string | null | undefined,
): AnalyticsConsentState {
  const v = (value || "").trim().toLowerCase();
  if (v === "granted" || v === "denied") return v;
  return "unset";
}

export function readAnalyticsConsent(
  storage?: Pick<Storage, "getItem"> | null,
): AnalyticsConsentState {
  if (typeof window === "undefined" && !storage) return "unset";
  try {
    const store = storage ?? window.localStorage;
    return normalizeAnalyticsConsent(store.getItem(ANALYTICS_CONSENT_STORAGE_KEY));
  } catch {
    return "unset";
  }
}

export function writeAnalyticsConsent(
  state: AnalyticsConsentState,
  storage?: Pick<Storage, "setItem" | "removeItem"> | null,
): void {
  if (typeof window === "undefined" && !storage) return;
  try {
    const store = storage ?? window.localStorage;
    if (state === "unset") {
      store.removeItem(ANALYTICS_CONSENT_STORAGE_KEY);
      return;
    }
    store.setItem(ANALYTICS_CONSENT_STORAGE_KEY, state);
  } catch {
    /* private mode / blocked storage */
  }
}

export function isGa4Configured(
  measurementId: string | null | undefined = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID,
): boolean {
  const id = (measurementId || "").trim();
  return /^G-[A-Z0-9]+$/i.test(id);
}

export function getGa4MeasurementId(
  env: NodeJS.ProcessEnv | { NEXT_PUBLIC_GA_MEASUREMENT_ID?: string | null } = process.env,
): string | null {
  const id = (env.NEXT_PUBLIC_GA_MEASUREMENT_ID || "").trim();
  return isGa4Configured(id) ? id : null;
}

/**
 * Whether the optional GA4 script may load.
 * Does NOT affect first-party analytics.
 */
export function shouldLoadGa4(opts: {
  measurementId?: string | null;
  isProductionSeo: boolean;
  consent: AnalyticsConsentState;
}): boolean {
  if (!opts.isProductionSeo) return false;
  if (!isGa4Configured(opts.measurementId)) return false;
  return opts.consent === "granted";
}
