"use client";

import Link from "next/link";

import { UpcomingEventRow } from "@/components/host/command-center/UpcomingEventRow";
import { Button, Card } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import type { RoadmapItem } from "@/lib/host-roadmap";
import type { EventItem } from "@/lib/types/events";

export function NextBestActionCard({
  item,
}: {
  item: RoadmapItem | null;
}) {
  if (!item) {
    return (
      <Card className="space-y-3">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
          Next best action
        </p>
        <h2 className="text-lg font-bold text-foreground">Setup complete</h2>
        <p className="text-sm text-muted-foreground">
          No open setup items. Review upcoming events or portfolio analytics.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link href="/host/events">
            <Button size="sm" variant="secondary">
              View events
            </Button>
          </Link>
          <Link href="/host/analytics">
            <Button size="sm" variant="secondary">
              View analytics
            </Button>
          </Link>
        </div>
      </Card>
    );
  }

  return (
    <Card className="space-y-3">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
        Next best action
      </p>
      <h2 className="text-lg font-bold text-foreground">{item.label}</h2>
      <p className="text-sm text-muted-foreground">{item.why}</p>
      <Link href={item.href}>
        <Button size="sm">{item.status === "in_progress" ? "Continue" : "Start"}</Button>
      </Link>
    </Card>
  );
}

export function ReadinessGapsSection({ items }: { items: RoadmapItem[] }) {
  if (items.length === 0) return null;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Setup checklist
          </p>
          <h3 className="text-lg font-bold text-foreground">Open items</h3>
        </div>
        <Link href="/host/roadmap">
          <Button size="sm">Continue setup</Button>
        </Link>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <Link
            key={item.id}
            href={item.href}
            className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
          >
            <div className="min-w-0">
              <p className="font-bold text-foreground">{item.label}</p>
              <p className="text-sm text-muted-foreground">{item.why}</p>
            </div>
            <span className="text-xs font-bold uppercase tracking-[0.08em] text-accent">
              {item.status === "in_progress" ? "In progress" : "Not started"}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}

type UpcomingEventActions = {
  canEdit: boolean;
  canScan: boolean;
  canMerch: boolean;
  canAnalytics: boolean;
};

export function UpcomingEventsSection({
  events,
  actions,
}: {
  events: EventItem[];
  actions: UpcomingEventActions;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Next up
          </p>
          <h3 className="text-lg font-bold text-foreground">Upcoming events</h3>
        </div>
        <Link href="/host/events?tab=upcoming">
          <Button size="sm" variant="secondary">
            View all
          </Button>
        </Link>
      </div>
      {events.length === 0 ? (
        <Card className="space-y-2">
          <p className="font-bold text-foreground">No upcoming events</p>
          <p className="text-sm text-muted-foreground">
            Create your first event to start selling tickets.
          </p>
          <Link href="/host/events/new">
            <Button size="sm">Create event</Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <UpcomingEventRow key={event.id} event={event} actions={actions} />
          ))}
        </div>
      )}
    </section>
  );
}

export type TodayOpsMetrics = {
  pendingCheckIns: number | null;
  pendingPickups: number | null;
  unreadMessages: number | null;
  openInquiries: number | null;
  loaded: boolean;
};

export function TodaysOperationsSection({
  events,
  metrics,
  canViewMessages,
  canViewSponsors,
  canScan = false,
  canMerchPickup = false,
  /**
   * When set (selected-events desk scope), Scanner/Pickup only for these ids.
   * Omit / null = host-wide or owner (all listed events).
   */
  assignedEventIds = null,
}: {
  events: EventItem[];
  metrics: TodayOpsMetrics;
  canViewMessages: boolean;
  canViewSponsors: boolean;
  /** `canScanTickets` — Scanner / check-in only. */
  canScan?: boolean;
  /** `canScanMerch` — Pickup / fulfill only (not merch.view). */
  canMerchPickup?: boolean;
  assignedEventIds?: string[] | null;
}) {
  const assignedSet =
    assignedEventIds && assignedEventIds.length > 0
      ? new Set(assignedEventIds.map(String))
      : null;

  function canActOnEvent(eventId: string): boolean {
    if (!assignedSet) return true;
    return assignedSet.has(String(eventId));
  }
  const statItems = [
    {
      label: "Events today",
      value: events.length,
      show: true,
    },
    {
      label: "Pending check-ins",
      value: metrics.pendingCheckIns,
      show: metrics.loaded,
    },
    {
      label: "Merch pickups",
      value: metrics.pendingPickups,
      show: metrics.loaded,
    },
    {
      label: "Unread messages",
      value: metrics.unreadMessages,
      show: canViewMessages && metrics.loaded,
    },
    {
      label: "Sponsor inquiries",
      value: metrics.openInquiries,
      show: canViewSponsors && metrics.loaded,
    },
  ].filter((item) => item.show);

  return (
    <section className="space-y-3">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Today
        </p>
        <h3 className="text-lg font-bold text-foreground">
          Today&apos;s operations
        </h3>
      </div>

      {metrics.loaded && statItems.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {statItems.map((item) => (
            <Card key={item.label} className="space-y-1 py-3">
              <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                {item.label}
              </p>
              <p className="text-xl font-extrabold tabular-nums text-foreground">
                {item.value ?? "—"}
              </p>
            </Card>
          ))}
        </div>
      ) : null}

      {events.length === 0 ? (
        <Card className="py-4">
          <p className="text-sm text-muted-foreground">No events in the next 24 hours.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <div
              key={event.id}
              className="flex min-w-0 flex-wrap items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3 dark:bg-surface-elevated"
            >
              <div className="min-w-0">
                <p className="font-bold text-foreground">{event.title}</p>
                <p className="text-sm text-muted-foreground">
                  Doors · {formatDateTime(event.start_datetime)}
                </p>
              </div>
              <div className="flex min-w-0 flex-wrap gap-2">
                {canScan && canActOnEvent(event.id) ? (
                  <Link href={`/host/events/${event.id}/check-in`}>
                    <Button size="sm">Scanner</Button>
                  </Link>
                ) : null}
                {canMerchPickup && canActOnEvent(event.id) ? (
                  <Link href={`/host/events/${event.id}/merchandise/fulfillment`}>
                    <Button size="sm" variant="secondary">
                      Pickup
                    </Button>
                  </Link>
                ) : null}
                <Link href={`/host/events/${event.id}`}>
                  <Button size="sm" variant="secondary">
                    Open
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

type QuickAction = {
  label: string;
  href: string;
  visible: boolean;
};

export function QuickActionsRow({ actions }: { actions: QuickAction[] }) {
  const visible = actions.filter((action) => action.visible);
  if (visible.length === 0) return null;

  return (
    <section className="space-y-3">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Quick actions
        </p>
        <h3 className="text-lg font-bold text-foreground">Shortcuts</h3>
      </div>
      <div className="flex flex-wrap gap-2">
        {visible.map((action) => (
          <Link key={action.href + action.label} href={action.href}>
            <Button size="sm" variant="secondary">
              {action.label}
            </Button>
          </Link>
        ))}
      </div>
    </section>
  );
}
