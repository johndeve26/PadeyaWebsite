"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  Select,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchAdminMerchOrders } from "@/lib/merch-api";
import type { MerchAdminOrder } from "@/lib/types/merch";

const FULFILL_STATUSES = [
  "awaiting_pickup",
  "collect_at_stand",
  "fulfilled",
  "cancelled",
] as const;

export default function AdminMerchandiseOrdersPage() {
  const [items, setItems] = useState<MerchAdminOrder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    const rows = await fetchAdminMerchOrders({
      status: statusFilter === "all" ? undefined : statusFilter,
      issues: issuesOnly && statusFilter === "all" ? true : undefined,
      q: debouncedSearch || undefined,
      limit: 200,
    });
    setItems(rows);
  }, [statusFilter, issuesOnly, debouncedSearch]);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoading(true);
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load merch orders");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Merchandise orders"
      description="Pickup fulfillments and open issues. Shows order reference, product, event, and host — not payment amounts or gateway IDs."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/merchandise">
            <Button variant="secondary">Products</Button>
          </Link>
          <Link href="/admin/merchandise/print-on-demand">
            <Button variant="secondary">Print on demand</Button>
          </Link>
          <Link href="/admin/merchandise/reports">
            <Button variant="secondary">Reports</Button>
          </Link>
          <Link href="/admin">
            <Button variant="ghost">Admin home</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Load failed">
          {error}
        </Alert>
      ) : null}

      <FilterBar
        trailing={
          <span className="text-sm text-muted-foreground">
            {items.length} fulfillment{items.length === 1 ? "" : "s"}
          </span>
        }
      >
        <Input
          label="Search"
          placeholder="Order ref, product, event, pickup code…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select
          label="Fulfillment status"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            if (e.target.value !== "all") setIssuesOnly(false);
          }}
        >
          <option value="all">All statuses</option>
          {FULFILL_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Select
          label="Issues"
          value={issuesOnly ? "issues" : "all"}
          onChange={(e) => {
            const next = e.target.value === "issues";
            setIssuesOnly(next);
            if (next) setStatusFilter("all");
          }}
        >
          <option value="all">All fulfillments</option>
          <option value="issues">Open / cancelled issues</option>
        </Select>
      </FilterBar>

      {loading && !error ? <SkeletonLoader lines={5} /> : null}

      {!loading && items.length === 0 && !error ? (
        <EmptyState
          title="No merch orders"
          description="No fulfillments match these filters yet."
        />
      ) : !loading ? (
        <DataTable
          rows={items}
          rowKey={(item) => item.id}
          emptyTitle="No matching fulfillments"
          emptyDescription="Try a different filter."
          columns={[
            {
              key: "order",
              header: "Order",
              primary: true,
              cell: (item) => (
                <div className="space-y-1">
                  <p className="font-semibold text-foreground">
                    {item.order_reference ?? item.order_id.slice(0, 8)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {item.product_name} · {item.variant_label} × {item.quantity}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Pickup {item.pickup_code}
                    {item.buyer_name ? ` · ${item.buyer_name}` : ""}
                  </p>
                </div>
              ),
            },
            {
              key: "status",
              header: "Status",
              cell: (item) => (
                <div className="flex flex-wrap gap-1.5">
                  <StatusBadge status={item.status} />
                  {item.is_issue ? <StatusBadge status="flagged" /> : null}
                  {item.order_status ? (
                    <StatusBadge status={item.order_status} />
                  ) : null}
                </div>
              ),
            },
            {
              key: "event",
              header: "Event / host",
              cell: (item) => (
                <div className="space-y-1 text-sm text-muted-foreground">
                  <p>{item.event_title ?? "—"}</p>
                  <p>
                    {item.host_name ?? "—"}
                    {item.host_status ? ` (${item.host_status})` : ""}
                  </p>
                </div>
              ),
            },
            {
              key: "when",
              header: "Created",
              cell: (item) => (
                <div className="text-sm text-muted-foreground">
                  <p>{formatDateTime(item.created_at)}</p>
                  {item.fulfilled_at ? (
                    <p>Fulfilled {formatDateTime(item.fulfilled_at)}</p>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      ) : null}
    </DashboardShell>
  );
}
