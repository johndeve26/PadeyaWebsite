"use client";

import { useEffect, useId, useRef, useState } from "react";

import {
  fieldControlClass,
  fieldErrorClass,
  fieldHintClass,
  fieldLabelClass,
} from "@/lib/ui/field";
import {
  hasGoogleMapsApiKey,
  loadGoogleMapsPlaces,
  placeResultToSelection,
  type PlaceSelection,
} from "@/lib/google-maps";

/**
 * Google Places Autocomplete for venue search.
 * Requires NEXT_PUBLIC_GOOGLE_MAPS_API_KEY (Maps JavaScript API + Places).
 */
export function PlacesAutocompleteInput({
  label = "Search venue with Google Places",
  hint = "Search a place — we fill venue name, address, and coordinates.",
  placeholder = "Search a venue, address, or paste a Google Maps link",
  disabled,
  onPlaceSelected,
  countryBias,
  types,
  value,
  onValueChange,
}: {
  label?: string;
  hint?: string;
  placeholder?: string;
  disabled?: boolean;
  onPlaceSelected: (place: PlaceSelection) => void;
  /** Optional ISO country code bias, e.g. "ng". */
  countryBias?: string | null;
  /** Google Places Autocomplete types, e.g. ["(cities)"]. */
  types?: string[];
  /** Controlled value for paste / Maps link detection alongside Places. */
  value?: string;
  onValueChange?: (value: string) => void;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const onPlaceSelectedRef = useRef(onPlaceSelected);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const enabled = hasGoogleMapsApiKey();

  useEffect(() => {
    onPlaceSelectedRef.current = onPlaceSelected;
  }, [onPlaceSelected]);

  useEffect(() => {
    if (!enabled || disabled) return;
    let cancelled = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let autocomplete: any = null;

    void loadGoogleMapsPlaces()
      .then(() => {
        if (cancelled || !inputRef.current || !window.google?.maps?.places) {
          return;
        }
        autocomplete = new window.google.maps.places.Autocomplete(
          inputRef.current,
          {
            fields: [
              "formatted_address",
              "geometry",
              "name",
              "url",
              "place_id",
              "address_components",
            ],
            ...(types?.length ? { types } : {}),
            ...(countryBias
              ? { componentRestrictions: { country: countryBias.toLowerCase() } }
              : {}),
          },
        );
        autocomplete.addListener("place_changed", () => {
          const place = autocomplete.getPlace();
          const selection = placeResultToSelection(place);
          if (selection) onPlaceSelectedRef.current(selection);
        });
        if (!cancelled) {
          setReady(true);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(
            "Could not load Google Places. Check NEXT_PUBLIC_GOOGLE_MAPS_API_KEY and API restrictions.",
          );
        }
      });

    return () => {
      cancelled = true;
      if (autocomplete) {
        window.google?.maps?.event?.clearInstanceListeners?.(autocomplete);
      }
    };
  }, [enabled, disabled, countryBias, types]);

  if (!enabled) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-dashed border-border-strong/40 bg-surface-inset px-4 py-3">
        <p className="text-sm font-semibold text-heading">
          Google Places search unavailable
        </p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          Add{" "}
          <code className="font-mono text-[11px]">
            NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
          </code>{" "}
          to the frontend env (Maps JavaScript API + Places API enabled), then
          restart Next. You can still paste a Maps link or use Advanced location
          details for coordinates.
        </p>
      </div>
    );
  }

  return (
    <label className="flex w-full flex-col gap-1.5 text-sm" htmlFor={inputId}>
      <span className={fieldLabelClass}>{label}</span>
      <input
        id={inputId}
        ref={inputRef}
        type="text"
        disabled={disabled || !ready}
        value={onValueChange ? (value ?? "") : undefined}
        onChange={
          onValueChange
            ? (e) => onValueChange(e.target.value)
            : undefined
        }
        placeholder={ready ? placeholder : "Loading Google Places…"}
        className={fieldControlClass({
          error: Boolean(error),
          className: "h-11 px-3.5",
        })}
        autoComplete="off"
      />
      {hint && !error ? <span className={fieldHintClass}>{hint}</span> : null}
      {error ? <span className={fieldErrorClass}>{error}</span> : null}
    </label>
  );
}
