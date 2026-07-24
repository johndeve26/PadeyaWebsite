"use client";

import { cn } from "@/lib/cn";

export type MerchFilterKey =
  | "all"
  | "available"
  | "pickup"
  | "shipping"
  | "bundles"
  | "vault"
  | "ticket"
  | "low_stock"
  | "sponsor"
  | "post_event";

const FILTERS: { key: MerchFilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "available", label: "Available" },
  { key: "pickup", label: "Pickup at event" },
  { key: "shipping", label: "Shipping" },
  { key: "bundles", label: "Bundles" },
  { key: "vault", label: "Vault exclusive" },
  { key: "ticket", label: "Ticket-holder only" },
  { key: "low_stock", label: "Low stock" },
  { key: "sponsor", label: "Sponsor-branded" },
  { key: "post_event", label: "Post-event drops" },
];

type Props = {
  value: MerchFilterKey;
  onChange: (key: MerchFilterKey) => void;
  hiddenKeys?: MerchFilterKey[];
  className?: string;
};

export function MerchFilterChips({
  value,
  onChange,
  hiddenKeys = [],
  className,
}: Props) {
  const visible = FILTERS.filter((f) => !hiddenKeys.includes(f.key));

  return (
    <div
      className={cn(
        "-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 scrollbar-thin",
        className,
      )}
      role="tablist"
      aria-label="Filter merch"
    >
      {visible.map((filter) => {
        const active = value === filter.key;
        return (
          <button
            key={filter.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(filter.key)}
            className={cn(
              "shrink-0 rounded-full border px-3 py-1.5 text-xs font-extrabold uppercase tracking-wide transition-colors",
              active
                ? "border-foreground bg-foreground text-background"
                : "border-border bg-card text-muted-foreground hover:border-foreground/40 hover:text-foreground",
            )}
          >
            {filter.label}
          </button>
        );
      })}
    </div>
  );
}
