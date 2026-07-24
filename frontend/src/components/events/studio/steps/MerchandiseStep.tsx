"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, EmptyState, SkeletonLoader, StatusBadge } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { fetchHostMerchProducts } from "@/lib/merch-api";
import type { MerchProduct } from "@/lib/types/merch";

import { EventStudioSection } from "../EventStudioSection";

export function MerchandiseStep({ eventId }: { eventId?: string }) {
  const [products, setProducts] = useState<MerchProduct[] | null>(null);

  useEffect(() => {
    if (!eventId) return;
    let active = true;
    void fetchHostMerchProducts(eventId)
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

  return (
    <EventStudioSection
      title="Merchandise"
      description="Optional pickup-only merch for this event. Not required to publish — skip anytime."
    >
      {!eventId ? (
        <EmptyState
          title="Save a draft first"
          description="Create the event draft, then come back to add merch — or manage it later from Event ops."
        />
      ) : (
        <div className="space-y-4">
          {products === null ? (
            <SkeletonLoader lines={3} />
          ) : products.length > 0 ? (
            <ul className="space-y-3">
              {products.slice(0, 5).map((product) => (
                <li
                  key={product.id}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3 last:border-0"
                >
                  <div>
                    <p className="font-bold text-foreground">{product.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatNgn(product.base_price)} ·{" "}
                      {product.total_inventory ?? 0} in stock
                    </p>
                  </div>
                  <StatusBadge status={product.status} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No merch yet"
              description="Add tees, caps, or masks buyers can collect at the door. Completely optional."
            />
          )}
          <div className="flex flex-wrap gap-2">
            <Link href={`/host/events/${eventId}/merchandise/new`}>
              <Button size="sm">Add merch product</Button>
            </Link>
            <Link href={`/host/events/${eventId}/merchandise`}>
              <Button size="sm" variant="secondary">
                Open merch studio
              </Button>
            </Link>
            <Link href={`/host/events/${eventId}/merchandise/fulfillment`}>
              <Button size="sm" variant="ghost">
                Fulfillment
              </Button>
            </Link>
          </div>
          <p className="text-xs text-muted-foreground">
            You can continue without merch. Publishing does not require products.
          </p>
        </div>
      )}
    </EventStudioSection>
  );
}
