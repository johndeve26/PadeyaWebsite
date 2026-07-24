"use client";

import Link from "next/link";

import { Media } from "@/components/ui";
import { trackEventCardClick } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import type { RankedRelatedEvent } from "@/lib/discovery/related-discovery";
import { lowestTicketPrice } from "@/lib/discovery/related-discovery";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import { formatDateTime, formatNgn } from "@/lib/format";

export function RelatedDiscoveryEventCard({
  item,
  className,
}: {
  item: RankedRelatedEvent;
  className?: string;
}) {
  const { event, badge } = item;
  const place = formatPublicPlaceLabel(event);
  const price = lowestTicketPrice(event);
  const priceLabel =
    price == null ? null : price === 0 ? "Free" : `From ${formatNgn(price)}`;
  const image =
    event.banner_url || event.mobile_banner_url || event.social_share_image_url;

  return (
    <Link
      href={`/events/${event.slug}`}
      onClick={() => {
        trackEventCardClick({
          targetEventId: event.id,
          hostId: event.host_id,
          listContext: "related_events",
          clickTarget: item.relationship,
        });
      }}
      className={cn(
        "group flex h-full min-w-0 flex-col overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)]",
        "dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        "transition-transform duration-300 hover:-translate-y-0.5 hover:shadow-[var(--shadow)]",
        className,
      )}
    >
      <div className="relative aspect-[16/10] overflow-hidden bg-ink">
        {image ? (
          <Media
            src={image}
            alt=""
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="padeya-hero-glow absolute inset-0 opacity-80" />
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/75 to-transparent px-3 pb-3 pt-8">
          <span className="inline-flex rounded-[var(--radius-sm)] bg-accent px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-primary-foreground">
            {badge}
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
        <div className="space-y-1.5">
          {event.category?.name ? (
            <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
              {event.category.name}
            </p>
          ) : null}
          <h3 className="line-clamp-2 text-lg font-extrabold tracking-tight text-foreground">
            {event.title}
          </h3>
          <p className="text-sm text-muted-foreground">
            {formatDateTime(event.start_datetime)}
          </p>
        </div>

        <dl className="mt-auto space-y-1 text-sm text-muted-foreground">
          {place ? (
            <div className="flex gap-2">
              <dt className="sr-only">Place</dt>
              <dd className="line-clamp-1">{place}</dd>
            </div>
          ) : null}
          {event.host_display_name ? (
            <div className="flex gap-2">
              <dt className="sr-only">Host</dt>
              <dd className="line-clamp-1 font-medium text-foreground">
                {event.host_display_name}
              </dd>
            </div>
          ) : null}
        </dl>

        <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
          <p className="text-sm font-extrabold text-foreground">
            {priceLabel ?? "See tickets"}
          </p>
          <span className="text-xs font-extrabold uppercase tracking-wide text-foreground underline decoration-accent underline-offset-4">
            View event
          </span>
        </div>
      </div>
    </Link>
  );
}
