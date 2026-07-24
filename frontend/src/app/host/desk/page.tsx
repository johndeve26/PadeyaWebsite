"use client";

import { useEffect, useState } from "react";

import { RestrictedActionNotice } from "@/components/account/RestrictedActionNotice";
import { HostDeskEventList } from "@/components/host/desk/HostDeskEventList";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, EmptyState, SkeletonLoader } from "@/components/ui";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { ApiError } from "@/lib/api";
import { canScanMerch, canScanTickets } from "@/lib/host-access";
import { fetchWorkspaceDeskEvents } from "@/lib/hosts-api";
import type { HostDeskEvent } from "@/lib/types/host-workspace";

export default function HostDeskPage() {
  const { active } = useHostWorkspace();
  const { has } = useUserRestrictions();
  const cannotScan = has("cannot_scan_tickets");
  const [deskEvents, setDeskEvents] = useState<HostDeskEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const scanTickets = canScanTickets(active) && !cannotScan;
  const scanMerch = canScanMerch(active);

  useEffect(() => {
    if (!active?.host_id) return;
    let cancelled = false;
    void fetchWorkspaceDeskEvents(active.host_id)
      .then((rows) => {
        if (!cancelled) setDeskEvents(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load desk events",
          );
          setDeskEvents([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [active?.host_id]);

  const title =
    scanTickets && !scanMerch
      ? "Ticket scanner"
      : scanMerch && !scanTickets
        ? "Merch pickup"
        : "Event desk";

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Tickets & Entry"
        title={title}
        description={
          active?.is_owner
            ? "Events you can operate from the door or merch desk."
            : `Assigned events for ${active?.role_label || "your role"}. Access follows team permissions and event scope.`
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {cannotScan ? <RestrictedActionNotice /> : null}

        {!scanTickets && !scanMerch && !active?.is_owner ? (
          <EmptyState
            title="No desk tools on this role"
            description="Ask the host owner to grant ticket scan or merch pickup permissions, or assign you on an event."
          />
        ) : deskEvents === null ? (
          <SkeletonLoader lines={4} />
        ) : deskEvents.length === 0 ? (
          <EmptyState
            title="No assigned events yet"
            description="Ask the host owner to add you on an event’s Attendees staff list, or grant host-wide desk access."
          />
        ) : (
          <HostDeskEventList
            events={deskEvents}
            showTicketScanner={scanTickets || Boolean(active?.is_owner)}
            showHostCheckIn={scanTickets || Boolean(active?.is_owner)}
            showMerchPickup={scanMerch || Boolean(active?.is_owner)}
          />
        )}
      </DashboardShell>
    </RequireHost>
  );
}
