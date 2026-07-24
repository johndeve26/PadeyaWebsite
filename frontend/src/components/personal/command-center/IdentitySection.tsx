"use client";

import Link from "next/link";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Button, Card, SkeletonLoader } from "@/components/ui";
import { passportVisibilityLabel } from "@/lib/personal-command-center";
import type { FanPassport } from "@/lib/types/passport";

export type ReviewPrompt = {
  ticketId: string;
  eventTitle: string | null;
};

export function IdentitySection({
  loading,
  passport,
  needsPassportSetup,
  reviewPrompt,
}: {
  loading: boolean;
  passport: FanPassport | null;
  needsPassportSetup: boolean;
  reviewPrompt: ReviewPrompt | null;
}) {
  if (loading) {
    return (
      <section className="min-w-0 space-y-3">
        <SectionLabel>Identity</SectionLabel>
        <SkeletonLoader lines={3} />
      </section>
    );
  }

  const score =
    passport?.completion_score != null
      ? Math.round(Number(passport.completion_score))
      : null;
  const badges = passport?.badges_earned?.length ?? 0;
  const visibility = passportVisibilityLabel(passport?.visibility);

  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>Identity</SectionLabel>
      <Card className="min-w-0 space-y-3">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-base font-bold tracking-tight text-foreground sm:text-lg">
              Fan Passport
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {score != null ? `${score}% complete` : "Your stamps and badges"}
              {badges > 0 ? ` · ${badges} badge${badges === 1 ? "" : "s"}` : ""}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">{visibility}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Link href="/dashboard/passport">
              <Button size="sm">Open Passport</Button>
            </Link>
            <Link href="/dashboard/badges">
              <Button size="sm" variant="secondary">
                Badges
              </Button>
            </Link>
          </div>
        </div>
        {needsPassportSetup ? (
          <p className="text-sm text-muted-foreground">
            Set a username to share your Fan Passport when you are ready.
          </p>
        ) : null}
        {reviewPrompt ? (
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
            <p className="min-w-0 break-words text-sm text-foreground">
              Leave a verified review
              {reviewPrompt.eventTitle
                ? ` for ${reviewPrompt.eventTitle}`
                : " for an event you attended"}
              .
            </p>
            <Link
              href={`/dashboard/reviews?ticket_id=${encodeURIComponent(reviewPrompt.ticketId)}`}
              className="shrink-0"
            >
              <Button size="sm" variant="secondary">
                Write review
              </Button>
            </Link>
          </div>
        ) : (
          <Link
            href="/dashboard/reviews"
            className="inline-block text-sm font-semibold text-accent underline-offset-2 hover:underline"
          >
            Your reviews
          </Link>
        )}
      </Card>
    </section>
  );
}
