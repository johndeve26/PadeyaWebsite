"use client";

import { useEffect, useState } from "react";

import {
  AREA_SUGGEST_OPTION,
  CITY_SUGGEST_OPTION,
  LocationSelector,
  type LocationCascadeValue,
} from "@/components/discovery/LocationSelector";
import { Button, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchTaxonomyLocationDetail,
  fetchTaxonomyLocations,
  suggestTaxonomyArea,
  suggestTaxonomyCity,
  type LocationKind,
  type TaxonomyLocation,
} from "@/lib/taxonomy-api";

import type { EventStudioValues } from "./types";

type SuggestKind = "city" | "area" | null;

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

/**
 * Country → state → city → area cascade using taxonomy locations.
 * Dual-writes location_id + country/state/city/area labels for payload + privacy.
 */
export function LocationTaxonomyFields({
  values,
  onChange,
}: {
  values: EventStudioValues;
  onChange: (key: keyof EventStudioValues, value: string) => void;
}) {
  const onlineOnly = values.location_visibility === "online_only";
  const cityRequired =
    !onlineOnly &&
    values.event_type !== "online" &&
    values.location_visibility !== "online_only";

  const [countries, setCountries] = useState<TaxonomyLocation[]>([]);
  const [states, setStates] = useState<TaxonomyLocation[]>([]);
  const [cities, setCities] = useState<TaxonomyLocation[]>([]);
  const [areas, setAreas] = useState<TaxonomyLocation[]>([]);
  const [cascade, setCascade] = useState<LocationCascadeValue>(emptyCascade);
  const [suggestKind, setSuggestKind] = useState<SuggestKind>(null);
  const [suggestName, setSuggestName] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);

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
    if (!values.location_id) {
      return () => {
        alive = false;
      };
    }
    void fetchTaxonomyLocations()
      .then(async (all) => {
        const node = all.find((l) => l.id === values.location_id);
        if (!node || !alive) return;
        const detail = await fetchTaxonomyLocationDetail(node.kind, node.slug);
        if (!alive) return;
        const byKind = Object.fromEntries(
          [...detail.ancestors, detail.location].map((l) => [l.kind, l]),
        ) as Partial<Record<LocationKind, TaxonomyLocation>>;
        setCascade({
          country: byKind.country ?? null,
          state: byKind.state ?? null,
          city: byKind.city ?? null,
          area: byKind.area ?? null,
        });
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [values.location_id]);

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
    let alive = true;
    void loadChildren("area", cascade.city?.id ?? "").then((rows) => {
      if (alive) setAreas(rows);
    });
    return () => {
      alive = false;
    };
  }, [cascade.city?.id]);

  function closeSuggest() {
    setSuggestKind(null);
    setSuggestName("");
    setSuggestError(null);
  }

  function applyLeaf(node: TaxonomyLocation | null, next: LocationCascadeValue) {
    if (!node) {
      onChange("location_id", "");
      return;
    }
    onChange("location_id", node.id);
    onChange("country", next.country?.name ?? "");
    onChange("state", next.state?.name ?? "");
    onChange("city", next.city?.name ?? "");
    onChange("area", next.area?.name ?? "");
    if (node.kind === "area" && !values.public_location_label.trim()) {
      const label = [node.name, next.city?.name || next.state?.name]
        .filter(Boolean)
        .join(", ");
      onChange("public_location_label", label);
    } else if (
      (node.kind === "city" || node.kind === "state") &&
      !values.public_location_label.trim()
    ) {
      onChange("public_location_label", node.name);
    }
  }

  async function submitSuggest() {
    const name = suggestName.trim();
    if (name.length < 2) {
      setSuggestError(
        suggestKind === "city"
          ? "Enter a city name (at least 2 characters)."
          : "Enter an area name (at least 2 characters).",
      );
      return;
    }
    setSuggesting(true);
    setSuggestError(null);
    try {
      if (suggestKind === "city") {
        if (!cascade.state?.id) {
          setSuggestError("Select a state first.");
          return;
        }
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
        setCascade(next);
        setAreas([]);
        applyLeaf(created, next);
      } else if (suggestKind === "area") {
        if (!cascade.city?.id) {
          setSuggestError("Select a city first.");
          return;
        }
        const created = await suggestTaxonomyArea({
          cityId: cascade.city.id,
          name,
        });
        const nextAreas = await loadChildren("area", cascade.city.id);
        setAreas(nextAreas);
        const next = {
          country: cascade.country,
          state: cascade.state,
          city: cascade.city,
          area: created,
        };
        setCascade(next);
        applyLeaf(created, next);
      }
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

  const suggestParentLabel =
    suggestKind === "city"
      ? cascade.state?.name
      : suggestKind === "area"
        ? cascade.city?.name
        : null;

  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm font-semibold text-foreground">
          Place on Pàdéyá taxonomy
          {cityRequired ? " *" : ""}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Country → state → city → area. Missing a city? Choose{" "}
          <span className="font-semibold text-foreground">Other…</span> under
          City. Missing an area? Suggest one. Both are saved for other hosts to
          use next time.
        </p>
      </div>
      <LocationSelector
        value={cascade}
        options={{ countries, states, cities, areas }}
        disabled={onlineOnly}
        allowSuggestCity={!onlineOnly}
        allowSuggestArea={!onlineOnly}
        onCountryChange={(id) => {
          const country = countries.find((c) => c.id === id) ?? null;
          const next = { country, state: null, city: null, area: null };
          setCascade(next);
          closeSuggest();
          applyLeaf(country, next);
        }}
        onStateChange={(id) => {
          const state = states.find((c) => c.id === id) ?? null;
          const next = {
            country: cascade.country,
            state,
            city: null,
            area: null,
          };
          setCascade(next);
          closeSuggest();
          applyLeaf(state, next);
        }}
        onCityChange={(id) => {
          if (id === CITY_SUGGEST_OPTION) {
            setSuggestKind("city");
            setSuggestName("");
            setSuggestError(null);
            return;
          }
          const city = cities.find((c) => c.id === id) ?? null;
          const next = {
            country: cascade.country,
            state: cascade.state,
            city,
            area: null,
          };
          setCascade(next);
          closeSuggest();
          applyLeaf(city, next);
        }}
        onAreaChange={(id) => {
          if (id === AREA_SUGGEST_OPTION) {
            setSuggestKind("area");
            setSuggestName("");
            setSuggestError(null);
            return;
          }
          const area = areas.find((c) => c.id === id) ?? null;
          const next = {
            country: cascade.country,
            state: cascade.state,
            city: cascade.city,
            area,
          };
          setCascade(next);
          closeSuggest();
          applyLeaf(area ?? cascade.city, next);
        }}
      />

      {suggestKind && suggestParentLabel && !onlineOnly ? (
        <div className="rounded-[var(--radius-lg)] border border-border bg-card/80 p-4 dark:bg-surface-elevated/80">
          <p className="text-sm font-semibold text-foreground">
            {suggestKind === "city"
              ? `Suggest a new city in ${suggestParentLabel}`
              : `Suggest a new area in ${suggestParentLabel}`}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Saved for other hosts to select next time. Use the common local name.
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="min-w-0 flex-1 space-y-1.5">
              <span className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                {suggestKind === "city" ? "City name" : "Area name"}
              </span>
              <Input
                value={suggestName}
                onChange={(e) => setSuggestName(e.target.value)}
                placeholder={
                  suggestKind === "city" ? "e.g. Ikorodu North" : "e.g. Sangotedo"
                }
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
                {suggesting
                  ? "Saving…"
                  : suggestKind === "city"
                    ? "Save city"
                    : "Save area"}
              </Button>
            </div>
          </div>
          {suggestError ? (
            <p className="mt-2 text-xs font-semibold text-danger">{suggestError}</p>
          ) : null}
        </div>
      ) : null}

      {onlineOnly ? (
        <p className="text-xs text-muted-foreground">
          Online-only events do not need a physical taxonomy place. You can still set
          one for marketing hubs if useful.
        </p>
      ) : null}
    </div>
  );
}
