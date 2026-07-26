"use client";

import Link from "next/link";

import { HostFollowControls } from "@/components/hosts/HostFollowControls";
import { Button } from "@/components/ui";
import { formatDate } from "@/lib/format";
import {
  cityEventsHref,
  historicalTicketsWereLabel,
  memoriesHref,
} from "@/lib/events/completed-event";
import type { EventItem } from "@/lib/types/events";
import type { EventMemory, MemoryUpcomingEvent } from "@/lib/types/memories";

type CompletedEventSidebarProps = {
  event: EventItem;
  memory: EventMemory | null;
  previewMode?: boolean;
  isOwnHost?: boolean;
  manageEventHref?: string;
};

export function CompletedEventSidebar({
  event,
  memory,
  previewMode = false,
  isOwnHost = false,
  manageEventHref,
}: CompletedEventSidebarProps) {
  const count = memory?.counts?.memory_count ?? 0;
  const contributors = memory?.counts?.contributor_count ?? 0;
  const rating =
    memory?.verified_rating != null && Number(memory.verified_rating) > 0
      ? Number(memory.verified_rating).toFixed(1)
      : null;
  const reviewCount = memory?.review_count ?? 0;
  const ticketsWere = historicalTicketsWereLabel(
    (event.ticket_types ?? []).map((t) => t.price),
  );
  const memoriesPath = memoriesHref(event.slug);
  const cityHref = cityEventsHref(event.city);
  const upcoming =
    (memory?.upcoming_events ?? []).filter(Boolean).slice(0, 2) as MemoryUpcomingEvent[];
  const hostHref = event.host_slug
    ? `/u/${encodeURIComponent(event.host_slug)}`
    : "/hosts";

  return (
    <aside className="min-w-0 space-y-4 lg:sticky lg:top-24 lg:self-start">
      <div className="rounded-[var(--radius-xl)] border border-ink bg-ink p-5 text-paper shadow-[var(--shadow)] sm:p-6">
        <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-accent">
          Event ended
        </p>
        <h2 className="mt-2 text-xl font-extrabold tracking-tight sm:text-2xl">
          {event.title} took place on {formatDate(event.start_datetime)}.
        </h2>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm text-subtle-foreground">
          {count > 0 ? (
            <p>
              <span className="font-extrabold text-paper">{count}</span>{" "}
              {count === 1 ? "memory" : "memories"}
            </p>
          ) : (
            <p>Memories album open</p>
          )}
          {contributors > 0 ? (
            <p>
              <span className="font-extrabold text-paper">{contributors}</span>{" "}
              {contributors === 1 ? "contributor" : "contributors"}
            </p>
          ) : null}
          {rating && reviewCount > 0 ? (
            <p>
              <span className="font-extrabold text-paper">{rating}★</span>{" "}
              verified attendee rating
            </p>
          ) : null}
        </div>

        <div className="mt-5 grid gap-2">
          {previewMode ? (
            <Button className="w-full" size="lg" disabled>
              Preview only
            </Button>
          ) : isOwnHost && manageEventHref ? (
            <Link href={manageEventHref} className="block">
              <Button className="w-full" size="lg">
                Manage memories
              </Button>
            </Link>
          ) : (
            <Link href={memoriesPath} className="block">
              <Button className="w-full" size="lg">
                View memories
              </Button>
            </Link>
          )}
          {!previewMode && event.host_id && !isOwnHost ? (
            <HostFollowControls
              hostId={event.host_id}
              hostSlug={event.host_slug || undefined}
              hostDisplayName={event.host_display_name || "Host"}
              loginNextPath={`/events/${event.slug}`}
              size="md"
              className="w-full [&_button]:w-full"
            />
          ) : null}
        </div>

        {ticketsWere ? (
          <p className="mt-4 border-t border-paper/15 pt-4 text-xs text-subtle-foreground">
            {ticketsWere}
          </p>
        ) : null}

        <div className="mt-4 space-y-2 border-t border-paper/15 pt-4 text-sm">
          {upcoming[0] ? (
            <div>
              <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-subtle-foreground">
                Upcoming from this host
              </p>
              <Link
                href={`/events/${upcoming[0].slug}`}
                className="mt-1 inline-block font-semibold text-paper underline decoration-accent underline-offset-4"
              >
                {upcoming[0].title} →
              </Link>
            </div>
          ) : null}
          {cityHref ? (
            <Link
              href={cityHref}
              className="inline-block text-sm font-semibold text-accent underline-offset-4 hover:underline"
            >
              Explore upcoming events →
            </Link>
          ) : (
            <Link
              href="/events"
              className="inline-block text-sm font-semibold text-accent underline-offset-4 hover:underline"
            >
              Explore upcoming events →
            </Link>
          )}
          <Link
            href={hostHref}
            className="block text-xs text-subtle-foreground underline-offset-2 hover:underline"
          >
            View host profile
          </Link>
        </div>
      </div>
    </aside>
  );
}
