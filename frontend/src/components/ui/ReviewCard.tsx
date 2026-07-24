import Link from "next/link";

import { Badge } from "./Badge";
import { Card } from "./Card";
import { cn } from "@/lib/cn";
import { reviewerInitials } from "@/lib/legacy-presentation";

function Stars({ rating }: { rating: number }) {
  return (
    <span
      className="text-base font-semibold tracking-tight text-foreground"
      aria-label={`${rating} of 5`}
    >
      {"★".repeat(rating)}
      <span className="text-subtle-foreground">{"★".repeat(Math.max(0, 5 - rating))}</span>
    </span>
  );
}

export function ReviewCard({
  rating,
  title,
  body,
  reviewerName,
  eventTitle,
  eventHref,
  reply,
  verified = true,
  dateLabel,
  reactionCount,
  className = "",
}: {
  rating: number;
  title?: string | null;
  body: string;
  reviewerName?: string | null;
  eventTitle?: string | null;
  /** When set, the event title links to the event page. */
  eventHref?: string | null;
  reply?: { body: string; author_name?: string | null } | null;
  verified?: boolean;
  dateLabel?: string | null;
  /** Optional — only when real reaction data exists */
  reactionCount?: number | null;
  className?: string;
}) {
  const initials = reviewerInitials(reviewerName);

  return (
    <Card
      className={cn(
        "space-y-4 transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-0.5 hover:border-border-strong/15 hover:shadow-[var(--shadow)]",
        className,
      )}
    >
      <div className="flex items-start gap-3.5">
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-primary sm:h-14 sm:w-14 sm:text-base"
          aria-hidden
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-bold text-foreground sm:text-lg">
              {reviewerName?.trim() || "Verified attendee"}
            </p>
            {verified ? (
              <Badge tone="accent" className="gap-1">
                <span aria-hidden>✓</span> Verified
              </Badge>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Stars rating={rating} />
            {dateLabel ? (
              <span className="text-sm text-muted-foreground">{dateLabel}</span>
            ) : null}
          </div>
          {eventTitle ? (
            <p className="text-sm font-medium text-muted-foreground">
              Event attended ·{" "}
              {eventHref ? (
                <Link
                  href={eventHref}
                  className="font-semibold text-foreground underline-offset-2 hover:underline"
                >
                  {eventTitle}
                </Link>
              ) : (
                eventTitle
              )}
            </p>
          ) : null}
        </div>
      </div>

      {title ? (
        <h3 className="text-lg font-extrabold tracking-tight text-foreground">
          {title}
        </h3>
      ) : null}

      <p className="whitespace-pre-wrap text-base leading-relaxed text-muted-foreground sm:text-[1.05rem] sm:leading-relaxed">
        {body}
      </p>

      {reactionCount != null && reactionCount > 0 ? (
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          {reactionCount} reaction{reactionCount === 1 ? "" : "s"}
        </p>
      ) : null}

      {reply ? (
        <div className="rounded-[var(--radius-md)] border border-accent/25 border-l-[3px] border-l-accent bg-[color-mix(in_srgb,var(--primary)_6%,transparent)] px-4 py-3.5 sm:px-5">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-foreground/70">
            Host reply
            {reply.author_name ? ` · ${reply.author_name}` : ""}
          </p>
          <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed text-foreground sm:text-base">
            {reply.body}
          </p>
        </div>
      ) : null}
    </Card>
  );
}
