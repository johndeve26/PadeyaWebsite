"use client";

import type { EventMemory } from "@/lib/types/memories";

import { EventDetailPanel } from "../EventDetailPanel";

type CompletedEventReviewsProps = {
  memory: EventMemory | null;
};

/** Only renders when real verified review data exists on the memory payload. */
export function CompletedEventReviews({ memory }: CompletedEventReviewsProps) {
  const reviews = memory?.top_reviews ?? [];
  const count = memory?.review_count ?? 0;
  const rating =
    memory?.verified_rating != null && Number(memory.verified_rating) > 0
      ? Number(memory.verified_rating).toFixed(1)
      : null;

  if (!reviews.length || count <= 0) return null;

  return (
    <EventDetailPanel title="What attendees said">
      {rating ? (
        <p className="mb-4 text-sm text-muted-foreground">
          <span className="text-2xl font-extrabold text-foreground">{rating}★</span>
          {" · "}
          {count} verified {count === 1 ? "attendee" : "attendees"}
        </p>
      ) : (
        <p className="mb-4 text-sm text-muted-foreground">
          {count} verified {count === 1 ? "review" : "reviews"}
        </p>
      )}
      <ul className="space-y-4">
        {reviews.slice(0, 4).map((review) => (
          <li
            key={review.id}
            className="rounded-xl border border-border bg-surface-muted/60 p-4 dark:bg-surface-inset/40"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-extrabold text-foreground" aria-label={`${review.rating} stars`}>
                {"★".repeat(Math.max(0, Math.min(5, review.rating)))}
              </p>
              <span className="rounded-[var(--radius-sm)] bg-primary/15 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-primary">
                ✓ Verified attendee
              </span>
            </div>
            {review.title ? (
              <p className="mt-2 font-semibold text-foreground">{review.title}</p>
            ) : null}
            <p className="mt-1 text-sm leading-relaxed text-body">{review.body}</p>
            {review.reviewer_name ? (
              <p className="mt-2 text-xs text-muted-foreground">
                {review.reviewer_name}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </EventDetailPanel>
  );
}
