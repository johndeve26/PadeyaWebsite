/** Google Maps / Places helpers (browser). Key is optional — UI degrades without it. */

type LatLngLike = {
  lat: number | (() => number);
  lng: number | (() => number);
};

type AddressComponent = {
  long_name: string;
  short_name: string;
  types: string[];
};

export type GooglePlaceResult = {
  name?: string;
  formatted_address?: string;
  place_id?: string;
  url?: string;
  geometry?: { location?: LatLngLike };
  address_components?: AddressComponent[];
};

/** Loose Maps JS surface used by Places + interactive Event Map. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type GoogleMapsNs = { maps: any };

declare global {
  interface Window {
    google?: GoogleMapsNs;
    __padeyaGoogleMapsPromise?: Promise<void>;
  }
}

export function getGoogleMapsApiKey(): string | undefined {
  const key = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY?.trim();
  return key || undefined;
}

export function hasGoogleMapsApiKey(): boolean {
  return Boolean(getGoogleMapsApiKey());
}

/** Load Maps JS (+ Places). Same script powers autocomplete and Event Map. */
export function loadGoogleMapsPlaces(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Google Maps is browser-only"));
  }
  if (window.google?.maps?.Map) {
    return Promise.resolve();
  }
  if (window.__padeyaGoogleMapsPromise) {
    return window.__padeyaGoogleMapsPromise;
  }

  const key = getGoogleMapsApiKey();
  if (!key) {
    return Promise.reject(new Error("Missing NEXT_PUBLIC_GOOGLE_MAPS_API_KEY"));
  }

  window.__padeyaGoogleMapsPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      "script[data-padeya-google-maps]",
    );
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener(
        "error",
        () => reject(new Error("Failed to load Google Maps")),
        { once: true },
      );
      return;
    }

    const script = document.createElement("script");
    script.dataset.padeyaGoogleMaps = "1";
    script.async = true;
    script.src =
      `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}` +
      `&libraries=places&v=weekly`;
    script.onload = () => resolve();
    script.onerror = () => {
      window.__padeyaGoogleMapsPromise = undefined;
      reject(new Error("Failed to load Google Maps"));
    };
    document.head.appendChild(script);
  });

  return window.__padeyaGoogleMapsPromise;
}

/** Alias — interactive map + Places share one loader. */
export const loadGoogleMaps = loadGoogleMapsPlaces;

/** Round coords for privacy-safe approximate public pins (~1km). */
export function approximateCoordsFromExact(
  lat: number,
  lng: number,
): { latitude: string; longitude: string } {
  return {
    latitude: (Math.round(lat * 100) / 100).toFixed(2),
    longitude: (Math.round(lng * 100) / 100).toFixed(2),
  };
}

export type PlaceSelection = {
  name: string;
  formattedAddress: string;
  latitude: string;
  longitude: string;
  placeUrl: string;
  placeId: string;
  areaHint: string;
  cityHint: string;
  stateHint: string;
  countryHint: string;
  postcode: string;
};

function component(
  components: AddressComponent[] | undefined,
  type: string,
): string {
  const match = components?.find((c) => c.types.includes(type));
  return match?.long_name ?? "";
}

function readLatLng(loc: LatLngLike): { lat: number; lng: number } | null {
  const lat = typeof loc.lat === "function" ? loc.lat() : Number(loc.lat);
  const lng = typeof loc.lng === "function" ? loc.lng() : Number(loc.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
}

export function placeResultToSelection(
  place: GooglePlaceResult,
): PlaceSelection | null {
  const loc = place.geometry?.location;
  if (!loc) return null;
  const coords = readLatLng(loc);
  if (!coords) return null;

  const components = place.address_components;
  const areaHint =
    component(components, "neighborhood") ||
    component(components, "sublocality") ||
    component(components, "sublocality_level_1");
  const cityHint =
    component(components, "locality") ||
    component(components, "administrative_area_level_2");
  const stateHint = component(components, "administrative_area_level_1");
  const countryHint = component(components, "country");
  const postcode = component(components, "postal_code");

  const placeId = place.place_id || "";
  const placeUrl =
    place.url ||
    (placeId
      ? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(placeId)}`
      : `https://www.google.com/maps/search/?api=1&query=${coords.lat},${coords.lng}`);

  return {
    name: place.name || "",
    formattedAddress: place.formatted_address || "",
    latitude: coords.lat.toFixed(6),
    longitude: coords.lng.toFixed(6),
    placeUrl,
    placeId,
    areaHint,
    cityHint,
    stateHint,
    countryHint,
    postcode,
  };
}
