"use client";

import { useEffect, useState } from "react";

import { HostAmbassadorsNav } from "@/components/ambassadors/HostAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { fetchHostPlatformAttributedSales } from "@/lib/promos-api";

type Row = {
  order_reference?: string | null;
  event_title?: string | null;
  product_type: string;
  gross_attributed_sale: string;
  attribution_badge: string;
  commission_funded_by: string;
  host_proceeds_note: string;
};

export default function HostPlatformAttributedSalesPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchHostPlatformAttributedSales();
        if (active) setRows(data);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Could not load platform-attributed sales",
          );
          setRows([]);
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
      eyebrow="Host · Ambassadors"
      title="Platform-attributed sales"
      description="Read-only. These sales used a Pàdéyá platform referral. Commission is funded by Pàdéyá and is not deducted from your settlement."
    >
      <HostAmbassadorsNav />
      {error ? <Alert tone="danger" title="Error">{error}</Alert> : null}
      {rows === null ? <SkeletonLoader lines={4} /> : null}
      {rows && rows.length === 0 ? (
        <EmptyState
          title="No platform referrals yet"
          description="When a platform ambassador drives a sale on your event, it appears here without reducing your host proceeds."
        />
      ) : null}
      {rows && rows.length > 0 ? (
        <div className="space-y-3">
          {rows.map((row, idx) => (
            <Card key={`${row.order_reference}-${idx}`} className="space-y-2 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="success">{row.attribution_badge}</Badge>
                <Badge tone="outline">Commission funded by Pàdéyá</Badge>
              </div>
              <p className="text-sm">
                Order {row.order_reference || "—"} · {row.event_title || "Event"} ·{" "}
                {row.product_type}
              </p>
              <p className="font-semibold">
                Gross attributed sale: {formatNgn(Number(row.gross_attributed_sale))}
              </p>
              <p className="text-sm text-muted-foreground">{row.host_proceeds_note}</p>
            </Card>
          ))}
        </div>
      ) : null}
    </DashboardShell>
  );
}
