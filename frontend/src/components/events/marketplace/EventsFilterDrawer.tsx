"use client";

import type { EventsFilterValues } from "@/components/events/marketplace/EventsFilterBar";
import { PriceRangeSlider } from "@/components/events/marketplace/PriceRangeSlider";
import { Button, Drawer, Select } from "@/components/ui";
import type { DatePreset } from "@/lib/events/marketplace-listing";
import { priceRangeStep } from "@/lib/events/marketplace-listing";

export function EventsFilterDrawer({
  open,
  onClose,
  values,
  onChange,
  cities,
  priceBoundMax,
  onApply,
  onClear,
}: {
  open: boolean;
  onClose: () => void;
  values: EventsFilterValues;
  onChange: (patch: Partial<EventsFilterValues>) => void;
  cities: { slug: string; name: string }[];
  priceBoundMax: number;
  onApply: () => void;
  onClear: () => void;
}) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Filters"
      description="Narrow events by location, date, and price."
      footer={
        <div className="flex gap-2">
          <Button type="button" variant="secondary" className="flex-1" onClick={onClear}>
            Clear filters
          </Button>
          <Button type="button" className="flex-1" onClick={onApply}>
            Apply filters
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
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
        <PriceRangeSlider
          id="events-filter-drawer-price"
          min={0}
          max={priceBoundMax}
          valueMin={values.priceMin}
          valueMax={values.priceMax}
          step={priceRangeStep(priceBoundMax)}
          onChange={onChange}
        />
      </div>
    </Drawer>
  );
}
