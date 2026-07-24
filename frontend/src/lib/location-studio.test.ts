import { describe, expect, it } from "vitest";

import {
  fanMapPreview,
  STUDIO_ADVANCED_LOCATION_FIELD_KEYS,
  studioMapsOpenUrl,
} from "./location-studio-preview";

type StudioMapSlice = Parameters<typeof fanMapPreview>[0];

function studioValues(overrides: Partial<StudioMapSlice>): StudioMapSlice {
  return {
    location_visibility: "full_public",
    venue_name: "",
    address: "",
    area: "",
    city: "",
    state: "",
    country: "",
    postcode: "",
    latitude: "",
    longitude: "",
    google_place_id: "",
    formatted_address: "",
    google_maps_share_url: "",
    google_maps_place_url: "",
    public_location_label: "",
    approximate_latitude: "",
    approximate_longitude: "",
    approximate_map_label: "",
    reveal_note: "",
    online_event_url: "",
    ...overrides,
  } as StudioMapSlice;
}

describe("location studio preview", () => {
  it("full public uses exact coordinates for fan map", () => {
    const values = studioValues({
      location_visibility: "full_public",
      venue_name: "Palm Hall",
      address: "14 Palm Close",
      latitude: "6.4698",
      longitude: "3.5852",
      city: "Lagos",
    });
    const preview = fanMapPreview(values);
    expect(preview.mode).toBe("exact");
    expect(preview.mapLatitude).toBe("6.4698");
    expect(preview.mapLongitude).toBe("3.5852");
    expect(studioMapsOpenUrl(values)).toContain("6.4698");
  });

  it("approximate mode does not use exact coordinates for open URL", () => {
    const values = studioValues({
      location_visibility: "area_only",
      latitude: "6.4698",
      longitude: "3.5852",
      approximate_latitude: "6.45",
      approximate_longitude: "3.48",
      approximate_map_label: "Lekki Phase 1 area",
      public_location_label: "Lekki, Lagos",
    });
    const preview = fanMapPreview(values);
    expect(preview.mode).toBe("approximate");
    expect(preview.mapLatitude).toBe("6.45");
    expect(preview.mapLongitude).toBe("3.48");
    const url = studioMapsOpenUrl(values);
    expect(url).toBeTruthy();
    expect(url).not.toContain("6.4698");
    expect(url).toContain("Lekki");
  });

  it("hidden until payment shows city/area preview without exact coords in map pin", () => {
    const values = studioValues({
      location_visibility: "hidden_until_payment",
      latitude: "6.4698",
      longitude: "3.5852",
      approximate_latitude: "6.45",
      approximate_longitude: "3.48",
      city: "Lagos",
      area: "Lekki",
      public_location_label: "Lekki, Lagos",
    });
    const preview = fanMapPreview(values);
    expect(preview.mode).toBe("hidden");
    expect(preview.lines[0]).toContain("Lekki");
    expect(preview.mapLatitude).toBe("6.45");
    expect(studioMapsOpenUrl(values)).not.toContain("6.4698");
  });

  it("online only has no map", () => {
    const preview = fanMapPreview(
      studioValues({ location_visibility: "online_only" }),
    );
    expect(preview.mode).toBe("none");
    expect(preview.mapLatitude).toBeNull();
    expect(
      studioMapsOpenUrl(studioValues({ location_visibility: "online_only" })),
    ).toBeNull();
  });

  it("advanced accordion covers raw coordinate and maps fields", () => {
    expect(STUDIO_ADVANCED_LOCATION_FIELD_KEYS).toEqual(
      expect.arrayContaining([
        "latitude",
        "longitude",
        "approximate_latitude",
        "approximate_longitude",
        "google_maps_share_url",
        "google_maps_place_url",
        "postcode",
        "google_place_id",
      ]),
    );
  });
});
