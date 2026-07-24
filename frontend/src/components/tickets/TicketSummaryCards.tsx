"use client";

import { StatCard } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { TicketDashboardTab } from "@/lib/tickets/buyer-ticket-groups";

type Summary = {
  upcoming: number;
  checkedInOrPast: number;
  cancelled: number;
  total: number;
};

const CARDS: {
  id: TicketDashboardTab;
  title: string;
  hint: string;
  mark: string;
  valueKey: keyof Summary;
  accent?: boolean;
}[] = [
  {
    id: "upcoming",
    title: "Active",
    hint: "Ready for entry",
    mark: "QR",
    valueKey: "upcoming",
    accent: true,
  },
  {
    id: "past",
    title: "Checked in / Past",
    hint: "Used or ended",
    mark: "✓",
    valueKey: "checkedInOrPast",
  },
  {
    id: "cancelled",
    title: "Cancelled / Refunded",
    hint: "Not for entry",
    mark: "—",
    valueKey: "cancelled",
  },
  {
    id: "all",
    title: "Total",
    hint: "All tickets",
    mark: "Σ",
    valueKey: "total",
  },
];

export function TicketSummaryCards({
  summary,
  activeTab,
  onSelect,
}: {
  summary: Summary;
  activeTab: TicketDashboardTab;
  onSelect: (tab: TicketDashboardTab) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {CARDS.map((card) => {
        const selected = activeTab === card.id;
        const value = summary[card.valueKey];
        const showAccent = Boolean(card.accent && value > 0);
        return (
          <button
            key={card.id}
            type="button"
            className="min-w-0 text-left"
            onClick={() => onSelect(card.id)}
            aria-pressed={selected}
          >
            <StatCard
              title={card.title}
              value={value}
              hint={card.hint}
              icon={<span aria-hidden>{card.mark}</span>}
              className={cn(
                "h-full transition-shadow",
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
