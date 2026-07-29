"use client";

import { Input, Select } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { SponsorHostSort } from "@/lib/sponsor-host-presentation";

export function SponsorFilterBar({
  search,
  onSearchChange,
  city,
  cities,
  onCityChange,
  category,
  categories,
  onCategoryChange,
  sort,
  onSortChange,
  verifiedOnly,
  onVerifiedOnlyChange,
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
  sort: SponsorHostSort;
  onSortChange: (v: SponsorHostSort) => void;
  verifiedOnly: boolean;
  onVerifiedOnlyChange: (v: boolean) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-xl)] border border-border bg-card p-4 shadow-[var(--shadow)] sm:p-5 dark:bg-surface-elevated",
        className,
      )}
    >
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4 [&_>_*]:min-w-0">
        <div className="xl:col-span-2">
          <Input
            label="Search hosts"
            placeholder="Name, username, city…"
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
              {c.charAt(0).toUpperCase() + c.slice(1)}
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
          label="Sort by"
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SponsorHostSort)}
        >
          <option value="slots">Open slots</option>
          <option value="audience">Audience reach</option>
          <option value="tier">Legacy tier</option>
          <option value="name">Name</option>
        </Select>
      </div>
      <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-foreground">
        <input
          type="checkbox"
          className="h-4 w-4 accent-[var(--brand-green)]"
          checked={verifiedOnly}
          onChange={(e) => onVerifiedOnlyChange(e.target.checked)}
        />
        <span className="font-semibold">Verified hosts only</span>
      </label>
    </div>
  );
}
