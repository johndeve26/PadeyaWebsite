"use client";

import { StatCard } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { MerchWalletTab } from "@/lib/merch/buyer-merch-wallet";

type Summary = {
  ready: number;
  inProgress: number;
  completed: number;
  cancelled: number;
  total: number;
};

const CARDS: {
  id: MerchWalletTab;
  title: string;
  hint: string;
  mark: string;
  valueKey: keyof Summary;
  accent?: boolean;
}[] = [
  {
    id: "ready",
    title: "Ready for pickup",
    hint: "QR ready",
    mark: "QR",
    valueKey: "ready",
    accent: true,
  },
  {
    id: "shipping",
    title: "In progress",
    hint: "Processing / shipping",
    mark: "…",
    valueKey: "inProgress",
  },
  {
    id: "completed",
    title: "Delivered / Picked up",
    hint: "Completed",
    mark: "✓",
    valueKey: "completed",
  },
  {
    id: "cancelled",
    title: "Cancelled / Refunded",
    hint: "Not available",
    mark: "—",
    valueKey: "cancelled",
  },
  {
    id: "all",
    title: "Total merch",
    hint: "All orders",
    mark: "Σ",
    valueKey: "total",
  },
];

export function BuyerMerchSummaryCards({
  summary,
  activeTab,
  onSelect,
}: {
  summary: Summary;
  activeTab: MerchWalletTab;
  onSelect: (tab: MerchWalletTab) => void;
}) {
  return (
    <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {CARDS.map((card) => {
        const selected = activeTab === card.id;
        const value = summary[card.valueKey];
        const showAccent = Boolean(card.accent && value > 0);
        return (
          <button
            key={card.id}
            type="button"
            className="min-w-0 w-full text-left"
            onClick={() => onSelect(card.id)}
            aria-pressed={selected}
          >
            <StatCard
              title={card.title}
              value={value}
              hint={card.hint}
              icon={<span aria-hidden>{card.mark}</span>}
              className={cn(
                "h-full w-full transition-shadow",
                selected && "ring-1 ring-border-strong/40",
                showAccent && selected && "ring-primary/35",
                showAccent && !selected && "border-primary/20",
              )}
            />
          </button>
        );
      })}
    </div>
  );
}
