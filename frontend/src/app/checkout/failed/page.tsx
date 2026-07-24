"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { SkeletonLoader } from "@/components/ui";

function safeRef(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().slice(0, 64);
  if (!/^[a-zA-Z0-9_\-]+$/.test(trimmed)) return null;
  return trimmed;
}

function CheckoutFailedInner() {
  const params = useSearchParams();
  const orderRef =
    safeRef(params.get("order")) ||
    safeRef(params.get("order_id")) ||
    safeRef(params.get("reference"));
  const eventSlug = safeRef(params.get("event"));

  return (
    <PublicPageShell
      eyebrow="Checkout"
      title="Payment didn’t complete"
      description="No worries — you weren’t charged for a failed confirmation. You can retry checkout or contact Support with your reference."
      actions={
        <PublicCtaPair
          primaryHref={
            eventSlug ? `/events/${eventSlug}/checkout` : "/events"
          }
          primaryLabel={eventSlug ? "Try checkout again" : "Browse events"}
          secondaryHref="/support/new?category=payments_refunds"
          secondaryLabel="Contact support"
        />
      }
      narrow
    >
      <div className="mx-auto max-w-lg rounded-[var(--radius-lg)] border border-border bg-card p-6 text-center dark:bg-surface-elevated">
        <p className="text-sm text-muted-foreground">
          {orderRef ? (
            <>
              Reference{" "}
              <span className="font-semibold text-foreground">{orderRef}</span>
            </>
          ) : (
            <>If you have an order ID from email, include it in your ticket.</>
          )}
        </p>
        <p className="mt-3 text-xs text-muted-foreground">
          Status only — we do not display bank payloads, card data, or gateway
          secrets here. Check{" "}
          <Link href="/dashboard/orders" className="font-semibold text-primary">
            Orders
          </Link>{" "}
          after a few moments if you believe payment succeeded.
        </p>
      </div>
    </PublicPageShell>
  );
}

export default function CheckoutFailedPage() {
  return (
    <Suspense fallback={<SkeletonLoader className="mx-auto mt-20 max-w-md" />}>
      <CheckoutFailedInner />
    </Suspense>
  );
}
