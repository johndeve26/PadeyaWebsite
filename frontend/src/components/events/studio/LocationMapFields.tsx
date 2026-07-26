"use client";

import { useCallback, useState } from "react";

import { PlacesAutocompleteInput } from "@/components/events/PlacesAutocompleteInput";
import { Button, Input } from "@/components/ui";
import { parseMapsUrlCoords } from "@/lib/event-maps";
import {
  approximateCoordsFromExact,
  type PlaceSelection,
} from "@/lib/google-maps";
import { studioMapsOpenUrl } from "@/lib/location-studio-preview";
import {
  publicLabelFromResolvedPlace,
  ensureTaxonomyFromPlaceHints,
} from "@/lib/taxonomy-resolve-place";

import { StudioFieldGroup, StudioMicrocopy } from "./studio-ui";
import type { EventStudioValues } from "./types";

const POSTCODE_COUNTRIES = new Set([
  "united kingdom",
  "uk",
  "gb",
  "united states",
  "usa",
  "us",
  "canada",
  "ca",
  "ireland",
  "ie",
  "australia",
  "au",
]);

function countryUsesPostcode(country: string): boolean {
  const key = country.trim().toLowerCase();
  if (!key) return false;
  return POSTCODE_COUNTRIES.has(key);
}

export function LocationMapFields({
  values,
  onChange,
  disabled,
}: {
  values: EventStudioValues;
  onChange: <K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) => void;
  disabled?: boolean;
}) {
  const previewUrl = studioMapsOpenUrl(values);
  const countryBias =
    values.country?.toLowerCase() === "nigeria"
      ? "ng"
      : values.country?.length === 2
        ? values.country
        : null;
  const [searchDraft, setSearchDraft] = useState("");
  const [resolvingTaxonomy, setResolvingTaxonomy] = useState(false);

  const applyPlace = useCallback(
    (place: PlaceSelection) => {
      if (place.name) onChange("venue_name", place.name);
      if (place.formattedAddress) onChange("address", place.formattedAddress);
      onChange("latitude", place.latitude);
      onChange("longitude", place.longitude);
      onChange("google_place_id", place.placeId || "");
      onChange("formatted_address", place.formattedAddress || "");
      onChange("google_maps_place_url", place.placeUrl);
      onChange("google_maps_share_url", place.placeUrl);
      if (place.postcode) onChange("postcode", place.postcode);

      // Places is source of truth for a new pick — overwrite stale geo labels.
      // Clear taxonomy leaf until resolve finishes so UI does not keep Lekki/etc.
      onChange("location_id", "");
      onChange("country", place.countryHint || "");
      onChange("state", place.stateHint || "");
      onChange("city", place.cityHint || "");
      onChange("area", place.areaHint || "");

      const publicLabel = [
        place.areaHint || place.name,
        place.cityHint || place.stateHint,
      ]
        .filter(Boolean)
        .join(", ");
      if (publicLabel) onChange("public_location_label", publicLabel);

      const approx = approximateCoordsFromExact(
        Number(place.latitude),
        Number(place.longitude),
      );
      onChange("approximate_latitude", approx.latitude);
      onChange("approximate_longitude", approx.longitude);
      const approxLabel =
        publicLabel ||
        [place.areaHint || place.cityHint, place.stateHint || place.countryHint]
          .filter(Boolean)
          .join(", ");
      if (approxLabel) onChange("approximate_map_label", approxLabel);

      setSearchDraft("");

      // Sync taxonomy cascade (location_id) from Places — create missing city/area.
      setResolvingTaxonomy(true);
      void ensureTaxonomyFromPlaceHints(
        {
          countryHint: place.countryHint,
          stateHint: place.stateHint,
          cityHint: place.cityHint,
          areaHint: place.areaHint,
        },
        { createMissing: true },
      )
        .then((resolved) => {
          if (!resolved) {
            onChange("location_id", "");
            return;
          }
          onChange("location_id", resolved.locationId);
          // Prefer taxonomy display names when matched (canonical hub labels).
          onChange("country", resolved.country || place.countryHint || "");
          onChange("state", resolved.state || place.stateHint || "");
          onChange("city", resolved.city || place.cityHint || "");
          // Keep Google area hint when taxonomy has no matching area leaf.
          onChange("area", resolved.area || place.areaHint || "");
          const taxonomyLabel = publicLabelFromResolvedPlace(
            resolved,
            place.areaHint,
            place.cityHint,
          );
          if (taxonomyLabel) {
            onChange("public_location_label", taxonomyLabel);
            onChange("approximate_map_label", taxonomyLabel);
          }
        })
        .catch(() => {
          /* keep Places labels; host can set taxonomy manually */
        })
        .finally(() => {
          setResolvingTaxonomy(false);
        });
    },
    [onChange],
  );

  function tryApplyMapsLink(raw: string) {
    const url = raw.trim();
    if (!url || !parseMapsUrlCoords(url)) return;
    onChange("google_maps_share_url", url);
    const coords = parseMapsUrlCoords(url);
    if (!coords) return;
    if (!values.latitude) onChange("latitude", coords.latitude);
    if (!values.longitude) onChange("longitude", coords.longitude);
    const approx = approximateCoordsFromExact(
      Number(coords.latitude),
      Number(coords.longitude),
    );
    if (!values.approximate_latitude) {
      onChange("approximate_latitude", approx.latitude);
    }
    if (!values.approximate_longitude) {
      onChange("approximate_longitude", approx.longitude);
    }
  }

  const showPostcodeInAdvanced = !countryUsesPostcode(values.country);
  const showPublicMapArea =
    values.location_visibility !== "full_public" &&
    values.location_visibility !== "online_only";

  return (
    <>
      <StudioFieldGroup title="Venue search">
        <StudioMicrocopy>
          Search fills venue, address, coordinates, and the place hierarchy for
          discovery.
        </StudioMicrocopy>

        {!values.latitude || !values.longitude ? (
          <p
            className="rounded-[var(--radius-sm)] border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-foreground"
            role="status"
          >
            Pick a venue from search, paste a Google Maps link, or use Advanced
            location details to enter coordinates manually.
          </p>
        ) : (
          <p className="text-xs font-semibold text-primary" role="status">
            {resolvingTaxonomy
              ? "Matching place for discovery (adding missing city/area if needed)…"
              : "Map location is ready."}
          </p>
        )}

        <PlacesAutocompleteInput
          disabled={disabled}
          countryBias={countryBias}
          onPlaceSelected={applyPlace}
          label="Search venue or paste Google Maps link"
          hint="Search a venue, address, or paste a Google Maps link."
          placeholder="Search a venue, address, or paste a Google Maps link"
          value={searchDraft}
          onValueChange={(next) => {
            setSearchDraft(next);
            tryApplyMapsLink(next);
          }}
        />
      </StudioFieldGroup>

      {showPublicMapArea ? (
        <Input
          label="Public map area"
          hint="Label and pin fans see when the exact street is hidden."
          value={values.approximate_map_label}
          onChange={(e) => onChange("approximate_map_label", e.target.value)}
          disabled={disabled}
          placeholder="Lekki Phase 1 area"
        />
      ) : null}

      <details className="group rounded-[var(--radius-lg)] border border-border bg-card/40 dark:bg-surface-elevated/40">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold text-foreground marker:content-none [&::-webkit-details-marker]:hidden">
          Advanced location details
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            (filled automatically from Google Maps)
          </span>
        </summary>
        <div className="space-y-4 border-t border-border px-4 py-4">
          <StudioMicrocopy>
            These are filled automatically from Google Maps. Only edit if you
            know what you&apos;re doing.
          </StudioMicrocopy>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Exact latitude"
              value={values.latitude}
              onChange={(e) => onChange("latitude", e.target.value)}
              disabled={disabled}
              placeholder="6.4281"
            />
            <Input
              label="Exact longitude"
              value={values.longitude}
              onChange={(e) => onChange("longitude", e.target.value)}
              disabled={disabled}
              placeholder="3.4219"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Approximate latitude"
              value={values.approximate_latitude}
              onChange={(e) => onChange("approximate_latitude", e.target.value)}
              disabled={disabled}
              placeholder="6.45"
            />
            <Input
              label="Approximate longitude"
              value={values.approximate_longitude}
              onChange={(e) =>
                onChange("approximate_longitude", e.target.value)
              }
              disabled={disabled}
              placeholder="3.43"
            />
          </div>

          <Input
            label="Google Maps place URL"
            value={values.google_maps_place_url}
            onChange={(e) => onChange("google_maps_place_url", e.target.value)}
            disabled={disabled}
          />
          <Input
            label="Google Maps share link"
            value={values.google_maps_share_url}
            onChange={(e) => {
              const url = e.target.value;
              onChange("google_maps_share_url", url);
              tryApplyMapsLink(url);
            }}
            disabled={disabled}
            placeholder="https://maps.app.goo.gl/… or maps.google.com/…"
          />

          {showPostcodeInAdvanced ? (
            <Input
              label="Postcode"
              value={values.postcode}
              onChange={(e) => onChange("postcode", e.target.value)}
              disabled={disabled}
            />
          ) : null}

          <Input
            label="Google place ID"
            value={values.google_place_id}
            onChange={(e) => onChange("google_place_id", e.target.value)}
            disabled={disabled}
            placeholder="ChIJ…"
          />

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              disabled={!previewUrl}
              onClick={() => {
                if (previewUrl) {
                  window.open(previewUrl, "_blank", "noopener,noreferrer");
                }
              }}
            >
              Open map preview
            </Button>
          </div>
        </div>
      </details>
    </>
  );
}
