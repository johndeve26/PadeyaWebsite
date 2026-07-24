"use client";

import Link from "next/link";
import { startTransition, useEffect, useMemo, useState } from "react";

import { CommandCenterHeader } from "@/components/host/command-center/CommandCenterHeader";
import {
  NextBestActionCard,
  QuickActionsRow,
  ReadinessGapsSection,
  TodaysOperationsSection,
  UpcomingEventsSection,
  type TodayOpsMetrics,
} from "@/components/host/command-center/CommandCenterSections";
import {
  PendingTasksSection,
  type PendingTask,
} from "@/components/host/command-center/PendingTasksSection";
import { SalesSnapshotSection } from "@/components/host/command-center/SalesSnapshotSection";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, MetricCard, SkeletonLoader } from "@/components/ui";
import { fetchHostAnalytics, fetchHostEventAnalyticsOverview } from "@/lib/analytics-api";
import { fetchHostConversions } from "@/lib/ambassadors-api";
import { fetchMyEvents } from "@/lib/events-api";
import { formatDateTime, formatNgn } from "@/lib/format";
import { fetchHostBalance } from "@/lib/finance-api";
import {
  canCreateEvents,
  canCreateMerch,
  canEditEvents,
  canInviteTeam,
  canManageAmbassadors,
  canScanMerch,
  canScanTickets,
  canViewFinanceSummary,
  canViewHostAnalytics,
  canViewSponsorships,
  hasHostPermission,
} from "@/lib/host-access";
import { todaysOperations, upcomingEvents } from "@/lib/host-events-list";
import {
  buildRoadmapItems,
  incompleteRoadmapItems,
  nextBestRoadmapItem,
  type RoadmapItem,
} from "@/lib/host-roadmap";
import { fetchMyHost } from "@/lib/hosts-api";
import { fetchHostTeamInvites, fetchHostTeamMembers } from "@/lib/hosts-lifecycle-api";
import { fetchMyLegacyPage } from "@/lib/legacy-api";
import { fetchAllHostMerchProducts, fetchHostMerchStats } from "@/lib/merch-api";
import { fetchUnreadCount } from "@/lib/messaging-api";
import { fetchHostCampaigns } from "@/lib/promos-api";
import { fetchHostInquiries, fetchHostSponsorshipSlots } from "@/lib/sponsorships-api";
import type { HostBalance } from "@/lib/types/finance";
import type { EventItem, Host } from "@/lib/types/events";
import type { LegacyPage } from "@/lib/types/legacy";

function openInquiryCount(
  inquiries: { status: string }[],
): number {
  return inquiries.filter((row) =>
    ["new", "reviewing"].includes(row.status.toLowerCase()),
  ).length;
}

function todayOpsAction(
  todayEvents: EventItem[],
  roadmapItems: RoadmapItem[] | null,
): RoadmapItem | null {
  if (!roadmapItems || todayEvents.length === 0) return null;
  if (nextBestRoadmapItem(roadmapItems)) return null;
  const event = todayEvents[0];
  return {
    id: "today-scanner",
    label: "Open today's scanner",
    why: `${event.title} starts ${formatDateTime(event.start_datetime)}.`,
    href: `/host/events/${event.id}/check-in`,
    status: "in_progress",
    category: "operate",
    sortOrder: 0,
  };
}

