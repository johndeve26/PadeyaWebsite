"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { EmailVerificationBanner } from "@/components/auth/EmailVerificationBanner";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { AmbassadorSection } from "@/components/personal/command-center/AmbassadorSection";
import { CommunitySection } from "@/components/personal/command-center/CommunitySection";
import { HostRecommendationsSection } from "@/components/personal/command-center/HostRecommendationsSection";
import { EventRecommendationsSection } from "@/components/events/EventRecommendationsSection";
import {
  IdentitySection,
  type ReviewPrompt,
} from "@/components/personal/command-center/IdentitySection";
import { MyActivitySection } from "@/components/personal/command-center/MyActivitySection";
import { NextUpSection } from "@/components/personal/command-center/NextUpSection";
import { PersonalWorkspaceRoutingCard } from "@/components/personal/command-center/PersonalWorkspaceRoutingCard";
import { QuickActionsSection } from "@/components/personal/command-center/QuickActionsSection";
import { VaultSection } from "@/components/personal/command-center/VaultSection";
import { WelcomeEmptySection } from "@/components/personal/command-center/WelcomeEmptySection";
import { Button } from "@/components/ui";
import { useUnreadMessages } from "@/hooks/useUnreadMessages";
import { fetchMyOrders, fetchMyTickets } from "@/lib/commerce-api";
import { fetchMyFollowing } from "@/lib/crm-api";
import { fetchConnectRequests } from "@/lib/fan-connect-api";
import { fetchMyRefunds } from "@/lib/finance-api";
import { ownedHostIds } from "@/lib/host-affiliation";
import { fetchBuyerCart, fetchMyMerch, type BuyerCart } from "@/lib/merch-api";
import { fetchMyPassport } from "@/lib/passport-api";
import {
  cartLineCount,
  isQuietPersonalHome,
  passportVisibilityLabel,
  pickReviewPromptTicket,
} from "@/lib/personal-command-center";
import { fetchAmbassadorEarningsSummary } from "@/lib/promos-api";
import {
  fetchMyReviews,
  fetchReviewEligibility,
} from "@/lib/reviews-api";
import type { Order, Ticket } from "@/lib/types/commerce";
import type { RefundRequest } from "@/lib/types/finance";
import type { VaultSubscription } from "@/lib/types/lifecycle";
import type { MerchFulfillment } from "@/lib/types/merch";
import type { FanPassport } from "@/lib/types/passport";
import type { AmbassadorEarningsSummary } from "@/lib/types/promos";
import type { VaultLibrarySummary } from "@/lib/types/vault";
import { fetchMyVaultLibrary } from "@/lib/vault-api";
import { fetchMyVaultSubscriptions } from "@/lib/vault-subscriptions-api";

/**
 * Personal Command Center body for `/dashboard`.
 *
 * Data rules:
 * - P0 first paint: tickets, orders, merch, cart (+ messages via unread hook)
 * - Soft P1: refunds (activity chips) — after P0, non-blocking
 * - Deferred: Passport, Vault, Ambassador, Connect, Following, reviews
 * - No N+1: at most one eligibility check for a single review candidate
 * - Badges come from fetchMyPassport (badges_earned) — no separate badges fetch
 * - Ambassador enrollments signal comes from earnings summary — no enrollments list fetch
 * Mode switching stays in shell chrome only.
 *
 * Privacy (own data only — BUYER_DASHBOARD_AUDIT §12):
 * Allowed: own tickets, orders, merch, refunds, messages, Passport, Vault,
 *   reviews, Ambassador activity, Connect pending count, Following count.
 * Forbidden: host finance, team, attendees, scanner; admin tools; agent queues;
 *   raw QR secrets; raw payment provider refs; other users’ private Connect
 *   fields; hidden venue details beyond ticket.location_label from the API.
 */
