"use client";

import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  DataTable,
  FilterBar,
  SearchBar,
  Select,
  SkeletonLoader,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import { fetchAdminOrders } from "@/lib/commerce-api";
import { formatDate, formatNgn } from "@/lib/format";
import type { Order } from "@/lib/types/commerce";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "paid", label: "Paid" },
  { value: "cancelled", label: "Cancelled" },
  { value: "refunded", label: "Refunded" },
];

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchAdminOrders();
        if (active) setOrders(items);
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load orders");
          setOrders([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const counts = useMemo(
    () => ({
      total: orders?.length ?? 0,
      paid: orders?.filter((o) => o.status === "paid").length ?? 0,
      pending: orders?.filter((o) => o.status === "pending").length ?? 0,
    }),
    [orders],
  );

  const filtered = useMemo(() => {
    if (!orders) return [];
    const q = search.trim().toLowerCase();
    return orders.filter((order) => {
      if (statusFilter !== "all" && order.status !== statusFilter) return false;
      if (!q) return true;
      return (
        order.reference.toLowerCase().includes(q) ||
        order.buyer_email.toLowerCase().includes(q) ||
        (order.event_title ?? "").toLowerCase().includes(q) ||
        order.buyer_name.toLowerCase().includes(q)
      );
    });
  }, [orders, statusFilter, search]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Orders"
      description="Lookup buyer orders and payment status."
    >
      {error ? (
        <Alert tone="danger" title="Could not load orders">
          {error}
        </Alert>
      ) : null}

      {orders ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard title="Total orders" value={counts.total} />
            <StatCard title="Paid" value={counts.paid} />
            <StatCard title="Pending" value={counts.pending} />
          </div>

          <FilterBar>
            <Select
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <SearchBar
              placeholder="Reference, buyer, or event…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </FilterBar>

          <DataTable
        rows={filtered}
        rowKey={(order) => order.id}
        emptyTitle="No orders found"
        emptyDescription={
          search || statusFilter !== "all"
            ? "Try adjusting your search or status filter."
            : "Orders will appear here once buyers checkout."
        }
        columns={[
          {
            key: "event",
            header: "Event",
            primary: true,
            cell: (order) => (
              <span className="font-bold text-foreground">
                {order.event_title ?? "Event order"}
              </span>
            ),
          },
          {
            key: "reference",
            header: "Reference",
            cell: (order) => (
              <span className="font-mono text-sm">{order.reference}</span>
            ),
          },
          {
            key: "buyer",
            header: "Buyer",
            cell: (order) => (
              <div className="min-w-0">
                <p className="font-semibold">{order.buyer_name}</p>
                <p className="text-sm text-muted-foreground">{order.buyer_email}</p>
              </div>
            ),
          },
          {
            key: "date",
            header: "Date",
            cell: (order) => formatDate(order.paid_at ?? order.created_at),
          },
          {
            key: "total",
            header: "Total",
            cell: (order) => (
              <span className="font-bold tabular-nums">
                {formatNgn(order.total_amount)}
              </span>
            ),
          },
          {
            key: "status",
            header: "Status",
            cell: (order) => <StatusBadge status={order.status} />,
          },
        ]}
          />
        </>
      ) : null}

      {orders == null && !error ? <SkeletonLoader lines={4} /> : null}
    </DashboardShell>
  );
}
