"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { EventOpsNav } from "@/components/host/EventOpsNav";
import { EventMerchSubnav } from "@/components/merch/host/EventMerchSubnav";
import { HostMerchFulfillmentQueue } from "@/components/merch/host/HostMerchFulfillmentQueue";
import { HostMerchPickupDesk } from "@/components/merch/host/HostMerchPickupDesk";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchHostMerchFulfillments } from "@/lib/merch-api";
import type { MerchFulfillment } from "@/lib/types/merch";

export default function EventMerchandiseFulfillmentPage() {
  const params = useParams<{ id: string }>();
  const [rows, setRows] = useState<MerchFulfillment[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const items = await fetchHostMerchFulfillments(params.id);
    setRows(items);
  }, [params.id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchHostMerchFulfillments(params.id);
        if (active) {
          setRows(items);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Failed to load fulfillment queue",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Fulfillment desk"
        description="Scan merch pickup QR (padeya.merch.pickup) or look up MRCH codes — never ticket QR. Collection is once; staff and timestamp are recorded."
        actions={
          <Link href={`/host/events/${params.id}/merchandise`}>
            <Button size="sm" variant="secondary">
              Studio home
            </Button>
          </Link>
        }
      >
        <EventOpsNav eventId={params.id} />
        <EventMerchSubnav eventId={params.id} />
        {error ? (
          <Alert tone="danger" title="Could not load queue">
            {error}
          </Alert>
        ) : null}
        <Card className="space-y-4">
          <HostMerchPickupDesk eventId={params.id} onPickedUp={load} />
        </Card>
        <Card className="space-y-4">
          {rows === null ? (
            <SkeletonLoader lines={4} />
          ) : (
            <HostMerchFulfillmentQueue
              rows={rows}
              onChanged={load}
              emptyTitle="No fulfillments yet"
              emptyDescription="Paid merch pickups appear here. Use search and status filters to run the desk."
            />
          )}
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
