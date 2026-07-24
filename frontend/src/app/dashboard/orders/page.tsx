"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  DataTable,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { fetchMyOrders } from "@/lib/commerce-api";
import { formatDate, formatNgn } from "@/lib/format";
import type { Order } from "@/lib/types/commerce";

export default function MyOrdersPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchMyOrders();
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

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Orders"
      title="Your orders"
      description="Receipts and payment status for every purchase on Pàdéyá."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/merchandise">
            <Button variant="secondary" size="sm">
              Merch
            </Button>
          </Link>
          <Link href="/events">
            <Button variant="secondary" size="sm">
              Browse events
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load orders">
          {error}
        </Alert>
      ) : null}

      {orders === null ? (
        <SkeletonLoader lines={5} />
      ) : orders.length === 0 ? (
        <EmptyState
          title="No orders yet"
          description="Confirmed purchases and receipts will show up here."
          action={
            <Link href="/events">
              <Button size="lg">Browse events</Button>
            </Link>
          }
        />
      ) : (
        <DataTable
          rows={orders}
          rowKey={(order) => order.id}
          emptyTitle="No orders yet"
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
              key: "date",
              header: "Date",
              cell: (order) =>
                formatDate(order.paid_at ?? order.created_at),
            },
            {
              key: "items",
              header: "Items",
              cell: (order) => {
                const ticketQty = order.items
                  .filter(
                    (i) =>
                      (i.item_kind || "ticket") !== "merch" &&
                      !i.merch_variant_id,
                  )
                  .reduce((n, i) => n + i.quantity, 0);
                const merchQty = order.items
                  .filter(
                    (i) =>
                      i.item_kind === "merch" || Boolean(i.merch_variant_id),
                  )
                  .reduce((n, i) => n + i.quantity, 0);
                const parts = [
                  ticketQty ? `${ticketQty} ticket(s)` : null,
                  merchQty ? `${merchQty} merch` : null,
                ].filter(Boolean);
                return parts.join(" · ") || "—";
              },
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
            {
              key: "action",
              header: "",
              cell: (order) => (
                <Link href={`/dashboard/orders/${order.id}`}>
                  <Button size="sm" variant="secondary">
                    Receipt
                  </Button>
                </Link>
              ),
            },
          ]}
        />
      )}
    </DashboardShell>
  );
}
