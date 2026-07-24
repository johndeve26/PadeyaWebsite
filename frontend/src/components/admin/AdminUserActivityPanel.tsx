"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Alert,
  DataTable,
  Drawer,
  EmptyState,
  Pagination,
  SectionHeader,
  SkeletonLoader,
  StatCard,
  type DataTableColumn,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminUserActivityDetail } from "@/lib/admin-lifecycle-api";
import { formatDateTime } from "@/lib/format";
import type {
  AdminUserActivityDetailList,
  AdminUserActivityKind,
  AdminUserActivitySection,
} from "@/lib/types/lifecycle";

type ActivityCard = {
  kind: AdminUserActivityKind;
  title: string;
  count: number;
};

function str(row: Record<string, unknown>, key: string): string {
  const v = row[key];
  if (v == null || v === "") return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function hrefCell(href: string | null | undefined, label: string) {
  if (!href) return "—";
  return (
    <Link href={href} className="font-semibold text-primary hover:underline">
      {label}
    </Link>
  );
}

function moneyCell(
  row: Record<string, unknown>,
  financeIncluded: boolean,
  amountKey = "amount",
  currencyKey = "currency",
) {
  if (!financeIncluded) return "Restricted";
  const amount = row[amountKey];
  const currency = row[currencyKey];
  if (amount == null) return "—";
  return currency ? `${currency} ${amount}` : String(amount);
}

const CARD_META: {
  kind: AdminUserActivityKind;
  title: string;
  countKey: keyof AdminUserActivitySection;
}[] = [
  { kind: "tickets", title: "Tickets", countKey: "tickets_count" },
  { kind: "orders", title: "Orders", countKey: "orders_count" },
  { kind: "merch", title: "Merch", countKey: "merch_count" },
  { kind: "refunds", title: "Refunds", countKey: "refunds_count" },
  { kind: "reviews", title: "Reviews", countKey: "reviews_count" },
  { kind: "hosts", title: "Hosts owned", countKey: "host_workspaces_owned" },
  { kind: "teams", title: "Teams joined", countKey: "host_teams_joined" },
  {
    kind: "ambassadors",
    title: "Ambassador campaigns",
    countKey: "ambassador_campaigns_joined",
  },
];

function columnsFor(
  kind: AdminUserActivityKind,
  financeIncluded: boolean,
): DataTableColumn<Record<string, unknown>>[] {
  switch (kind) {
    case "tickets":
      return [
        {
          key: "public_code",
          header: "Ticket",
          primary: true,
          cell: (r) => str(r, "public_code"),
        },
        { key: "event_name", header: "Event", cell: (r) => str(r, "event_name") },
        { key: "host_name", header: "Host", cell: (r) => str(r, "host_name") },
        {
          key: "ticket_type",
          header: "Type",
          cell: (r) => str(r, "ticket_type"),
        },
        { key: "status", header: "Status", cell: (r) => str(r, "status") },
        {
          key: "checked_in",
          header: "Checked in",
          cell: (r) => str(r, "checked_in"),
        },
        {
          key: "purchase_date",
          header: "Purchased",
          cell: (r) =>
            r.purchase_date
              ? formatDateTime(String(r.purchase_date))
              : "—",
        },
        {
          key: "order_reference",
          header: "Order",
          cell: (r) => str(r, "order_reference"),
        },
        {
          key: "links",
          header: "Links",
          cell: (r) => (
            <span className="flex flex-wrap gap-2">
              {hrefCell(
                typeof r.event_admin_href === "string"
                  ? r.event_admin_href
                  : null,
                "Event",
              )}
              {hrefCell(
                typeof r.order_admin_href === "string"
                  ? r.order_admin_href
                  : null,
                "Order",
              )}
            </span>
          ),
        },
      ];
    case "orders":
      return [
        {
          key: "order_reference",
          header: "Order",
          primary: true,
          cell: (r) => str(r, "order_reference"),
        },
        { key: "subject", header: "Item", cell: (r) => str(r, "subject") },
        {
          key: "amount",
          header: "Amount",
          cell: (r) => moneyCell(r, financeIncluded),
        },
        {
          key: "payment_status",
          header: "Payment",
          cell: (r) => str(r, "payment_status"),
        },
        {
          key: "paystack_reference",
          header: "Payment ref",
          cell: (r) =>
            financeIncluded ? str(r, "paystack_reference") : "Restricted",
        },
        {
          key: "ticket_count",
          header: "Tickets",
          cell: (r) => str(r, "ticket_count"),
        },
        {
          key: "refund_status",
          header: "Refund",
          cell: (r) => str(r, "refund_status"),
        },
        {
          key: "created_at",
          header: "Created",
          cell: (r) =>
            r.created_at ? formatDateTime(String(r.created_at)) : "—",
        },
      ];
    case "merch":
      return [
        {
          key: "merch_item",
          header: "Item",
          primary: true,
          cell: (r) => str(r, "merch_item"),
        },
        {
          key: "event_host",
          header: "Event / host",
          cell: (r) =>
            [str(r, "event_name"), str(r, "host_name")]
              .filter((x) => x !== "—")
              .join(" · ") || "—",
        },
        { key: "quantity", header: "Qty", cell: (r) => str(r, "quantity") },
        {
          key: "amount",
          header: "Amount",
          cell: (r) => moneyCell(r, financeIncluded),
        },
        {
          key: "fulfillment_status",
          header: "Fulfillment",
          cell: (r) => str(r, "fulfillment_status"),
        },
        {
          key: "pickup_or_check_in_status",
          header: "Pickup",
          cell: (r) => str(r, "pickup_or_check_in_status"),
        },
        {
          key: "order_reference",
          header: "Order",
          cell: (r) => str(r, "order_reference"),
        },
        {
          key: "created_at",
          header: "Created",
          cell: (r) =>
            r.created_at ? formatDateTime(String(r.created_at)) : "—",
        },
      ];
    case "refunds":
      return [
        {
          key: "id",
          header: "Refund",
          primary: true,
          cell: (r) => str(r, "id").slice(0, 8),
        },
        {
          key: "order_reference",
          header: "Order",
          cell: (r) => str(r, "order_reference"),
        },
        {
          key: "amount",
          header: "Amount",
          cell: (r) => moneyCell(r, financeIncluded),
        },
        { key: "status", header: "Status", cell: (r) => str(r, "status") },
        {
          key: "reason_category",
          header: "Reason category",
          cell: (r) => str(r, "reason_category"),
        },
        {
          key: "requested_at",
          header: "Requested",
          cell: (r) =>
            r.requested_at ? formatDateTime(String(r.requested_at)) : "—",
        },
        {
          key: "resolved_at",
          header: "Resolved",
          cell: (r) =>
            r.resolved_at ? formatDateTime(String(r.resolved_at)) : "—",
        },
        {
          key: "handled_by_admin_name",
          header: "Handled by",
          cell: (r) => str(r, "handled_by_admin_name"),
        },
      ];
    case "reviews":
      return [
        {
          key: "id",
          header: "Review",
          primary: true,
          cell: (r) => str(r, "id").slice(0, 8),
        },
        {
          key: "target_name",
          header: "Target",
          cell: (r) => str(r, "target_name"),
        },
        { key: "rating", header: "Rating", cell: (r) => str(r, "rating") },
        {
          key: "visibility",
          header: "Visibility",
          cell: (r) => str(r, "visibility"),
        },
        {
          key: "verified_attendance",
          header: "Verified",
          cell: (r) => str(r, "verified_attendance"),
        },
        {
          key: "moderation_status",
          header: "Moderation",
          cell: (r) => str(r, "moderation_status"),
        },
        {
          key: "created_at",
          header: "Created",
          cell: (r) =>
            r.created_at ? formatDateTime(String(r.created_at)) : "—",
        },
        {
          key: "target_link",
          header: "Target link",
          cell: (r) =>
            hrefCell(
              typeof r.target_admin_href === "string"
                ? r.target_admin_href
                : null,
              "Open",
            ),
        },
      ];
    case "hosts":
      return [
        {
          key: "host_name",
          header: "Host",
          primary: true,
          cell: (r) => str(r, "host_name"),
        },
        { key: "id", header: "Host ID", cell: (r) => str(r, "id").slice(0, 8) },
        {
          key: "verification_status",
          header: "Verification",
          cell: (r) => str(r, "verification_status"),
        },
        {
          key: "events_count",
          header: "Events",
          cell: (r) => str(r, "events_count"),
        },
        {
          key: "revenue",
          header: "Revenue",
          cell: (r) => {
            if (!financeIncluded) return "Restricted";
            const summary = r.revenue_summary as
              | Record<string, unknown>
              | null
              | undefined;
            if (!summary) return "—";
            return `${summary.currency ?? "NGN"} earned ${summary.lifetime_earned ?? "—"}`;
          },
        },
        { key: "status", header: "Status", cell: (r) => str(r, "status") },
        {
          key: "created_at",
          header: "Created",
          cell: (r) =>
            r.created_at ? formatDateTime(String(r.created_at)) : "—",
        },
        {
          key: "link",
          header: "Link",
          cell: (r) =>
            hrefCell(
              typeof r.host_admin_href === "string" ? r.host_admin_href : null,
              "Hosts",
            ),
        },
      ];
    case "teams":
      return [
        {
          key: "host_name",
          header: "Host",
          primary: true,
          cell: (r) => str(r, "host_name"),
        },
        { key: "role", header: "Role", cell: (r) => str(r, "role") },
        {
          key: "permissions",
          header: "Permissions",
          cell: (r) => str(r, "permissions"),
        },
        {
          key: "joined_at",
          header: "Joined",
          cell: (r) =>
            r.joined_at ? formatDateTime(String(r.joined_at)) : "—",
        },
        { key: "status", header: "Status", cell: (r) => str(r, "status") },
        {
          key: "invited_by_name",
          header: "Invited by",
          cell: (r) => str(r, "invited_by_name"),
        },
        {
          key: "link",
          header: "Link",
          cell: (r) =>
            hrefCell(
              typeof r.host_admin_href === "string" ? r.host_admin_href : null,
              "Host",
            ),
        },
      ];
    case "ambassadors":
      return [
        {
          key: "campaign_name",
          header: "Campaign",
          primary: true,
          cell: (r) => str(r, "campaign_name"),
        },
        {
          key: "event_or_host",
          header: "Event / host",
          cell: (r) => str(r, "event_or_host"),
        },
        {
          key: "role_status",
          header: "Status",
          cell: (r) => str(r, "role_status"),
        },
        {
          key: "referral_code",
          header: "Code",
          cell: (r) => str(r, "referral_code"),
        },
        { key: "clicks", header: "Clicks", cell: (r) => str(r, "clicks") },
        {
          key: "conversions",
          header: "Conversions",
          cell: (r) => str(r, "conversions"),
        },
        {
          key: "rewards_earned",
          header: "Rewards",
          cell: (r) =>
            financeIncluded ? str(r, "rewards_earned") : "Restricted",
        },
        {
          key: "payout_status",
          header: "Payout",
          cell: (r) =>
            financeIncluded ? str(r, "payout_status") : "Restricted",
        },
        {
          key: "joined_at",
          header: "Joined",
          cell: (r) =>
            r.joined_at ? formatDateTime(String(r.joined_at)) : "—",
        },
      ];
    default:
      return [];
  }
}

function DetailTable({
  kind,
  data,
}: {
  kind: AdminUserActivityKind;
  data: AdminUserActivityDetailList;
}) {
  const columns = useMemo(
    () => columnsFor(kind, data.finance_fields_included),
    [kind, data.finance_fields_included],
  );
  const rows = data.items as Record<string, unknown>[];
  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={(row) =>
        String(row.id ?? row.order_reference ?? row.public_code ?? row.campaign_id)
      }
      emptyTitle={`No ${kind} yet`}
      emptyDescription="Nothing to show for this activity category."
    />
  );
}

