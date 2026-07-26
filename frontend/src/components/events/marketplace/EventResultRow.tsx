import Link from "next/link";

import { Badge, Button, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  isFreeEvent,
  isVipEvent,
  minTicketPrice,
} from "@/lib/discovery/event-filters";
import { ticketAvailabilityLabel } from "@/lib/discovery/marketplace-groups";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import { formatDate, formatNgn } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import type { EventItem } from "@/lib/types/events";

function priceLabel(event: EventItem): string {
  if (isFreeEvent(event)) return "Free";
  const min = minTicketPrice(event);
  if (min == null) return "See tickets";
  return `From ${formatNgn(min)}`;
}

function formatTime(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-NG", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function hostInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

export function EventResultRow({
  event,
  className = "",
}: {
  event: EventItem;
  className?: string;
}) {
  const cover = resolveEventImage(
    event.slug,
    event.title,
    event.banner_url,
    event.category?.name || event.category?.slug,
  );
  const place = formatPublicPlaceLabel(event);
  const stock = ticketAvailabilityLabel(event);
  const online = String(event.event_type || "").toLowerCase() === "online";
  const free = isFreeEvent(event);
  const vip = isVipEvent(event);
  const soldOut = stock === "Sold out";
  const time = formatTime(event.start_datetime);
  const hostName = event.host_display_name?.trim() || null;
  const hostHref = event.host_slug
    ? `/@${event.host_slug.replace(/^@/, "")}`
    : null;

  return (
    <article
      className={cn(
        "group relative overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card",
        "shadow-[var(--shadow-soft)] transition-all duration-300",
        "hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-[var(--shadow-glow)]",
        "dark:bg-surface-elevated",
        className,
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 w-0.5 bg-accent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      />

      <div className="flex min-w-0 flex-col gap-0 sm:flex-row">
        <Link
          href={`/events/${event.slug}`}
          prefetch={false}
          className="relative aspect-[16/10] w-full shrink-0 overflow-hidden bg-ink sm:aspect-auto sm:h-auto sm:w-[11.5rem] md:w-[13.5rem] lg:w-[15rem]"
        >
          {cover ? (
            <Media
              src={cover}
              alt=""
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04] sm:absolute sm:inset-0"
            />
          ) : (
            <div className="padeya-hero-glow absolute inset-0 opacity-85" />
          )}
          <div
            aria-hidden
            className="absolute inset-0 bg-gradient-to-t from-ink/70 via-transparent to-transparent sm:bg-gradient-to-r sm:from-transparent sm:via-transparent sm:to-ink/40"
          />
          {event.featured ? (
            <span className="absolute left-2.5 top-2.5 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] text-primary-foreground">
              Featured
            </span>
          ) : null}
        </Link>

        <div className="flex min-w-0 flex-1 flex-col gap-4 p-4 sm:flex-row sm:items-stretch sm:gap-5 sm:p-5 md:p-6">
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex flex-wrap items-center gap-1.5">
              {event.category?.name ? (
                <Badge tone="outline" size="sm">
                  {event.category.name}
                </Badge>
              ) : null}
              {vip ? (
                <Badge tone="accent" size="sm">
                  VIP
                </Badge>
              ) : null}
              {free ? (
                <Badge tone="success" size="sm">
                  Free
                </Badge>
              ) : null}
              {online ? (
                <Badge tone="dark" size="sm">
                  Online
                </Badge>
              ) : null}
              {stock && !free ? (
                <Badge
                  tone={soldOut ? "danger" : "warning"}
                  size="sm"
                >
                  {stock}
                </Badge>
              ) : null}
            </div>

            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                {formatDate(event.start_datetime)}
                {time ? ` · ${time}` : ""}
              </p>
              <Link
                href={`/events/${event.slug}`}
                prefetch={false}
                className="block min-w-0"
              >
                <h3 className="text-balance text-lg font-extrabold tracking-tight text-foreground transition-colors group-hover:text-heading sm:text-xl md:text-[1.35rem] md:leading-snug">
                  {event.title}
                </h3>
              </Link>
              {place ? (
                <p className="truncate text-sm text-muted-foreground">
                  {place}
                </p>
              ) : null}
            </div>

            {hostName ? (
              <div className="flex items-center gap-2.5 pt-0.5">
                <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-[10px] font-extrabold text-foreground">
                  {hostInitials(hostName)}
                </span>
                {hostHref ? (
                  <Link
                    href={hostHref}
                    prefetch={false}
                    className="truncate text-sm font-medium text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                  >
                    {hostName}
                  </Link>
                ) : (
                  <span className="truncate text-sm font-medium text-muted-foreground">
                    {hostName}
                  </span>
                )}
              </div>
            ) : null}
          </div>

          <div className="flex shrink-0 flex-row items-center justify-between gap-3 border-t border-border/70 pt-3 sm:w-[9.5rem] sm:flex-col sm:items-end sm:justify-between sm:border-t-0 sm:pt-0 md:w-[10.5rem]">
            <div className="sm:text-right">
              {!free ? (
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                  From
                </p>
              ) : null}
              <p
                className={cn(
                  "text-base font-extrabold tracking-tight sm:text-lg",
                  free ? "text-accent" : "text-foreground",
                )}
              >
                {free ? "Free" : priceLabel(event).replace(/^From\s+/, "")}
              </p>
            </div>
            <Link
              href={`/events/${event.slug}`}
              prefetch={false}
              className="shrink-0"
            >
              <Button
                size="sm"
                variant={soldOut ? "secondary" : "primary"}
                className="min-w-[7.5rem]"
              >
                {soldOut ? "View event" : "Get tickets"}
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
