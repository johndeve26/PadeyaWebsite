"use client";

import Link from "next/link";

import { formatNgn } from "@/lib/format";
import {
  formatEventVisibilityBrief,
  type EventListMetrics,
} from "@/lib/host-events-list";
import type { EventItem } from "@/lib/types/events";

function dash(value: string | number | null | undefined, loading?: boolean) {
  if (loading) return "…";
  if (value == null || value === "") return "—";
  return String(value);
}

const MERCH_STATUS_LABEL: Record<string, string> = {
  selling: "Selling",
  paused: "Paused",
  closed: "Closed",
  no_merch: "None",
};

const merchEditLinkClass =
  "shrink-0 text-xs text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline";

type MetricCellProps = {
  event: EventItem;
  metrics: EventListMetrics | undefined;
  loading?: boolean;
  showFinance?: boolean;
  /** Show quiet Edit link to event merch studio. */
  canEditMerch?: boolean;
};

export function HostEventSoldCell({ metrics, loading }: MetricCellProps) {
  return (
    <span className="tabular-nums text-foreground">
      {dash(metrics?.tickets_sold, loading)}
    </span>
  );
}

export function HostEventRevenueCell({
  metrics,
  loading,
  showFinance,
}: MetricCellProps) {
  if (!showFinance) {
    return <span className="text-muted-foreground">—</span>;
  }
  const revenue = metrics?.revenue;
  if (loading) return <span className="text-muted-foreground">…</span>;
  if (revenue == null) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="tabular-nums text-foreground">{formatNgn(revenue)}</span>
  );
}

export function HostEventCheckInCell({ metrics, loading }: MetricCellProps) {
  return (
    <span className="tabular-nums text-foreground">
      {dash(metrics?.check_in_count, loading)}
    </span>
  );
}

export function HostEventVisibilityCell({ event }: Pick<MetricCellProps, "event">) {
  return (
    <span className="text-foreground">
      {formatEventVisibilityBrief(event.visibility, event.location_visibility)}
    </span>
  );
}

export function HostEventMerchCell({
  event,
  metrics,
  loading,
  canEditMerch,
}: MetricCellProps) {
  const merchHref = `/host/events/${event.id}/merchandise`;
  const editLink =
    canEditMerch && !loading ? (
      <Link href={merchHref} className={merchEditLinkClass} title="Edit merch">
        Edit
      </Link>
    ) : null;

  if (loading) return <span className="text-muted-foreground">…</span>;

  if (metrics?.merch_product_count != null) {
    const status =
      MERCH_STATUS_LABEL[metrics.merch_sales_status ?? ""] ??
      metrics.merch_sales_status ??
      "—";
    const pending =
      metrics.merch_pending_pickup != null && metrics.merch_pending_pickup > 0
        ? ` · ${metrics.merch_pending_pickup} pickup`
        : "";
    return (
      <span className="inline-flex min-w-0 max-w-full items-center gap-1.5">
        <span className="min-w-0 truncate text-foreground">
          {metrics.merch_product_count} · {status}
          {pending}
        </span>
        {editLink}
      </span>
    );
  }

  if (event.allow_merch_only_checkout) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="text-foreground">Checkout</span>
        {editLink}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-muted-foreground">—</span>
      {editLink}
    </span>
  );
}

export function HostEventAmbassadorCell({ event }: MetricCellProps) {
  if (event.open_ambassadors_enabled) {
    return <span className="text-foreground">On</span>;
  }
  // Demote the common "Off" case — low signal in a dense table.
  return <span className="text-muted-foreground">—</span>;
}

export function HostEventSponsorCell({ event }: MetricCellProps) {
  const count = event.sponsor_logo_urls?.length ?? 0;
  if (count > 0) return <span>{count}</span>;
  return <span className="text-muted-foreground">—</span>;
}
