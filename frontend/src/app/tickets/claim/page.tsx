"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { EmailVerificationBanner } from "@/components/auth/EmailVerificationBanner";
import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { Alert, Button, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { claimTransferredTicket, claimTicketTransferById, fetchMyTicketTransfers } from "@/lib/advanced-tickets-api";
import { fetchTransferClaimContext } from "@/lib/tickets/claim-context";
import type { TicketTransferActivity } from "@/lib/types/advanced-tickets";

function safeToken(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().slice(0, 200);
  if (!/^[A-Za-z0-9_\-]+$/.test(trimmed)) return null;
  return trimmed;
}

function safeEmail(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim().toLowerCase().slice(0, 320);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return null;
  return trimmed;
}

function ClaimInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const token = safeToken(params.get("token"));
  const recipientEmailHint = safeEmail(params.get("email"));
  const [resolvedEmail, setResolvedEmail] = useState<string | null>(
    recipientEmailHint,
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingReceived, setPendingReceived] = useState<TicketTransferActivity[]>([]);
  const [pendingLoading, setPendingLoading] = useState(false);
  const autoClaimAttempted = useRef(false);

  const recipientEmail = resolvedEmail ?? recipientEmailHint;

  const loginNext = token
    ? `/tickets/claim?token=${encodeURIComponent(token)}${
        recipientEmail ? `&email=${encodeURIComponent(recipientEmail)}` : ""
      }`
    : "/tickets/claim";

  const registerHref = (() => {
    const next = encodeURIComponent(loginNext);
    if (recipientEmail) {
      return `/register?email=${encodeURIComponent(recipientEmail)}&next=${next}`;
    }
    return `/register?next=${next}`;
  })();

  useEffect(() => {
    if (recipientEmailHint || !token) return;
    let active = true;
    void (async () => {
      try {
        const ctx = await fetchTransferClaimContext(token);
        if (!active) return;
        setResolvedEmail(safeEmail(ctx.recipient_email));
      } catch {
        // ignore
      }
    })();
    return () => {
      active = false;
    };
  }, [token, recipientEmailHint]);

  useEffect(() => {
    if (loading || token || !user?.is_verified) {
      if (!token && !user) {
        setPendingReceived([]);
      }
      return;
    }
    let active = true;
    setPendingLoading(true);
    void (async () => {
      try {
        const items = await fetchMyTicketTransfers();
        if (!active) return;
        setPendingReceived(
          items.filter((row) => row.status === "pending" && row.role === "received"),
        );
      } catch {
        if (active) setPendingReceived([]);
      } finally {
        if (active) setPendingLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [loading, token, user?.id, user?.is_verified]);

  async function runClaim() {
    if (!token) {
      setError("Missing or invalid claim link.");
      return false;
    }
    if (!user) {
      return false;
    }
    if (!user.is_verified) {
      setError("Verify your email first — check your inbox or Profile & security.");
      return false;
    }
    setBusy(true);
    setError(null);
    try {
      await claimTransferredTicket(token);
      router.push("/dashboard/tickets");
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not claim this ticket");
      return false;
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (loading || !token || !user?.is_verified || autoClaimAttempted.current) {
      return;
    }
    autoClaimAttempted.current = true;
    void runClaim().then((ok) => {
      if (!ok) {
        autoClaimAttempted.current = false;
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- claim once when auth ready
  }, [loading, token, user?.id, user?.is_verified]);

  if (loading) {
    return <SkeletonLoader className="mx-auto mt-20 max-w-md" />;
  }

  if (!token) {
    const showDashboardClaim =
      user?.is_verified && (pendingLoading || pendingReceived.length > 0);

    return (
      <PublicPageShell
        eyebrow="Ticket transfer"
        title={user ? "Claim from your inbox or My tickets" : "Open your transfer link"}
        description={
          user
            ? "Email links include a secure token. If you signed up after a transfer, you can also claim pending tickets from My tickets — no email link required."
            : "Use the claim link from the transfer email, or sign in after creating an account with the recipient address."
        }
        narrow
      >
        {user && !user.is_verified ? (
          <EmailVerificationBanner className="mx-auto mb-4 max-w-lg" />
        ) : null}

        {error ? (
          <Alert tone="danger" title="Could not claim">
            {error}
          </Alert>
        ) : null}

        {showDashboardClaim ? (
          <Card className="mx-auto max-w-lg space-y-4 p-6 dark:bg-surface-elevated">
            <div className="space-y-1">
              <h2 className="text-lg font-extrabold text-foreground">Pending transfers for you</h2>
              <p className="text-sm text-muted-foreground">
                These were sent to{" "}
                <span className="font-semibold text-foreground">{user?.email}</span>. Claim here or
                from Transfer history on My tickets.
              </p>
            </div>
            {pendingLoading ? (
              <SkeletonLoader lines={2} />
            ) : (
              <ul className="space-y-3">
                {pendingReceived.map((row) => (
                  <li
                    key={row.id}
                    className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="font-semibold text-foreground">
                        {row.event_title ?? "Event ticket"}
                      </p>
                      {row.ticket_public_code ? (
                        <p className="font-mono text-xs text-muted-foreground">
                          {row.ticket_public_code}
                        </p>
                      ) : null}
                    </div>
                    <Button
                      size="sm"
                      disabled={busy}
                      onClick={() => {
                        setBusy(true);
                        setError(null);
                        void (async () => {
                          try {
                            await claimTicketTransferById(row.id);
                            router.push("/dashboard/tickets");
                          } catch (err) {
                            setError(
                              err instanceof ApiError ? err.detail : "Could not claim this ticket",
                            );
                          } finally {
                            setBusy(false);
                          }
                        })();
                      }}
                    >
                      {busy ? "Claiming…" : "Claim ticket"}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        ) : (
          <Alert tone="warning" title="No claim token in this URL">
            {user ? (
              <>
                If someone transferred a ticket to your email, open the link in that message — it
                looks like{" "}
                <span className="font-mono text-xs">/tickets/claim?token=…</span>. Already signed
                in with the right email? Go to{" "}
                <Link href="/dashboard/tickets" className="font-semibold text-primary underline">
                  My tickets
                </Link>{" "}
                and tap Claim ticket under Transfer history.
              </>
            ) : (
              <>
                The secure link is in the transfer email. After you create an account with that
                recipient address, claim from My tickets or open the email link again.
              </>
            )}
          </Alert>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          {user ? (
            <Link href="/dashboard/tickets">
              <Button>Go to My tickets</Button>
            </Link>
          ) : (
            <>
              <Link href="/login?next=%2Fdashboard%2Ftickets">
                <Button>Log in</Button>
              </Link>
              <Link href="/register?next=%2Fdashboard%2Ftickets">
                <Button variant="secondary">Create account</Button>
              </Link>
            </>
          )}
        </div>
      </PublicPageShell>
    );
  }

  const loginHref = `/login?next=${encodeURIComponent(loginNext)}`;
  const canClaim = Boolean(user?.is_verified);

  return (
    <PublicPageShell
      eyebrow="Ticket transfer"
      title="Claim your ticket"
      description="Someone transferred an event ticket to you. Sign in with the recipient email from that message, then claim."
      actions={
        <PublicCtaPair
          primaryHref={user ? "/dashboard/tickets" : loginHref}
          primaryLabel={user ? "My tickets" : "Log in"}
          secondaryHref={registerHref}
          secondaryLabel="Create account"
        />
      }
      narrow
    >
      {user && !user.is_verified ? (
        <EmailVerificationBanner className="mx-auto mb-4 max-w-lg" />
      ) : null}

      <div className="mx-auto max-w-lg space-y-4">
        <Card className="space-y-4 p-6 dark:bg-surface-elevated">
          <div className="space-y-1">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
              Transferred to you
            </p>
            <h2 className="text-lg font-extrabold text-foreground">Complete your claim</h2>
            {recipientEmail ? (
              <p className="text-sm text-muted-foreground">
                This ticket was sent to{" "}
                <span className="font-semibold text-foreground">{recipientEmail}</span>.
                Log in or register with that exact email.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Log in or create an account with the recipient email from the transfer message,
                then claim once to get your QR pass.
              </p>
            )}
            {user ? (
              <p className="text-sm text-muted-foreground">
                Signed in as{" "}
                <span className="font-semibold text-foreground">{user.email}</span>
                {recipientEmail &&
                user.email?.trim().toLowerCase() !== recipientEmail ? (
                  <span className="mt-1 block text-sm text-warning-foreground">
                    That may not match the recipient email — switch accounts if claim fails.
                  </span>
                ) : null}
              </p>
            ) : null}
          </div>

          {error ? (
            <Alert tone="danger" title="Could not claim">
              {error}
            </Alert>
          ) : null}

          {!user ? (
            <div className="space-y-2">
              <Link href={loginHref} className="block">
                <Button className="w-full" size="lg">
                  Log in to claim
                </Button>
              </Link>
              <Link href={registerHref} className="block">
                <Button className="w-full" size="lg" variant="secondary">
                  Create account to claim
                </Button>
              </Link>
            </div>
          ) : !user.is_verified ? (
            <Button className="w-full" size="lg" disabled>
              Verify email to claim
            </Button>
          ) : (
            <Button
              className="w-full"
              size="lg"
              disabled={busy}
              onClick={() => void runClaim()}
            >
              {busy ? "Claiming…" : "Claim ticket to my account"}
            </Button>
          )}

          {canClaim && !busy ? (
            <p className="text-xs text-muted-foreground">
              If nothing happens, tap the button above once.
            </p>
          ) : null}
        </Card>
      </div>
    </PublicPageShell>
  );
}

export default function TicketTransferClaimPage() {
  return (
    <Suspense fallback={<SkeletonLoader className="mx-auto mt-20 max-w-md" />}>
      <ClaimInner />
    </Suspense>
  );
}
