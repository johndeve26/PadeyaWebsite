"use client";

import { useEffect, useRef, useState } from "react";

import {
  CITY_SUGGEST_OPTION,
  LocationSelector,
  type LocationCascadeValue,
} from "@/components/discovery/LocationSelector";
import { Button, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchTaxonomyLocations,
  findTaxonomyLocationByName,
  suggestTaxonomyCity,
  type LocationKind,
  type TaxonomyLocation,
} from "@/lib/taxonomy-api";

export type ProfileLocationLabels = {
  country: string;
  state: string;
  city: string;
};

export type ProfileLocationSeed = Partial<ProfileLocationLabels>;

async function loadChildren(
  kind: LocationKind,
  parentId: string,
): Promise<TaxonomyLocation[]> {
  if (!parentId) return [];
  return fetchTaxonomyLocations({ kind, parentId });
}

function emptyCascade(): LocationCascadeValue {
  return { country: null, state: null, city: null, area: null };
}

function labelsFromCascade(cascade: LocationCascadeValue): ProfileLocationLabels {
  return {
    country: cascade.country?.name ?? "",
    state: cascade.state?.name ?? "",
    city: cascade.city?.name ?? "",
  };
}

/**
 * Country → state → city using taxonomy (same as event studio).
 * Optional city suggestion via “Other…”.
 */
export function ProfileLocationTaxonomyFields({
  value,
  onChange,
  seed,
  hint,
}: {
  value: ProfileLocationLabels;
  onChange: (next: ProfileLocationLabels) => void;
  /** Prefill cascade once (e.g. from signup or saved preference). */
  seed?: ProfileLocationSeed | null;
  hint?: string;
}) {
  const [countries, setCountries] = useState<TaxonomyLocation[]>([]);
  const [states, setStates] = useState<TaxonomyLocation[]>([]);
  const [cities, setCities] = useState<TaxonomyLocation[]>([]);
  const [cascade, setCascade] = useState<LocationCascadeValue>(emptyCascade);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [suggestName, setSuggestName] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const seedAppliedRef = useRef(false);

  useEffect(() => {
    let alive = true;
    void fetchTaxonomyLocations({ kind: "country" }).then((rows) => {
      if (alive) setCountries(rows);
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    void loadChildren("state", cascade.country?.id ?? "").then((rows) => {
      if (alive) setStates(rows);
    });
    return () => {
      alive = false;
    };
  }, [cascade.country?.id]);

  useEffect(() => {
    let alive = true;
    void loadChildren("city", cascade.state?.id ?? "").then((rows) => {
      if (alive) setCities(rows);
    });
    return () => {
      alive = false;
    };
  }, [cascade.state?.id]);

  useEffect(() => {
    if (seedAppliedRef.current || !countries.length) return;
    const merged: ProfileLocationSeed = {
      country: seed?.country || "Nigeria",
      state: seed?.state,
      city: seed?.city,
    };
    if (!merged.country?.trim()) return;

    let cancelled = false;
    void (async () => {
      const country =
        findTaxonomyLocationByName(countries, merged.country) ?? null;
      if (!country || cancelled) {
        return;
      }

      let state: TaxonomyLocation | null = null;
      let city: TaxonomyLocation | null = null;
      const stateRows = await loadChildren("state", country.id);
      if (cancelled) return;
      if (merged.state?.trim()) {
        state = findTaxonomyLocationByName(stateRows, merged.state);
      }
      if (state) {
        const cityRows = await loadChildren("city", state.id);
        if (cancelled) return;
        setCities(cityRows);
        if (merged.city?.trim()) {
          city = findTaxonomyLocationByName(cityRows, merged.city);
        }
      }
      setStates(stateRows);
      const next = { country, state, city, area: null };
      setCascade(next);
      onChange(labelsFromCascade(next));
      seedAppliedRef.current = true;
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- seed once when countries load
  }, [countries, seed]);

  function applyCascade(next: LocationCascadeValue) {
    setCascade(next);
    onChange(labelsFromCascade(next));
  }

  function closeSuggest() {
    setSuggestOpen(false);
    setSuggestName("");
    setSuggestError(null);
  }

  async function submitSuggest() {
    const name = suggestName.trim();
    if (name.length < 2) {
      setSuggestError("Enter a city name (at least 2 characters).");
      return;
    }
    if (!cascade.state?.id) {
      setSuggestError("Select a state first.");
      return;
    }
    setSuggesting(true);
    setSuggestError(null);
    try {
      const created = await suggestTaxonomyCity({
        stateId: cascade.state.id,
        name,
      });
      const nextCities = await loadChildren("city", cascade.state.id);
      setCities(nextCities);
      const next = {
        country: cascade.country,
        state: cascade.state,
        city: created,
        area: null,
      };
      applyCascade(next);
      closeSuggest();
    } catch (err) {
      setSuggestError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Could not save suggestion.",
      );
    } finally {
      setSuggesting(false);
    }
  }

  return (
    <div className="space-y-3">
      {hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : (
        <p className="text-xs text-muted-foreground">
          Pick from Pàdéyá locations. Missing a city? Choose{" "}
          <span className="font-semibold text-foreground">Other…</span> under City
          to suggest one for other hosts.
        </p>
      )}
      <LocationSelector
        value={cascade}
        options={{ countries, states, cities, areas: [] }}
        showArea={false}
        allowSuggestCity
        onCountryChange={(id) => {
          const country = countries.find((c) => c.id === id) ?? null;
          applyCascade({ country, state: null, city: null, area: null });
          closeSuggest();
        }}
        onStateChange={(id) => {
          const state = states.find((c) => c.id === id) ?? null;
          applyCascade({
            country: cascade.country,
            state,
            city: null,
            area: null,
          });
          closeSuggest();
        }}
        onCityChange={(id) => {
          if (id === CITY_SUGGEST_OPTION) {
            setSuggestOpen(true);
            setSuggestName("");
            setSuggestError(null);
            return;
          }
          const city = cities.find((c) => c.id === id) ?? null;
          applyCascade({
            country: cascade.country,
            state: cascade.state,
            city,
            area: null,
          });
          closeSuggest();
        }}
        onAreaChange={() => undefined}
      />

      {suggestOpen && cascade.state?.name ? (
        <div className="rounded-[var(--radius-lg)] border border-border bg-card/80 p-4 dark:bg-surface-elevated/80">
          <p className="text-sm font-semibold text-foreground">
            Suggest a new city in {cascade.state.name}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Saved for other hosts to select next time. Use the common local name.
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="min-w-0 flex-1 space-y-1.5">
              <span className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                City name
              </span>
              <Input
                value={suggestName}
                onChange={(e) => setSuggestName(e.target.value)}
                placeholder="e.g. Ikorodu North"
                disabled={suggesting}
                maxLength={160}
              />
            </label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={suggesting}
                onClick={closeSuggest}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={suggesting || suggestName.trim().length < 2}
                onClick={() => void submitSuggest()}
              >
                {suggesting ? "Saving…" : "Save city"}
              </Button>
            </div>
          </div>
          {suggestError ? (
            <p className="mt-2 text-xs font-semibold text-danger">{suggestError}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
