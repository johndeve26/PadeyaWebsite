"use client";

import { SectionHeader } from "@/components/ui";
import type { FanPassportPublicPage } from "@/lib/types/passport";

type Props = {
  page: FanPassportPublicPage;
};

/** Scene/city/host highlights only — avoids repeating stamp & stat counts. */
export function PassportHighlights({ page }: Props) {
  const topHost = page.followed_hosts[0] ?? null;

  const cards = [
    {
      label: "Favorite scenes",
      value:
        page.favorite_categories.length > 0
          ? page.favorite_categories.slice(0, 3).join(" · ")
          : null,
    },
    {
      label: "Cities explored",
      value:
        page.favorite_cities.length > 0
          ? page.favorite_cities.slice(0, 3).join(" · ")
          : page.cities_explored > 0
            ? `${page.cities_explored} cities`
            : null,
    },
    {
      label: "Most followed host",
      value: topHost
        ? `${topHost.display_name} · @${topHost.username}`
        : null,
    },
  ].filter((card): card is { label: string; value: string } =>
    Boolean(card.value),
  );

  if (cards.length === 0) return null;

  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="Highlights"
        title="Passport highlights"
        description="Scenes, cities, and hosts this fan shows up for."
      />
      <ul className="grid gap-3 sm:grid-cols-3">
        {cards.map((card) => (
          <li
            key={card.label}
            className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4"
          >
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              {card.label}
            </p>
            <p className="mt-2 text-sm font-semibold leading-snug text-foreground">
              {card.value}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
