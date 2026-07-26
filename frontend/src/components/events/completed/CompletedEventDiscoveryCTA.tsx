"use client";

import Link from "next/link";

import { HostFollowControls } from "@/components/hosts/HostFollowControls";
import { Button } from "@/components/ui";
import { cityEventsHref } from "@/lib/events/completed-event";
import type { EventItem } from "@/lib/types/events";

type CompletedEventDiscoveryCTAProps = {
  event: EventItem;
  previewMode?: boolean;
  isOwnHost?: boolean;
};

export function CompletedEventDiscoveryCTA({
  event,
  previewMode = false,
  isOwnHost = false,
}: CompletedEventDiscoveryCTAProps) {
  const cityHref = cityEventsHref(event.city) || "/events";
  const cityLabel = event.city?.trim()
    ? `Explore events in ${event.city.trim()}`
    : "Explore events";

  return (
    <section className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink px-5 py-8 text-paper shadow-[var(--shadow)] sm:px-8 sm:py-10">
      <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-accent">
        What&apos;s next
      </p>
      <h2 className="mt-2 text-balance text-2xl font-extrabold tracking-tight sm:text-3xl">
        Ready for your next adventure?
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-subtle-foreground sm:text-base">
        {event.title} may be over
        {event.city ? `, but ${event.city} isn\u2019t slowing down.` : "."} Find
        the next night, or stay close to the host.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link href={cityHref}>
          <Button type="button" size="lg">
            {cityLabel}
          </Button>
        </Link>
        {!previewMode && event.host_id && !isOwnHost ? (
          <HostFollowControls
            hostId={event.host_id}
            hostSlug={event.host_slug || undefined}
            hostDisplayName={event.host_display_name || "Host"}
            loginNextPath={`/events/${event.slug}`}
            size="lg"
          />
        ) : event.host_slug ? (
          <Link href={`/u/${encodeURIComponent(event.host_slug)}`}>
            <Button type="button" variant="secondary" size="lg">
              View host profile
            </Button>
          </Link>
        ) : null}
      </div>
    </section>
  );
}