export function PersonalCommandCenter() {
  const { user } = useAuth();
  const { workspaces, loading: workspacesLoading } = useHostWorkspace();
  /** P0 — available immediately via existing realtime/poll hook (not a page fetch). */
  const unreadMessages = useUnreadMessages();

  const [p0Loading, setP0Loading] = useState(true);
  const [deferredLoading, setDeferredLoading] = useState(true);
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [merch, setMerch] = useState<MerchFulfillment[] | null>(null);
  const [cart, setCart] = useState<BuyerCart | null>(null);
  const [refunds, setRefunds] = useState<RefundRequest[] | null>(null);
  const [connectPending, setConnectPending] = useState<number | null>(null);
  const [followingCount, setFollowingCount] = useState<number | null>(null);
  const [passport, setPassport] = useState<FanPassport | null>(null);
  const [vault, setVault] = useState<VaultLibrarySummary | null>(null);
  const [subscriptions, setSubscriptions] = useState<VaultSubscription[] | null>(
    null,
  );
  const [ambassador, setAmbassador] =
    useState<AmbassadorEarningsSummary | null>(null);
  const [reviewPrompt, setReviewPrompt] = useState<ReviewPrompt | null>(null);

  // P0 — next ticket / activity chips
  useEffect(() => {
    let alive = true;
    void (async () => {
      const [ticketsRes, ordersRes, merchRes, cartRes] = await Promise.allSettled([
        fetchMyTickets(),
        fetchMyOrders(),
        fetchMyMerch(),
        fetchBuyerCart(),
      ]);
      if (!alive) return;
      setTickets(ticketsRes.status === "fulfilled" ? ticketsRes.value : []);
      setOrders(ordersRes.status === "fulfilled" ? ordersRes.value : []);
      setMerch(merchRes.status === "fulfilled" ? merchRes.value : []);
      setCart(cartRes.status === "fulfilled" ? cartRes.value : null);
      setP0Loading(false);
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Soft P1 — refunds for My activity (after P0; does not block Next up)
  useEffect(() => {
    if (p0Loading) return;
    let alive = true;
    void (async () => {
      try {
        const rows = await fetchMyRefunds();
        if (alive) setRefunds(rows);
      } catch {
        if (alive) setRefunds([]);
      }
    })();
    return () => {
      alive = false;
    };
  }, [p0Loading]);

  // Deferred — Passport, Vault, Ambassador, Connect, Following (+ one review check)
  useEffect(() => {
    if (p0Loading || workspacesLoading) return;
    let alive = true;
    void (async () => {
      const [
        connectRes,
        followingRes,
        passportRes,
        vaultRes,
        subsRes,
        ambassadorRes,
        reviewsRes,
      ] = await Promise.allSettled([
        fetchConnectRequests("incoming"),
        fetchMyFollowing(),
        fetchMyPassport(),
        fetchMyVaultLibrary(),
        fetchMyVaultSubscriptions(),
        fetchAmbassadorEarningsSummary(),
        fetchMyReviews(),
      ]);
      if (!alive) return;

      setConnectPending(
        connectRes.status === "fulfilled" ? connectRes.value.items.length : 0,
      );
      setFollowingCount(
        followingRes.status === "fulfilled" ? followingRes.value.length : 0,
      );
      setPassport(passportRes.status === "fulfilled" ? passportRes.value : null);
      setVault(vaultRes.status === "fulfilled" ? vaultRes.value : null);
      setSubscriptions(subsRes.status === "fulfilled" ? subsRes.value : []);
      setAmbassador(
        ambassadorRes.status === "fulfilled" ? ambassadorRes.value : null,
      );

      // Single eligibility call for one candidate — never loop tickets with N+1
      const reviews =
        reviewsRes.status === "fulfilled" ? reviewsRes.value : [];
      const ownedIds = ownedHostIds(workspaces);
      const candidate = tickets
        ? pickReviewPromptTicket(tickets, reviews, new Date(), {
            excludeHostIds: ownedIds,
          })
        : null;
      if (candidate) {
        try {
          const elig = await fetchReviewEligibility({
            ticketId: candidate.id,
          });
          if (!alive) return;
          setReviewPrompt(
            elig.eligible
              ? {
                  ticketId: candidate.id,
                  eventTitle: elig.event_title || candidate.event_title || null,
                }
              : null,
          );
        } catch {
          if (alive) setReviewPrompt(null);
        }
      } else {
        setReviewPrompt(null);
      }

      setDeferredLoading(false);
    })();
    return () => {
      alive = false;
    };
    // tickets is set before p0Loading flips false in the same render
    // eslint-disable-next-line react-hooks/exhaustive-deps -- after P0 + workspaces
  }, [p0Loading, workspacesLoading, workspaces]);

  const statusBits = [
    passport ? passportVisibilityLabel(passport.visibility) : null,
    user?.email || null,
  ].filter(Boolean);

  const showBecomeHost = !workspacesLoading && workspaces.length === 0;
  const needsPassportSetup = Boolean(
    passport && !(passport.username || "").trim(),
  );
  const quietHome =
    !p0Loading &&
    tickets != null &&
    orders != null &&
    merch != null &&
    isQuietPersonalHome({ tickets, orders, merch, cart });

  return (
    <DashboardShell
      tone="soft"
      compact
      operationalHeader
      eyebrow="Personal Command Center"
      title={`Hello, ${user?.full_name ?? "there"}`}
      description={
        quietHome
          ? "Start with an event, your Fan Passport, or promoting something you love."
          : "Your next ticket, pickups, and messages — in one place on Pàdéyá."
      }
      actions={
        <Link href="/events">
          <Button size="sm">Browse events</Button>
        </Link>
      }
    >
      <div className="min-w-0 space-y-5 sm:space-y-6">
        <EmailVerificationBanner />
        <PersonalWorkspaceRoutingCard />

        {!quietHome && statusBits.length > 0 ? (
          <p className="break-words text-sm text-muted-foreground">
            {statusBits.join(" · ")}
          </p>
        ) : null}

        {quietHome ? (
          <WelcomeEmptySection showBecomeHost={showBecomeHost} />
        ) : (
          <>
            <NextUpSection
              loading={p0Loading}
              tickets={tickets}
              merch={merch}
              cart={cart}
            />

            <div className="min-w-0 md:hidden">
              <QuickActionsSection showBecomeHost={showBecomeHost} />
            </div>

            <MyActivitySection
              loading={p0Loading}
              tickets={tickets}
              orders={orders}
              merch={merch}
              refunds={refunds}
              cartLines={cartLineCount(cart)}
            />
          </>
        )}

        <CommunitySection
          unreadMessages={unreadMessages}
          connectPending={connectPending}
          followingCount={followingCount}
        />

        <HostRecommendationsSection />

        <EventRecommendationsSection surface="dashboard_events_for_you" />

        {!quietHome ? (
          <div className="grid min-w-0 gap-5 lg:grid-cols-2 lg:gap-6">
            <IdentitySection
              loading={deferredLoading && passport === null}
              passport={passport}
              needsPassportSetup={needsPassportSetup}
              reviewPrompt={reviewPrompt}
            />
            <VaultSection
              loading={deferredLoading && vault === null}
              library={vault}
              subscriptions={subscriptions}
            />
          </div>
        ) : null}

        {!quietHome ? (
          <AmbassadorSection
            loading={deferredLoading && ambassador === null}
            summary={ambassador}
          />
        ) : null}

        {!quietHome ? (
          <div className="hidden min-w-0 md:block">
            <QuickActionsSection showBecomeHost={showBecomeHost} />
          </div>
        ) : null}
      </div>
    </DashboardShell>
  );
}
