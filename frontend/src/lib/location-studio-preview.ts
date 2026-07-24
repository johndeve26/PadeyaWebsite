import type { EventStudioValues } from "@/components/events/studio/types";

export type FanMapPreviewMode = "exact" | "approximate" | "hidden" | "none";

export type FanMapPreview = {
  mode: FanMapPreviewMode;
  headline: string;
  lines: string[];
  note: string | null;
  mapLatitude: string | null;
  mapLongitude: string | null;
  mapLabel: string | null;
  openUrl: string | null;
};

/** Google Maps open URL for host preview (respects visibility, never leaks hidden exact coords in approximate modes). */
export function studioMapsOpenUrl(values: EventStudioValues): string | null {
  const visibility = values.location_visibility;
  if (visibility === "online_only") return null;

  if (visibility === "full_public" && values.latitude && values.longitude) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      `${values.latitude},${values.longitude}`,
    )}`;
  }

  if (
    visibility !== "full_public" &&
    values.approximate_latitude &&
    values.approximate_longitude
  ) {
    const label =
      values.approximate_map_label ||
      values.public_location_label ||
      values.city ||
      `${values.approximate_latitude},${values.approximate_longitude}`;
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(label)}`;
  }

  if (visibility === "full_public" && values.latitude && values.longitude) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      `${values.latitude},${values.longitude}`,
    )}`;
  }

  return null;
}

/** What fans see on the public event page (Studio preview card). */
export function fanMapPreview(values: EventStudioValues): FanMapPreview {
  const visibility = values.location_visibility;

  if (visibility === "online_only") {
    return {
      mode: "none",
      headline: "What fans will see",
      lines: ["Online event — no physical map pin."],
      note: values.online_event_url
        ? "Join link follows your online access reveal rule."
        : "Add an online event URL when you have one.",
      mapLatitude: null,
      mapLongitude: null,
      mapLabel: null,
      openUrl: null,
    };
  }

  if (visibility === "full_public") {
    const place =
      [values.venue_name, values.address].filter(Boolean).join(" · ") ||
      values.public_location_label ||
      values.area ||
      "Exact venue";
    return {
      mode: "exact",
      headline: "What fans will see",
      lines: [place, [values.area, values.city, values.state].filter(Boolean).join(", ")].filter(
        Boolean,
      ),
      note: null,
      mapLatitude: values.latitude || null,
      mapLongitude: values.longitude || null,
      mapLabel: values.venue_name || values.address || null,
      openUrl: studioMapsOpenUrl(values),
    };
  }

  if (visibility === "area_only") {
    const areaLine =
      values.public_location_label ||
      values.approximate_map_label ||
      [values.area, values.city].filter(Boolean).join(", ") ||
      "Approximate area";
    return {
      mode: "approximate",
      headline: "What fans will see",
      lines: [areaLine],
      note: "Exact street address and pin stay private until your reveal rules allow.",
      mapLatitude: values.approximate_latitude || null,
      mapLongitude: values.approximate_longitude || null,
      mapLabel:
        values.approximate_map_label ||
        values.public_location_label ||
        values.area ||
        null,
      openUrl: studioMapsOpenUrl(values),
    };
  }

  const hiddenLine =
    values.public_location_label ||
    [values.area, values.city, values.state].filter(Boolean).join(", ") ||
    values.city ||
    "City / area only";
  return {
    mode: "hidden",
    headline: "What fans will see",
    lines: [hiddenLine],
    note:
      values.reveal_note ||
      "Exact venue is shown only to confirmed ticket holders when reveal rules allow.",
    mapLatitude: values.approximate_latitude || null,
    mapLongitude: values.approximate_longitude || null,
    mapLabel: hiddenLine,
    openUrl: studioMapsOpenUrl(values),
  };
}

/** Fields hosts edit in Advanced — must stay wired to form state. */
export const STUDIO_ADVANCED_LOCATION_FIELD_KEYS = [
  "latitude",
  "longitude",
  "approximate_latitude",
  "approximate_longitude",
  "google_maps_place_url",
  "google_maps_share_url",
  "postcode",
  "google_place_id",
] as const satisfies readonly (keyof EventStudioValues)[];
