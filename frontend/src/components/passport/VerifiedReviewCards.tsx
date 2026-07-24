"use client";

import Link from "next/link";

import { Badge, SectionHeader } from "@/components/ui";
import { formatDate } from "@/lib/format";

export type PassportReviewCard = {
  id: string;
  rating: number;
  body?: string | null;
  event_title?: string | null;
  host_username?: string | null;
  created_at: string;
};

type Props = {
  reviews: PassportReviewCard[];
};

export function VerifiedReviewCards({ reviews }: Props) {
  if (reviews.length === 0) {
    return (
      <section className="space-y-3">
        <SectionHeader
          eyebrow="Reviews"
          title="Verified reviews written"
          description="Only public-safe verified reviews appear here."
        />
        <p className="text-sm text-muted-foreground">
          Verified public reviews will appear here.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="Reviews"
        title="Verified reviews written"
        description="Only public-safe verified reviews appear here."
      />
      <ul className="space-y-3">
        {reviews.map((r) => (
          <li
            key={r.id}
            className="rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] sm:p-5"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-2xl font-extrabold tabular-nums text-foreground">
                {r.rating}
                <span className="text-base font-bold text-muted-foreground">
                  /5
                </span>
              </p>
              <Badge tone="success" size="sm">
                Verified check-in
              </Badge>
              {r.created_at ? (
                <span className="text-xs font-semibold text-muted-foreground">
                  {formatDate(r.created_at)}
                </span>
              ) : null}
            </div>
            {r.event_title ? (
              <p className="mt-2 text-sm font-bold text-foreground">
                {r.event_title}
              </p>
            ) : (
              <p className="mt-2 text-sm font-semibold text-muted-foreground">
                Public event review
              </p>
            )}
            {r.body ? (
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground sm:text-base">
                {r.body}
              </p>
            ) : null}
            {r.host_username ? (
              <p className="mt-3 text-sm">
                <Link
                  href={`/@${r.host_username}`}
                  className="font-bold text-foreground underline-offset-2 hover:underline"
                >
                  View host Legacy
                </Link>
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
