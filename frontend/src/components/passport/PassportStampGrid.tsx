"use client";

import { useMemo, useState } from "react";

import { Button, SectionHeader } from "@/components/ui";
import type { FanBadge } from "@/lib/types/passport";

import { stampSourceForBadge } from "./badge-source";
import { PassportStampCard } from "./PassportStampCard";

type Props = {
  badges: FanBadge[];
  /** Default 6 keeps a clean 3×2 first screen. */
  initialVisible?: number;
  /** Hide section chrome when nested in another card. */
  embedded?: boolean;
};

export function PassportStampGrid({
  badges,
  initialVisible = 6,
  embedded = false,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const sorted = useMemo(() => {
    return [...badges].sort((a, b) => {
      const aMerch = stampSourceForBadge(a) === "Merch" ? 1 : 0;
      const bMerch = stampSourceForBadge(b) === "Merch" ? 1 : 0;
      if (aMerch !== bMerch) return bMerch - aMerch;
      return a.name.localeCompare(b.name);
    });
  }, [badges]);

  if (badges.length === 0) {
    return (
      <section className="space-y-3">
        {embedded ? null : (
          <SectionHeader
            eyebrow="Stamps"
            title="Passport stamps"
            description="Earned from verified tickets, check-ins, reviews, merch support, and host loyalty."
          />
        )}
        <p className="text-sm text-muted-foreground">
          Badges appear after verified tickets, check-ins, reviews, merch
          support, and host activity.
        </p>
      </section>
    );
  }

  const visible = expanded ? sorted : sorted.slice(0, initialVisible);

  return (
    <section className="space-y-5">
      {embedded ? null : (
        <SectionHeader
          eyebrow="Stamps"
          title="Passport stamps"
          description="Earned from verified tickets, check-ins, reviews, merch support, and host loyalty."
        />
      )}
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((badge) => (
          <li key={badge.id}>
            <PassportStampCard
              badge={badge}
              emphasized={stampSourceForBadge(badge) === "Merch"}
            />
          </li>
        ))}
      </ul>
      {sorted.length > initialVisible ? (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show less" : `Show all ${sorted.length} stamps`}
        </Button>
      ) : null}
    </section>
  );
}
