"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EventMerchCatalog } from "@/components/merch/EventMerchCatalog";
import { EventMerchHero } from "@/components/merch/EventMerchHero";
import { MerchCartSummary } from "@/components/merch/MerchCartSummary";
import {
  Button,
  Container,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import {
  captureAmbassadorReferral,
  readAmbassadorCodeFromSearchParams,
} from "@/lib/ambassador-referral";
import { fetchPublicEvent } from "@/lib/events-api";
import {
  buildDraftCartCheckoutHref,
  draftCartItemCount,
  readMerchDraftCart,
  upsertMerchDraftLine,
  writeMerchDraftCart,
  type MerchDraftCart,
} from "@/lib/merch-draft-cart";
import { trackAmbassadorReferralLanding } from "@/lib/referral-click-track";
import type { EventItem } from "@/lib/types/events";

export default function EventMerchPage() {
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const referralCode = readAmbassadorCodeFromSearchParams(searchParams);
  const [event, setEvent] = useState<EventItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cart, setCart] = useState<MerchDraftCart | null>(null);
  const [meta, setMeta] = useState({
    hasShipping: false,
    hasVault: false,
    hasLowStock: false,
    productCount: 0,
  });
  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: event?.host_id,
    hostSlug: event?.host_slug,
  });

  useEffect(() => {
    void fetchPublicEvent(params.slug)
      .then((item) => {
        setEvent(item);
        setCart(readMerchDraftCart(item.id));
        if (referralCode) {
          captureAmbassadorReferral(params.slug, referralCode);
          captureAmbassadorReferral(item.id, referralCode);
          void trackAmbassadorReferralLanding({
            referral_code: referralCode,
            event_id: item.id,
            landing_path: `/events/${params.slug}/merch?ref=${referralCode}`,
            source: "merch_page",
          });
        }
      })
      .catch(() => setError("Event not found."));
  }, [params.slug, referralCode]);

  if (error) {
    return (
      <main className="bg-background py-16">
        <Container>
          <EmptyState
            title="Merch unavailable"
            description={error}
            action={
              <Link href="/events">
                <Button variant="secondary">Browse events</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  if (!event) {
    return (
      <main className="bg-background py-16">
        <Container>
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  const cartCount = draftCartItemCount(cart);
  const checkoutHref =
    cart && cart.lines.length > 0
      ? buildDraftCartCheckoutHref({
          eventSlug: event.slug,
          cart,
          referralCode: referralCode || undefined,
        })
      : `/events/${event.slug}/checkout${
          referralCode ? `?ref=${referralCode}` : ""
        }`;

  const hostStoreHref = event.host_slug
    ? `/u/${event.host_slug}/merch`
    : null;
  const manageEventHref = `/host/events/${event.id}`;

  if (isOwnHost) {
    return (
      <main className="bg-background py-16">
        <Container className="max-w-xl space-y-4 text-center">
          <EmptyState
            title="This is your event merch"
            description="Buy and promote merch from your Host workspace — Personal checkout is blocked for your own host."
            action={
              <Link href={manageEventHref}>
                <Button>Manage event</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  function removeLine(variantId: string) {
    if (!cart) return;
    const line = cart.lines.find((l) => l.variantId === variantId);
    if (!line) return;
    const next = upsertMerchDraftLine(cart, { ...line, quantity: 0 });
    writeMerchDraftCart(next);
    setCart(next);
  }

  return (
    <main className="bg-background pb-24 pt-8 sm:pt-10 lg:pb-16">
      <Container className="space-y-10">
        <EventMerchHero
          event={event}
          hasShipping={meta.hasShipping}
          hasVault={meta.hasVault}
          hasLowStock={meta.hasLowStock}
          cartCount={cartCount}
          checkoutHref={checkoutHref}
          hostStoreHref={hostStoreHref}
        />

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-w-0 space-y-8">
            <EventMerchCatalog
              eventId={event.id}
              eventSlug={event.slug}
              eventTitle={event.title}
              hostId={event.host_id}
              hostName={event.host_display_name}
              hostSlug={event.host_slug}
              referralCode={referralCode || undefined}
              cart={cart}
              onCartChange={setCart}
              onMetaChange={setMeta}
            />
          </div>

          <div className="hidden lg:block">
            <div className="sticky top-24">
              <MerchCartSummary
                cart={cart}
                checkoutHref={checkoutHref}
                allowMerchOnly={Boolean(event.allow_merch_only_checkout)}
                onRemoveLine={removeLine}
              />
            </div>
          </div>
        </div>
      </Container>

      <MerchCartSummary
        variant="mobile-bar"
        cart={cart}
        checkoutHref={checkoutHref}
        allowMerchOnly={Boolean(event.allow_merch_only_checkout)}
      />
    </main>
  );
}
