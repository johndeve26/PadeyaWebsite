"use client";

import { type ReactNode } from "react";

import { cn } from "@/lib/cn";
import type { MerchWalletTab } from "@/lib/merch/buyer-merch-wallet";

const LABELS: Record<MerchWalletTab, string> = {
  ready: "Ready for pickup",
  shipping: "Shipping / Delivery",
  completed: "Picked up / Delivered",
  cancelled: "Cancelled / Refunded",
  all: "All",
};

export function BuyerMerchTabs({
  activeTab,
  counts,
  onChange,
  children,
}: {
  activeTab: MerchWalletTab;
  counts: {
    ready: number;
    shipping: number;
    completed: number;
    cancelled: number;
    all: number;
  };
  onChange: (tab: MerchWalletTab) => void;
  children: ReactNode;
}) {
  const items: { id: MerchWalletTab; count: number }[] = [
    { id: "ready", count: counts.ready },
    { id: "shipping", count: counts.shipping },
    { id: "completed", count: counts.completed },
    { id: "cancelled", count: counts.cancelled },
    { id: "all", count: counts.all },
  ];

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "sticky top-0 z-20 -mx-1 border-b border-border/80 bg-background/90 px-1 py-2 backdrop-blur-md",
          "dark:bg-surface/90",
        )}
      >
        <div
          role="tablist"
          aria-label="Merch filters"
          className="flex gap-1 overflow-x-auto rounded-[var(--radius-md)] border border-border bg-muted p-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {items.map((item) => {
            const selected = item.id === activeTab;
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={selected}
                className={cn(
                  "shrink-0 rounded-[calc(var(--radius-md)-2px)] px-3.5 py-2 text-sm font-semibold transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  selected
                    ? "bg-card text-heading shadow-[var(--shadow-soft)] ring-1 ring-border dark:bg-surface-elevated"
                    : "text-muted-foreground hover:bg-surface-inset hover:text-foreground",
                )}
                onClick={() => onChange(item.id)}
              >
                {LABELS[item.id]} ({item.count})
              </button>
            );
          })}
        </div>
      </div>
      <div role="tabpanel">{children}</div>
    </div>
  );
}
