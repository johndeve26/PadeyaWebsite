"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { LocationChips } from "@/components/discovery/LocationChips";
import {
  LocationSelector,
  type LocationCascadeValue,
} from "@/components/discovery/LocationSelector";
import { Button, Container } from "@/components/ui";
import {
  trackLocationFilterUsed,
  type LocationAnalyticsMeta,
} from "@/lib/analytics";
import { POPULAR_LOCATION_SHORTCUTS } from "@/lib/discovery/popular-locations";
import { cn } from "@/lib/cn";
import {
  fetchTaxonomyLocationDetail,
  fetchTaxonomyLocations,
  locationHubPath,
  type LocationKind,
  type TaxonomyLocation,
} from "@/lib/taxonomy-api";

export type LocationFilterValue = {
  kind: LocationKind;
  slug: string;
  name: string;
} | null;

const EMPTY: LocationCascadeValue = {
  country: null,
  state: null,
  city: null,
  area: null,
};

function deepest(c: LocationCascadeValue): LocationFilterValue {
  if (c.area) return { kind: "area", slug: c.area.slug, name: c.area.name };
  if (c.city) return { kind: "city", slug: c.city.slug, name: c.city.name };
  if (c.state) return { kind: "state", slug: c.state.slug, name: c.state.name };
  if (c.country)
    return { kind: "country", slug: c.country.slug, name: c.country.name };
  return null;
}

function metaFromCascade(c: LocationCascadeValue): LocationAnalyticsMeta {
  return {
    country: c.country?.name,
    state: c.state?.name,
    city: c.city?.name,
    area: c.area?.name,
  };
}

function metaFromShortcut(
  kind: LocationKind,
  label: string,
): LocationAnalyticsMeta {
  if (kind === "country") return { country: label };
  if (kind === "state") return { state: label };
  if (kind === "city") return { city: label };
  return { area: label };
}

async function loadChildren(
  kind: LocationKind,
  parentId: string | undefined,
): Promise<TaxonomyLocation[]> {
  if (!parentId) return [];
  return fetchTaxonomyLocations({ kind, parentId });
}

/**
 * Discovery location filter section: cascade selector, active chip, popular chips.
 */
export function LocationFilterBar({
  value,
  onChange,
  className = "",
}: {
  value: LocationFilterValue;
  onChange: (next: LocationFilterValue) => void;
  className?: string;
}) {
  const [cascade, setCascade] = useState<LocationCascadeValue>(EMPTY);
  const [countries, setCountries] = useState<TaxonomyLocation[]>([]);
  const [states, setStates] = useState<TaxonomyLocation[]>([]);
  const [cities, setCities] = useState<TaxonomyLocation[]>([]);
  const [areas, setAreas] = useState<TaxonomyLocation[]>([]);

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
    if (!value) {
      queueMicrotask(() => {
        if (alive) setCascade(EMPTY);
      });
      return () => {
        alive = false;
      };
    }
    void fetchTaxonomyLocationDetail(value.kind, value.slug)
      .then((detail) => {
        if (!alive) return;
        const byKind = Object.fromEntries(
          [...detail.ancestors, detail.location].map((l) => [l.kind, l]),
        ) as Record<string, TaxonomyLocation>;
        setCascade({
          country: byKind.country ?? null,
          state: byKind.state ?? null,
          city: byKind.city ?? null,
          area: byKind.area ?? null,
        });
      })
      .catch(() => {
        if (alive) setCascade(EMPTY);
      });
    return () => {
      alive = false;
    };
  }, [value]);

  useEffect(() => {
    let alive = true;
    void loadChildren("state", cascade.country?.id).then((rows) => {
      if (alive) setStates(rows);
    });
    return () => {
      alive = false;
    };
  }, [cascade.country?.id]);

  useEffect(() => {
    let alive = true;
    void loadChildren("city", cascade.state?.id).then((rows) => {
      if (alive) setCities(rows);
    });
    return () => {
      alive = false;
    };
  }, [cascade.state?.id]);

  useEffect(() => {
    let alive = true;
    void loadChildren("area", cascade.city?.id).then((rows) => {
      if (alive) setAreas(rows);
    });
    return () => {
      alive = false;
    };
  }, [cascade.city?.id]);

  const active = useMemo(() => deepest(cascade), [cascade]);

  function applyCascade(next: LocationCascadeValue) {
    setCascade(next);
    trackLocationFilterUsed(metaFromCascade(next));
    onChange(deepest(next));
  }

  function clear() {
    applyCascade(EMPTY);
  }

  const popularItems = POPULAR_LOCATION_SHORTCUTS.map((item) => ({
    kind: item.kind,
    slug: item.slug,
    name: item.label,
  }));

  return (
    <section
      aria-label="Events by Location"
      className={cn(
        "border-b border-border bg-card py-10 sm:py-12",
        className,
      )}
    >
      <Container className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl space-y-1.5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
              Events by Location
            </p>
            <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
              Where do you want to go?
            </h2>
            <p className="text-base leading-relaxed text-muted-foreground">
              Browse by country, state, city, or neighborhood, then refine the
              night.
            </p>
          </div>
          <Link
            href="/events/location"
            className="text-sm font-bold text-foreground underline-offset-4 hover:underline"
          >
            Browse all locations →
          </Link>
        </div>

        <LocationSelector
          value={cascade}
          options={{ countries, states, cities, areas }}
          onCountryChange={(id) => {
            const country = countries.find((c) => c.id === id) ?? null;
            applyCascade({ country, state: null, city: null, area: null });
          }}
          onStateChange={(id) => {
            const state = states.find((c) => c.id === id) ?? null;
            applyCascade({ ...cascade, state, city: null, area: null });
          }}
          onCityChange={(id) => {
            const city = cities.find((c) => c.id === id) ?? null;
            applyCascade({ ...cascade, city, area: null });
          }}
          onAreaChange={(id) => {
            const area = areas.find((c) => c.id === id) ?? null;
            applyCascade({ ...cascade, area });
          }}
        />

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Link href="/events/location">
              <Button type="button" size="sm" variant="secondary">
                Browse location hubs
              </Button>
            </Link>
            {active ? (
              <span className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-3 py-1.5 text-sm font-semibold text-foreground">
                {active.name}
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground"
                  onClick={clear}
                  aria-label="Clear location filter"
                >
                  ×
                </button>
              </span>
            ) : null}
            {active ? (
              <button
                type="button"
                className="text-sm font-bold text-foreground underline-offset-4 hover:underline"
                onClick={clear}
              >
                Clear location
              </button>
            ) : null}
          </div>
          {active ? (
            <Link
              href={locationHubPath(active.kind, active.slug)}
              className="text-sm font-bold text-foreground underline-offset-4 hover:underline"
            >
              Open {active.name} hub →
            </Link>
          ) : null}
        </div>

        <LocationChips
          items={popularItems}
          active={value}
          label="Popular"
          onSelect={(item) => {
            trackLocationFilterUsed(
              metaFromShortcut(item.kind as LocationKind, item.name),
            );
            onChange({
              kind: item.kind as LocationKind,
              slug: item.slug,
              name: item.name,
            });
          }}
        />
      </Container>
    </section>
  );
}
