"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import { EventMerchCatalog } from "@/components/merch/EventMerchCatalog";
import { Button } from "@/components/ui";
import { trackMerchSectionViewed } from "@/lib/analytics";
import { fetchMerchCatalog } from "@/lib/merch-api";
import type { MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  eventId: string;
  eventSlug: string;
  eventTitle: string;
  hostId?: string | null;
  hostName?: string | null;
  hostSlug?: string | null;
  referralCode?: string;
  /** Host event preview — show a small empty note instead of hiding. */
  previewMode?: boolean;
  /** Own-host owner — no buyer CTAs; link to manage event. */
  ownHostMode?: boolean;
};

/** Public event page merch panel — hidden when catalog is empty (except host preview). */
export function EventMerchSection({
  eventId,
  eventSlug,
  eventTitle,
  hostId,
  hostName,
  hostSlug,
  referralCode,
  previewMode = false,
  ownHostMode = false,
}: Props) {
  const [products, setProducts] = useState<MerchCatalogProduct[] | null>(null);
  const trackedRef = useRef(false);

  useEffect(() => {
    let active = true;
    void fetchMerchCatalog(eventId)
      .then((rows) => {
        if (active) setProducts(rows);
      })
      .catch(() => {
        if (active) setProducts([]);
      });
    return () => {
      active = false;
    };
  }, [eventId]);

  useEffect(() => {
    if (!products || trackedRef.current || previewMode) return;
    const onPage = products.filter((p) => p.show_on_event_page !== false);
    if (onPage.length === 0) return;
    trackedRef.current = true;
    trackMerchSectionViewed({
      targetEventId: eventId,
      hostId: hostId ?? undefined,
      productCount: onPage.length,
    });
  }, [products, eventId, hostId, previewMode]);

  if (products === null) return null;

  const onPage = products.filter((p) => p.show_on_event_page !== false);

  if (onPage.length === 0) {
    if (!previewMode) return null;
    return (
      <EventDetailPanel title="Official event merch">
        <p className="text-sm text-muted-foreground">No merch yet</p>
      </EventDetailPanel>
    );
  }

  const drops = onPage.filter((p) => p.is_post_event_drop);
  const hasDrops = drops.length > 0;
  const title =
    hasDrops && drops.length === onPage.length
      ? "Post-event merch"
      : "Official event merch";
  const blurb = hasDrops
    ? "Recap merch and limited souvenirs from this event on Pàdéyá."
    : "Pre-order official merch and pick it up at the event.";
  const merchHref = `/events/${eventSlug}/merch${
    referralCode ? `?ref=${referralCode}` : ""
  }`;
  const manageEventHref = `/host/events/${eventId}`;

  if (ownHostMode) {
    return (
      <EventDetailPanel title={title}>
        <p className="mb-4 text-sm leading-relaxed text-muted-foreground">
          Merch for this event is managed from your host workspace.
        </p>
        <Link href={manageEventHref}>
          <Button size="sm">Manage event</Button>
        </Link>
      </EventDetailPanel>
    );
  }

  return (
    <EventDetailPanel
      title={title}
      action={
        <Link
          href={merchHref}
          className="text-xs font-extrabold uppercase tracking-wide text-accent"
        >
          View all merch
        </Link>
      }
    >
      <p className="mb-4 text-sm leading-relaxed text-muted-foreground">
        {blurb}
      </p>
      <EventMerchCatalog
        eventId={eventId}
        eventSlug={eventSlug}
        eventTitle={eventTitle}
        hostId={hostId}
        hostName={hostName}
        hostSlug={hostSlug}
        referralCode={referralCode}
        compact
        products={products}
      />
      <div className="mt-4">
        <Link href={merchHref}>
          <Button size="sm" variant="secondary">
            View all merch
          </Button>
        </Link>
      </div>
    </EventDetailPanel>
  );
}
