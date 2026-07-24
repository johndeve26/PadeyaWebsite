"use client";

import Link from "next/link";

import { Badge, Button } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import type { EventItem } from "@/lib/types/events";

type Props = {
  event: EventItem;
  hasShipping?: boolean;
  hasVault?: boolean;
  hasLowStock?: boolean;
  cartCount?: number;
  checkoutHref: string;
  hostStoreHref?: string | null;
};

export function EventMerchHero({
  event,
  hasShipping = false,
  hasVault = false,
  hasLowStock = false,
  cartCount = 0,
  checkoutHref,
  hostStoreHref,
}: Props) {
  const location =
    event.public_location_label ||
    [event.city, event.state].filter(Boolean).join(", ") ||
    null;

  return (
    <header className="space-y-5">
      <nav
        aria-label="Breadcrumb"
        className="flex flex-wrap items-center gap-1.5 text-xs font-bold text-muted-foreground"
      >
        <Link href="/events" className="hover:text-foreground">
          Events
        </Link>
        <span aria-hidden>/</span>
        <Link
          href={`/events/${event.slug}`}
          className="max-w-[12rem] truncate hover:text-foreground sm:max-w-none"
        >
          {event.title}
        </Link>
        <span aria-hidden>/</span>
        <span className="text-foreground">Merch</span>
      </nav>

      <div className="space-y-3">
        <p className="text-[11px] font-extrabold uppercase tracking-[0.2em] text-muted-foreground">
          Official event merch
        </p>
        <h1 className="max-w-3xl text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">
          {event.title}
        </h1>
        <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
          Pre-order official merch and pick it up at the event.
        </p>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
        {event.start_datetime ? (
          <span>{formatDateTime(event.start_datetime)}</span>
        ) : null}
        {location ? <span>{location}</span> : null}
        {event.host_display_name ? (
          <span>
            Hosted by{" "}
            {event.host_slug ? (
              <Link
                href={`/@${event.host_slug}`}
                className="font-bold text-foreground underline-offset-2 hover:underline"
              >
                {event.host_display_name}
              </Link>
            ) : (
              <span className="font-bold text-foreground">
                {event.host_display_name}
              </span>
            )}
          </span>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-1.5">
        <Badge tone="outline" size="sm">
          Pickup at event
        </Badge>
        {hasShipping ? (
          <Badge tone="outline" size="sm">
            Shipping available
          </Badge>
        ) : null}
        {hasVault ? (
          <Badge tone="accent" size="sm">
            Vault exclusives
          </Badge>
        ) : null}
        {hasLowStock ? (
          <Badge tone="warning" size="sm">
            Limited stock
          </Badge>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <Link href={`/events/${event.slug}`}>
          <Button variant="secondary" size="sm">
            Back to event
          </Button>
        </Link>
        {hostStoreHref ? (
          <Link href={hostStoreHref}>
            <Button variant="secondary" size="sm">
              View host merch store
            </Button>
          </Link>
        ) : null}
        {cartCount > 0 ? (
          <Link href={checkoutHref}>
            <Button size="sm">Go to checkout</Button>
          </Link>
        ) : null}
      </div>
    </header>
  );
}
