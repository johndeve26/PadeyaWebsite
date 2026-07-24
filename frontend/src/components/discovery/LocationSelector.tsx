"use client";

import { cn } from "@/lib/cn";
import type { TaxonomyLocation } from "@/lib/taxonomy-api";

export type LocationCascadeValue = {
  country: TaxonomyLocation | null;
  state: TaxonomyLocation | null;
  city: TaxonomyLocation | null;
  area: TaxonomyLocation | null;
};

export type LocationSelectorOptions = {
  countries: TaxonomyLocation[];
  states: TaxonomyLocation[];
  cities: TaxonomyLocation[];
  areas: TaxonomyLocation[];
};

/** Sentinel value for the City select “Other…” option. */
export const CITY_SUGGEST_OPTION = "__suggest_city__";
/** Sentinel value for the Area select “Suggest new…” option. */
export const AREA_SUGGEST_OPTION = "__suggest_area__";

const selectClass =
  "h-11 w-full rounded-[var(--radius-md)] border border-border bg-card px-3 text-sm font-semibold text-foreground disabled:opacity-45";

/**
 * Country → state → city → area cascade selects.
 * Presentational — parent owns options loading and change handlers.
 */
export function LocationSelector({
  value,
  options,
  onCountryChange,
  onStateChange,
  onCityChange,
  onAreaChange,
  allowSuggestCity = false,
  allowSuggestArea = false,
  showArea = true,
  className = "",
  disabled = false,
}: {
  value: LocationCascadeValue;
  options: LocationSelectorOptions;
  onCountryChange: (id: string) => void;
  onStateChange: (id: string) => void;
  onCityChange: (id: string) => void;
  onAreaChange: (id: string) => void;
  /** When true, City select includes “Other…”. */
  allowSuggestCity?: boolean;
  /** When true, Area select includes “Suggest a new area…”. */
  allowSuggestArea?: boolean;
  /** When false, hide the area column (host profile / onboarding). */
  showArea?: boolean;
  className?: string;
  disabled?: boolean;
}) {
  return (
    <div
      className={cn(
        showArea
          ? "grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
          : "grid gap-3 sm:grid-cols-3",
        className,
      )}
    >
      <label className="space-y-1.5">
        <span className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          Country
        </span>
        <select
          className={selectClass}
          value={value.country?.id ?? ""}
          disabled={disabled}
          onChange={(e) => onCountryChange(e.target.value)}
        >
          <option value="">Select country</option>
          {options.countries.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-1.5">
        <span className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          State
        </span>
        <select
          className={selectClass}
          value={value.state?.id ?? ""}
          disabled={disabled || !value.country}
          onChange={(e) => onStateChange(e.target.value)}
        >
          <option value="">Select state</option>
          {options.states.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-1.5">
        <span className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          City
        </span>
        <select
          className={selectClass}
          value={value.city?.id ?? ""}
          disabled={disabled || !value.state}
          onChange={(e) => onCityChange(e.target.value)}
        >
          <option value="">Select city</option>
          {options.cities.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
          {allowSuggestCity && value.state ? (
            <option value={CITY_SUGGEST_OPTION}>Other…</option>
          ) : null}
        </select>
      </label>
      {showArea ? (
      <label className="space-y-1.5">
        <span className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          Area
        </span>
        <select
          className={selectClass}
          value={value.area?.id ?? ""}
          disabled={disabled || !value.city}
          onChange={(e) => onAreaChange(e.target.value)}
        >
          <option value="">Select area (optional)</option>
          {options.areas.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
          {allowSuggestArea && value.city ? (
            <option value={AREA_SUGGEST_OPTION}>Suggest a new area…</option>
          ) : null}
        </select>
      </label>
      ) : null}
    </div>
  );
}
