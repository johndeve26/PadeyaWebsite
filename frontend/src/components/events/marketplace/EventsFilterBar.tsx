"use client";

import { PriceRangeSlider } from "@/components/events/marketplace/PriceRangeSlider";
import { Select } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { DatePreset } from "@/lib/events/marketplace-listing";
import { priceRangeStep } from "@/lib/events/marketplace-listing";

export type EventsFilterValues = {
  city: string;
  date: DatePreset;
  priceMin: number;
  priceMax: number;
};

/**
 * Desktop facet controls for /events.
 * Mobile filters open from the sticky bottom bar + EventsFilterDrawer.
 * Chrome surface is owned by the marketplace client wrapper.
 */
export function EventsFilterBar({
  values,
  onChange,
  cities,
  priceBoundMax,
  className = "",
}: {
  values: EventsFilterValues;
  onChange: (patch: Partial<EventsFilterValues>) => void;
  cities: { slug: string; name: string }[];
  priceBoundMax: number;
  className?: string;
}) {
  return (
    <div className={cn("hidden min-w-0 lg:block", className)}>
      <div className="grid min-w-0 gap-3 lg:grid-cols-2 [&_>_*]:min-w-0">
        <Select
          label="Location"
          value={values.city}
          onChange={(e) => onChange({ city: e.target.value })}
        >
          <option value="all">Search location</option>
          {cities.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          label="Date"
          value={values.date}
          onChange={(e) => onChange({ date: e.target.value as DatePreset })}
        >
          <option value="any">Any date</option>
          <option value="today">Today</option>
          <option value="this-weekend">This weekend</option>
          <option value="this-week">This week</option>
        </Select>
      </div>

      <PriceRangeSlider
        id="events-filter-bar-price"
        className="mt-4"
        min={0}
        max={priceBoundMax}
        valueMin={values.priceMin}
        valueMax={values.priceMax}
        step={priceRangeStep(priceBoundMax)}
        onChange={onChange}
      />
    </div>
  );
}
