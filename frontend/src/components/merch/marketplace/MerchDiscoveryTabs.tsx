"use client";

import { cn } from "@/lib/cn";
import {
  MERCH_DISCOVERY_TABS,
  type MerchDiscoveryTab,
} from "@/lib/merch/marketplace-curation";

type Props = {
  active: MerchDiscoveryTab;
  onChange: (tab: MerchDiscoveryTab) => void;
  className?: string;
};

export function MerchDiscoveryTabs({ active, onChange, className }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Merch discovery"
      className={cn(
        "flex gap-2 overflow-x-auto pb-1 scrollbar-none",
        className,
      )}
    >
      {MERCH_DISCOVERY_TABS.map((tab) => {
        const selected = active === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => {
              onChange(tab.id);
              if (tab.sectionId) {
                document
                  .getElementById(tab.sectionId)
                  ?.scrollIntoView({ behavior: "smooth", block: "start" });
              }
            }}
            className={cn(
              "shrink-0 rounded-full px-4 py-2 text-sm font-bold transition-colors",
              selected
                ? "bg-primary text-ink shadow-[var(--shadow-soft)]"
                : "border border-border bg-card text-muted-foreground hover:border-primary/30 hover:text-foreground",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