export function OwnerCommandCenter() {
  const { active, isOwner } = useHostWorkspace();
  const [host, setHost] = useState<Host | null>(null);
  const [legacy, setLegacy] = useState<LegacyPage | null>(null);
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [balance, setBalance] = useState<HostBalance | null>(null);
  const [roadmapItems, setRoadmapItems] = useState<RoadmapItem[] | null>(null);
  const [analytics, setAnalytics] = useState<Awaited<
    ReturnType<typeof fetchHostAnalytics>
  > | null>(null);
  const [unreadMessages, setUnreadMessages] = useState<number | null>(null);
  const [pendingInvites, setPendingInvites] = useState<number | null>(null);
  const [pendingRewards, setPendingRewards] = useState<number | null>(null);
  const [openInquiries, setOpenInquiries] = useState<number | null>(null);
  const [merchUnitsSold, setMerchUnitsSold] = useState<number | null>(null);
  const [ambassadorConversions, setAmbassadorConversions] = useState<number | null>(
    null,
  );
  const [todayOpsSnapshot, setTodayOpsSnapshot] = useState<{
    key: string;
    pendingCheckIns: number;
    pendingPickups: number;
  } | null>(null);
  const [analyticsLoaded, setAnalyticsLoaded] = useState(false);
  const [merchLoaded, setMerchLoaded] = useState(false);
  const [messagesLoaded, setMessagesLoaded] = useState(false);
  const [ambassadorsLoaded, setAmbassadorsLoaded] = useState(false);
  const [inquiriesLoaded, setInquiriesLoaded] = useState(false);
  const [nowMs] = useState(() => Date.now());

  const canViewMoney = canViewFinanceSummary(active);
  const canViewMessages = hasHostPermission(
    active,
    "messages.view",
    "messages.reply",
  );
  const canViewSponsors = canViewSponsorships(active);
  const canViewAmbassadors = canManageAmbassadors(active);

  const messagesReady = !canViewMessages || messagesLoaded;
  const ambassadorsReady = !canViewAmbassadors || ambassadorsLoaded;
  const inquiriesReady = !canViewSponsors || inquiriesLoaded;
  const canEdit = canEditEvents(active);
  // Match Upcoming row + desk rules: scan helpers only (owners pass via is_owner).
  const canScan = canScanTickets(active);
  const canMerchPickup = canScanMerch(active);
  const canMerch =
    canMerchPickup || hasHostPermission(active, "merch.view", "merch.create");
  const canAnalytics = canViewHostAnalytics(active);
  const assignedEventIds =
    active &&
    !active.is_owner &&
    active.scope === "selected_events" &&
    active.scoped_event_ids.length > 0
      ? active.scoped_event_ids.map(String)
      : null;

  // Refetch when the active host workspace changes (Host A → Host B).
  // Parent also remounts via key={active.host_id}; this dep + reset covers
  // in-place reuse and cancels in-flight fetches from the previous host.
  useEffect(() => {
    const hostId = active?.host_id;
    if (!hostId) return;

    let cancelled = false;

    startTransition(() => {
      setHost(null);
      setLegacy(null);
      setEvents(null);
      setRoadmapItems(null);
      setAnalytics(null);
      setBalance(null);
      setUnreadMessages(null);
      setPendingInvites(null);
      setPendingRewards(null);
      setOpenInquiries(null);
      setMerchUnitsSold(null);
      setAmbassadorConversions(null);
      setTodayOpsSnapshot(null);
      setAnalyticsLoaded(false);
      setMerchLoaded(false);
      setMessagesLoaded(false);
      setAmbassadorsLoaded(false);
      setInquiriesLoaded(false);
    });

    void (async () => {
      const [
        hostRecord,
        legacyPage,
        eventRows,
        teamMembers,
        merch,
        campaigns,
        slots,
        invites,
      ] = await Promise.all([
        fetchMyHost().catch(() => null),
        fetchMyLegacyPage().catch(() => null),
        fetchMyEvents().catch(() => []),
        fetchHostTeamMembers(false).catch(() => []),
        fetchAllHostMerchProducts().catch(() => []),
        fetchHostCampaigns().catch(() => []),
        fetchHostSponsorshipSlots().catch(() => []),
        fetchHostTeamInvites(false).catch(() => []),
      ]);

      if (cancelled) return;

      setHost(hostRecord);
      setLegacy(legacyPage);
      setEvents(eventRows);
      setPendingInvites(invites.length);
      setMerchUnitsSold(
        merch.reduce((sum, product) => sum + (product.sold_count ?? 0), 0),
      );
      setMerchLoaded(true);
      setRoadmapItems(
        buildRoadmapItems({
          host: hostRecord,
          legacy: legacyPage,
          events: eventRows,
          teamMemberCount: teamMembers.length,
          merchProductCount: merch.length,
          campaignCount: campaigns.length,
          sponsorshipSlotCount: slots.length,
        }),
      );
    })();

    void fetchHostBalance()
      .then((row) => {
        if (!cancelled) setBalance(row);
      })
      .catch(() => undefined);

    void fetchHostAnalytics()
      .then((summary) => {
        if (!cancelled) setAnalytics(summary);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setAnalyticsLoaded(true);
      });

    if (canViewMessages) {
      void fetchUnreadCount()
        .then((count) => {
          if (!cancelled) setUnreadMessages(count);
        })
        .catch(() => undefined)
        .finally(() => {
          if (!cancelled) setMessagesLoaded(true);
        });
    }

    if (canViewAmbassadors) {
      void fetchHostConversions()
        .then((rows) => {
          if (cancelled) return;
          setPendingRewards(
            rows.filter((row) => row.status === "attributed").length,
          );
          setAmbassadorConversions(rows.length);
        })
        .catch(() => undefined)
        .finally(() => {
          if (!cancelled) setAmbassadorsLoaded(true);
        });
    }

    if (canViewSponsors) {
      void fetchHostInquiries()
        .then((rows) => {
          if (!cancelled) setOpenInquiries(openInquiryCount(rows));
        })
        .catch(() => undefined)
        .finally(() => {
          if (!cancelled) setInquiriesLoaded(true);
        });
    }

    return () => {
      cancelled = true;
    };
  }, [
    active?.host_id,
    canViewAmbassadors,
    canViewMessages,
    canViewSponsors,
  ]);

  const loadedEvents = useMemo(() => events ?? [], [events]);
  const upcoming = useMemo(
    () => upcomingEvents(loadedEvents, 3, nowMs),
    [loadedEvents, nowMs],
  );
  const todayOps = useMemo(
    () => todaysOperations(loadedEvents, nowMs),
    [loadedEvents, nowMs],
  );
  const nextEvent = upcoming[0] ?? null;
  const gaps = useMemo(
    () => incompleteRoadmapItems(roadmapItems ?? [], 3),
    [roadmapItems],
  );

  const nextAction = useMemo(() => {
    const roadmapNext = roadmapItems ? nextBestRoadmapItem(roadmapItems) : null;
    if (roadmapNext) return roadmapNext;
    return todayOpsAction(todayOps, roadmapItems);
  }, [roadmapItems, todayOps]);

  const todayOpsKey = useMemo(
    () => todayOps.map((event) => event.id).join(","),
    [todayOps],
  );

  const todayMetrics = useMemo((): TodayOpsMetrics => {
    const shared = {
      unreadMessages: messagesReady ? unreadMessages : null,
      openInquiries: inquiriesReady ? openInquiries : null,
      loaded: messagesReady && inquiriesReady,
    };
    if (todayOps.length === 0) {
      return {
        ...shared,
        pendingCheckIns: 0,
        pendingPickups: 0,
        loaded: shared.loaded,
      };
    }
    if (!todayOpsSnapshot || todayOpsSnapshot.key !== todayOpsKey) {
      return {
        ...shared,
        pendingCheckIns: null,
        pendingPickups: null,
        loaded: false,
      };
    }
    return {
      ...shared,
      pendingCheckIns: todayOpsSnapshot.pendingCheckIns,
      pendingPickups: todayOpsSnapshot.pendingPickups,
      loaded: shared.loaded,
    };
  }, [
    todayOps.length,
    todayOpsKey,
    todayOpsSnapshot,
    unreadMessages,
    openInquiries,
    messagesReady,
    inquiriesReady,
  ]);

  useEffect(() => {
    if (!active?.host_id || todayOps.length === 0) return;

    let cancelled = false;
    void (async () => {
      const overviews = await Promise.all(
        todayOps.map((event) =>
          fetchHostEventAnalyticsOverview(event.id).catch(() => null),
        ),
      );
      const stats = await Promise.all(
        todayOps.map((event) =>
          fetchHostMerchStats(event.id).catch(() => null),
        ),
      );

      if (cancelled) return;

      let pendingCheckIns = 0;
      for (const overview of overviews) {
        if (!overview) continue;
        pendingCheckIns += Math.max(0, overview.purchases - overview.check_in_count);
      }

      const pendingPickups = stats.reduce(
        (sum, row) => sum + (row?.pending_pickup ?? 0),
        0,
      );

      setTodayOpsSnapshot({
        key: todayOpsKey,
        pendingCheckIns,
        pendingPickups,
      });
    })();

    return () => {
      cancelled = true;
    };
  }, [active?.host_id, todayOps, todayOpsKey]);

  const draftEvents = useMemo(
    () =>
      loadedEvents.filter((event) =>
        ["draft", "pending_review", "rejected"].includes(event.status),
      ).length,
    [loadedEvents],
  );

  const pendingTasks = useMemo(() => {
    const tasks: PendingTask[] = [];
    if (draftEvents > 0) {
      tasks.push({
        id: "draft-events",
        label: "Draft events",
        description: "Finish setup or publish when ready.",
        href: "/host/events?tab=drafts",
        count: draftEvents,
      });
    }
    if ((pendingInvites ?? 0) > 0) {
      tasks.push({
        id: "team-invites",
        label: "Pending team invites",
        description: "Resend or revoke outstanding invites.",
        href: "/host/team/invites",
        count: pendingInvites ?? 0,
      });
    }
    if (canViewAmbassadors && (pendingRewards ?? 0) > 0) {
      tasks.push({
        id: "ambassador-rewards",
        label: "Ambassador rewards to review",
        description: "Approve or reject attributed conversions.",
        href: "/host/ambassadors/conversions",
        count: pendingRewards ?? 0,
      });
    }
    if (canViewMessages && (unreadMessages ?? 0) > 0) {
      tasks.push({
        id: "unread-messages",
        label: "Unread messages",
        description: "Fans and partners are waiting on a reply.",
        href: "/host/messages",
        count: unreadMessages ?? 0,
      });
    }
    if (canViewSponsors && (openInquiries ?? 0) > 0) {
      tasks.push({
        id: "sponsor-inquiries",
        label: "Open sponsor inquiries",
        description: "Review brand interest on your slots.",
        href: "/host/sponsorships",
        count: openInquiries ?? 0,
      });
    }
    return tasks;
  }, [
    canViewAmbassadors,
    canViewMessages,
    canViewSponsors,
    draftEvents,
    openInquiries,
    pendingInvites,
    pendingRewards,
    unreadMessages,
  ]);

  return (
    <DashboardShell
      tone="soft"
      hideHeader
      compact
    >
      <CommandCenterHeader host={host} legacy={legacy} />

      <div className="grid gap-4 sm:grid-cols-2">
        <MetricCard
          label="Next event"
          value={
            nextEvent
              ? formatDateTime(nextEvent.start_datetime)
              : "None scheduled"
          }
          description={
            nextEvent
              ? `${nextEvent.title} · ${nextEvent.status}`
              : "Create or publish your next night"
          }
          action={
            <Link href={nextEvent ? `/host/events/${nextEvent.id}` : "/host/events/new"}>
              <Button size="sm" variant="secondary">
                {nextEvent ? "Open event" : "Create event"}
              </Button>
            </Link>
          }
        />
        {isOwner ? (
          <MetricCard
            label="Available balance"
            value={
              canViewMoney && balance
                ? formatNgn(balance.available_balance)
                : canViewMoney
                  ? "—"
                  : "Hidden"
            }
            description={
              canViewMoney
                ? "Ready for payout request"
                : "Finance summary not granted for your role"
            }
            action={
              canViewMoney ? (
                <Link href="/host/payouts">
                  <Button size="sm" variant="secondary">
                    Payouts
                  </Button>
                </Link>
              ) : undefined
            }
          />
        ) : null}
      </div>

      {roadmapItems === null ? (
        <SkeletonLoader lines={4} />
      ) : (
        <NextBestActionCard item={nextAction} />
      )}

      {roadmapItems ? <ReadinessGapsSection items={gaps} /> : null}

      <UpcomingEventsSection
        events={upcoming}
        actions={{
          canEdit,
          canScan,
          canMerch,
          canAnalytics,
        }}
      />

      <TodaysOperationsSection
        events={todayOps}
        metrics={todayMetrics}
        canViewMessages={canViewMessages}
        canViewSponsors={canViewSponsors}
        canScan={canScan}
        canMerchPickup={canMerchPickup}
        assignedEventIds={assignedEventIds}
      />

      <SalesSnapshotSection
        data={{
          ticketsSold: analytics?.tickets_sold ?? null,
          ticketRevenue: analytics?.revenue ?? null,
          merchUnits: merchUnitsSold,
          ambassadorConversions,
          openInquiries,
          analyticsLoaded,
          merchLoaded,
          ambassadorsLoaded: ambassadorsReady,
          inquiriesLoaded: inquiriesReady,
        }}
        canViewMoney={canViewMoney}
        canViewSponsors={canViewSponsors}
        canViewAmbassadors={canViewAmbassadors}
      />

      <PendingTasksSection tasks={pendingTasks} />

      <QuickActionsRow
        actions={[
          {
            label: "Create event",
            href: "/host/events/new",
            visible: canCreateEvents(active),
          },
          {
            label: "Open scanner",
            href: todayOps[0]
              ? `/host/events/${todayOps[0].id}/check-in`
              : "/host/desk",
            visible: canScan,
          },
          {
            label: "Add merch",
            href: "/host/merchandise/new",
            visible: canCreateMerch(active),
          },
          {
            label: "Invite team",
            href: "/host/team/invites",
            visible: canInviteTeam(active),
          },
          {
            label: "Create ambassador campaign",
            href: "/host/ambassadors/campaigns/new",
            visible: canManageAmbassadors(active),
          },
          {
            label: "View analytics",
            href: "/host/analytics",
            visible: canViewHostAnalytics(active),
          },
        ]}
      />
    </DashboardShell>
  );
}
