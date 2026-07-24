"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  EmptyState,
  RefundCard,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyRefunds } from "@/lib/finance-api";
import type { RefundRequest } from "@/lib/types/finance";

export default function MyRefundsPage() {
  const [rows, setRows] = useState<RefundRequest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchMyRefunds();
        if (active) setRows(items);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load refunds");
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Refunds"
      title="My refund requests"
      description="Full refunds only for now. Partial refunds are not available yet. Approved refunds invalidate related tickets."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/refunds/new">
            <Button>Request refund</Button>
          </Link>
          <Link href="/dashboard/orders">
            <Button variant="secondary">My orders</Button>
          </Link>
        </div>
      }
    >
      <Alert tone="info" title="How refunds work">
        Requests are reviewed against the event policy. You’ll see status updates here
        — support may escalate complex cases.
      </Alert>

      {error ? (
        <Alert tone="danger" title="Could not load refunds">
          {error}
        </Alert>
      ) : null}

      {!loaded && !error ? <SkeletonLoader lines={3} /> : null}

      <div className="space-y-3">
        {loaded
          ? rows.map((r) => <RefundCard key={r.id} refund={r} />)
          : null}
        {loaded && rows.length === 0 && !error ? (
          <EmptyState
            title="No refund requests yet"
            description="If something goes wrong with an order, you can request a full refund here."
            action={
              <Link href="/dashboard/refunds/new">
                <Button>Request refund</Button>
              </Link>
            }
          />
        ) : null}
      </div>
    </DashboardShell>
  );
}
