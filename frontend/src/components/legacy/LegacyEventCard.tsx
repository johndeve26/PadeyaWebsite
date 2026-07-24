"use client";

import Link from "next/link";

import { TrackImpression } from "@/components/analytics/TrackImpression";
import { Badge, Card, Media } from "@/components/ui";
import { trackEventCardClick, trackLegacyClick } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import {
  formatLegacyDate,
  inferEventCategory,
  resolveEventImage,
} from "@/lib/legacy-presentation";
import type { LegacyEventCard as LegacyEvent } from "@/lib/types/legacy";

export function LegacyEventCard({
  event,
  variant = "upcoming",
  className = "",
}: {
  event: LegacyEvent;
  variant?: "upcoming" | "past";
  className?: string;
}) {
  const href =
    variant === "past" && event.memory_path
      ? event.memory_path
      : `/events/${event.slug}`;
  const image = resolveEventImage(event.slug, event.title, event.banner_url);
  const category = inferEventCategory(event.title, event.slug);
  const isUpcoming = variant === "upcoming";
  const listContext = isUpcoming ? "legacy_upcoming" : "legacy_upcoming";
  const statusLabel = event.status
    ? event.status.replace(/_/g, " ")
    : isUpcoming
      ? "Upcoming"
      : "Completed";

  return (
    <TrackImpression
      targetEventId={event.id}
      listContext={listContext}
      className={cn("h-full", className)}
    >
      <Link
        href={href}
        className="group block h-full"
        onClick={() => {
          trackEventCardClick({
            targetEventId: event.id,
            listContext,
            clickTarget: isUpcoming ? "legacy_upcoming" : "legacy_memory",
          });
          if (!isUpcoming || Boolean(event.memory_path)) {
            trackLegacyClick({ targetEventId: event.id });
          }
        }}
      >
        <Card
          hover
          padded={false}
          className="flex h-full flex-col overflow-hidden shadow-[var(--shadow-soft)] transition-[transform,box-shadow] duration-200 group-hover:-translate-y-1 group-hover:shadow-[var(--shadow)]"
        >
          <div className="relative aspect-[16/9] overflow-hidden bg-surface-dark sm:aspect-[16/9.2]">
            <Media
              src={image}
              alt=""
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.06]"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-ink/75 via-ink/10 to-transparent" />
            <div className="absolute left-3 top-3 flex flex-wrap gap-2">
              <Badge tone="accent">{category}</Badge>
              <Badge tone={isUpcoming ? "dark" : "outline"}>
                {isUpcoming ? "Upcoming" : "Completed"}
              </Badge>
              {event.status && event.status.toLowerCase() !== "published" ? (
                <Badge tone="outline" className="capitalize">
                  {statusLabel}
                </Badge>
              ) : null}
              {event.memory_path ? <Badge tone="outline">Memory</Badge> : null}
            </div>
          </div>
          <div className="flex flex-1 flex-col gap-2.5 p-5 sm:p-6">
            <h3 className="text-xl font-extrabold tracking-tight text-foreground group-hover:underline sm:text-[1.35rem] sm:leading-snug">
              {event.title}
            </h3>
            <p className="text-sm font-semibold text-foreground/80 sm:text-base">
              {formatLegacyDate(event.start_datetime)}
            </p>
            {event.city ? (
              <p className="text-sm text-muted-foreground sm:text-[0.95rem]">
                {event.city}
              </p>
            ) : null}
            <p className="mt-auto pt-3 text-sm font-bold text-foreground transition-transform duration-200 group-hover:translate-x-0.5">
              {isUpcoming
                ? "View event →"
                : event.memory_path
                  ? "Open memory →"
                  : "View event →"}
            </p>
          </div>
        </Card>
      </Link>
    </TrackImpression>
  );
}
