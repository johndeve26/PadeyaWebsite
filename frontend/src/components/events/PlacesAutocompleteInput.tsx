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
 *
 * Important: the text field stays uncontrolled while Autocomplete is attached.
 * Binding React `value` fights the Maps widget and can freeze typing after ~2 chars.
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
  /** External clear/reset signal (e.g. "" after a place is applied). */
  value?: string;
  onValueChange?: (value: string) => void;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const onPlaceSelectedRef = useRef(onPlaceSelected);
  const onValueChangeRef = useRef(onValueChange);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const enabled = hasGoogleMapsApiKey();
  // Stable dep — inline `types={["(cities)"]}` must not remount Autocomplete every render.
  const typesKey = types?.join(",") ?? "";

  useEffect(() => {
    onPlaceSelectedRef.current = onPlaceSelected;
  }, [onPlaceSelected]);

  useEffect(() => {
    onValueChangeRef.current = onValueChange;
  }, [onValueChange]);

  // Only honor external clears (after place apply). Never rewrite while typing —
  // React `value=` + Google Autocomplete freezes input after ~2 characters.
  useEffect(() => {
    if (value !== "" || !inputRef.current) return;
    if (inputRef.current.value !== "") {
      inputRef.current.value = "";
    }
  }, [value]);

  useEffect(() => {
    if (!enabled || disabled) return;
    let cancelled = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let autocomplete: any = null;
    const typesList = typesKey
      ? typesKey.split(",").filter(Boolean)
      : undefined;

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
            ...(typesList?.length ? { types: typesList } : {}),
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
          setReady(false);
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
  }, [enabled, disabled, countryBias, typesKey]);

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
        // Keep enabled for paste/typing even while Places finishes loading.
        disabled={disabled}
        defaultValue={value ?? ""}
        onChange={(e) => {
          onValueChangeRef.current?.(e.target.value);
        }}
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
