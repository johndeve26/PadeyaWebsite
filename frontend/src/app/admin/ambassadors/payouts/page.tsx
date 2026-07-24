"use client";

import { useEffect, useState } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  fetchAdminConversions,
  fetchAdminAmbassadorReports,
  setAdminConversionRewardStatus,
} from "@/lib/promos-api";
import type {
  AmbassadorConversionAdmin,
  AmbassadorReportsSummary,
} from "@/lib/types/promos";

export default function AdminAmbassadorPayoutsPage() {
  const [summary, setSummary] = useState<AmbassadorReportsSummary | null>(null);
  const [payable, setPayable] = useState<AmbassadorConversionAdmin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const [report, approved] = await Promise.all([
      fetchAdminAmbassadorReports(),
      fetchAdminConversions({ status: "approved" }),
    ]);
    setSummary(report);
    setPayable(approved);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load payouts");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function markPaid(id: string) {
    if (!window.confirm("Mark this Ambassador reward as paid?")) return;
    setBusy(true);
    setError(null);
    try {
      await setAdminConversionRewardStatus(id, "paid");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Mark paid failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Ambassadors"
      title="Payouts & rewards"
      description="Manage Ambassador reward status. Approve on Conversions, then mark paid here. Full payout rails with evidence ship later."
    >
      <AdminAmbassadorsNav />
      {error ? <Alert tone="danger" title="Something went wrong">{error}</Alert> : null}

      {!summary ? (
        <SkeletonLoader lines={3} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Estimated"
              value={formatNgn(Number(summary.estimated_earnings))}
            />
            <StatCard title="Approved"
              value={formatNgn(Number(summary.approved_earnings))}
            />
            <StatCard title="Payable"
              value={formatNgn(Number(summary.payable_earnings))}
            />
            <StatCard title="Paid"
              value={formatNgn(Number(summary.paid_earnings))}
            />
          </div>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">
              Payable rewards
            </h2>
            {payable.length === 0 ? (
              <EmptyState
                title="Nothing payable"
                description="Approved conversions ready for payout appear here."
              />
            ) : (
              payable.map((row) => (
                <Card
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 p-4"
                >
                  <div>
                    <p className="font-semibold text-foreground">
                      {row.ambassador_display_name} ·{" "}
                      {formatNgn(Number(row.commission_owed))}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {row.event_title} · {row.ambassador_referral_code}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone="accent">approved</Badge>
                    <Button disabled={busy} onClick={() => void markPaid(row.id)}>
                      Mark paid
                    </Button>
                  </div>
                </Card>
              ))
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}
