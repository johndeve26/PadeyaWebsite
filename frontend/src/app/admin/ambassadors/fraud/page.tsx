"use client";

import { useEffect, useState } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import {
  fetchAdminFraudFlags,
  type DomainFraudFlag,
} from "@/lib/ambassadors-api";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { fetchAdminConversions } from "@/lib/promos-api";
import type { AmbassadorConversionAdmin } from "@/lib/types/promos";

/**
 * Fraud flags: click spikes + reversed conversions.
 * Approve/reverse actions remain on Conversions.
 */
export default function AdminAmbassadorFraudPage() {
  const [flags, setFlags] = useState<DomainFraudFlag[] | null>(null);
  const [reversed, setReversed] = useState<AmbassadorConversionAdmin[] | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [spikeFlags, reversedRows] = await Promise.all([
          fetchAdminFraudFlags({ status: "open" }).catch(() => []),
          fetchAdminConversions({ status: "reversed" }),
        ]);
        if (active) {
          setFlags(spikeFlags);
          setReversed(reversedRows);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load fraud flags",
          );
          setFlags([]);
          setReversed([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const loading = flags === null || reversed === null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Ambassadors"
      title="Fraud flags"
                description="Suspicious click volume (spikes, low unique ratio) and reversed conversions. Investigate here; take approve/reverse actions on Conversions."
    >
      <AdminAmbassadorsNav />
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {loading ? <SkeletonLoader lines={4} /> : null}

      {!loading ? (
        <div className="space-y-8">
          <section className="space-y-3">
            <h2 className="text-lg font-bold">Click spikes</h2>
            {flags.length === 0 ? (
              <EmptyState
                title="No open click spikes"
                description="Suspicious click volume flags appear when a hashed IP exceeds the threshold or total clicks far exceed unique visitors."
              />
            ) : (
              flags.map((flag) => (
                <Card key={flag.id} className="space-y-2 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-foreground">
                        {flag.flag_type} · code{" "}
                        <span className="font-mono text-sm">
                          {flag.ambassador_code || "—"}
                        </span>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {flag.click_count} clicks in window · ip_hash{" "}
                        <span className="font-mono text-xs">
                          {(flag.ip_hash || "").slice(0, 12)}…
                        </span>
                      </p>
                    </div>
                    <Badge tone="warning">{flag.status}</Badge>
                  </div>
                </Card>
              ))
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold">Reversed conversions</h2>
            {reversed.length === 0 ? (
              <EmptyState
                title="No reversed conversions"
                description="Refunds, ticket cancels, and admin reverses appear here."
              />
            ) : (
              reversed.map((row) => (
                <Card key={row.id} className="space-y-2 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-foreground">
                        {row.ambassador_display_name || "Ambassador"}{" "}
                        <span className="font-mono text-sm text-muted-foreground">
                          {row.ambassador_referral_code}
                        </span>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {row.event_title || row.event_id} · {row.tickets_sold}{" "}
                        tickets · {formatNgn(Number(row.revenue_amount))} ·
                        commission {formatNgn(Number(row.commission_owed))}
                      </p>
                      {row.reversal_reason ? (
                        <p className="mt-1 text-sm text-danger-foreground">
                          Flag reason: {row.reversal_reason}
                        </p>
                      ) : null}
                    </div>
                    <Badge tone="warning">{row.status}</Badge>
                  </div>
                </Card>
              ))
            )}
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}
