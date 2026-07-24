"use client";

import { useEffect, useState } from "react";

import { Button, Input, Select } from "@/components/ui";
import { apiRequest } from "@/lib/api";

type Vocab = { id: string; name: string; slug: string };
type Location = { id: string; name: string; slug: string; kind: string };

export type HostTaxonomyState = {
  hostTypeSlugs: string[];
  categorySlugs: string[];
  audienceSlugs: string[];
  primaryCitySlug: string;
  serviceAreaSlugs: string[];
  nichePositioning: string;
};

export function emptyHostTaxonomy(): HostTaxonomyState {
  return {
    hostTypeSlugs: [],
    categorySlugs: [],
    audienceSlugs: [],
    primaryCitySlug: "",
    serviceAreaSlugs: [],
    nichePositioning: "",
  };
}

function toggleSlug(list: string[], slug: string): string[] {
  return list.includes(slug) ? list.filter((s) => s !== slug) : [...list, slug];
}

/** Host settings taxonomy editors (types, categories, city, audience). */
export function HostTaxonomyFields({
  value,
  onChange,
}: {
  value: HostTaxonomyState;
  onChange: (next: HostTaxonomyState) => void;
}) {
  const [hostTypes, setHostTypes] = useState<Vocab[]>([]);
  const [categories, setCategories] = useState<Vocab[]>([]);
  const [audiences, setAudiences] = useState<Vocab[]>([]);
  const [cities, setCities] = useState<Location[]>([]);
  const [areas, setAreas] = useState<Location[]>([]);

  useEffect(() => {
    void Promise.all([
      apiRequest<Vocab[]>("/taxonomy/host-types", { auth: false }).catch(() => []),
      apiRequest<Vocab[]>("/taxonomy/categories", { auth: false }).catch(() => []),
      apiRequest<Vocab[]>("/taxonomy/audience-types", { auth: false }).catch(
        () => [],
      ),
      apiRequest<Location[]>("/taxonomy/locations?kind=city", { auth: false }).catch(
        () => [],
      ),
      apiRequest<Location[]>("/taxonomy/locations?kind=area", { auth: false }).catch(
        () => [],
      ),
    ]).then(([types, cats, aud, cityRows, areaRows]) => {
      setHostTypes(types);
      setCategories(cats);
      setAudiences(aud);
      setCities(cityRows);
      setAreas(areaRows);
    });
  }, []);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Position your Legacy niche so Event Studio can inherit defaults and
        discovery hubs stay connected.
      </p>
      <Input
        label="Niche positioning"
        hint="One line for Legacy (e.g. “Lagos nightlife & Detty Fridays”)."
        value={value.nichePositioning}
        onChange={(e) =>
          onChange({ ...value, nichePositioning: e.target.value })
        }
      />
      <Select
        label="Primary city"
        value={value.primaryCitySlug}
        onChange={(e) =>
          onChange({ ...value, primaryCitySlug: e.target.value })
        }
      >
        <option value="">Select city</option>
        {cities.map((c) => (
          <option key={c.id} value={c.slug}>
            {c.name}
          </option>
        ))}
      </Select>
      <ChipGroup
        label="Host types"
        options={hostTypes}
        selected={value.hostTypeSlugs}
        onToggle={(slug) =>
          onChange({
            ...value,
            hostTypeSlugs: toggleSlug(value.hostTypeSlugs, slug),
          })
        }
      />
      <ChipGroup
        label="Categories"
        options={categories}
        selected={value.categorySlugs}
        onToggle={(slug) =>
          onChange({
            ...value,
            categorySlugs: toggleSlug(value.categorySlugs, slug),
          })
        }
      />
      <ChipGroup
        label="Audience"
        options={audiences}
        selected={value.audienceSlugs}
        onToggle={(slug) =>
          onChange({
            ...value,
            audienceSlugs: toggleSlug(value.audienceSlugs, slug),
          })
        }
      />
      <ChipGroup
        label="Service areas"
        options={areas}
        selected={value.serviceAreaSlugs}
        onToggle={(slug) =>
          onChange({
            ...value,
            serviceAreaSlugs: toggleSlug(value.serviceAreaSlugs, slug),
          })
        }
      />
    </div>
  );
}

function ChipGroup({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: { slug: string; name: string }[];
  selected: string[];
  onToggle: (slug: string) => void;
}) {
  if (!options.length) return null;
  return (
    <div>
      <p className="mb-2 text-sm font-bold text-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const on = selected.includes(opt.slug);
          return (
            <Button
              key={opt.slug}
              type="button"
              size="sm"
              variant={on ? "primary" : "secondary"}
              onClick={() => onToggle(opt.slug)}
            >
              {opt.name}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
