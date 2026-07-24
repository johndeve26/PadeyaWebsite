"use client";

import { useState } from "react";

import { Button, Input, Select } from "@/components/ui";
import {
  MERCH_CATEGORIES,
  MERCH_KINDS,
  MERCH_MARKETPLACE_SORTS,
} from "@/lib/merch-product-types";
import type { MerchMarketplaceQuery } from "@/lib/merch-api";

export type MarketplaceFiltersValue = MerchMarketplaceQuery;

type Props = {
  value: MarketplaceFiltersValue;
  onChange: (next: MarketplaceFiltersValue) => void;
  onSubmit?: () => void;
  className?: string;
  /** Desktop compact bar — primary filters only until expanded. */
  compact?: boolean;
  advancedOpen?: boolean;
  onAdvancedOpenChange?: (open: boolean) => void;
};

export function MarketplaceFilters({
  value,
  onChange,
  onSubmit,
  className,
  compact = false,
  advancedOpen: advancedOpenProp,
  onAdvancedOpenChange,
}: Props) {
  const [advancedInternal, setAdvancedInternal] = useState(false);
  const advancedOpen = advancedOpenProp ?? advancedInternal;
  const setAdvancedOpen = onAdvancedOpenChange ?? setAdvancedInternal;

  function patch(partial: Partial<MarketplaceFiltersValue>) {
    onChange({ ...value, ...partial });
  }

  const primaryGrid = compact
    ? "grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5"
    : "grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

  return (
    <form
      className={className}
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.();
      }}
    >
      <div className={primaryGrid}>
        <label className="block space-y-1 text-sm">
          <span className="font-bold text-foreground">Search</span>
          <Input
            value={value.q ?? ""}
            onChange={(e) => patch({ q: e.target.value })}
            placeholder="Keyword"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="font-bold text-foreground">Category</span>
          <Select
            value={value.category ?? ""}
            onChange={(e) =>
              patch({ category: e.target.value || undefined })
            }
          >
            <option value="">All</option>
            {MERCH_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </Select>
        </label>
        <label className="block space-y-1 text-sm">
          <span className="font-bold text-foreground">Type</span>
          <Select
            value={value.type ?? ""}
            onChange={(e) => patch({ type: e.target.value || undefined })}
          >
            <option value="">All types</option>
            {MERCH_KINDS.filter((k) => k.value !== "bundle").map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </Select>
        </label>
        <label className="block space-y-1 text-sm">
          <span className="font-bold text-foreground">Availability</span>
          <Select
            value={value.availability ?? ""}
            onChange={(e) =>
              patch({ availability: e.target.value || undefined })
            }
          >
            <option value="">Any</option>
            <option value="available">In stock</option>
            <option value="sold_out">Sold out</option>
            <option value="coming_soon">Coming soon</option>
          </Select>
        </label>
        {compact ? (
          <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="w-full"
              onClick={() => setAdvancedOpen(!advancedOpen)}
            >
              {advancedOpen ? "Fewer filters" : "More filters"}
            </Button>
            <Button type="submit" size="sm" className="w-full shrink-0">
              Apply
            </Button>
          </div>
        ) : null}
      </div>

      {(!compact || advancedOpen) && (
        <div className="mt-3 grid gap-2 border-t border-border/60 pt-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <label className="block space-y-1 text-sm">
            <span className="font-bold text-foreground">Host</span>
            <Input
              value={value.host ?? ""}
              onChange={(e) => patch({ host: e.target.value })}
              placeholder="@slug or name"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-bold text-foreground">Event</span>
            <Input
              value={value.event ?? ""}
              onChange={(e) => patch({ event: e.target.value })}
              placeholder="Event slug"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-bold text-foreground">Min price</span>
            <Input
              type="number"
              min={0}
              value={value.price_min ?? ""}
              onChange={(e) =>
                patch({
                  price_min: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              placeholder="0"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-bold text-foreground">Max price</span>
            <Input
              type="number"
              min={0}
              value={value.price_max ?? ""}
              onChange={(e) =>
                patch({
                  price_max: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              placeholder="Any"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-bold text-foreground">Fulfillment</span>
            <Select
              value={value.fulfillment_type ?? ""}
              onChange={(e) =>
                patch({ fulfillment_type: e.target.value || undefined })
              }
            >
              <option value="">Any</option>
              <option value="pickup">Pickup</option>
              <option value="delivery">Delivery</option>
              <option value="digital">Digital / POD</option>
            </Select>
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-bold text-foreground">Sort</span>
            <Select
              value={value.sort ?? "featured"}
              onChange={(e) => patch({ sort: e.target.value })}
            >
              {MERCH_MARKETPLACE_SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          </label>
          <div className="flex flex-wrap items-end gap-3 sm:col-span-2">
            <label className="inline-flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                className="size-4 accent-[var(--primary)]"
                checked={Boolean(value.vault_only)}
                onChange={(e) => patch({ vault_only: e.target.checked })}
              />
              Vault only
            </label>
            <label className="inline-flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                className="size-4 accent-[var(--primary)]"
                checked={Boolean(value.drops_only)}
                onChange={(e) => patch({ drops_only: e.target.checked })}
              />
              Drops only
            </label>
          </div>
        </div>
      )}

      {!compact ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button type="submit" size="sm">
            Apply filters
          </Button>
        </div>
      ) : null}
    </form>
  );
}
