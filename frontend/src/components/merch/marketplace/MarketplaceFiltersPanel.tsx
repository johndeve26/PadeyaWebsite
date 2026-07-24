"use client";

import { useState } from "react";

import {
  MarketplaceFilters,
  type MarketplaceFiltersValue,
} from "@/components/merch/marketplace/MarketplaceFilters";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

type Props = {
  value: MarketplaceFiltersValue;
  onChange: (next: MarketplaceFiltersValue) => void;
  onSubmit: () => void;
  className?: string;
};

export function MarketplaceFiltersPanel({
  value,
  onChange,
  onSubmit,
  className,
}: Props) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between gap-3 lg:hidden">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setMobileOpen((o) => !o)}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? "Hide filters" : "Filter"}
        </Button>
        <Button type="button" size="sm" onClick={onSubmit}>
          Apply
        </Button>
      </div>

      {mobileOpen ? (
        <div className="rounded-[var(--radius-lg)] border border-border bg-card p-4 dark:bg-surface-elevated lg:hidden">
          <MarketplaceFilters
            value={value}
            onChange={onChange}
            onSubmit={() => {
              onSubmit();
              setMobileOpen(false);
            }}
          />
        </div>
      ) : null}

      <div className="hidden lg:block">
        <div className="sticky top-20 z-10 rounded-[var(--radius-lg)] border border-border bg-card/95 p-3 backdrop-blur-sm dark:bg-surface-elevated/95">
          <MarketplaceFilters
            value={value}
            onChange={onChange}
            onSubmit={onSubmit}
            compact
            advancedOpen={advancedOpen}
            onAdvancedOpenChange={setAdvancedOpen}
          />
        </div>
      </div>
    </div>
  );
}
