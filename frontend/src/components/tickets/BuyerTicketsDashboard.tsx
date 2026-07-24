"use client";

import { useEffect, useMemo, useState } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { TicketEmptyState } from "@/components/tickets/TicketEmptyState";
import { TicketEventGroupCard } from "@/components/tickets/TicketEventGroupCard";
import { TicketOfflineHint } from "@/components/tickets/TicketOfflineBadge";
import { TicketQrModal } from "@/components/tickets/TicketQrModal";
import { TicketStatusTabs } from "@/components/tickets/TicketStatusTabs";
import { TicketSummaryCards } from "@/components/tickets/TicketSummaryCards";
import { SectionHeader } from "@/components/ui";
import {
  trackBuyerTicketsPageView,
  trackTicketTabChanged,
} from "@/lib/analytics";
import { ownedHostIds } from "@/lib/host-affiliation";
import {
  filterTicketsForTab,
  groupTicketsByEvent,
  summarizeTickets,
  type TicketDashboardTab,
  type TicketEventGroup,
} from "@/lib/tickets/buyer-ticket-groups";
import type { Ticket } from "@/lib/types/commerce";

function sectionCopy(tab: TicketDashboardTab): {
  title: string;
  description: string;
} {
  if (tab === "upcoming") {
    return {
      title: "Ready for entry",
      description:
        "Open your QR code at the door. Cached tickets stay available offline.",
    };
  }
  if (tab === "past") {
    return {
      title: "Past tickets",
      description: "Checked-in and ended events — history only, not for entry.",
    };
  }
  if (tab === "cancelled") {
    return {
      title: "Cancelled / Refunded",
      description: "These passes are no longer valid for entry.",
    };
  }
  return {
    title: "All tickets",
    description: "Active passes first, then past and inactive tickets.",
  };
}

function GroupList({
  groups,
  tone,
  defaultOpenFirst,
  onViewQr,
  affiliatedHostIds,
}: {
  groups: TicketEventGroup[];
  tone: "active" | "past" | "cancelled";
  defaultOpenFirst?: boolean;
  onViewQr: (ticket: Ticket) => void;
  affiliatedHostIds: Set<string>;
}) {
  if (!groups.length) return null;
  return (
    <ul className="m-0 list-none space-y-4 p-0">
      {groups.map((group, index) => (
        <li key={group.eventId}>
          <TicketEventGroupCard
            group={group}
            tone={tone}
            defaultOpen={Boolean(defaultOpenFirst && index === 0)}
            onViewQr={onViewQr}
            showLeaveReview={
              !(group.hostId && affiliatedHostIds.has(group.hostId))
            }
            showMessageHost={
              !(group.hostId && affiliatedHostIds.has(group.hostId))
            }
          />
        </li>
      ))}
    </ul>
  );
}

export function BuyerTicketsDashboard({ tickets }: { tickets: Ticket[] }) {
  const { workspaces } = useHostWorkspace();
  const affiliatedHostIds = useMemo(
    () => new Set(ownedHostIds(workspaces)),
    [workspaces],
  );
  const [tab, setTab] = useState<TicketDashboardTab>("upcoming");
  const [qrTicketId, setQrTicketId] = useState<string | null>(null);
  const summary = useMemo(() => summarizeTickets(tickets), [tickets]);

  useEffect(() => {
    trackBuyerTicketsPageView();
  }, []);

  const upcomingGroups = useMemo(
    () => groupTicketsByEvent(filterTicketsForTab(tickets, "upcoming")),
    [tickets],
  );
  const pastGroups = useMemo(
    () => groupTicketsByEvent(filterTicketsForTab(tickets, "past")),
    [tickets],
  );
  const cancelledGroups = useMemo(
    () => groupTicketsByEvent(filterTicketsForTab(tickets, "cancelled")),
    [tickets],
  );

  const filteredGroups = useMemo(() => {
    if (tab === "upcoming") return upcomingGroups;
    if (tab === "past") return pastGroups;
    if (tab === "cancelled") return cancelledGroups;
    return null;
  }, [tab, upcomingGroups, pastGroups, cancelledGroups]);

  const copy = sectionCopy(tab);
  const empty =
    tab === "upcoming"
      ? upcomingGroups.length === 0
      : tab === "past"
        ? pastGroups.length === 0
        : tab === "cancelled"
          ? cancelledGroups.length === 0
          : tickets.length === 0;

  function selectTab(next: TicketDashboardTab) {
    setTab(next);
    trackTicketTabChanged({ tab: next });
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 sm:max-w-4xl">
      <TicketSummaryCards
        summary={summary}
        activeTab={tab}
        onSelect={selectTab}
      />

      <TicketStatusTabs
        activeTab={tab}
        counts={{
          upcoming: summary.upcoming,
          past: summary.checkedInOrPast,
          cancelled: summary.cancelled,
          all: summary.total,
        }}
        onChange={selectTab}
      >
        {empty ? (
          <TicketEmptyState tab={tab} />
        ) : (
          <div className="space-y-6">
            {tab !== "all" ? (
              <>
                <SectionHeader
                  title={copy.title}
                  description={copy.description}
                  className="pb-0"
                />
                {tab === "upcoming" ? <TicketOfflineHint /> : null}
                <GroupList
                  groups={filteredGroups || []}
                  tone={
                    tab === "upcoming"
                      ? "active"
                      : tab === "past"
                        ? "past"
                        : "cancelled"
                  }
                  defaultOpenFirst={tab === "upcoming"}
                  onViewQr={(ticket) => setQrTicketId(ticket.id)}
                  affiliatedHostIds={affiliatedHostIds}
                />
              </>
            ) : (
              <>
                {upcomingGroups.length ? (
                  <section className="space-y-3">
                    <SectionHeader
                      title="Ready for entry"
                      description="Open your QR code at the door. Cached tickets stay available offline."
                      className="pb-0"
                    />
                    <GroupList
                      groups={upcomingGroups}
                      tone="active"
                      defaultOpenFirst
                      onViewQr={(ticket) => setQrTicketId(ticket.id)}
                      affiliatedHostIds={affiliatedHostIds}
                    />
                  </section>
                ) : null}
                {pastGroups.length ? (
                  <section className="space-y-3">
                    <SectionHeader
                      title="Past tickets"
                      description="Checked-in and ended events."
                      className="pb-0"
                    />
                    <GroupList
                      groups={pastGroups}
                      tone="past"
                      onViewQr={(ticket) => setQrTicketId(ticket.id)}
                      affiliatedHostIds={affiliatedHostIds}
                    />
                  </section>
                ) : null}
                {cancelledGroups.length ? (
                  <section className="space-y-3">
                    <SectionHeader
                      title="Cancelled / Refunded"
                      description="These passes are no longer valid for entry."
                      className="pb-0"
                    />
                    <GroupList
                      groups={cancelledGroups}
                      tone="cancelled"
                      onViewQr={(ticket) => setQrTicketId(ticket.id)}
                      affiliatedHostIds={affiliatedHostIds}
                    />
                  </section>
                ) : null}
              </>
            )}
          </div>
        )}
      </TicketStatusTabs>

      {qrTicketId ? (
        <TicketQrModal
          key={qrTicketId}
          ticketId={qrTicketId}
          open
          onClose={() => setQrTicketId(null)}
        />
      ) : null}
    </div>
  );
}
