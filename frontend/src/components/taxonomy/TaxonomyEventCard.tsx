import Link from "next/link";

import { EventHoverPreview } from "@/components/discovery/EventHoverPreview";
import { Badge, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import { ticketAvailabilityLabel } from "@/lib/discovery/marketplace-groups";
import { citySlugFromName } from "@/lib/discovery/slugify";
import { formatPublicPlaceLabel, locationVisibilityOf } from "@/lib/event-privacy";
import { formatDateTime, formatNgn } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import { eventCardAlt } from "@/lib/seo/image-alt";
import type { EventItem } from "@/lib/types/events";

export type TaxonomyEventCardProps = {
  event?: EventItem;
  title?: string;
  slug?: string;
  city?: string | null;
  category?: string | null;
  className?: string;
  /** Larger media + stronger title for spotlight. */
  featured?: boolean;
  /** Horizontal-leaning denser card for supporting rail. */
  compact?: boolean;
  /** Desktop hover preview popover. */
  preview?: boolean;
};

function priceFrom(event?: EventItem): string | null {
  if (!event) return null;
  const types = event.ticket_types ?? [];
  if (!types.length) return null;
  const prices = types
    .map((t) => Number(t.price))
    .filter((n) => Number.isFinite(n));
  if (!prices.length) return null;
  const min = Math.min(...prices);
  if (min === 0) return "Free";
  return `From ${formatNgn(min)}`;
}

function hostInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

function privacyNote(event?: EventItem): string | null {
  if (!event?.location_visibility) return null;
  const v = String(event.location_visibility);
  if (v === "area_only") return "Area shown · full address private";
  if (
    v === "hidden_until_payment" ||
    v === "hidden_until_24h_before" ||
    v === "hidden_until_manual_approval"
  ) {
    return "Exact venue revealed later";
  }
  if (v === "online_only") return "Online event";
  return null;
}

/** Discovery card with internal links into taxonomy hubs. */
export function TaxonomyEventCard({
  event,
  title,
  slug,
  city,
  category,
  className = "",
  featured = false,
  compact = false,
  preview = false,
}: TaxonomyEventCardProps) {
  const resolvedTitle = event?.title ?? title ?? "Event";
  const resolvedSlug = event?.slug ?? slug ?? "";
  const resolvedCity = event?.city ?? city;
  const place = event
    ? formatPublicPlaceLabel(event)
    : city || null;
  const resolvedCategory = event?.category?.name ?? category;
  const categorySlug = event?.category?.slug;
  const visibility = event ? locationVisibilityOf(event) : "full_public";
  const citySlug =
    visibility === "full_public" || visibility === "area_only"
      ? resolvedCity
        ? citySlugFromName(resolvedCity)
        : null
      : null;
  const hostSlug = event?.host_slug;
  const hostName = event?.host_display_name;
  const cover = event
    ? resolveEventImage(
        event.slug,
        event.title,
        event.banner_url,
        event.category?.name || event.category?.slug,
      )
    : null;
  const when = event?.start_datetime
    ? formatDateTime(event.start_datetime)
    : null;
  const price = priceFrom(event);
  const stock = event ? ticketAvailabilityLabel(event) : null;
  const privacy = privacyNote(event);
  const badgeSide = event ? event.id.charCodeAt(0) % 2 === 0 : false;

  return (
    <article
      className={cn(
        "padeya-discovery-card group relative flex rounded-[var(--radius-lg)] border border-border bg-card",
        compact ? "flex-row overflow-hidden" : "h-full flex-col",
        className,
      )}
    >
      {preview && event && !compact ? (
        <EventHoverPreview event={event} />
      ) : null}
      <Link
        href={`/events/${resolvedSlug}`}
        className={cn(
          "relative block overflow-hidden bg-ink",
          compact
            ? "relative w-[38%] min-w-[7.5rem] shrink-0 self-stretch"
            : "aspect-[16/10] rounded-t-[var(--radius-lg)]",
        )}
      >

        {cover ? (
          <Media
            src={cover}
            alt={eventCardAlt(event?.title || title)}
            className={cn(
              "padeya-image-zoom h-full w-full object-cover",
              compact ? "absolute inset-0" : "",
            )}
          />
        ) : (
          <div
            aria-hidden
            className="padeya-hero-glow absolute inset-0 opacity-90"
          />
        )}
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-ink/75 via-transparent to-transparent"
        />
        <div
          className={cn(
            "absolute top-2.5 flex flex-wrap gap-1.5",
            badgeSide ? "right-2.5 justify-end" : "left-2.5",
          )}
        >
          {event?.featured ? <Badge tone="accent" size="sm">Featured</Badge> : null}
          {resolvedCategory && !compact ? (
            <Badge tone="dark" size="sm">
              {resolvedCategory}
            </Badge>
          ) : null}
        </div>
        {stock ? (
          <div
            className={cn(
              "absolute top-2.5",
              badgeSide ? "left-2.5" : "right-2.5",
            )}
          >
            <Badge
              tone={stock === "Sold out" ? "danger" : "warning"}
              size="sm"
            >
              {stock}
            </Badge>
          </div>
        ) : null}
        {price && !compact ? (
          <p className="absolute bottom-3 left-3 text-sm font-extrabold text-paper drop-shadow sm:text-base">
            {price}
          </p>
        ) : null}
      </Link>

      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col gap-2",
          compact ? "p-3.5 sm:p-4" : "p-4 sm:p-5",
        )}
      >
        <Link href={`/events/${resolvedSlug}`} className="block min-w-0 flex-1 space-y-1.5">
          <h3
            className={cn(
              "line-clamp-2 text-balance font-extrabold tracking-tight text-foreground",
              featured
                ? "text-xl sm:text-2xl"
                : compact
                  ? "text-sm sm:text-base"
                  : "text-base sm:text-lg",
            )}
          >
            {resolvedTitle}
          </h3>
          {when ? (
            <p
              className={cn(
                "font-medium text-foreground/80",
                compact ? "text-xs sm:text-sm" : "text-sm sm:text-[0.95rem]",
              )}
            >
              {when}
            </p>
          ) : null}
          {place ? (
            <p
              className={cn(
                "text-muted-foreground",
                compact ? "text-xs sm:text-sm" : "text-sm",
              )}
            >
              {place}
            </p>
          ) : null}
          {privacy ? (
            <p className="text-xs font-semibold text-muted-foreground">{privacy}</p>
          ) : null}
          {price && compact ? (
            <p className="text-sm font-extrabold text-foreground">{price}</p>
          ) : null}
        </Link>

        {hostName ? (
          <div className="flex items-center gap-2">
            <span
              aria-hidden
              className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-muted text-[10px] font-extrabold text-foreground"
            >
              {hostInitials(hostName)}
            </span>
            {hostSlug ? (
              <Link
                href={`/@${hostSlug}`}
                onClick={(e) => e.stopPropagation()}
                className="truncate text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                {hostName}
              </Link>
            ) : (
              <p className="truncate text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                {hostName}
              </p>
            )}
          </div>
        ) : null}

        <div
          className={cn(
            "mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border text-sm",
            compact ? "pt-2.5" : "pt-3",
          )}
        >
          {resolvedCity && citySlug ? (
            <Link
              href={`/events/city/${citySlug}`}
              onClick={(e) => e.stopPropagation()}
              className="font-semibold text-foreground underline-offset-2 hover:underline"
            >
              {resolvedCity}
            </Link>
          ) : null}
          {resolvedCategory && categorySlug ? (
            <Link
              href={
                citySlug
                  ? `/events/city/${citySlug}/${categorySlug}`
                  : `/events/c/${categorySlug}`
              }
              onClick={(e) => e.stopPropagation()}
              className="text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              {resolvedCategory}
            </Link>
          ) : null}
        </div>
      </div>
    </article>
  );
}
