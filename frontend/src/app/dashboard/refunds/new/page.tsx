"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyOrders } from "@/lib/commerce-api";
import { createRefundRequest } from "@/lib/finance-api";
import { formatNgn } from "@/lib/format";
import type { Order } from "@/lib/types/commerce";

export default function NewRefundPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [orderId, setOrderId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchMyOrders()
      .then((rows) => {
        if (active) {
          setOrders(rows.filter((o) => o.status === "paid"));
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load orders");
        }
      })
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const selected = useMemo(
    () => orders.find((o) => o.id === orderId) ?? null,
    [orders, orderId],
  );

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createRefundRequest({ order_id: orderId, reason });
      router.push("/dashboard/refunds");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create refund request");
      setSubmitting(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Refunds"
      title="Request a refund"
      description="Subject to the event refund policy. Full refunds only — tickets become invalid if approved."
      actions={
        <Link href="/dashboard/refunds">
          <Button variant="secondary">Back</Button>
        </Link>
      }
    >
      <Alert tone="info" title="Full refund only">
        Partial refunds are not available yet. If approved, related tickets stop
        validating at the door.
      </Alert>

      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {loaded && orders.length === 0 ? (
        <EmptyState
          title="No paid orders to refund"
          description="Refunds can only be requested for paid orders."
          action={
            <Link href="/dashboard/orders">
              <Button variant="secondary">View orders</Button>
            </Link>
          }
        />
      ) : (
        <Card className="max-w-xl space-y-5 shadow-[var(--shadow-soft)]">
          <form className="space-y-4" onSubmit={onSubmit}>
            <Select
              label="Paid order"
              hint="Only paid orders are eligible for refund requests"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              required
            >
              <option value="">Select order</option>
              {orders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.event_title || o.reference} · {formatNgn(o.total_amount)}
                </option>
              ))}
            </Select>

            {selected ? (
              <div className="rounded-[var(--radius-md)] border border-border bg-surface-inset px-4 py-3 text-sm">
                <p className="font-bold text-foreground">
                  {selected.event_title ?? "Order"}
                </p>
                <p className="mt-1 text-muted-foreground">
                  {selected.reference} · {formatNgn(selected.total_amount)} ·{" "}
                  {selected.items.reduce((n, i) => n + i.quantity, 0)} ticket(s)
                </p>
              </div>
            ) : null}

            <Textarea
              label="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              minLength={5}
              hint="Be clear — support uses this during review."
            />
            <Button type="submit" size="lg" disabled={submitting || !orderId}>
              {submitting ? "Submitting…" : "Submit request"}
            </Button>
          </form>
        </Card>
      )}
    </DashboardShell>
  );
}