export function AdminUserActivityPanel({
  userId,
  activity,
}: {
  userId: string;
  activity: AdminUserActivitySection;
}) {
  const cards: ActivityCard[] = CARD_META.map((c) => ({
    kind: c.kind,
    title: c.title,
    count: activity[c.countKey] ?? 0,
  }));

  const [selected, setSelected] = useState<AdminUserActivityKind | null>(null);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminUserActivityDetailList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const sync = () => setIsMobile(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  const load = useCallback(async () => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAdminUserActivityDetail(userId, selected, {
        page,
        limit: 20,
      });
      setData(res);
    } catch (err) {
      setData(null);
      setError(
        err instanceof ApiError ? err.detail : "Failed to load activity details",
      );
    } finally {
      setLoading(false);
    }
  }, [userId, selected, page]);

  useEffect(() => {
    // Intentional fetch when activity kind / page changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load() updates activity detail
    void load();
  }, [load]);

  const selectKind = (kind: AdminUserActivityKind) => {
    setSelected((prev) => (prev === kind ? null : kind));
    setPage(1);
    setData(null);
    setError(null);
  };

  const selectedTitle =
    cards.find((c) => c.kind === selected)?.title ?? "Activity details";
  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.limit)) : 1;

  const detailBody = selected ? (
    <div className="space-y-4">
      {!isMobile ? (
        <SectionHeader
          eyebrow="Details"
          title={selectedTitle}
          description={
            data?.finance_fields_included === false
              ? "Amounts and payment references are hidden without finance permission."
              : "Safe admin records for this activity category."
          }
        />
      ) : null}
      {loading ? <SkeletonLoader lines={6} /> : null}
      {!loading && error ? (
        <Alert tone="danger" title="Could not load details">
          {error}
        </Alert>
      ) : null}
      {!loading && !error && data && data.total === 0 ? (
        <EmptyState
          title={`No ${selectedTitle.toLowerCase()}`}
          description="This account has no records in this category yet."
        />
      ) : null}
      {!loading && !error && data && data.total > 0 ? (
        <>
          <DetailTable kind={selected} data={data} />
          <Pagination
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
          />
        </>
      ) : null}
    </div>
  ) : null;

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Activity"
        title="Platform activity"
        description="Counts across commerce and host participation. Click a card to inspect records."
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <StatCard
            key={card.kind}
            title={card.title}
            value={card.count}
            active={selected === card.kind}
            actionLabel="View details"
            onClick={() => selectKind(card.kind)}
          />
        ))}
      </div>

      {/* Desktop / laptop: inline table under cards */}
      {selected && !isMobile ? (
        <div className="rounded-[var(--radius-lg)] border border-border bg-card p-4 dark:bg-surface-elevated sm:p-5">
          {detailBody}
        </div>
      ) : null}

      {/* Mobile: drawer */}
      <Drawer
        open={Boolean(selected && isMobile)}
        onClose={() => setSelected(null)}
        title={selectedTitle}
        description="Safe admin activity records"
        className="sm:max-w-2xl"
      >
        {detailBody}
      </Drawer>
    </div>
  );
}
