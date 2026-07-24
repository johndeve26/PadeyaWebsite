"use client";

import { cn } from "@/lib/cn";
import { resolveEventImage } from "@/lib/legacy-presentation";
import { resolveMediaUrl } from "@/lib/media";
import type { EventItem } from "@/lib/types/events";

export type ThumbDensity = "large" | "medium" | "small";

/** Density scales with how many events share the day. */
export function thumbDensityForCount(count: number): ThumbDensity {
  if (count <= 1) return "large";
  if (count <= 3) return "medium";
  return "small";
}

function maxVisibleForDensity(
  density: ThumbDensity,
  variant: "month" | "strip",
): number {
  if (variant === "strip") {
    return density === "large" ? 1 : 2;
  }
  // Cap month slices so cells stay readable (3–4 equal rows + optional +N).
  if (density === "large") return 1;
  if (density === "medium") return 3;
  return 4;
}

/**
 * How many thumbs to render vs +N overflow.
 * Month reserves a flex slot for +N; strip shows +N as text beside thumbs.
 */
export function visibleThumbPlan(
  count: number,
  variant: "month" | "strip" = "month",
): { density: ThumbDensity; visible: number; overflow: number } {
  const density = thumbDensityForCount(count);
  const maxSlots = maxVisibleForDensity(density, variant);
  if (count <= maxSlots) {
    return { density, visible: count, overflow: 0 };
  }
  if (variant === "strip") {
    return { density, visible: maxSlots, overflow: count - maxSlots };
  }
  const visible = Math.max(1, maxSlots - 1);
  return { density, visible, overflow: count - visible };
}

/** Prefer mobile banner (typically smaller) when present. */
export function eventCalendarThumbSrc(event: EventItem): string {
  return resolveEventImage(
    event.slug,
    event.title,
    event.mobile_banner_url || event.banner_url,
    event.category?.name || event.category?.slug,
  );
}

/**
 * Compact banner thumbnails for a calendar day cell.
 * Month: equal flex rows fill remaining cell height.
 * Strip: compact fixed chips beside the date.
 */
export function CalendarDayEventThumbs({
  events,
  className = "",
  variant = "month",
}: {
  events: EventItem[];
  className?: string;
  /** Month grid uses larger cells; strip uses tighter chips. */
  variant?: "month" | "strip";
}) {
  const count = events.length;
  if (!count) return null;

  const { density, visible: visibleCount, overflow } = visibleThumbPlan(
    count,
    variant,
  );
  const visible = events.slice(0, visibleCount);

  if (variant === "strip") {
    return (
      <StripThumbs
        events={visible}
        overflow={overflow}
        density={density}
        className={className}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden",
        className,
      )}
    >
      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-0.5">
        {visible.map((event) => (
          <ThumbFrame
            key={event.id}
            event={event}
            className="min-h-0 w-full flex-1"
            width={160}
            height={80}
            sizes="(max-width: 1024px) 20vw, 160px"
            featuredRing={event.featured}
          />
        ))}
        {overflow > 0 ? (
          <span
            className="flex min-h-0 flex-1 items-center justify-center rounded-[3px] bg-muted text-[9px] font-bold text-primary"
            aria-label={`${overflow} more events`}
          >
            +{overflow}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function StripThumbs({
  events,
  overflow,
  density,
  className = "",
}: {
  events: EventItem[];
  overflow: number;
  density: ThumbDensity;
  className?: string;
}) {
  const size =
    density === "large"
      ? "h-6 w-9"
      : density === "medium"
        ? "h-5 w-7"
        : "h-4 w-5";
  const px = density === "large" ? 36 : density === "medium" ? 28 : 20;
  const py = density === "large" ? 24 : density === "medium" ? 20 : 16;

  return (
    <div
      className={cn(
        "flex max-w-full items-center justify-center gap-0.5 overflow-hidden",
        className,
      )}
      aria-hidden
    >
      {events.map((event) => (
        <ThumbFrame
          key={event.id}
          event={event}
          className={cn(size, "shrink-0")}
          width={px}
          height={py}
          sizes={`${px}px`}
          featuredRing={event.featured}
        />
      ))}
      {overflow > 0 ? (
        <span className="text-[8px] font-bold leading-none text-primary">
          +{overflow}
        </span>
      ) : null}
    </div>
  );
}

function ThumbFrame({
  event,
  className,
  width,
  height,
  sizes,
  featuredRing,
}: {
  event: EventItem;
  className?: string;
  width: number;
  height: number;
  sizes: string;
  featuredRing?: boolean;
}) {
  const src = resolveMediaUrl(eventCalendarThumbSrc(event));

  return (
    <span
      title={event.title}
      className={cn(
        "relative block min-w-0 overflow-hidden rounded-[3px] bg-muted",
        "ring-1 ring-inset ring-border/60 transition group-hover:ring-primary/35",
        featuredRing && "ring-primary/45",
        className,
      )}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        width={width}
        height={height}
        sizes={sizes}
        loading="lazy"
        decoding="async"
        className="h-full w-full object-cover"
      />
    </span>
  );
}
