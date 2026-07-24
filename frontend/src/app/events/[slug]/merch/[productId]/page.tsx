"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EventMerchDetail } from "@/components/merch/EventMerchDetail";
import {
  Button,
  Card,
  Container,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
} from "@/components/ui";
import { fetchPublicEvent } from "@/lib/events-api";
import { fetchMerchCatalog } from "@/lib/merch-api";
import type { EventItem } from "@/lib/types/events";
import type { MerchCatalogProduct } from "@/lib/types/merch";

export default function EventMerchProductPage() {
  const params = useParams<{ slug: string; productId: string }>();
  const searchParams = useSearchParams();
  const referralCode = (searchParams.get("ref") || "").trim();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [product, setProduct] = useState<MerchCatalogProduct | null | undefined>(
    undefined,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const item = await fetchPublicEvent(params.slug);
        if (!active) return;
        setEvent(item);
        const catalog = await fetchMerchCatalog(item.id);
        if (!active) return;
        const found =
          catalog.find((p) => p.id === params.productId) ??
          catalog.find((p) => p.slug === params.productId) ??
          null;
        setProduct(found);
        if (!found) setError("This merch item is not available.");
      } catch {
        if (active) setError("Event not found.");
      }
    })();
    return () => {
      active = false;
    };
  }, [params.productId, params.slug]);

  if (error && !product) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          <EmptyState
            title="Merch unavailable"
            description={error}
            action={
              <Link href={`/events/${params.slug}`}>
                <Button variant="secondary">Back to event</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  if (!event || product === undefined) {
    return (
      <main className="bg-background py-16">
        <Container width="narrow">
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  if (!product) {
    return null;
  }

  return (
    <main className="bg-muted py-8 sm:py-12">
      <Container width="narrow" className="space-y-6">
        <SectionHeader
          eyebrow="Event merch"
          title={product.name}
          description="Pre-order official merch and pick it up at the event."
        />
        <Card className="space-y-4 p-4 sm:p-6">
          <EventMerchDetail
            product={product}
            eventId={event.id}
            eventSlug={event.slug}
            eventTitle={event.title}
            hostId={event.host_id}
            hostName={event.host_display_name}
            hostSlug={event.host_slug}
            referralCode={referralCode || undefined}
            showFullPageLink={false}
          />
        </Card>
        <div className="flex flex-wrap gap-2">
          <Link href={`/events/${event.slug}/merch`}>
            <Button variant="secondary">All merch</Button>
          </Link>
          <Link href={`/events/${event.slug}`}>
            <Button variant="ghost">Back to event</Button>
          </Link>
        </div>
      </Container>
    </main>
  );
}
