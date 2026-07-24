/**
 * Default public discovery market when geo is unavailable / declined.
 * Override with NEXT_PUBLIC_DEFAULT_DISCOVERY_CITY_SLUG / _LABEL.
 */

export type DefaultDiscoveryCity = {
  slug: string;
  label: string;
  /** Public map anchor when GPS is unavailable — proximity sort still applies. */
  lat: number;
  lng: number;
};

export const DEFAULT_DISCOVERY_CITY: DefaultDiscoveryCity = {
  slug:
    process.env.NEXT_PUBLIC_DEFAULT_DISCOVERY_CITY_SLUG?.trim() || "lagos",
  label:
    process.env.NEXT_PUBLIC_DEFAULT_DISCOVERY_CITY_LABEL?.trim() || "Lagos",
  lat: 6.5244,
  lng: 3.3792,
};
