"use client";

import { Button, Input, Select } from "@/components/ui";
import { cn } from "@/lib/cn";
import type {
  SponsorAudienceBucket,
  SponsorBudgetRange,
  SponsorSlotSort,
} from "@/lib/sponsor-slot-presentation";

export function SponsorshipSlotFilters({
  search,
  onSearchChange,
  city,
  cities,
  onCityChange,
  category,
  categories,
  onCategoryChange,
  slotType,
  slotTypes,
  onSlotTypeChange,
  budget,
  onBudgetChange,
  audience,
  onAudienceChange,
  sort,
  onSortChange,
  onClear,
  hasActiveFilters,
  className = "",
}: {
  search: string;
  onSearchChange: (v: string) => void;
  city: string;
  cities: string[];
  onCityChange: (v: string) => void;
  category: string;
  categories: string[];
  onCategoryChange: (v: string) => void;
  slotType: string;
  slotTypes: { value: string; label: string }[];
  onSlotTypeChange: (v: string) => void;
  budget: SponsorBudgetRange;
  onBudgetChange: (v: SponsorBudgetRange) => void;
  audience: SponsorAudienceBucket;
  onAudienceChange: (v: SponsorAudienceBucket) => void;
  sort: SponsorSlotSort;
  onSortChange: (v: SponsorSlotSort) => void;
  onClear: () => void;
  hasActiveFilters: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-xl)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] sm:p-5 dark:bg-surface-elevated",
        className,
      )}
    >
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3 [&_>_*]:min-w-0">
        <div className="sm:col-span-2 xl:col-span-3">
          <Input
            label="Search"
            placeholder="Slot, host, event, city…"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
        <Select
          label="Category"
          value={category}
          onChange={(e) => onCategoryChange(e.target.value)}
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </Select>
        <Select
          label="City"
          value={city}
          onChange={(e) => onCityChange(e.target.value)}
        >
          <option value="all">All cities</option>
          {cities.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </Select>
        <Select
          label="Slot type"
          value={slotType}
          onChange={(e) => onSlotTypeChange(e.target.value)}
        >
          <option value="all">All slot types</option>
          {slotTypes.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </Select>
        <Select
          label="Budget range"
          value={budget}
          onChange={(e) => onBudgetChange(e.target.value as SponsorBudgetRange)}
        >
          <option value="all">Any budget</option>
          <option value="under_50k">Under ₦50k</option>
          <option value="50k_200k">₦50k – ₦200k</option>
          <option value="over_200k">Over ₦200k</option>
        </Select>
        <Select
          label="Audience"
          value={audience}
          onChange={(e) =>
            onAudienceChange(e.target.value as SponsorAudienceBucket)
          }
        >
          <option value="all">Any audience</option>
          <option value="high_reach">High reach (5K+)</option>
          <option value="growing">Growing (under 5K)</option>
        </Select>
        <Select
          label="Sort by"
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SponsorSlotSort)}
        >
          <option value="recommended">Recommended</option>
          <option value="newest">Newest</option>
          <option value="price_asc">Lowest price</option>
          <option value="audience">Highest audience</option>
          <option value="closing">Closing soon</option>
        </Select>
      </div>
      {hasActiveFilters ? (
        <div className="mt-4">
          <Button type="button" variant="ghost" size="sm" onClick={onClear}>
            Clear filters
          </Button>
        </div>
      ) : null}
    </div>
  );
}
