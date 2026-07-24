"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { Button, Input, SkeletonLoader } from "@/components/ui";
import {
  CHECKOUT_BUYER_EMAIL_KEY,
  downloadOrderPdfByReference,
  fetchOrderSummaryByReference,
  type OrderReferenceSummary,
} from "@/lib/commerce-api";

function safeRef(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().slice(0, 64);
  if (!/^[a-zA-Z0-9_\-]+$/.test(trimmed)) return null;
  return trimmed;
}

function CheckoutSuccessInner() {
  const params = useSearchParams();
  const { user } = useAuth();
  const orderRef =
    safeRef(params.get("order")) ||
    safeRef(params.get("order_id")) ||
    safeRef(params.get("reference"));

  const [email, setEmail] = useState("");
  const [summary, setSummary] = useState<OrderReferenceSummary | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.email) {
      setEmail(user.email);
      return;
    }
    try {
      const stored = sessionStorage.getItem(CHECKOUT_BUYER_EMAIL_KEY);
      if (stored) setEmail(stored);
    } catch {
      /* ignore */
    }
  }, [user?.email]);

  useEffect(() => {
    if (!orderRef || !email.trim()) return;
    let active = true;
    const load = async () => {
      try {
        const row = await fetchOrderSummaryByReference(orderRef, email);
        if (active) {
          setSummary(row);
          setPollError(null);
        }
      } catch {
        if (active) {
          setPollError(
            "We could not verify this order yet. Check the email you used at checkout.",
          );
        }
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), 4000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [orderRef, email]);

  async function onDownloadPdf() {
    if (!orderRef || !email.trim()) return;
    setDownloadBusy(true);
    setDownloadError(null);
    try {
      await downloadOrderPdfByReference(orderRef, email);
    } catch (err) {
      setDownloadError(
        err instanceof Error ? err.message : "Could not download PDF.",
      );
    } finally {
      setDownloadBusy(false);
    }
  }

  const pdfReady = Boolean(summary?.pdf_available);
  const waitingForPayment = summary?.status === "pending";

  return (
    <PublicPageShell
      eyebrow="Checkout"
      title="You're all set"
      description="Thanks for choosing Pàdéyá. Watch your inbox for your receipt and set-password link (if you checked out without signing in). Ticket and order PDFs are emailed to you and any ticket recipients too."
      actions={
        <PublicCtaPair
          primaryHref={
            orderRef ? `/dashboard/orders/${orderRef}` : "/dashboard/tickets"
          }
          primaryLabel={orderRef ? "View order" : "My tickets"}
          secondaryHref="/login"
          secondaryLabel="Sign in"
        />
      }
      narrow
    >
      <div className="mx-auto max-w-lg space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-6 dark:bg-surface-elevated">
        <p className="text-center text-sm text-muted-foreground">
          {orderRef ? (
            <>
              Reference{" "}
              <span className="font-semibold text-foreground">{orderRef}</span>
            </>
          ) : (
            <>
              Open{" "}
              <Link href="/dashboard/orders" className="font-semibold text-primary">
                Orders
              </Link>{" "}
              or{" "}
              <Link href="/dashboard/tickets" className="font-semibold text-primary">
                Tickets
              </Link>
              .
            </>
          )}
        </p>

        {orderRef && !user ? (
          <Input
            label="Checkout email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            hint="Same address you used to pay — needed to download your PDF."
            autoComplete="email"
          />
        ) : null}

        {pollError ? (
          <p className="text-sm text-destructive">{pollError}</p>
        ) : null}

        {waitingForPayment ? (
          <p className="text-sm text-muted-foreground">
            Confirming payment… this usually takes a few seconds.
          </p>
        ) : null}

        {pdfReady ? (
          <Button
            type="button"
            className="w-full"
            disabled={downloadBusy || !email.trim()}
            onClick={() => void onDownloadPdf()}
          >
            {downloadBusy ? "Preparing PDF…" : "Download order PDF"}
          </Button>
        ) : orderRef && email.trim() && !pollError ? (
          <p className="text-sm text-muted-foreground">
            PDF download unlocks when payment is confirmed.
          </p>
        ) : null}

        {downloadError ? (
          <p className="text-sm text-destructive">{downloadError}</p>
        ) : null}

        <p className="text-center text-sm text-muted-foreground">
          We also email PDFs to the buyer and anyone who received tickets in
          this order. Use the set-password link in your inbox to open your
          dashboard.
        </p>
      </div>
    </PublicPageShell>
  );
}

export default function CheckoutSuccessPage() {
  return (
    <Suspense fallback={<SkeletonLoader className="mx-auto mt-20 max-w-md" />}>
      <CheckoutSuccessInner />
    </Suspense>
  );
}
