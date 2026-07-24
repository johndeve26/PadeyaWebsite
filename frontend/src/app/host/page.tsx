"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { OwnerCommandCenter } from "@/components/host/command-center/OwnerCommandCenter";
import { HostDeskEventList } from "@/components/host/desk/HostDeskEventList";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, EmptyState, SkeletonLoader } from "@/components/ui";
import {
  canScanMerch,
  canScanTickets,
  canViewEvents,
  canViewSponsorships,
  hasHostPermission,
  isHostReadOnlyMember,
} from "@/lib/host-access";
import { fetchWorkspaceDeskEvents } from "@/lib/hosts-api";
import type {
  HostDeskEvent,
  HostWorkspace,
} from "@/lib/types/host-workspace";

/** Role/action title — never the host display name (shell already shows Host: {name}). */
function memberOverviewTitle(workspace: HostWorkspace): string {
  const canTickets = canScanTickets(workspace);
  const canMerch = canScanMerch(workspace);

  if (canTickets && !canMerch) return "Scanner workspace";
  if (canMerch && !canTickets) return "Merch pickup desk";
  if (canTickets && canMerch) return "Desk workspace";

  if (
    workspace.role === "sponsor_manager" ||
    (canViewSponsorships(workspace) &&
      !hasHostPermission(workspace, "events.edit", "events.create", "team.view"))
  ) {
    return "Sponsor workspace";
  }

  if (isHostReadOnlyMember(workspace) || workspace.role === "viewer") {
    return "Read-only host workspace";
  }

  const label = workspace.role_label?.trim();
  if (label) return `${label} workspace`;
  return "Team workspace";
}

function MemberDeskOverview({
  workspace,
  hostId,
  canTickets,
  canMerch,
  canViewAnalytics,
  canBrowseEvents,
}: {
  workspace: HostWorkspace;
  hostId: string;
  canTickets: boolean;
  canMerch: boolean;
  canViewAnalytics: boolean;
  canBrowseEvents: boolean;
}) {
  const [deskEvents, setDeskEvents] = useState<HostDeskEvent[] | null>(null);
  const deskRole = canTickets || canMerch;
  const title = memberOverviewTitle(workspace);
  const roleLabel = workspace.role_label || workspace.role;
  const hostName = workspace.display_name;

  useEffect(() => {
    if (!deskRole) return;
    let cancelled = false;
    void fetchWorkspaceDeskEvents(hostId)
      .then((rows) => {
        if (!cancelled) setDeskEvents(rows);
      })
      .catch(() => {
        if (!cancelled) setDeskEvents([]);
      });
    return () => {
      cancelled = true;
    };
  }, [hostId, deskRole]);

  const primaryHref = deskRole
    ? "/host/desk"
    : canBrowseEvents
      ? "/host/events"
      : canViewSponsorships(workspace)
        ? "/host/sponsorships"
        : "/host";

  const primaryLabel = deskRole
    ? "Open desk"
    : canBrowseEvents
      ? "View events"
      : canViewSponsorships(workspace)
        ? "Sponsorships"
        : "Overview";

  return (
    <DashboardShell
      tone="soft"
      operationalHeader
      eyebrow="Overview"
      title={title}
      description={
        deskRole
          ? `You’re helping as ${roleLabel} on ${hostName}. Desk access follows your permissions and assigned events.`
          : `Access as ${roleLabel} on ${hostName}. Destructive host actions and payouts stay with the owner.`
      }
      actions={
        primaryHref !== "/host" ? (
          <Link href={primaryHref}>
            <Button>{primaryLabel}</Button>
          </Link>
        ) : undefined
      }
    >
      <div className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
          {deskRole ? "Tickets & Entry" : "Member access"}
        </p>
        <h2 className="mt-2 text-xl font-bold text-foreground">{title}</h2>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-muted-foreground">
          {deskRole
            ? "Open Tickets & Entry for scanner or pickup queues on assigned events."
            : "Browse pages your role allows. Owner-only tools stay hidden."}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {canTickets ? (
            <Link href="/host/desk">
              <Button size="sm" variant="secondary">
                Scanner
              </Button>
            </Link>
          ) : null}
          {canMerch ? (
            <Link href="/host/desk">
              <Button size="sm" variant="secondary">
                Pickup queue
              </Button>
            </Link>
          ) : null}
          {deskRole ? (
            <Link href="/host/desk">
              <Button size="sm" variant="secondary">
                Assigned events
              </Button>
            </Link>
          ) : canBrowseEvents ? (
            <Link href="/host/events">
              <Button size="sm" variant="secondary">
                View events
              </Button>
            </Link>
          ) : null}
          {canViewAnalytics ? (
            <Link href="/host/analytics">
              <Button size="sm" variant="secondary">
                Analytics
              </Button>
            </Link>
          ) : null}
        </div>
      </div>

      {deskRole ? (
        <section className="space-y-4">
          {deskEvents === null ? (
            <SkeletonLoader lines={4} />
          ) : deskEvents.length === 0 ? (
            <EmptyState
              title="No desk events yet"
              description="Ask the host owner to assign you on an event, or grant host-wide desk access."
            />
          ) : (
            <HostDeskEventList
              events={deskEvents}
              showTicketScanner={canTickets}
              showMerchPickup={canMerch}
              showEventLink={false}
            />
          )}
        </section>
      ) : (
        <EmptyState
          title="No payouts or edit tools"
          description="This workspace stays within your granted permissions."
        />
      )}
    </DashboardShell>
  );
}

export default function HostHomePage() {
  const { active, isOwner, loading } = useHostWorkspace();

  const memberProps = useMemo(() => {
    // Host admins and all other non-owners use MemberDeskOverview — never OwnerCommandCenter.
    if (!active || isOwner) return null;
    return {
      workspace: active,
      hostId: active.host_id,
      canTickets: canScanTickets(active),
      canMerch: canScanMerch(active),
      canViewAnalytics: hasHostPermission(
        active,
        "analytics.view_events",
        "analytics.view_merch",
        "analytics.view_sponsors",
      ),
      canBrowseEvents: canViewEvents(active),
    };
  }, [active, isOwner]);

  return (
    <RequireHost>
      {loading || !active ? (
        <main className="bg-background py-16">
          <SkeletonLoader lines={6} />
        </main>
      ) : isOwner ? (
        <OwnerCommandCenter key={active.host_id} />
      ) : memberProps ? (
        <MemberDeskOverview {...memberProps} />
      ) : null}
    </RequireHost>
  );
}
