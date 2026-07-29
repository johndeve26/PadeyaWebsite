"use client";

import type { FanPassportPublicPage } from "@/lib/types/passport";

type Props = {
  page: FanPassportPublicPage;
};

const STATS: {
  key: keyof Pick<
    FanPassportPublicPage,
    | "events_attended"
    | "hosts_followed"
    | "badges_earned_count"
    | "categories_explored"
  >;
  label: string;
}[] = [
  { key: "events_attended", label: "Events attended" },
  { key: "hosts_followed", label: "Hosts followed" },
  { key: "badges_earned_count", label: "Badges earned" },
  { key: "categories_explored", label: "Favorite scene" },
];

export function FanPassportStats({ page }: Props) {
  return (
    <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {STATS.map((stat) => (
        <div
          key={stat.key}
          className="flex h-full flex-col rounded-[var(--radius-lg)] border border-border bg-card px-3.5 py-3.5 shadow-[var(--shadow-soft)] sm:py-4"
        >
          <p className="text-2xl font-extrabold tabular-nums tracking-tight text-heading">
            {page[stat.key] ?? 0}
          </p>
          <p className="mt-1 text-sm font-bold leading-snug text-foreground">
            {stat.label}
          </p>
        </div>
      ))}
    </section>
  );
}
