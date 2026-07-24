"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { EmailVerificationBanner } from "@/components/auth/EmailVerificationBanner";
import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { Alert, Button, Card, Input, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { claimGuestOrder, startGuestOrderClaim } from "@/lib/commerce-api";

function safeToken(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().slice(0, 200);
  if (!/^[A-Za-z0-9_\-]+$/.test(trimmed)) return null;
  return trimmed;
}

function safeRef(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().slice(0, 64);
  if (!/^[a-zA-Z0-9_\-]+$/.test(trimmed)) return null;
  return trimmed;
}

function normalizeOrderReference(raw: string): string {
  const cleaned = raw.replace(/\s+/g, "");
  if (!cleaned) return "";
  const upper = cleaned.toUpperCase();
  if (upper.startsWith("PDY-")) {
    return `PDY-${upper.slice(4)}`;
  }
  return upper;
}

function AccountTicketsPanel({ signedIn }: { signedIn: boolean }) {
  return (
    <Card className="space-y-3 border-primary/30 bg-primary/5 p-5 dark:bg-primary/10">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
        Have a Pàdéyá account?
      </p>
      <h2 className="text-lg font-extrabold text-foreground">
        You don&apos;t need this guest page
      </h2>
      <p className="text-sm text-muted-foreground">
        {signedIn
          ? "If you paid while signed in, your tickets and receipt are already on your account."
          : "If you checked out while logged in, sign in and open My tickets or Orders — no claim link required."}
      </p>
      <div className="flex flex-wrap gap-2 pt-1">
        {signedIn ? (
          <>
            <Link href="/dashboard/tickets">
              <Button size="sm">My tickets</Button>
            </Link>
            <Link href="/dashboard/orders">
              <Button size="sm" variant="secondary">
                Orders
              </Button>
            </Link>
          </>
        ) : (
          <>
            <Link href="/login?next=/dashboard/tickets">
              <Button size="sm">Log in</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" variant="secondary">
                Create account
              </Button>
            </Link>
          </>
        )}
      </div>
    </Card>
  );
}

function ClaimInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const token = safeToken(params.get("token"));
  const orderRefFromQuery = safeRef(params.get("order"));
  const [reference, setReference] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onAccountOrderId, setOnAccountOrderId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (orderRefFromQuery) {
      setReference(orderRefFromQuery);
    }
  }, [orderRefFromQuery]);

  useEffect(() => {
    if (user?.email && !email.trim()) {
      setEmail(user.email);
    }
  }, [user, email]);

  async function onClaim() {
    if (!token) {
      setError("Missing or invalid claim link.");
      return;
    }
    if (!user) {
      setError("Log in or create an account with the buyer email, then claim.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await claimGuestOrder(token);
      setMessage(result.message);
      router.push("/dashboard/tickets");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not claim tickets");
    } finally {
      setBusy(false);
    }
  }

  async function onResend() {
    const ref = normalizeOrderReference(reference);
    const buyerEmail = email.trim();
    if (!ref || !buyerEmail) {
      setError("Enter the order reference and buyer email.");
      setMessage(null);
      return;
    }
    if (!ref.startsWith("PDY-")) {
      setError("Order reference should start with PDY- (from your receipt).");
      setMessage(null);
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    setOnAccountOrderId(null);
    try {
      const result = await startGuestOrderClaim({
        order_reference: ref,
        email: buyerEmail,
      });
      if (result.status === "on_account" && result.order_id) {
        setOnAccountOrderId(result.order_id);
        return;
      }
      setMessage(result.detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not send claim link");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <SkeletonLoader className="mx-auto mt-20 max-w-md" />;
  }

  const loginNext = token
    ? `/checkout/claim?token=${token}${orderRefFromQuery ? `&order=${orderRefFromQuery}` : ""}`
    : "/checkout/claim";

  return (
    <PublicPageShell
      eyebrow="Guest checkout only"
      title="Claim guest tickets"
      description="For people who paid without a Pàdéyá account. Use the email link after payment, or request a new link below."
      actions={
        <PublicCtaPair
          primaryHref={user ? "/dashboard/tickets" : `/login?next=${encodeURIComponent(loginNext)}`}
          primaryLabel={user ? "My tickets" : "Log in (guest buyers)"}
          secondaryHref="/dashboard/orders"
          secondaryLabel="Orders"
        />
      }
      narrow
    >
      {user && !user.is_verified ? (
        <EmailVerificationBanner className="mx-auto mb-4 max-w-lg" />
      ) : null}

      <div className="mx-auto max-w-lg space-y-4">
        <AccountTicketsPanel signedIn={Boolean(user)} />

        <Card className="space-y-4 p-6 dark:bg-surface-elevated">
          <div className="space-y-1">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
              Guest checkout
            </p>
            <h2 className="text-lg font-extrabold text-foreground">
              {token ? "Complete your claim" : "Resend your claim link"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {token
                ? "This secure link is from your guest confirmation email. Log in with the same buyer email, then claim tickets to your account."
                : "Lost the email? Enter your order reference and the buyer email from checkout. We’ll send a new claim link — guest orders only."}
            </p>
          </div>

          {token ? (
            <>
              <p className="text-sm text-muted-foreground">
                {orderRefFromQuery ? (
                  <>
                    Order{" "}
                    <span className="font-semibold text-foreground">
                      {orderRefFromQuery}
                    </span>
                  </>
                ) : (
                  "Secure claim link ready."
                )}
              </p>
              <Button
                className="w-full"
                disabled={busy || !user}
                onClick={() => void onClaim()}
              >
                {busy ? "Claiming…" : "Claim tickets to my account"}
              </Button>
              {!user ? (
                <p className="text-xs text-muted-foreground">
                  <Link
                    href={`/login?next=${encodeURIComponent(loginNext)}`}
                    className="font-semibold text-foreground underline-offset-2 hover:underline"
                  >
                    Log in
                  </Link>{" "}
                  or{" "}
                  <Link
                    href={`/register?next=${encodeURIComponent(loginNext)}`}
                    className="font-semibold text-foreground underline-offset-2 hover:underline"
                  >
                    create an account
                  </Link>{" "}
                  with the buyer email first.
                </p>
              ) : null}
            </>
          ) : (
            <div className="space-y-3">
              <Input
                label="Order reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="PDY-A940B8FDCBEAC920"
                autoComplete="off"
              />
              <p className="text-xs text-muted-foreground">
                From your guest receipt or confirmation email — not the bank transaction
                ID.
              </p>
              <Input
                label="Buyer email (guest checkout)"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
              <Button
                className="w-full"
                variant="secondary"
                disabled={busy || !reference.trim() || !email.trim()}
                onClick={() => void onResend()}
              >
                {busy ? "Sending…" : "Email guest claim link"}
              </Button>
            </div>
          )}

          {onAccountOrderId ? (
            <Alert tone="success" title="Already on a Pàdéyá account">
              <p>
                {user
                  ? "That order was not guest checkout — your tickets are already on this account."
                  : "That order is on a Pàdéyá account. Sign in with the buyer email you used at checkout."}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link href={`/dashboard/orders/${onAccountOrderId}`}>
                  <Button size="sm">View order</Button>
                </Link>
                <Link href="/dashboard/tickets">
                  <Button size="sm" variant="secondary">
                    My tickets
                  </Button>
                </Link>
              </div>
            </Alert>
          ) : null}
          {message ? (
            <Alert tone="success" title="Sent">
              {message}
            </Alert>
          ) : null}
          {error ? (
            <Alert tone="danger" title="Couldn’t complete guest claim">
              {error}
            </Alert>
          ) : null}
        </Card>
      </div>
    </PublicPageShell>
  );
}

export default function CheckoutClaimPage() {
  return (
    <Suspense fallback={<SkeletonLoader className="mx-auto mt-20 max-w-md" />}>
      <ClaimInner />
    </Suspense>
  );
}
