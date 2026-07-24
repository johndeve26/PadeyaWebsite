/** Location picked at signup — pre-fills host onboarding (session only). */

export const REGISTER_LOCATION_STORAGE_KEY = "padeya.register.location";

export type RegisterLocationSeed = {
  country?: string;
  state?: string;
  city?: string;
};

export function readRegisterLocationSeed(): RegisterLocationSeed | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(REGISTER_LOCATION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as RegisterLocationSeed;
    if (!parsed || typeof parsed !== "object") return null;
    return {
      country: typeof parsed.country === "string" ? parsed.country : undefined,
      state: typeof parsed.state === "string" ? parsed.state : undefined,
      city: typeof parsed.city === "string" ? parsed.city : undefined,
    };
  } catch {
    return null;
  }
}

export function writeRegisterLocationSeed(seed: RegisterLocationSeed): void {
  if (typeof window === "undefined") return;
  const hasValue = [seed.country, seed.state, seed.city].some(
    (v) => (v || "").trim().length > 0,
  );
  if (!hasValue) {
    window.sessionStorage.removeItem(REGISTER_LOCATION_STORAGE_KEY);
    return;
  }
  window.sessionStorage.setItem(
    REGISTER_LOCATION_STORAGE_KEY,
    JSON.stringify({
      country: seed.country?.trim() || undefined,
      state: seed.state?.trim() || undefined,
      city: seed.city?.trim() || undefined,
    }),
  );
}

export function clearRegisterLocationSeed(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(REGISTER_LOCATION_STORAGE_KEY);
}
